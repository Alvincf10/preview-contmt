"""Compare a rendered page with its design picture, region by region."""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "nextion" / "assets" / "pages"
RENDER = Path("C:/Users/Alvin/AppData/Local/Temp/pages")

# Page name -> the design picture it was built from.
PICTURE = {
    "pInit": "00_init",
    "pUser": "01_user_info",
    "pMain": "02_main_menu",
    "pBase": "03_baseline",
    "pNewB": "04_new_baseline",
    "pMat": "05_material_data",
    "pMatu": "06_maturity_data",
    "pBaseR": "07_baseline_result",
    "pSaveB": "08_saved_baseline",
    "pKuat": "09_kuat_tekan",
    "pSelB": "10_select_baseline",
    "pRT": "11_realtime",
    "pStr": "12_strength_result",
    "pHist": "13_history",
    "pHistD": "14_history_detail",
    "pSet": "15_settings",
    "pDev": "16_device_info",
}

page = sys.argv[1] if len(sys.argv) > 1 else "pMat"
picture = PICTURE[page]
rendered = next(RENDER.glob(f"*_{page}.png"))
design = Image.open(DESIGN / f"{picture}.png").convert("RGB")
render = Image.open(rendered).convert("RGB")
print("design", design.size, "render", render.size)

# Side by side at full height, so any drawn difference is visible.
pair = Image.new("RGB", (design.width * 2 + 8, design.height), (255, 0, 0))
pair.paste(design, (0, 0))
pair.paste(render, (design.width + 8, 0))
out = Path("C:/Users/Alvin/AppData/Local/Temp") / f"pair_{page}.png"
pair.save(out)
print("wrote", out, "(left: design picture, right: built panel)")

# How much the built page differs from the picture, ignoring the reserve.
diff = 0
total = 0
for y in range(0, design.height, 3):
    for x in range(0, design.width, 3):
        total += 1
        if design.getpixel((x, y)) != render.getpixel((x, y)):
            diff += 1
print(f"pixels differing: {diff}/{total} = {100 * diff / total:.1f}%")

