#!/usr/bin/env python3
"""Regenerate everything, in the one order that produces a correct panel.

Three steps depend on each other:

1. `nx_source.py` lays the pages out and decides how wide each field must be.
2. `find_baked.py` reads those boxes and measures which ones sit over a sample
   value the design drew.
3. `clean_pictures.py` erases those sample values from the pictures.

Run out of order, a field widened in step 1 leaves sample text beside it that step
3 already passed. So the whole thing runs twice: the first pass establishes the
boxes, the second cleans against the boxes the final build will use.
"""

import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
PYTHON = sys.executable


def run(script: str) -> str:
    result = subprocess.run([PYTHON, str(TOOLS / script)], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"{script} failed:\n{result.stdout[-2000:]}{result.stderr[-2000:]}")
    return result.stdout.strip()


def main() -> int:
    run("nx_source.py")
    run("find_baked.py")
    run("clean_pictures.py")

    # Again, now that the boxes are final and the pictures are clean.
    layout = run("nx_source.py")
    baked = run("find_baked.py")
    cleaned = run("clean_pictures.py")

    print(layout.splitlines()[-1])
    print(baked.splitlines()[-1])
    print(cleaned.splitlines()[-2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
