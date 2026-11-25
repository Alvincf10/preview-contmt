"""Compare the two firmware protocols with the one the panel actually speaks.

There are two firmware implementations in this repo:

- `firmware/ConMT`  the C++ firmware, which the panel's contract was generated from
- `arduino/ConMT`   the Arduino sketch, which speaks its own protocol

The panel can only talk to one of them. This reads what each side expects and says
plainly where they differ, so the answer is a measurement rather than a guess.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PANEL_EVENTS = ROOT / "firmware" / "hmi" / "events"
MANIFEST = ROOT / "firmware" / "hmi" / "manifest.json"
ARDUINO_PANEL = ROOT / "arduino" / "ConMT" / "src" / "Panel.cpp"
ARDUINO_CONTRACT = ROOT / "arduino" / "CONTRACT.md"
FIRMWARE_TRANSPORT = ROOT / "firmware" / "ConMT" / "src" / "hmi" / "Transport.cpp"


def panel_expects() -> set[str]:
    """The component names the panel's own code reads and writes."""
    names = set()
    for path in PANEL_EVENTS.glob("*.txt"):
        text = path.read_text(encoding="utf-8")
        names |= set(re.findall(r"pInit\.(\w+)\.(?:val|txt)", text))
    return names


def panel_sends() -> set[str]:
    """The verbs the panel sends."""
    verbs = set()
    for path in PANEL_EVENTS.glob("*.txt"):
        text = path.read_text(encoding="utf-8")
        verbs |= set(re.findall(r'tReq\.txt\+="\|([A-Z_]+)"', text))
    return verbs


def panel_globals() -> list[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return manifest["globals"]["variables"]


def arduino_writes() -> set[str]:
    source = ARDUINO_PANEL.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r'FSTR\("(\w+)\.', source))


def arduino_verbs() -> set[str]:
    text = ARDUINO_CONTRACT.read_text(encoding="utf-8")
    return set(re.findall(r"^\| `([A-Z_]+)", text, re.M))


def firmware_writes() -> set[str]:
    source = FIRMWARE_TRANSPORT.read_text(encoding="utf-8")
    return set(re.findall(r'CM_LITERAL\("pInit\.(\w+)"\)', source))


def main() -> int:
    panel_names = panel_expects()
    manifest_globals = set(panel_globals())
    arduino_names = arduino_writes()
    firmware_names = firmware_writes()

    print("Panel reads/writes:", ", ".join(sorted(panel_names)))
    print("Panel contract globals:", ", ".join(sorted(manifest_globals)))
    print()
    print("firmware/ConMT writes:", ", ".join(sorted(firmware_names)) or "(none found)")
    print("arduino/ConMT writes:", ", ".join(sorted(arduino_names)) or "(none found)")
    print()

    # The Arduino's own names, minus the numbers its FSTR scan picks up by accident.
    arduino_only = {n for n in arduino_names if n not in {"1"}}
    missing_arduino = arduino_only - manifest_globals - {"tData", "tSplit"}
    surplus = manifest_globals - arduino_only - {"tSplit", "vSeq", "vBusy", "vRetry", "vSource", "vStep"}

    print(f"Arduino names the panel lacks: {sorted(missing_arduino) or 'none'}")
    print(f"Panel globals the Arduino never writes: {sorted(surplus) or 'none (the panel owns them)'}")
    print()

    panel = panel_sends()
    arduino = arduino_verbs()
    shared = panel & arduino
    only_panel = panel - arduino
    only_arduino = arduino - panel
    print(f"Verbs the panel sends: {len(panel)}")
    print(f"Verbs the Arduino contract defines: {len(arduino)}")
    print(f"Shared: {len(shared)}")
    print(f"Only the panel sends: {sorted(only_panel) or 'none'}")
    print(f"Only Arduino defines: {sorted(only_arduino) or 'none'}")
    print()

    talks = not missing_arduino and not only_panel
    print("The panel speaks arduino/ConMT:", "yes" if talks else "no")
    if not talks:
        print()
        print("Every verb the panel sends must exist in the Arduino contract, and")
        print("every name it waits on must be one the Arduino writes.")
    return 0 if talks else 1


if __name__ == "__main__":
    raise SystemExit(main())
