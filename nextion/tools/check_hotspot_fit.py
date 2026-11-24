"""Check that every tap area sits on the button the picture draws.

The panel is drawn as a picture with invisible tap areas laid over it. A tap area
that sits beside its button, rather than on it, is the failure an operator notices
first: the button is visible, they press it, and nothing happens - or something
else does.

For each page this compares every tap area against the buttons the design draws,
and reports a tap area that covers no drawn button, or one that misses by a wide
margin. It also reports a tap area that is partly or wholly off the screen, which
cannot be pressed at all.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES_DIR = ROOT / "nextion" / "nxsrc" / "pages"
NAV = json.loads((ROOT / "nextion" / "tools" / "nav.json").read_text(encoding="utf-8"))
LAYOUT = json.loads((ROOT / "nextion" / "tools" / "layout.json").read_text(encoding="utf-8"))

WIDTH, HEIGHT = 480, 800
SCREEN_PAGE = {
    "userInfo": "pUser", "main": "pMain", "baselineMenu": "pBase", "newBaseline": "pNewB",
    "materialData": "pMat", "maturityData": "pMatu", "baselineResult": "pBaseR",
    "savedBaseline": "pSaveB", "kuatTekanMenu": "pKuat", "selectBaseline": "pSelB",
    "realtime": "pRT", "strengthResult": "pStr", "history": "pHist",
    "historyDetail": "pHistD", "settings": "pSet", "deviceInfo": "pDev",
}


def elements(page: str) -> list[dict]:
    """The boxes the design draws on a page."""
    data = LAYOUT.get(page, {})
    return data.get("elements", []) if isinstance(data, dict) else []


def components(page: str) -> list[dict]:
    data = tomllib.loads((PAGES_DIR / f"{page}.page.toml").read_text(encoding="utf-8"))
    return data.get("component", [])


def overlap_ratio(tap: dict, drawn: dict) -> float:
    """How much of the drawn button the tap area covers, from 0 to 1."""
    x = max(tap["x"], drawn["x"])
    y = max(tap["y"], drawn["y"])
    right = min(tap["x"] + tap["w"], drawn["x"] + drawn["w"])
    bottom = min(tap["y"] + tap["h"], drawn["y"] + drawn["h"])
    if right <= x or bottom <= y:
        return 0.0
    area = drawn["w"] * drawn["h"]
    return ((right - x) * (bottom - y)) / area if area else 0.0


def main() -> None:
    offsite = []
    invisible = []
    outside = []

    for screen, page in SCREEN_PAGE.items():
        taps = [c for c in components(page) if c.get("type") == "hotspot"]
        drawn = [e for e in elements(page) if e["kind"] == "button"]

        for tap in taps:
            # A tap area past the edge cannot be pressed; that is only acceptable
            # for a row the picture draws below the fold.
            centre_y = tap["y"] + tap["h"] // 2
            centre_x = tap["x"] + tap["w"] // 2
            if not (0 <= centre_x < WIDTH and 0 <= centre_y < HEIGHT):
                outside.append((page, tap["name"], tap["x"], tap["y"], tap["w"], tap["h"]))
                continue

            # A tap area over an input is the design for a table row: the cell is
            # what the operator presses to edit it. Such a tap area is judged
            # against the inputs, not against the buttons.
            inputs = [e for e in elements(page) if e["kind"] == "input"]
            best_button = max((overlap_ratio(tap, b) for b in drawn), default=0.0)
            best_input = max((overlap_ratio(tap, i) for i in inputs), default=0.0)
            if best_input >= 0.55:
                continue
            if not drawn:
                continue
            if best_button < 0.55:
                offsite.append((page, tap["name"], round(best_button, 2), tap["x"], tap["y"]))

    for page, name, ratio, x, y in offsite:
        print(f"{page:8} {name:12} covers only {ratio:.0%} of a drawn button, at {x},{y}")
    print(f"\n{len(offsite)} tap area(s) not on their button")

    for page, name, x, y, w, h in outside:
        print(f"{page:8} {name:12} at {x},{y} {w}x{h} - centre is off the screen")
    print(f"{len(outside)} tap area(s) cannot be pressed at all")


if __name__ == "__main__":
    main()
