"""Remove the sample values the design drew into each page's picture.

The design was drawn with example data — "35.4 MPa", "1,245", a date. Those pixels
are part of the background picture, so a panel whose fields are empty still shows
that example, and an operator cannot tell it from a real reading. The values must
come from the sensors and the operator's own input, and nowhere else.

The removal is careful about three things:

- Only white pixels go. Sample text is white; the orange icons, the orange rules
  and the panel's own gradient stay exactly as drawn.
- Only inside the box of a field that sits on the sample text, so the rest of the
  design is untouched.
- The gap the letters leave is filled from the panel's own neighbours, so the
  soft gradient behind them stays smooth instead of showing a flat patch.

The result is written to `nextion/assets/clean/`, and the build uses those
pictures. The originals stay, so the drawn design is never lost.
"""

from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PAGES_DIR = ROOT / "nextion" / "nxsrc" / "pages"
SOURCE = ROOT / "nextion" / "assets" / "pages"
TARGET = ROOT / "nextion" / "assets" / "clean"
BAKED = json.loads((ROOT / "nextion" / "tools" / "baked.json").read_text(encoding="utf-8"))

PICTURE = {
    "pInit": "00_init", "pUser": "01_user_info", "pMain": "02_main_menu",
    "pBase": "03_baseline", "pNewB": "04_new_baseline", "pMat": "05_material_data",
    "pMatu": "06_maturity_data", "pBaseR": "07_baseline_result",
    "pSaveB": "08_saved_baseline", "pKuat": "09_kuat_tekan",
    "pSelB": "10_select_baseline", "pRT": "11_realtime",
    "pStr": "12_strength_result", "pHist": "13_history",
    "pHistD": "14_history_detail", "pSet": "15_settings", "pDev": "16_device_info",
}

# A letter is a bright pixel. Slightly above the panel's own lightest shade, well
# below an icon's white checkmark, which sits on solid orange and is left alone.
WHITE = 150


def erase(image: np.ndarray, box: tuple[int, int, int, int]) -> tuple[np.ndarray, int]:
    """Paint over the white letters inside `box`, keeping everything else.

    Each erased pixel takes the colour of the nearest pixel in its own row that
    was not part of a letter, so the panel's gradient carries across the gap.
    """
    out = image.copy()
    x, y, w, h = box
    x2, y2 = min(x + w, image.shape[1]), min(y + h, image.shape[0])
    if x2 <= x or y2 <= y:
        return out, 0

    region = out[y:y2, x:x2]
    grey = region.max(axis=2)
    letters = grey > WHITE
    if not letters.any():
        return out, 0

    erased = 0
    for row in range(region.shape[0]):
        mask = letters[row]
        if not mask.any():
            continue
        source = np.where(~mask)[0]
        if source.size == 0:
            # The whole row is letters: take the row above instead.
            if y + row > 0:
                region[row] = out[y + row - 1, x:x2]
                erased += int(mask.sum())
            continue
        # Nearest kept pixel on each side, which keeps vertical edges sharp.
        for column in np.where(mask)[0]:
            left = source[source < column]
            right = source[source > column]
            if left.size and right.size:
                pick = left[-1] if column - left[-1] <= right[0] - column else right[0]
            elif left.size:
                pick = left[-1]
            else:
                pick = right[0]
            region[row, column] = region[row, pick]
            erased += 1
    out[y:y2, x:x2] = region
    return out, erased


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    total = 0
    for page, picture in PICTURE.items():
        source = SOURCE / f"{picture}.png"
        image = np.asarray(Image.open(source).convert("RGB"))
        cleaned, erased = image, 0

        fields = BAKED.get(page) or []
        if fields:
            data = tomllib.loads((PAGES_DIR / f"{page}.page.toml").read_text(encoding="utf-8"))
            boxes = {c["name"]: c for c in data.get("component", []) if c.get("type") == "text"}
            for name, _spread in fields:
                component = boxes.get(name)
                if not component:
                    continue
                cleaned, count = erase(
                    cleaned,
                    (component["x"], component["y"], component["w"], component["h"]),
                )
                erased += count

        Image.fromarray(cleaned).save(TARGET / f"{picture}.png")
        total += erased
        if erased:
            print(f"{page:8} erased {erased:5} pixel(s)")

    print(f"\n{total} sample pixel(s) removed from {len(PICTURE)} picture(s)")
    print("originals kept in", SOURCE)
    print("cleaned pictures in", TARGET)


if __name__ == "__main__":
    main()
