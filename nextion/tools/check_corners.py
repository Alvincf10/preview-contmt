#!/usr/bin/env python3
"""Check that every page carries the status corners, and that they show something.

Every page shows the clock on the left and the battery on the right. Two things
can go wrong, and both look like "the clock is missing" on the panel:

1. **The field is absent.** The panel then has no place to put the time.
2. **The field is present but empty.** That is correct at build time - the MCU
   fills it - but it also means a page with no MCU connected shows nothing, which
   is exactly what the Editor shows.

So this reports which pages have the fields, and confirms the firmware sends them
on every page rather than only some.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "nextion" / "nxsrc" / "pages"
TRANSPORT = ROOT / "firmware" / "ConMT" / "src" / "hmi" / "Transport.cpp"

PAGES_WITH_CORNERS = [
    "pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR",
    "pSaveB", "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev",
]


def main() -> int:
    problems = 0

    for page in PAGES_WITH_CORNERS:
        path = PAGES / f"{page}.page.toml"
        if not path.exists():
            print(f"{page}: no page file")
            problems += 1
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        fields = {c["name"]: c for c in data.get("component", []) if c.get("type") == "text"}

        for name in ("tClock", "tBatt"):
            if name not in fields:
                print(f"{page}: no {name}, so the panel has nowhere to show it")
                problems += 1
                continue
            field = fields[name]
            # A field on the screen must not paint a background over the picture.
            if field.get("sta") != 3:
                print(f"{page}.{name}: sta={field.get('sta')!r} paints over the design")
                problems += 1

    # The firmware sends both on every page. If that stops, the fields stay empty
    # however many pages carry them.
    source = TRANSPORT.read_text(encoding="utf-8")
    for name in ("tClock", "tBatt"):
        if f'CM_TEXT(component,cc,"{name}")' not in source:
            print(f"the firmware never sends {name}")
            problems += 1

    print(f"\n{len(PAGES_WITH_CORNERS)} page(s) checked, {problems} problem(s)")
    print("Both fields start empty on purpose: the MCU fills them, so the Editor")
    print("shows nothing until a panel is connected.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
