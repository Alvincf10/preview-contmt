"""Build the ConMT Arduino sketch and export an Intel HEX for ATmega328P."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from avr_outline import outline


FLASH_LIMIT = 32256  # Arduino AVR Uno profile
SRAM_LIMIT = 1280   # Reserve space for the call stack and interrupt service.
MCU = "atmega328p"
FLOAT_FLAGS = "-mdouble=32 -mlong-double=32"
CLI_FLAGS = (
    f"-Oz {FLOAT_FLAGS} -mrelax -mcall-prologues "
    "-fno-inline-functions-called-once -fno-tree-scev-cprop -fipa-pta "
    "-ftree-loop-optimize -fno-tree-loop-im -fno-tree-dominator-opts -flto-partition=one "
    "-fmerge-all-constants -g0"
)


def command(*args, **kwargs):
    return subprocess.run([str(arg) for arg in args], text=True, check=True, **kwargs)


def find_cli():
    installed = shutil.which("arduino-cli")
    if installed:
        return Path(installed)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        ide = Path(local) / "Programs" / "Arduino IDE"
        cli = ide / "resources" / "app" / "lib" / "backend" / "resources" / "arduino-cli.exe"
        if cli.is_file():
            return cli
    raise RuntimeError("Pass --arduino-cli with the path to Arduino CLI.")


def compiler_tools(binary_dir):
    suffix = ".exe" if os.name == "nt" else ""
    gcc, size, objcopy = (binary_dir / (name + suffix) for name in ("avr-gcc", "avr-size", "avr-objcopy"))
    version = command(gcc, "--version", capture_output=True).stdout.splitlines()[0]
    if not re.search(r"\b16\.[12]\.0\b", version):
        raise RuntimeError("This build uses AVR GCC 16.1.0 or 16.2.0 and its final LTO assembly format.")
    return gcc, size, objcopy


def compile_arduino(cli, config, binary_dir, sketch, work):
    build = work / "arduino"
    args = [cli, "compile", "--profile", "conmt328p", "--build-path", build]
    if config:
        args += ["--config-file", config]
    properties = {
        "compiler.path": binary_dir.as_posix() + "/",
        "compiler.c.extra_flags": CLI_FLAGS,
        "compiler.cpp.extra_flags": CLI_FLAGS,
        "compiler.S.extra_flags": FLOAT_FLAGS,
        # This intermediate link exists only to capture GCC's final assembly.
        "compiler.c.elf.extra_flags": f"{CLI_FLAGS} -save-temps=obj -Wl,--defsym=__TEXT_REGION_LENGTH__=65536",
    }
    for name, value in properties.items():
        args += ["--build-property", f"{name}={value}"]
    result = subprocess.run([str(arg) for arg in args] + [str(sketch)], cwd=work,
                            text=True, capture_output=True)
    output = result.stdout + result.stderr
    if result.returncode and ("Sketch uses " not in output or "text section exceeds" not in output):
        raise RuntimeError(output.strip())
    print(next(line for line in output.splitlines() if line.startswith("Sketch uses ")))
    sources = list(build.glob("*.ltrans.s"))
    if len(sources) != 1:
        raise RuntimeError("Arduino build must produce one final LTO assembly file.")
    return sources[0]


def link_compact(gcc, size, source, work):
    assembly = source.read_text(encoding="utf-8")
    for step in range(1, 5):
        assembly, shared = outline(assembly, step)
        print(f"AVR instruction sharing pass {step}: {shared} repeated sequences")
        if not shared:
            break
    compact = work / "ConMT.s"
    compact.write_text(assembly, encoding="utf-8")
    elf = work / "ConMT.elf"
    command(gcc, f"-mmcu={MCU}", *FLOAT_FLAGS.split(), "-mrelax", "-Wl,--gc-sections",
            "-o", elf, compact, "-lm", cwd=work)
    sections = command(size, "-A", elf, capture_output=True).stdout
    counts = {name: int(value) for name, value in re.findall(r"^(\.\w+)\s+(\d+)", sections, re.M)}
    flash = counts[".text"] + counts.get(".data", 0)
    sram = counts.get(".data", 0) + counts.get(".bss", 0) + counts.get(".noinit", 0)
    print(f"ATmega328P: {flash} / {FLASH_LIMIT} bytes flash, {sram} bytes static SRAM")
    if flash > FLASH_LIMIT or sram > SRAM_LIMIT:
        raise RuntimeError("ConMT build exceeds its flash or static SRAM budget.")
    return elf


def build(args, work):
    binary_dir = args.avr_bin.resolve()
    cli = args.arduino_cli.resolve() if args.arduino_cli else find_cli()
    gcc, size, objcopy = compiler_tools(binary_dir)
    source = compile_arduino(cli, args.config, binary_dir, Path(__file__).resolve().parent / "ConMT", work)
    elf = link_compact(gcc, size, source, work)
    hex_file = work / "ConMT.hex"
    command(objcopy, "-O", "ihex", "-j", ".text", "-j", ".data", elf, hex_file)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(hex_file, output)
    print(f"HEX: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--avr-bin", type=Path, required=True, help="AVR GCC 16.1.0 or 16.2.0 bin directory")
    parser.add_argument("--output", type=Path, required=True, help="Intel HEX output")
    parser.add_argument("--arduino-cli", type=Path)
    parser.add_argument("--config", type=Path, help="Optional Arduino CLI configuration")
    parser.add_argument("--work-dir", type=Path, help="Keep an empty build directory for inspection")
    args = parser.parse_args()
    if args.config:
        args.config = args.config.resolve()
    if args.work_dir:
        work = args.work_dir.resolve()
        work.mkdir(parents=True, exist_ok=False)
        build(args, work)
    else:
        with tempfile.TemporaryDirectory(prefix="conmt-avr-") as temp:
            build(args, Path(temp))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as failure:
        raise SystemExit(str(failure)) from failure
