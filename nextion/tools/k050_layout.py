"""Use browser-exported geometry and artwork for the K050 component layer."""

from pathlib import Path
from itertools import combinations
import json
import re

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = ROOT / "nextion" / "tools" / "k050_web_layout.json"
WEB = json.loads(LAYOUT.read_text(encoding="utf-8")) if LAYOUT.exists() else {"pages": {}, "pictures": []}
LAB_ROWS = 4
SURFACE = "#1a2029"


def control(name, text, x, y, w, h=54, *, primary=False, font=20, capacity=None):
    return dict(name=name, type="button", x=x, y=y, w=w, h=h, sta=1, font=f"NotoSans{font}",
                xcen=1, ycen=1, bco="#bc5208" if primary else "#303844", bco2="#88430f",
                pco="#ffffff", pco2="#ffffff", txt=text,
                txt_maxl=capacity if capacity is not None else max(len(text), 4), events=["up"])


def geometry(page, name):
    return WEB["pages"][page]["boxes"][name]["rect"]


def region(page, name):
    return WEB["pages"][page]["regions"][name]


def picture(page, state="picture"):
    return WEB["pages"][page].get(state, WEB["pages"][page]["picture"])


def picture_id(name):
    return WEB["pictures"].index(name)


def crop(page, rect, state="picture"):
    return "picq " + ",".join(map(str, (*rect, picture_id(picture(page, state)))))


def patch_at(page, xy, box, state="patch"):
    x, y = xy
    sx, sy, w, h = box
    return f"xpic {x},{y},{w},{h},{sx},{sy},{picture_id(picture(page, state))}"


def color_code(css):
    colors = [int(value) for value in re.findall(r'\d+', css)[:3]]
    return "#" + "".join(f"{value:02x}" for value in colors) if len(colors) == 3 else "#ffffff"


def font_size(pixel_size):
    return 28 if pixel_size >= 22 else 20 if pixel_size >= 16 else 16


def draw_value(page, name, target):
    spec = WEB["pages"][page]["boxes"][name]
    x, y, w, h = spec["rect"]
    font = {16: 0, 20: 1, 28: 2}[font_size(spec["font"])]
    color = int(color_code(spec["color"])[1:], 16)
    rgb565 = ((color >> 19) << 11) | (((color >> 10) & 63) << 5) | ((color >> 3) & 31)
    return f"xstr {x},{y},{w},{h},{font},{rgb565},0,{spec['align']},1,3,{target}.txt"


def local_text(name, value, capacity):
    return dict(name=name, type="variable", vscope=0, sta=1, txt=value, txt_maxl=capacity)


def default_capacity(name, old):
    if name in ("tNotice", "tError"):
        return 96
    if name.startswith("tLog"):
        return 200
    return max(64, old.get("txt_maxl", 0))


def component(page, name, spec, original):
    old = original.get(name, {})
    kind = spec["kind"]
    if kind == "draw" or spec.get("baked") and kind == "text":
        return local_text(name, spec.get("value", old.get("txt", "")), default_capacity(name, old))
    x, y, w, h = spec["rect"]
    if not (0 <= x < x + w <= 480 and 0 <= y < y + h <= 800):
        raise ValueError(f"{page}.{name} is outside the 480×800 canvas: {spec['rect']}")
    item = dict(name=name, x=x, y=y, w=w, h=h)
    if kind == "touch":
        return dict(item, type="hotspot", events=["up"])
    data_art = page == "pMatu" and re.fullmatch(r"(t(Day|Tim|Fc|T)|mDelete)\d", name)
    patch = "patch" if data_art or kind == "paint" or spec.get("patch") else "picture"
    txt = old.get("txt", "") if kind == "text" and page.startswith(("pEdit", "pNumber", "pConfirm")) else ""
    return dict(item, type="text", sta=0, picc=picture(page, patch), txt=txt,
                txt_maxl=default_capacity(name, old) if kind != "paint" else 1,
                font=f"NotoSans{font_size(spec['font'])}", pco=color_code(spec["color"]),
                xcen=spec["align"], ycen=1, events=old.get("events", []) if page not in DOMAIN else [])


DOMAIN = {"pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR", "pSaveB",
          "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev"}


def layout(page, document):
    if not WEB["pages"]:
        raise ValueError("Generate k050_web_layout.json with export_k050_web.mjs first")
    original = {c["name"]: c for c in document["component"]}
    artwork = WEB["pages"][page]
    document["page"].update(sta=2, pic=artwork["picture"])
    boxes = artwork["boxes"]
    document["component"] = [c for c in original.values() if "x" not in c and c["name"] not in boxes]
    for name, spec in boxes.items():
        document["component"].append(component(page, name, spec, original))
    visible = (c for c in document["component"] if "x" in c)
    for a, b in combinations(visible, 2):
        overlap_x = min(a["x"] + a["w"], b["x"] + b["w"]) > max(a["x"], b["x"])
        overlap_y = min(a["y"] + a["h"], b["y"] + b["h"]) > max(a["y"], b["y"])
        if overlap_x and overlap_y:
            raise ValueError(f"{page}.{a['name']} overlaps {b['name']} in the web export")
