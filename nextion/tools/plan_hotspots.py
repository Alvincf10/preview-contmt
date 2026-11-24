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


def covered(page: str, button: dict) -> bool:
    data = tomllib.loads((PAGES_DIR / f"{page}.page.toml").read_text(encoding="utf-8"))
    for c in data.get("component", []):
        if c.get("type") != "hotspot":
            continue
        if (
            c["x"] < button["x"] + button["w"]
            and button["x"] < c["x"] + c["w"]
            and c["y"] < button["y"] + button["h"]
            and button["y"] < c["y"] + c["h"]
        ):
            return True
    return False


def main() -> None:
    generated = {}
    for screen, page in SCREEN_PAGE.items():
        entries = [e for e in NAV.get(page, []) if e.get("to")]
        entries = [e for e in entries if not any(f in (e.get("cls") or "") for f in FURNITURE)]
        made = []
        for index, entry in enumerate(entries):
            if covered(page, entry):
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
