"""Find fields too narrow for the value they will hold.

The design sized each field's box to the sample it drew, and an em-dash or a short
number made a small box. The MCU then writes a real value into it — "25.7", a
date, a baseline name — which needs more room than the sample did. A box that is
too narrow cuts that value off, and the operator reads a truncated number.

This measures each field against the longest value its kind can carry and lists
the ones too narrow.
"""

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "nextion" / "nxsrc" / "pages"

# A rough width per character at the small face the panel uses. Noto Sans at 16px
# averages about 8 pixels per digit, and 7 for the narrower letters. A field that
# is a pixel or two short still shows its value: the glyphs are not fixed width,
# and the estimate here is deliberately on the generous side.
DIGIT = 8
LETTER = 7
# The panel draws in a proportional face, so a value a few pixels over the
# estimate still fits. The slack keeps the check from flagging a box that is fine.
SLACK = 4

# The longest value each field can receive, by the name the contract uses.
LONGEST = {
    "tClock": "23:59:59",
    "tBatt": "100%",
    "tMsg": "Connection timeout",
    "tBase": "Beton Fc45 BP HKSIS Marunda",
    "tName": "Beton Fc45 BP HKSIS Marunda",
    "tProj": "HK Tower Phase 2",
    "tOp": "OP-001",
    "tDate": "28-09-2026",
    "tPDate": "28-09-2026",
    "tNowD": "28-09-2026",
    "tPour": "23:59:59",
    "tNowT": "23:59:59",
    "tTarget": "30 MPa",
    "tDatum": "-20 °C",
    "tM": "99,999",
    "tFc": "99.9 MPa",
    "tPct": "(100%)",
    "tAvg": "99.9 °C",
    "tInitTemp": "99.9 °C",
    "tS1": "99.9 °C",
    "tS2": "99.9 °C",
    "tS3": "99.9 °C",
    "tElapsed": "99:59:59",
    "tRefDay": "Day 28",
    "tA": "-99.9999",
    "tB": "-99.9999",
    "tR2": "0.9999",
    "tCount": "999",
    "tEq": "fc = -99.999 + 9.9999 ln(M)",
    "tHint": "Tap a Temp row, then SENSOR to fill.",
    "tVersion": "V1.0.1",
    "tMcu": "ATmega328P",
    "tProtocol": "CM1 contract2",
    "tCem": "9999",
    "tWat": "9999",
    "tCoa": "9999",
    "tFin": "9999",
    "tWC": "99.99",
    "tRetP": "99.9",
    "tRetB": "Sika Retarder",
    "tAccP": "99.9",
    "tAccB": "Sika Accelerator",
    "tFlyP": "99.9",
    "tFlyB": "Holcim Fly Ash",
    "tHour": "23",
    "tMin": "59",
    "tSec": "59",
    "tBright": "100%",
    "tSound": "ON",
    "tAuto": "ON",
    "tInterval": "86399",
    "tDay0": "999",
    "tTim0": "23:59",
    "tFc0": "99.99",
    "tT0": "99.99",
    "tRid0": "999",
    "tAt0": "28-09-2026 23:59",
    "tTmp0": "99.9",
    "tCm0": "99,999",
    "tCf0": "99.9 MPa",
    "tSavedAt": "28-09-2026",
    "tLastT": "23:59:59",
    "tStatus": "COMPLETED",
    "tId": "TEST-EXCEL-01",
    "tVal": "99.9 MPa",
    "tDate0": "28-09-2026",
    "tCount0": "41 days",
}


def need(field: str) -> int | None:
    """How wide a field must be for the longest value it can hold."""
    text = LONGEST.get(field)
    if text is None:
        # A table row's fields carry an index, so the base name applies.
        base = field.rstrip("012345")
        for suffix in ("", "0"):
            if base + suffix in LONGEST:
                text = LONGEST[base + suffix]
                break
    if text is None:
        return None
    digits = sum(1 for ch in text if ch.isdigit() or ch in ".,:%°-' ")
    letters = len(text) - digits
    return int(digits * DIGIT + letters * LETTER) + 2


def main() -> None:
    narrow = []
    for path in sorted(PAGES.glob("*.page.toml")):
        page = path.name.split(".")[0]
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        for component in data.get("component", []):
            if component.get("type") != "text":
                continue
            if component.get("x", 0) >= 480:
                continue
            wanted = need(component["name"])
            if wanted is None:
                continue
            if component["w"] + SLACK < wanted:
                narrow.append((page, component["name"], component["w"], wanted))

    for page, name, has, wants in narrow:
        print(f"{page:8} {name:12} {has:4}px wide, needs {wants:4}px  (a neighbour stops it)")
    print(f"\n{len(narrow)} field(s) narrower than the longest value they can hold")
    print("These are bounded by what the design draws beside them, so the value may be")
    print("cut. Widen the box by hand, or shorten the value the MCU sends.")


if __name__ == "__main__":
    main()
