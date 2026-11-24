"""Check the panel's navigation against the design, on the two things that matter.

1. **Coverage** — every button the picture draws has a tap area on top of it.
   A painted button with nothing over it is a dead button.
2. **The BACK chain** — the panel sends `NAV|BACK`, and the firmware's own table
   decides which page that is. So the table is what must match the design, not
   the event.

Forward navigation (NEXT, SAVE, START, GENERATE) works differently: the panel
sends the verb, and the firmware moves the page once the action succeeds. Those
are checked by their verb, not by a page number.
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAV = json.loads((ROOT / "nextion" / "tools" / "nav.json").read_text(encoding="utf-8"))
PAGES_DIR = ROOT / "nextion" / "nxsrc" / "pages"
EVENTS = ROOT / "firmware" / "hmi" / "events"
CONTROLLER = ROOT / "firmware" / "ConMT" / "src" / "app" / "Controller.cpp"

PAGES = [
    "pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR",
    "pSaveB", "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev",
]
SCREEN_PAGE = {
    "splash": "pInit", "userInfo": "pUser", "main": "pMain", "baselineMenu": "pBase",
    "newBaseline": "pNewB", "materialData": "pMat", "maturityData": "pMatu",
    "baselineResult": "pBaseR", "savedBaseline": "pSaveB", "kuatTekanMenu": "pKuat",
    "selectBaseline": "pSelB", "realtime": "pRT", "strengthResult": "pStr",
    "history": "pHist", "historyDetail": "pHistD", "settings": "pSet", "deviceInfo": "pDev",
}

# The picture's own furniture: the brand strip, the status corners, the badge.
FURNITURE = ("size-badge", "back-chip")


def hotspots(page: str) -> list[dict]:
    data = tomllib.loads((PAGES_DIR / f"{page}.page.toml").read_text(encoding="utf-8"))
    return [c for c in data.get("component", []) if c.get("type") == "hotspot"]


def overlaps(a: dict, b: dict) -> bool:
    return (
        a["x"] < b["x"] + b["w"]
        and b["x"] < a["x"] + a["w"]
        and a["y"] < b["y"] + b["h"]
        and b["y"] < a["y"] + a["h"]
    )


def main() -> int:
    problems = 0
    covered = 0
    total = 0

    # 1. Coverage: every drawn button has a tap area over it.
    for screen, page in SCREEN_PAGE.items():
        taps = hotspots(page)
        for entry in NAV.get(page, []):
            if not entry.get("to"):
                continue
            if any(f in entry.get("cls", "") for f in FURNITURE):
                continue
            total += 1
            if any(overlaps(tap, entry) for tap in taps):
                covered += 1
            else:
                name = (entry.get("text") or entry.get("cls", "?"))[:28]
                print(f"  {page}: the button {name!r} has no tap area on it")
                problems += 1

    # 2. Every tap area actually sends something.
    dead = [
        f"{page}.{tap['name']}"
        for page in PAGES
        for tap in hotspots(page)
        if not (EVENTS / f"{page}_{tap['name']}.txt").exists()
    ]
    for name in dead:
        print(f"  {name}: no event, so tapping it does nothing")
    problems += len(dead)

    # 3. The BACK chain the firmware walks must be the design's own chain.
    text = CONTROLLER.read_text(encoding="utf-8")
    match = re.search(r"static const uint8_t back\[\]\s*CM_ROM=\{([^}]*)\}", text)
    if not match:
        print("  could not find the firmware's back table")
        problems += 1
    else:
        table = [int(v) for v in match.group(1).split(",") if v.strip()]
        for page in PAGES:
            design_back = next((e["to"] for e in NAV.get(page, []) if e.get("text", "").strip().upper().startswith("BACK")), None)
            if not design_back:
                continue
            want = SCREEN_PAGE.get(design_back)
            got = PAGES[table[PAGES.index(page)]] if PAGES.index(page) < len(table) else "?"
            if got != want:
                print(f"  {page}: BACK goes to {got} on the panel, {want} in the design")
                problems += 1

    print(f"\n{covered}/{total} drawn buttons have a tap area")
    print(f"{len(dead)} tap area(s) without an event")
    print(f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
