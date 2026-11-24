"""Erase the sample text the design drew inside each K050 input box.

The K050 field boxes no longer match the boxes the older `nxsrc` cleaning used, so
white sample values ("45", "18C", "fc30 marunda final") still show through behind
the real value. For every text field of a K050 page, this copies the field's box
from the original design picture and fills every bright pixel with the nearest
non-bright pixel in its row, then writes the result to `nextion/assets/clean/`.

Only the box's inner area is touched, so the border and the panel's gradient stay
as drawn. Boxes that hold no sample text are copied unchanged.
"""
from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "nextion" / "nxsrc-K050" / "pages"
CLEAN = ROOT / "nextion" / "assets" / "clean"
ORIGINAL = ROOT / "nextion" / "assets" / "pages"
PICTURES = ROOT / "nextion" / "nxsrc-K050" / "pictures"

PICTURE = {
    "pInit": "00_init", "pUser": "01_user_info", "pMain": "02_main_menu",
    "pBase": "03_baseline", "pNewB": "04_new_baseline", "pMat": "05_material_data",
    "pMatu": "06_maturity_data", "pBaseR": "07_baseline_result",
    "pSaveB": "08_saved_baseline", "pKuat": "09_kuat_tekan",
    "pSelB": "10_select_baseline", "pRT": "11_realtime",
    "pStr": "12_strength_result", "pHist": "13_history",
    "pHistD": "14_history_detail", "pSet": "15_settings", "pDev": "16_device_info",
}

# Text the design itself must keep: the panel title's sample subtitle, the group
# headings, and the unit labels sit outside a field's box, so nothing here is a
# value the MCU writes.
SKIP = {("pMatu", "tHint")}
BRIGHT = 55


def fill_rows(region: np.ndarray) -> int:
    """Replace bright pixels with the nearest non-bright pixel in their row."""
    changed = 0
    for row in range(region.shape[0]):
        grey = region[row].max(axis=1)
        mask = grey > BRIGHT
        if not mask.any():
            continue
        source = np.where(~mask)[0]
        if source.size == 0:
            continue
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
            changed += 1
    return changed


def main() -> int:
    PICTURES.mkdir(parents=True, exist_ok=True)
    total = 0
    for page, picture in PICTURE.items():
        source_page = PAGES / f"{page}.page.toml"
        if not source_page.exists():
            continue
        data = tomllib.loads(source_page.read_text(encoding="utf-8"))
        # Start from the original design so every label and icon stays; only the
        # areas this panel's own field boxes cover are cleared.
        image = np.array(Image.open(ORIGINAL / f"{picture}.png").convert("RGB"))
        touched = 0
        for component in data.get("component", []):
            if component.get("type") not in ("text", "button"):
                continue
            if component.get("sta") == 1 or (page, component.get("name")) in SKIP:
                continue
            x, y, w, h = (component.get(k, 0) for k in ("x", "y", "w", "h"))
            if x >= 480 or y >= 800 or w < 8 or h < 8:
                continue
            left, top = x, y
            right, bottom = min(x + w, 480), min(y + h, 800)
            if right <= left or bottom <= top:
                continue
            touched += fill_rows(image[top:bottom, left:right])
        Image.fromarray(image).save(PICTURES / f"{picture}.png")
        total += touched
        if touched:
            print(f"{page:8} cleared {touched:5} sample pixel(s)")
    print(f"\n{total} sample pixel(s) removed from the K050 field boxes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
