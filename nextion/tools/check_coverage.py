"""How much of each drawn button does its tap area actually cover?

The check in `check_hotspot_fit.py` accepts anything over 55%, which is enough to
catch a tap area on the wrong control but not enough to catch one that leaves part
of its button dead. An operator presses the edge of a button and nothing happens.

This prints the exact coverage per button, so a gap of a few pixels is visible
rather than averaged away.
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
FURNITURE = ("size-badge", "back-chip")

SCREEN_PAGE = {
    "userInfo": "pUser", "main": "pMain", "baselineMenu": "pBase", "newBaseline": "pNewB",
    "materialData": "pMat", "maturityData": "pMatu", "baselineResult": "pBaseR",
    "savedBaseline": "pSaveB", "kuatTekanMenu": "pKuat", "selectBaseline": "pSelB",
    "realtime": "pRT", "strengthResult": "pStr", "history": "pHist",
    "historyDetail": "pHistD", "settings": "pSet", "deviceInfo": "pDev",
}


def elements(page: str) -> list[dict]:
    data = LAYOUT.get(page, {})
    return data.get("elements", []) if isinstance(data, dict) else []


def taps(page: str) -> list[dict]:
    data = tomllib.loads((PAGES_DIR / f"{page}.page.toml").read_text(encoding="utf-8"))
    return [c for c in data.get("component", []) if c.get("type") == "hotspot"]


def coverage(tap: dict, button: dict) -> tuple[float, int, int, int, int]:
    """The fraction of `button` that `tap` covers, and the uncovered borders."""
    x = max(tap["x"], button["x"])
    y = max(tap["y"], button["y"])
    right = min(tap["x"] + tap["w"], button["x"] + button["w"])
    bottom = min(tap["y"] + tap["h"], button["y"] + button["h"])
    if right <= x or bottom <= y:
        return 0.0, button["w"], button["h"], button["w"], button["h"]
    area = button["w"] * button["h"]
    covered = (right - x) * (bottom - y)
    left_gap = max(0, tap["x"] - button["x"])
    top_gap = max(0, tap["y"] - button["y"])
    right_gap = max(0, (button["x"] + button["w"]) - (tap["x"] + tap["w"]))
    bottom_gap = max(0, (button["y"] + button["h"]) - (tap["y"] + tap["h"]))
    return covered / area, left_gap, top_gap, right_gap, bottom_gap


def main() -> None:
    worst = []
    for screen, page in SCREEN_PAGE.items():
        drawn = [e for e in elements(page) if e["kind"] == "button"]
        for button in drawn:
            cx = button["x"] + button["w"] // 2
            cy = button["y"] + button["h"] // 2
            if not (0 <= cx < WIDTH and 0 <= cy < HEIGHT):
                continue
            if any(f in (button.get("cls") or "") for f in FURNITURE):
                continue

            # A tap area belongs to one drawn control. The one it belongs to is
            # the smallest control whose centre it covers: a card and the SELECT
            # button on it overlap, and the SELECT is what the tap area is for.
            owner = None
            for tap in taps(page):
                tx = tap["x"] + tap["w"] // 2
                ty = tap["y"] + tap["h"] // 2
                if button["x"] <= tx < button["x"] + button["w"] and button["y"] <= ty < button["y"] + button["h"]:
                    if owner is None or tap["w"] * tap["h"] < owner["w"] * owner["h"]:
                        owner = tap
            if owner is None:
                worst.append((page, (button.get("text") or "?")[:20], "-", 0.0, 0, 0, 0, 0))
                continue

            # The control the tap area is for is the one it overlaps most, so a
            # tap area meant for a card's SELECT is not measured against the card.
            claim = max(drawn, key=lambda b: coverage(owner, b)[0])
            if claim is not button:
                continue

            ratio, l, t, r, b = coverage(owner, button)
            label = (button.get("text") or button.get("cls", "?"))[:20]
            if ratio < 0.995:
                worst.append((page, label, owner["name"], ratio, l, t, r, b))

    for page, label, name, ratio, l, t, r, b in worst:
        print(
            f"{page:8} {name:10} {label:20} covers {ratio:6.1%}"
            f"  gaps L{l} T{t} R{r} B{b}"
        )
    print(f"\n{len(worst)} button(s) not fully covered")
    print("A gap is pixels of the drawn button that no tap area reaches.")


if __name__ == "__main__":
    main()
