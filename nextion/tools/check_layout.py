#!/usr/bin/env python3
"""Check that no two fields on a page overlap, and that none leaves the screen.

Two fields drawn over one spot read as a fault on the panel, and a field past
the edge is unreachable. Both are easy to introduce while moving things around,
so this runs as a plain check with no dependencies beyond the standard library.

Run it after editing `nxsrc/pages/`: it prints one line per page and exits
non-zero if anything is wrong, so it can gate a build.

Fields in the reserve are the exception the design makes necessary: a value the
MCU must be able to write, but that the drawn design does not show, sits just
past the right edge so the visible design stays exactly as drawn. They are
counted separately and never read as a fault.
"""
from __future__ import annotations

import itertools
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "nextion" / "nxsrc" / "pages"
WIDTH, HEIGHT = 480, 800

# A hotspot is a transparent tap area, so it is meant to sit on top of the
# field it edits: a hotspot over a text is the design, not a collision.
# A picture is the page itself, and a variable has no place on the screen.
IGNORED_OVERLAP_TYPES = {"picture", "variable", "hotspot"}

# The design draws these pairs on top of each other on purpose: the percentage
# sits inside the strength value, as one reading. They are listed so the check
# stays meaningful for everything else.
DESIGNED_OVERLAYS = {("tFc", "tPct")}

# Anything starting at or past this x is a reserve slot, not a drawn field.
RESERVE_X = 480


def main() -> int:
    problems = 0
    reserves = 0
    for path in sorted(PAGES.glob("*.page.toml")):
        page = tomllib.loads(path.read_text(encoding="utf-8"))
        components = [c for c in page.get("component", []) if "x" in c]
        shown = [c for c in components if c["x"] < RESERVE_X]
        reserved = [c for c in components if c["x"] >= RESERVE_X]
        reserves += len(reserved)

        fields = [c for c in shown if c.get("type") not in IGNORED_OVERLAP_TYPES]

        overlaps = [
            (a["name"], b["name"])
            for a, b in itertools.combinations(fields, 2)
            if a["x"] < b["x"] + b["w"]
            and b["x"] < a["x"] + a["w"]
            and a["y"] < b["y"] + b["h"]
            and b["y"] < a["y"] + a["h"]
            and (a["name"], b["name"]) not in DESIGNED_OVERLAYS
            and (b["name"], a["name"]) not in DESIGNED_OVERLAYS
        ]
        offscreen = [
            c["name"]
            for c in shown
            # A hotspot may sit past the edge: the design scrolls its table, and
            # a row below the fold still needs its tap area for when it scrolls
            # in. A field past the edge is the fault.
            if c.get("type") != "hotspot"
            and (c["x"] < 0 or c["y"] < 0 or c["x"] + c["w"] > WIDTH or c["y"] + c["h"] > HEIGHT)
        ]

        status = "ok" if not overlaps and not offscreen else "FAIL"
        print(
            f"{path.stem:12} fields={len(fields):3} overlaps={len(overlaps):3} "
            f"offscreen={len(offscreen):2} reserve={len(reserved):2} {status}"
        )
        for a, b in overlaps[:5]:
            print(f"    overlap: {a} / {b}")
        for name in offscreen[:5]:
            print(f"    offscreen: {name}")
        problems += len(overlaps) + len(offscreen)

    print(f"\n{problems} problem(s), {reserves} field(s) in the reserve")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
