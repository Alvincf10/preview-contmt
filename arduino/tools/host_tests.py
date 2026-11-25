#!/usr/bin/env python3
"""Build and run the Arduino sketch's own tests on this machine.

The sketch is written for an AVR, but its test file supplies a stand-in board, so
the whole thing compiles and runs on the host. That matters here: the tests print
the exact `tData` the firmware sends, which is the ground truth for how the panel
must split it.

The build targets Linux with zig and runs the result under WSL, the same way the
C++ firmware's tests are run, because the source uses POSIX calls.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIG = Path(r"C:\Users\Alvin\AppData\Local\Programs\Python\Python312\Lib\site-packages\ziglang\zig.exe")

SOURCES = [
    path
    for path in sorted(glob.glob(str(ROOT / "ConMT" / "src" / "*.cpp")))
    # The test file supplies its own `namespace board`, so the real one, which
    # needs Arduino.h, must not be compiled in.
    if not path.endswith(("Board.cpp", "SpiCard.cpp", "SdStore.cpp"))
]


def linux_path(path: Path | str) -> str:
    text = str(path).replace("\\", "/")
    return "/mnt/" + text[0].lower() + text[2:]


def main() -> int:
    out = Path(os.environ["TEMP"]) / "conmt_arduino_test"
    command = [
        str(ZIG), "c++", "-target", "x86_64-linux-gnu", "-std=c++17",
        "-D__NO_MATH_INLINES",
        "-I", str(ROOT / "ConMT" / "src"),
        "-o", str(out),
        str(ROOT / "tests" / "ConMTTest.cpp"),
        *SOURCES,
    ]
    build = subprocess.run(command, capture_output=True, text=True)
    if build.returncode != 0:
        print("the Arduino tests did not build:")
        print(build.stderr[:3000])
        return 1

    result = subprocess.run(
        ["wsl", "bash", "-lc", f"cd {linux_path(ROOT)} && {linux_path(out)}"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    print(result.stdout[-6000:])
    if result.returncode != 0:
        print(result.stderr[-4000:])
    print(f"\nexit {result.returncode}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
