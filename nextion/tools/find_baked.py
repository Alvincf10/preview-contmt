"""Find the sample values baked into each page's picture.

The design was drawn with example data: a predicted strength of 35.4 MPa, a
maturity of 1,245, a date. Those pixels are part of the background picture, so a
panel that leaves its fields empty still shows that example data — and the
operator cannot tell it apart from a real reading.

This measures, for every text field that sits on the screen, how much the picture
varies inside the field's own box. A flat panel is a box with almost no
variation; a box holding drawn sample text varies a lot.
"""

import json
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PAGES_DIR = ROOT / "nextion" / "nxsrc" / "pages"
ASSETS = ROOT / "nextion" / "assets" / "pages"

# Built page name -> the picture it was drawn from.
PICTURE = {
    "pInit": "00_init", "pUser": "01_user_info", "pMain": "02_main_menu",
    "pBase": "03_baseline", "pNewB": "04_new_baseline", "pMat": "05_material_data",
    "pMatu": "06_maturity_data", "pBaseR": "07_baseline_result",
    "pSaveB": "08_saved_baseline", "pKuat": "09_kuat_tekan",
    "pSelB": "10_select_baseline", "pRT": "11_realtime",
    "pStr": "12_strength_result", "pHist": "13_history",
    "pHistD": "14_history_detail", "pSet": "15_settings", "pDev": "16_device_info",
}

# A box whose pixels vary less than this is flat panel; more means something is
# drawn in it.
FLAT = 18.0


def main() -> None:
    report = {}
    for page, picture in PICTURE.items():
        path = PAGES_DIR / f"{page}.page.toml"
        if not path.exists():
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        image = np.asarray(Image.open(ASSETS / f"{picture}.png").convert("RGB")).astype(float)

        drawn = []
        for component in data.get("component", []):
            if component.get("type") != "text":
                continue
            x, y, w, h = (component.get(k, 0) for k in ("x", "y", "w", "h"))
            if x >= 480 or y >= 800 or w < 4 or h < 4:
                continue
            x2, y2 = min(x + w, 480), min(y + h, 800)
            if x2 <= x or y2 <= y:
                continue
            box = image[y:y2, x:x2]
            spread = float(box.std(axis=(0, 1)).mean())
            if spread >= FLAT:
                drawn.append((component["name"], round(spread, 1)))
        report[page] = drawn

    total = sum(len(v) for v in report.values())
    for page, drawn in report.items():
        if drawn:
            print(f"{page:8} {len(drawn):3} field(s) over drawn sample data")
            for name, spread in drawn[:8]:
                print(f"    {name:14} spread {spread}")
    print(f"\n{total} field(s) sit on sample data baked into the picture")
    (ROOT / "nextion" / "tools" / "baked.json").write_text(
        json.dumps(report, indent=1) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
