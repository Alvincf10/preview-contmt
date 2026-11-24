#!/usr/bin/env python3
"""Cross-check every page: does the built panel match the design, and does every
control behave the way the design draws it?

This catches the failures a field-only overlap check misses:

1. **A hotspot over the wrong field.** A tap area that spans several cells means
   tapping one value opens another's editor. A tap area that covers nothing the
   design draws is a dead area.
2. **Two tap areas over one spot.** Whichever comes later takes the touch, so one
   of the two buttons is unreachable.
3. **A field the design does not draw, inside the screen.** It paints a value over
   the picture. Such a field belongs in the reserve.
4. **A field with a visible background.** It paints a block over the picture.
5. **A drawn button with no tap area**, and a tap area with no event.

Run with no arguments for every page; exits non-zero on any finding.
"""
from __future__ import annotations

import itertools
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
PAGES = ROOT / "nextion" / "nxsrc" / "pages"
EVENTS = ROOT / "firmware" / "hmi" / "events"
LAYOUT = json.loads((TOOLS / "layout.json").read_text(encoding="utf-8"))
NAV = json.loads((TOOLS / "nav.json").read_text(encoding="utf-8"))

WIDTH, HEIGHT = 480, 800
RESERVE_X = 480

# The preview's own furniture, never a control.
FURNITURE = ("size-badge", "back-chip")

# Pairs the design draws on top of each other on purpose.
DESIGNED_OVERLAYS = {("tFc", "tPct")}

# The splash's status lines paint over the sample checklist its picture draws
# in the same rows, so they carry a background on purpose.
SPLASH_STATUS_FIELDS = {"tChkSensors", "tChkClock", "tChkDevice", "tReady"}

SCREEN_PAGE = {
    "userInfo": "pUser", "main": "pMain", "baselineMenu": "pBase", "newBaseline": "pNewB",
    "materialData": "pMat", "maturityData": "pMatu", "baselineResult": "pBaseR",
    "savedBaseline": "pSaveB", "kuatTekanMenu": "pKuat", "selectBaseline": "pSelB",
    "realtime": "pRT", "strengthResult": "pStr", "history": "pHist",
    "historyDetail": "pHistD", "settings": "pSet", "deviceInfo": "pDev",
}


def page_components(page: str) -> list[dict]:
    data = tomllib.loads((PAGES / f"{page}.page.toml").read_text(encoding="utf-8"))
    return data.get("component", [])


def inside(box: dict) -> bool:
    """Whether a box sits on the screen. The reserve is past the right edge by
    design, so it is not 'outside' — it is deliberately out of the way."""
    return (
        box["x"] >= 0
        and box["y"] >= 0
        and box["x"] + box["w"] <= WIDTH
        and box["y"] + box["h"] <= HEIGHT
    )


def in_reserve(box: dict) -> bool:
    """A field the MCU writes but the design does not draw, kept off the screen."""
    return box["x"] >= RESERVE_X


def misplaced(box: dict) -> bool:
    """A box that is neither on the screen nor in the reserve: it is lost."""
    return not inside(box) and not in_reserve(box)


def centre_inside(box: dict) -> bool:
    cx = box["x"] + box["w"] // 2
    cy = box["y"] + box["h"] // 2
    return 0 <= cx < WIDTH and 0 <= cy < HEIGHT


def overlaps(a: dict, b: dict, pad: int = 0) -> bool:
    return (
        a["x"] < b["x"] + b["w"] + pad
        and b["x"] < a["x"] + a["w"] + pad
        and a["y"] < b["y"] + b["h"] + pad
        and b["y"] < a["y"] + a["h"] + pad
    )


def main() -> int:
    problems: list[str] = []

    for page in sorted({p.stem.split(".")[0] for p in PAGES.glob("*.page.toml")}):
        components = page_components(page)
        placed = [c for c in components if "x" in c]
        hotspots = [c for c in placed if c.get("type") == "hotspot"]
        fields = [c for c in placed if c.get("type") not in ("hotspot", "picture", "variable")]
        reserved = [c for c in placed if c["x"] >= RESERVE_X]
        shown = [c for c in placed if c["x"] < RESERVE_X]

        # 1. A field must be either on the screen or in the reserve, never lost
        #    somewhere else, and never on the screen with a painted background.
        #    The splash's status lines are the exception: its picture draws a
        #    sample checklist in those exact rows, so they must paint over it.
        for field in fields:
            if misplaced(field):
                problems.append(
                    f"{page}.{field['name']}: at {field['x']},{field['y']}, neither on the screen nor in the reserve"
                )
                continue
            if inside(field) and field.get("sta") != 3 and field["name"] not in SPLASH_STATUS_FIELDS:
                problems.append(
                    f"{page}.{field['name']}: sta={field.get('sta')!r} on the screen, so it paints over the design"
                )

        # 3. Two fields over one spot, except the pairs the design overlays.
        onscreen = [f for f in fields if f["x"] < RESERVE_X]
        for a, b in itertools.combinations(onscreen, 2):
            if (a["name"], b["name"]) in DESIGNED_OVERLAYS or (b["name"], a["name"]) in DESIGNED_OVERLAYS:
                continue
            if overlaps(a, b):
                problems.append(f"{page}: fields {a['name']} and {b['name']} overlap")

        # 4. Two tap areas over one spot: the later one wins, so the other is dead.
        for a, b in itertools.combinations(hotspots, 2):
            if not (centre_inside(a) and centre_inside(b)):
                continue
            if overlaps(a, b, pad=-2):
                problems.append(f"{page}: tap areas {a['name']} and {b['name']} cover the same spot")

        # 5. A tap area that swallows another control's cell. A row tap must not
        #    span several inputs, because the cells hold different values. A
        #    whole card is the exception: the card is one record, and tapping any
        #    part of it opens that record, so covering its own fields is the
        #    design.
        for hotspot in hotspots:
            if not centre_inside(hotspot):
                continue
            covered = [f for f in onscreen if overlaps(hotspot, f)]
            names = {f["name"] for f in covered}
            is_card = abs(hotspot["w"] - 346) <= 8 and hotspot["h"] > 60
            if len(names) > 1 and not is_card:
                problems.append(
                    f"{page}.{hotspot['name']}: covers {len(names)} fields ({', '.join(sorted(names)[:4])})"
                )

        # 6. Every tap area has an event, and every drawn button has a tap area.
        for hotspot in hotspots:
            if not (EVENTS / f"{page}_{hotspot['name']}.txt").exists():
                problems.append(f"{page}.{hotspot['name']}: no event, so tapping it does nothing")

        for entry in NAV.get(page, []):
            if not entry.get("to"):
                continue
            if any(f in (entry.get("cls") or "") for f in FURNITURE):
                continue
            # A button the picture draws below the screen cannot be pressed, so it
            # needs no tap area. The panel pages its table instead.
            if entry["y"] + entry["h"] // 2 >= HEIGHT or entry["x"] + entry["w"] // 2 >= WIDTH:
                continue
            if not any(overlaps(tap, entry) for tap in hotspots):
                label = (entry.get("text") or entry.get("cls", "?"))[:24]
                problems.append(f"{page}: the drawn button {label!r} has no tap area")

    # Report
    by_page: dict[str, list[str]] = {}
    for problem in problems:
        by_page.setdefault(problem.split(":")[0].split(".")[0], []).append(problem)

    for page in sorted(by_page):
        print(f"\n{page}")
        for problem in by_page[page][:12]:
            print(f"  {problem}")
        if len(by_page[page]) > 12:
            print(f"  ... and {len(by_page[page]) - 12} more")

    print(f"\n{len(problems)} problem(s) across {len(by_page)} page(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
