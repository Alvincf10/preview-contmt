"""Build and run the firmware's own test suite on Windows, targeting Linux.

The host code uses POSIX calls (pread, pwrite, fsync), so it does not build for
Windows. zig ships a C++ compiler that can target Linux, and WSL runs the result,
which is what lets the firmware's tests run here at all.

Usage:
    python firmware/tools/host_tests.py            # build and run every test
    python firmware/tools/host_tests.py tests      # one test binary
"""

import glob
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _linux(path: Path) -> str:
    """The WSL path for a Windows path, because the tests run under WSL."""
    text = str(path).replace("\\", "/")
    return "/mnt/" + text[0].lower() + text[2:]

ZIG = Path(sys.executable).parent.parent / "Lib" / "site-packages" / "ziglang" / "zig.exe"
if not ZIG.exists():
    ZIG = Path(r"C:\Users\Alvin\AppData\Local\Programs\Python\Python312\Lib\site-packages\ziglang\zig.exe")

SOURCES = sorted(
    glob.glob(str(ROOT / "ConMT" / "src" / "core" / "*.cpp"))
    + glob.glob(str(ROOT / "ConMT" / "src" / "storage" / "*.cpp"))
    + glob.glob(str(ROOT / "ConMT" / "src" / "app" / "*.cpp"))
    + glob.glob(str(ROOT / "ConMT" / "src" / "hmi" / "*.cpp"))
) + [str(ROOT / "host" / "HostPorts.cpp")]

TESTS = {
    "tests": [],
    "workflow": [],
    "audit": [],
    "session_edges": [],
    "record_codec": [],
    "disk_index": [],
    "math_cases": [],
    "battery": [],
    "real_codec": [],
    "text": [],
    "hmi_snapshot": ['-DCONMT_HMI_FIXTURE="' + _linux(ROOT / "tests" / "fixtures" / "hmi-wire.txt") + '"'],
    "reference_workflow": ['-DCONMT_FIXTURE_PATH="' + _linux(ROOT / "tests" / "fixtures" / "excel.tsv") + '"'],
    "splash": [],
}


def build(name: str, extra: list[str]) -> Path:
    return build_from(ROOT / "tests" / f"{name}.cpp", extra, name)


def build_from(source: Path, extra: list[str], name: str | None = None) -> Path:
    out = Path(os.environ["TEMP"]) / f"conmt_{name or source.stem}"
    command = [
        str(ZIG), "c++", "-target", "x86_64-linux-gnu", "-std=c++11",
        # glibc declares `finite` as a macro alias, and ConMT has a function of
        # the same name. This keeps glibc's declaration out of the way.
        "-D__MATHCALL_ALIAS(name,args,proto)=int name proto",
        "-I", str(ROOT / "ConMT" / "src"), "-I", str(ROOT / "host"),
        *extra,
        "-o", str(out),
        str(source),
        *SOURCES,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"{name or source.stem} did not build:\n{result.stderr[:2000]}")
    return out


def run(binary: Path, args: list[str] | None = None) -> tuple[int, str]:
    # Run under WSL, which is where a Linux binary runs.
    windows_path = str(binary).replace("\\", "/")
    linux_path = "/mnt/" + windows_path[0].lower() + windows_path[2:]
    command = ["wsl", "bash", "-lc", f"cd /mnt/d/coding/preview-contmt/firmware && {linux_path} " + " ".join(args or [])]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    return result.returncode, (result.stdout + result.stderr)


def main() -> int:
    wanted = sys.argv[1:] or list(TESTS)
    failed = 0
    for name in wanted:
        if name not in TESTS:
            print(f"unknown test {name}; known: {', '.join(TESTS)}")
            failed += 1
            continue
        try:
            binary = build(name, TESTS[name])
        except SystemExit as error:
            print(f"FAIL {name}: {error}")
            failed += 1
            continue
        code, output = run(binary)
        status = "PASS" if code == 0 else "FAIL"
        first = [line for line in output.strip().splitlines() if line.strip()][-1:] or [""]
        print(f"{status} {name:22} {first[0][:100]}")
        if code != 0:
            failed += 1
            print(output[:1500])
    print(f"\n{len(wanted) - failed}/{len(wanted)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
