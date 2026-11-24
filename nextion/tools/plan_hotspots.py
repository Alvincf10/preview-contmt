#!/usr/bin/env python3
"""Add a tap area for every button the picture draws but the kit does not cover.

The kit names 48 tap areas. The design draws far more: table rows, settings
steppers, toggles, log expanders. A painted button with nothing over it is a
dead button, which is exactly what the operator notices first.

So a hotspot is made for each uncovered button, named from its place on the
page, and wired to the verb that button performs. The verb comes from the
button's own label where the contract has one, and from the page's role where it
does not.

The result is a plain table, so it is reviewable: every generated hotspot and
the verb it sends are listed in `auto_hotspots.json`.
"""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
NAV = json.loads((TOOLS / "nav.json").read_text(encoding="utf-8"))
ELEMENTS = {
    page: data.get("elements", [])
    for page, data in json.loads((TOOLS / "layout.json").read_text(encoding="utf-8")).items()
}
PAGES_DIR = ROOT / "nextion" / "nxsrc" / "pages"

PAGES = [
    "pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR",
    "pSaveB", "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev",
]
SCREEN_PAGE = {
    "userInfo": "pUser", "main": "pMain", "baselineMenu": "pBase", "newBaseline": "pNewB",
    "materialData": "pMat", "maturityData": "pMatu", "baselineResult": "pBaseR",
    "savedBaseline": "pSaveB", "kuatTekanMenu": "pKuat", "selectBaseline": "pSelB",
    "realtime": "pRT", "strengthResult": "pStr", "history": "pHist",
    "historyDetail": "pHistD", "settings": "pSet", "deviceInfo": "pDev",
}

FURNITURE = ("size-badge", "back-chip")

# A generated hotspot's verb, by the label the design draws on the button.
BY_LABEL = {
    "next": ("NAV", None),
    "back": ("NAV", "BACK"),
    "save": ("USER_SAVE", None),
    "generate baseline": ("BASE_GENERATE", None),
    "+ add day": ("ROW_ADD_LAB", None),
    "sensor": ("ROW_SENSOR", ["0"]),
    "start": ("MEASURE_START", None),
    "start test": ("NAV", "10"),
    "history": ("NAV", "13"),
    "select": ("BASE_PICK", ["0"]),
    "view log": ("HISTORY_PICK", ["0"]),
    "select baseline": ("NAV", "8"),
    "save result": ("RESULT_SAVE", None),
}

# A settings stepper and a toggle carry their own meaning, from the control.
SETTINGS_STEP = {"▴": "1", "▾": "-1"}


def covered(page: str, button: dict, kit: dict[str, dict], used: set[str]) -> bool:
    """Whether the contract already gives this button a tap area.

    The question is about the *contract*, not about coordinates: `nx_source.py`
    places a kit hotspot at the drawn button by looking its label up in HOTSPOTS,
    so a hotspot the kit names is already covered even when the kit's own
    coordinates are stale.

    Each hotspot covers one button, so a name already spent on an earlier button
    of the same label cannot cover this one: a page with four SELECT buttons and
    one named hotspot needs three generated tap areas, not none.
    """
    from hotspots_map import HOTSPOTS

    for component in kit.get(page, {}).get("components", []):
        if component.get("type") != "TouchCap":
            continue
        name = component["objname"]
        if name in used:
            continue
        label = HOTSPOTS.get(page, {}).get(name)
        if label is None:
            # A hotspot with no label keeps the kit's own coordinates.
            if (
                component["x"] < button["x"] + button["w"]
                and button["x"] < component["x"] + component["w"]
                and component["y"] < button["y"] + button["h"]
                and button["y"] < component["y"] + component["h"]
            ):
                used.add(name)
                return True
            continue
        # A labelled hotspot lands on the drawn button its label names.
        if (button.get("text") or "").strip().upper().startswith(label.upper()):
            used.add(name)
            return True
    return False


def claimed_boxes(page: str, kit: dict[str, dict]) -> list[dict]:
    """Where the contract's own tap areas will land.

    `nx_source.py` places a kit hotspot at the box its label names, which is not
    the same as the kit's own stale coordinates. A generated tap area must keep
    clear of where they actually land.
    """
    import nx_source

    boxes = []
    nx_source.DESIGN_CACHE = nx_source.load_design()
    for component in kit.get(page, {}).get("components", []):
        if component.get("type") != "TouchCap":
            continue
        if not all(key in component for key in ("x", "y", "w", "h")):
            continue
        box = nx_source.hotspot_box(page, component["objname"], component)
        if box:
            boxes.append({"x": box[0], "y": box[1], "w": box[2], "h": box[3]})
    return boxes


def main() -> None:
    generated = {}
    # The kit's own tap areas decide which buttons still need one.
    kit = {}
    for path in sorted((ROOT / "nextion" / "pages").glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        kit[page["name"]] = page

    for screen, page in SCREEN_PAGE.items():
        entries = [e for e in NAV.get(page, []) if e.get("to")]
        entries = [e for e in entries if not any(f in (e.get("cls") or "") for f in FURNITURE)]
        # A tap area is made only for a button that is on the screen and does not
        # overlap one already made. A list the picture draws past the edge, or a
        # row that falls in the footer's band, would otherwise put a tap area on
        # top of a real button.
        accepted: list[dict] = []
        for entry in entries:
            if entry["y"] + entry["h"] // 2 >= 800 or entry["x"] + entry["w"] // 2 >= 480:
                continue
            if any(
                entry["x"] < other["x"] + other["w"]
                and other["x"] < entry["x"] + entry["w"]
                and entry["y"] < other["y"] + other["h"]
                and other["y"] < entry["y"] + entry["h"]
                for other in accepted
            ):
                continue
            accepted.append(entry)
        entries = accepted

        made = []
        # A hotspot covers one button, so a name spent on an earlier button of
        # the same label is no longer available.
        used: set[str] = set()
        # Where the contract's own tap areas will land. A generated tap area must
        # keep clear of them, or a tap on SENSOR would delete a row.
        taken = claimed_boxes(page, kit)
        for index, entry in enumerate(entries):
            if covered(page, entry, kit, used):
                continue
            if any(
                entry["x"] < b["x"] + b["w"]
                and b["x"] < entry["x"] + entry["w"]
                and entry["y"] < b["y"] + b["h"]
                and b["y"] < entry["y"] + entry["h"]
                for b in taken
            ):
                continue
            label = (entry.get("text") or "").replace("\n", " ").strip().lower()
            verb, args = None, []
            if page == "pSet" and label in SETTINGS_STEP:
                verb, args = "SETTINGS_STEP", [SETTINGS_STEP[label]]
            elif page == "pSet" and label == "on":
                verb, args = "SETTINGS_TOGGLE", ["sound"]
            elif page == "pHistD":
                verb, args = "HISTORY_PICK", ["0"]
            else:
                for key, (v, a) in BY_LABEL.items():
                    if label.startswith(key):
                        verb, args = v, (a or [])
                        break
            made.append(
                {
                    "name": f"mAuto{index}",
                    "x": entry["x"] - 2,
                    "y": entry["y"] - 2,
                    "w": entry["w"] + 4,
                    "h": entry["h"] + 4,
                    "label": (entry.get("text") or "")[:24],
                    "verb": verb or "NAV",
                    "args": args,
                }
            )
        if made:
            generated[page] = made

    out = TOOLS / "auto_hotspots.json"
    out.write_text(json.dumps(generated, indent=1) + "\n", encoding="utf-8")
    total = sum(len(v) for v in generated.values())
    print(json.dumps({"pages": len(generated), "hotspots": total, "file": str(out)}))


if __name__ == "__main__":
    main()
