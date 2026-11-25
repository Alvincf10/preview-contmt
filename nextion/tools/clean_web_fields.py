"""Use the web screenshots as backgrounds for pages 6-16.

The DOM screenshot already has every label, panel and button where the web shows
them. The only thing that must not stay is the sample value inside a field the
MCU writes, so this clears each field's box (inset a pixel or two) and copies the
result into the K050 picture folder. Pages 1-5 keep their design pictures.
"""
from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "nextion" / "nxsrc-K050" / "pages"
WEB = ROOT / "nextion" / "assets" / "web"
PICTURES = ROOT / "nextion" / "nxsrc-K050" / "pictures"

PICTURE = {
    "pMatu": "06_maturity_data", "pBaseR": "07_baseline_result",
    "pSaveB": "08_saved_baseline", "pKuat": "09_kuat_tekan",
    "pSelB": "10_select_baseline", "pRT": "11_realtime",
    "pStr": "12_strength_result", "pHist": "13_history",
    "pHistD": "14_history_detail", "pSet": "15_settings", "pDev": "16_device_info",
}
BRIGHT = 55


def fill_rows(region: np.ndarray) -> int:
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
    total = 0
    for page, picture in PICTURE.items():
        source = WEB / f"{picture}.png"
        if page == "pDev":
            shutil.copy2(source, PICTURES / f"{picture}.png")
            print(f"{page:8} copied static web screenshot")
            continue
        data = tomllib.loads((PAGES / f"{page}.page.toml").read_text(encoding="utf-8"))
        image = np.array(Image.open(source).convert("RGB"))
        cleared = 0
        for component in data.get("component", []):
            if component.get("type") not in ("text", "button") or component.get("sta") == 1:
                continue
            x, y, w, h = (component.get(k, 0) for k in ("x", "y", "w", "h"))
            if x >= 480 or y >= 800 or w < 8 or h < 8:
                continue
            left, top = x + 1, y + 1
            right, bottom = min(x + w - 1, 480), min(y + h - 1, 800)
            if right <= left or bottom <= top:
                continue
            cleared += fill_rows(image[top:bottom, left:right])
        Image.fromarray(image).save(PICTURES / f"{picture}.png")
        total += cleared
        print(f"{page:8} cleared {cleared:5} sample pixel(s)")
    print(f"\n{total} pixel(s) cleared in web backgrounds 6-16")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
