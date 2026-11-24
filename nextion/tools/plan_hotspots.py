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
# The Arduino sets an absolute value, so a stepper step becomes a SETTINGS_SET of
# the new value: the panel reads the field it shows, adjusts it, and sends that.
STEPPER_FIELD = {
    "▴": "1",
    "▾": "-1",
}

# Which settings field a stepper belongs to, by its place on the page: hour,
# minute, second from the first three pairs, brightness from the fourth.
STEPPER_KEYS = ["hour", "minute", "second", "brightness"]
TOGGLE_KEYS = ["sound", "autoSave"]


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


def is_small_control(entry: dict) -> bool:
    """Whether a control is a small one inside a table row.

    A row's delete cross is a few dozen pixels square, while a footer button is
    wide. The small one is the more specific target: an operator aiming at it means
    it, not the wide button that reaches across it.
    """
    return entry["w"] <= 48 and entry["h"] <= 40


def trim_clear(entry: dict, taken: list[dict]) -> dict | None:
    """The part of a button that no existing tap area claims, or None.

    A row of a list can reach into the footer band where BACK sits. Refusing the
    whole row leaves it dead; giving the whole row steals the button. So the row
    keeps the part the obstruction does not cover.

    Only an obstruction that actually overlaps the row in both directions can
    shorten it. A control far to the left shares the row's vertical band but takes
    none of its width, and must not clip it.
    """
    top, bottom = entry["y"], entry["y"] + entry["h"]
    for other in taken:
        # No horizontal overlap means no obstruction.
        if not (entry["x"] < other["x"] + other["w"] and other["x"] < entry["x"] + entry["w"]):
            continue
        other_top = other["y"]
        other_bottom = other_top + other["h"]
        if not (other_top < bottom and top < other_bottom):
            continue
        if other_top <= top:
            # The obstruction covers the row's top: start below it.
            top = max(top, other_bottom)
        else:
            # The obstruction covers the row's bottom: end above it.
            bottom = min(bottom, other_top)
    if bottom - top < 16:
        return None
    trimmed = dict(entry)
    trimmed["y"] = top
    trimmed["h"] = bottom - top
    return trimmed


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
        # Where the contract's own tap areas will land.
        taken = claimed_boxes(page, kit)
        for index, entry in enumerate(entries):
            if covered(page, entry, kit, used):
                continue
            # A small control the kit does not name is more specific than a wide
            # footer button that happens to reach over it. The small one keeps its
            # own tap area; the wide one is trimmed elsewhere so a tap on the cross
            # does not press SENSOR. Nextion resolves a touch to the last component
            # at that point, and these are written after the kit's.
            if is_small_control(entry):
                pass
            else:
                entry = trim_clear(entry, taken)
                if entry is None:
                    continue
            label = (entry.get("text") or "").replace("\n", " ").strip().lower()
            verb, args = None, []
            if page == "pSet" and label in STEPPER_FIELD:
                # The Arduino sets an absolute value, so the tap becomes a
                # SETTINGS_SET of the new one. The step field and the direction are
                # recorded here; the event generator writes the arithmetic.
                index = len([m for m in made if m["verb"] == "SETTINGS_SET"])
                key = STEPPER_KEYS[min(index // 2, len(STEPPER_KEYS) - 1)]
                verb, args = "SETTINGS_SET", [key, STEPPER_FIELD[label]]
            elif page == "pSet" and label == "on":
                index = len([m for m in made if m["verb"] == "SETTINGS_SET" and m["args"][-1] == "toggle"])
                key = TOGGLE_KEYS[min(index, len(TOGGLE_KEYS) - 1)]
                verb, args = "SETTINGS_SET", [key, "toggle"]
            elif page == "pHistD":
                verb, args = "HISTORY_PICK", ["0"]
            else:
                for key, (v, a) in BY_LABEL.items():
                    if label.startswith(key):
                        verb, args = v, (a or [])
                        break
            made.append(
                {
                    # A distinct prefix: `write_missing_events` also names its
                    # hotspots mAuto<N>, and two components cannot share a name on
                    # one page. The counter is the length of `made`, which is unique
                    # by construction; `index` counts entries, and two entries can
                    # end up with the same number after a skip.
                    "name": f"mTap{len(made)}",
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
