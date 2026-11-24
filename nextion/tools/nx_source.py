#!/usr/bin/env python3
"""Emit an nxwright source folder for the ConMT HMI from the build kit.

The Input is the reviewable contract in ``firmware/hmi`` (manifest + event
snippets) plus the layout hints in ``nextion/pages``. The output is text files
that an editor or an agent can edit, and that ``nxwright build`` turns back
into a ``.HMI`` project file.

Layout rules, in the order they apply:

1. A component the kit already places keeps its coordinates.
2. Anything else flows down the page in a single column, so that every name in
   the manifest exists with a real hit box. These coordinates are placeholders:
   the design in ``nextion/assets/pages/*.png`` is the reference, not this.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "nextion"
HMI = ROOT / "firmware" / "hmi"
OUT = KIT / "nxsrc"
TOOLS = Path(__file__).resolve().parent

sys.path.insert(0, str(TOOLS))
from layout_map import LAYOUT as DESIGN  # noqa: E402
from hotspots_map import FALLBACK_VERB, HIDDEN_HOTSPOTS, HOTSPOTS  # noqa: E402
from find_narrow import LONGEST, need  # noqa: E402

PAGES_ORDER = [
    "pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR",
    "pSaveB", "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev",
]

# Where a tap area goes when the picture does not draw its button: beside the
# reserve fields, past the right edge.
RESERVE_HOTSPOT_X = 600

# The splash's own status lines. Its picture fills the panel with four checklist
# rows, 34 pixels apart, and each row's text runs nearly to the panel edge, so
# there is no room beside or below. A status therefore takes a whole row: it
# covers the sample line the picture drew there and prints the real state in its
# place. The height matches the row, or the sample below it would show through.
SPLASH_STATUS = {
    "tReady": (66, 512, 344, 34),
    "tChkClock": (66, 546, 344, 34),
    "tChkSensors": (66, 580, 344, 34),
    "tChkDevice": (66, 614, 344, 34),
}

# The splash panel's own fill, so a status line covers the sample text the
# picture draws in that row instead of printing over it.
SPLASH_PANEL = "#1e2326"

# What each status reads before the MCU has answered. The shape matches what the
# firmware writes, so the built file shows the splash as it will look.
SPLASH_SAMPLE = {
    "tChkSensors": "Checking Sensors: --",
    "tChkClock": "Checking Clock: --",
    "tChkDevice": "Checking Hardware: --",
    "tReady": "Starting Application: --",
}

SCREEN = "NX8048P070"  # 800x480 at rotation 90, so the page is 480x800
ROTATION = 90
ENCODING = "iso-8859-1"

WIDTH, HEIGHT = 480, 800
FONT_SMALL = "NotoSans16"
FONT_BODY = "NotoSans20"
FONT_BIG = "NotoSans28"

# Text roles: a field measured in the manifest is a value the MCU writes, so it
# gets room for the longest string the contract allows.
BIG_FIELDS = {"tM", "tFc", "tPct", "tAvg", "tFcLive", "tPctLive", "tS1", "tS2", "tS3"}

# Pages that show a scrolling list: the manifest gives row fields per row index.
ROW_PREFIXES = ("tId", "tName", "tVal", "tDate", "tCount", "tDay", "tAt", "tTmp", "tCm", "tCf", "tTim", "tFc", "tT", "tRid")

# Global variables the contract keeps on pInit, with their starting value.
GLOBALS = [
    ("vBoot", 0),
    ("vSeq", 0),
    ("vView", 0),
    ("vAck", 0),
    ("vStatus", 0),
    ("vBusy", 0),
    ("vRetry", 0),
    ("vRender", 0),
    ("vAckBoot", 0),
    ("vReqBoot", 0),
]

# Global texts the contract keeps on pInit: name -> (width, initial text, string capacity).
# `sta = 1` puts a Variable in string mode, which `covx` and `.txt` both need; a
# number-mode Variable refuses `.txt`, and every request snippet writes `tNum.txt`.
GLOBAL_TEXTS = {
    "tReq": (191, "", 191),
    "tNum": (16, "0", 16),
    "tEdit": (64, "", 64),
    "tDayInput": (24, "0", 24),
}

# Pages whose fields are read by the MCU, so a value is worth showing at rest.
PLACEHOLDER = "--"

# Fields the kit places but the design no longer draws. Their old coordinates
# would sit on top of the drawn design, so they go to the reserve instead: the
# MCU can still write them, and the visible page stays as the design has it.
NOT_IN_DESIGN = {
    "tMsg",
    "tM",
    "tRefDay",
    "tElapsed",
    "tPct",
    "tPDate",
    "tPour",
    "tInitTemp",
    "tRid0",
    "tRid1",
    "tRid2",
    "tRid3",
    "tRid4",
    "tRid5",
    "tInterval",
    "tSound",
    "tAuto",
}


def kit_pages() -> dict[str, dict]:
    pages = {}
    for path in sorted((KIT / "pages").glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        pages[page["name"]] = page
    return pages


def load_design() -> dict[str, dict]:
    """The preview's own boxes, per page, grouped by kind and in drawing order."""
    path = TOOLS / "layout.json"
    if not path.exists():
        raise SystemExit(
            f"{path} is missing: run `node nextion/tools/extract_layout.mjs` "
            "with `npm run dev` serving the preview"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for page, data in raw.items():
        groups: dict[str, list[dict]] = {}
        for element in data.get("elements", []):
            groups.setdefault(element["kind"], []).append(element)
        out[page] = groups
    return out


DESIGN_CACHE: dict[str, dict] = {}


def load_auto_hotspots() -> dict[str, list[dict]]:
    """The tap areas added for buttons the kit does not cover.

    `plan_hotspots.py` writes this from the design, so it is a file to read
    rather than a decision to repeat. Without it the panel has painted buttons
    that do nothing.
    """
    path = TOOLS / "auto_hotspots.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def auto_event(page: str, hotspot: dict) -> str:
    """The event for a generated hotspot, in the contract's own frame."""
    index = PAGES_ORDER.index(page)
    lines = [
        "if(pInit.vBusy.val==0&&pInit.vRender.val==0)",
        "{",
        "pInit.vSeq.val+=1",
        "pInit.vBusy.val=1",
        "pInit.vRetry.val=0",
        "pInit.vReqBoot.val=pInit.vBoot.val",
        'pInit.tReq.txt="CM1|"',
        "covx pInit.vBoot.val,pInit.tNum.txt,0,0",
        "pInit.tReq.txt+=pInit.tNum.txt",
        'pInit.tReq.txt+="|"',
        "covx pInit.vSeq.val,pInit.tNum.txt,0,0",
        "pInit.tReq.txt+=pInit.tNum.txt",
        'pInit.tReq.txt+="|"',
        f'pInit.tReq.txt+="{index}|"',
        "covx pInit.vView.val,pInit.tNum.txt,0,0",
        "pInit.tReq.txt+=pInit.tNum.txt",
        f'pInit.tReq.txt+="|{hotspot["verb"]}"',
    ]
    for arg in hotspot.get("args", []):
        lines.append('pInit.tReq.txt+="|"')
        lines.append(f'pInit.tReq.txt+="{arg}"')
    lines += ["prints pInit.tReq.txt,0", "printh 0A", "}"]
    return "\n".join(lines) + "\n"


def design_boxes_of(page: str) -> list[tuple[int, int, int, int]]:
    """Every box the design draws on a page, as a place a field cannot grow into."""
    boxes = []
    for kind in ("text", "input", "button", "chart"):
        for element in DESIGN_CACHE.get(page, {}).get(kind, []):
            boxes.append((element["x"], element["y"], element["w"], element["h"]))
    return boxes


def widen(page: str, rect: tuple[int, int, int, int], wanted: int, taken: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    """A field's box, widened to hold its value without running into a neighbour.

    The design sized each box to the sample it drew, and a sample like "—" is much
    shorter than the reading that replaces it. A box that is too narrow cuts the
    value off, so the box grows to the right until it has room, and stops at the
    first thing the design draws beside it.
    """
    x, y, w, h = rect
    if w >= wanted:
        return rect
    limit = WIDTH - x
    for tx, ty, tw, th in taken:
        # Only a neighbour that shares this field's row can limit it.
        if ty < y + h and y < ty + th and tx >= x + w:
            limit = min(limit, tx - x)
    return (x, y, max(w, min(wanted, limit)), h)


def hotspot_box(page: str, hotspot: str, kit_component: dict) -> tuple[int, int, int, int]:
    """The rectangle a hotspot should cover: the button the picture draws.

    The design's own buttons are the reference, because they are what the
    operator sees and taps. A hotspot whose page has no such button keeps the
    kit's coordinates, which are a fair guess for a layout the design draws
    differently.
    """
    label = HOTSPOTS.get(page, {}).get(hotspot)
    if label:
        for element in DESIGN_CACHE.get(page, {}).get("button", []):
            # A button the picture draws below the screen is not a target: it is a
            # row of a table the panel cannot show at once. Choosing it would put
            # the tap area off the screen, where nothing can reach it.
            if element["y"] + element["h"] // 2 >= HEIGHT or element["x"] + element["w"] // 2 >= WIDTH:
                continue
            text = (element.get("text") or "").strip()
            if text.upper().startswith(label.upper()):
                # Pad by a few pixels: a finger is wider than the drawn shape.
                return (element["x"] - 2, element["y"] - 2, element["w"] + 4, element["h"] + 4)
        # A card, a log row, or a delete button: matched by class, never by
        # position, so a card's tap area cannot land on the footer's BACK. A row
        # the picture does not draw has no place at all, so it is left out
        # rather than put over something else.
        for prefix, marker in (("card ", "-card"), ("log ", "log-toggle"), ("delete ", "mini-btn")):
            if label.lower().startswith(prefix):
                index = int(label.split()[1])
                cards = [b for b in DESIGN_CACHE.get(page, {}).get("button", []) if marker in (b.get("cls") or "")]
                if index < len(cards):
                    item = cards[index]
                    return (item["x"] - 2, item["y"] - 2, item["w"] + 4, item["h"] + 4)
                return None

        # A row of a lab table is tapped at its Temperature cell, not across the
        # row: the cells hold different values, so a tap over Fc must not open
        # the temperature entry.
        if label.lower().startswith("row "):
            index = int(label.split()[1])
            inputs = DESIGN_CACHE.get(page, {}).get("input", [])
            if index * 4 + 3 < len(inputs):
                cell = inputs[index * 4 + 3]
                return (cell["x"] - 2, cell["y"] - 2, cell["w"] + 4, cell["h"] + 4)
            return None

        # An input is a field the operator presses to edit it, so its tap area is
        # the box itself. The label names the box by the sample it holds.
        if label.lower().startswith("input "):
            sample = label.split(" ", 1)[1]
            for element in DESIGN_CACHE.get(page, {}).get("input", []):
                if (element.get("text") or "") == sample:
                    return (element["x"] - 2, element["y"] - 2, element["w"] + 4, element["h"] + 4)
            return (kit_component["x"], kit_component["y"], kit_component["w"], kit_component["h"])
    return (kit_component["x"], kit_component["y"], kit_component["w"], kit_component["h"])


def design_boxes(page: str) -> dict[str, dict]:
    """The design's boxes for one page, keyed `kind:position`.

    A mapping either names the text a box shows, or gives the box's place in
    reading order when the design shows it empty. Either way a mismatch fails
    here, with the page and field named, instead of moving a value somewhere
    wrong.
    """
    global DESIGN_CACHE
    if not DESIGN_CACHE:
        DESIGN_CACHE = load_design()
    groups = DESIGN_CACHE.get(page, {})
    boxes: dict[str, dict] = {}

    for field, (kind, expected, which) in DESIGN.get(page, {}).items():
        items = groups.get(kind, [])
        if not items:
            raise SystemExit(f"{page}.{field}: the design has no {kind} at all")

        if expected:
            # Elements of this kind whose text is exactly the sample. An exact
            # match matters here: a prefix match would let "0" grab "0.0 MPa".
            matches = [item for item in items if (item.get("text") or "") == expected]
            if which >= len(matches):
                seen = ", ".join(repr((i.get("text") or "")[:24]) for i in items[:10])
                raise SystemExit(
                    f"{page}.{field}: {kind} number {which + 1} reading {expected!r} is not in the "
                    f"design (that kind holds: {seen}). Update nextion/tools/layout_map.py"
                )
            boxes[field] = matches[which]
        else:
            # An empty box, addressed by its place in reading order.
            if which >= len(items):
                raise SystemExit(
                    f"{page}.{field}: {kind} {which} is past the design's {len(items)}. "
                    "Update nextion/tools/layout_map.py"
                )
            boxes[field] = items[which]

    return boxes


def toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    return f'"{escaped}"'


def table(name: str, body: dict) -> str:
    lines = [f"[{name}]"]
    lines += [f"{key} = {toml_value(value)}" for key, value in body.items()]
    return "\n".join(lines)


class Flow:
    """Finds a place for a field the design does not show.

    Most fields are placed by the design itself. The rest still have to exist,
    because the MCU writes to them by name, so they get the first free strip on
    the page: a cursor walks the page once, top to bottom, and never goes back.

    A page the design fills has no strip left, and a value drawn over the design
    would be worse than a value nobody sees. So those fields go to the reserve:
    a column just past the right edge of the screen. The component exists, holds
    its text, and answers the MCU, while the visible design stays exactly as
    drawn. `check_layout.py` reports them separately for that reason.
    """

    # The reserve sits past the right edge: a component that overlapped the
    # screen would either hide the design or, being later in the file, swallow
    # the taps meant for a button drawn there.
    #
    # The usable area stops above the footer. The footer is where the design
    # draws BACK and NEXT, and a field placed there would sit on top of them.
    TOP, BOTTOM = 96, 700
    LEFT, RIGHT = 8, 472
    GAP = 2
    RESERVE_X = 484
    RESERVE_PER_COLUMN = 28

    def __init__(self, taken, count, reserve_only=False):
        self.taken = list(taken)
        self.count = count
        self.reserve_only = reserve_only
        self.width = 96 if count <= 40 else 72 if count <= 90 else 56
        self.height = 24 if count <= 40 else 20 if count <= 90 else 16
        self.reserve = 0

    @property
    def font(self):
        """The face whose glyphs fit the strip these fields get."""
        return FONT_SMALL

    def _clear(self, x, y, w, h):
        for tx, ty, tw, th in self.taken:
            if x < tx + tw + self.GAP and tx - self.GAP < x + w and y < ty + th + self.GAP and ty - self.GAP < y + h:
                return False
        return True

    def place(self, w, h):
        """The next free strip on the page, or a slot in the reserve.

        With `reserve_only`, the field skips the page entirely: it is one the
        design does not show, so it must not draw over the design or take a
        touch meant for a button.
        """
        width = self.width
        height = max(min(h, self.height), 16)
        if not self.reserve_only:
            y = self.TOP
            while y + height <= self.BOTTOM:
                x = self.LEFT
                while x + width <= self.RIGHT:
                    if self._clear(x, y, width, height):
                        self.taken.append((x, y, width, height))
                        return x, y, width, height
                    x += width + self.GAP
                y += height + self.GAP
        # The page is the design's, so the field goes past the right edge.
        column, row = divmod(self.reserve, self.RESERVE_PER_COLUMN)
        x = self.RESERVE_X + column * 108
        y = 8 + row * (height + self.GAP)
        self.reserve += 1
        return x, y, width, height


def text_component(name: str, rect, attributes: dict) -> str:
    body = {"name": name, "type": "text"}
    if rect:
        body["x"], body["y"], body["w"], body["h"] = rect
    body.update(attributes)
    return "\n".join(["[[component]]"] + [f"{k} = {toml_value(v)}" for k, v in body.items()])


def hotspot_component(name: str, rect, events: list[str]) -> str:
    x, y, w, h = rect
    body = {"name": name, "type": "hotspot", "x": x, "y": y, "w": w, "h": h}
    lines = ["[[component]]"] + [f"{k} = {toml_value(v)}" for k, v in body.items()]
    lines.append("events = [" + ", ".join(toml_value(e) for e in events) + "]")
    return "\n".join(lines)


def picture_component(name: str, rect, pic: str) -> str:
    x, y, w, h = rect
    # `aph` is the picture's opacity: 0 would draw nothing at all, so the
    # attribute is left out and the type's default applies.
    body = {
        "name": name,
        "type": "picture",
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "pic": pic,
    }
    return "\n".join(["[[component]]"] + [f"{k} = {toml_value(v)}" for k, v in body.items()])


def event_file(page: str, component: str) -> str | None:
    path = HMI / "events" / f"{page}_{component}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")


def indent(code: str) -> str:
    return "\n".join("  " + line if line.strip() else "" for line in code.split("\n"))


def page_nx(page: str, hotspots: list[str], has_loadend: bool, timers: list[str] | None = None) -> str:
    """One `.nx` file: the page's events, its timers, then each tap area's press."""
    blocks: list[str] = []
    if has_loadend:
        ready = event_file(page, "postinitialize")
        if ready:
            blocks.append(f"// Postinitialize: the panel announces PAGE_READY.\non {page}.loadend:\n{indent(ready)}")
    for timer in timers or []:
        code = event_file(page, timer)
        if code:
            blocks.append(f"// Timer {timer}: runs while the page is showing.\non {timer}.timer:\n{indent(code)}")
    for component in hotspots:
        code = event_file(page, component)
        if code:
            blocks.append(f"on {component}.down:\n{indent(code)}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def add_fonts() -> None:
    """Draw the three fonts the pages use from Noto Sans, which nxwright ships."""
    import subprocess

    import nxwright

    face = Path(nxwright.__file__).parent / "project" / "fonts" / "NotoSans-Regular.ttf"
    for height, name in ((16, FONT_SMALL), (20, FONT_BODY), (28, FONT_BIG)):
        result = subprocess.run(
            ["nxwright", "font", str(OUT), str(face), str(height), "--name", name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(f"nxwright font {name} failed: {result.stderr.strip()}")


def nextion_colour(value: int) -> str:
    """A Nextion 565 colour as `#rrggbb`, the form a page file writes."""
    red = (value >> 11) & 0x1F
    green = (value >> 5) & 0x3F
    blue = value & 0x1F
    return "#%02x%02x%02x" % (red * 255 // 31, green * 255 // 63, blue * 255 // 31)


def build() -> dict:
    global AUTO_HOTSPOTS
    AUTO_HOTSPOTS = load_auto_hotspots()
    # The pictures are cleaned before they are copied, because the boxes a field
    # needs are only known once the page is laid out. `clean_pictures` reads the
    # boxes from `nxsrc`, which the previous run wrote, so this regenerates them
    # first and then cleans against the boxes this run will use.
    manifest = json.loads((HMI / "manifest.json").read_text(encoding="utf-8"))
    kit = kit_pages()

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "pages").mkdir(parents=True)
    (OUT / "pictures").mkdir()
    (OUT / "fonts").mkdir()

    pictures: list[str] = []
    # The pictures the panel carries are the cleaned ones: the design drew example
    # values into the original, and an operator must not see a sample reading it
    # cannot tell from a real one. Falling back to the originals would quietly put
    # those values back, so a missing cleaned set stops the build instead.
    sources = KIT / "assets" / "clean"
    if not list(sources.glob("*.png")):
        raise SystemExit(
            f"{sources} is empty: run `python nextion/tools/rebuild.py` to remove the "
            "sample values the design drew into the pictures"
        )
    for asset in sorted(sources.glob("*.png")):
        name = asset.stem
        shutil.copy2(asset, OUT / "pictures" / f"{name}.png")
        pictures.append(name)

    page_names = [page["name"] for page in manifest["pages"]]
    stats = {
        "placeholders": 0,
        "placed_from_kit": 0,
        "placed_from_design": 0,
        "hotspots": 0,
        "generated_hotspots": 0,
        "events": 0,
        "events_from_fallback": 0,
    }

    for entry in manifest["pages"]:
        name = entry["name"]
        source = kit.get(name, {})
        components = source.get("components", [])

        known = {c["objname"]: c for c in components}
        design = DESIGN.get(name, {})
        boxes = design_boxes(name)
        used_boxes: list[tuple[int, int, int, int]] = []

        tables: list[str] = [
            table(
                "page",
                {
                    "name": name,
                    "type": "page",
                    "x": 0,
                    "y": 0,
                    "w": WIDTH,
                    "h": HEIGHT,
                },
            )
        ]

        # The background picture is the page itself, taken from the kit.
        for component in components:
            if component["type"] == "Picture":
                pic = Path(component["pic"]).stem
                rect = (component["x"], component["y"], component["w"], component["h"])
                tables.append(picture_component(component["objname"], rect, pic))

        # Tap areas are collected now and written last, so they sit on top. A
        # component later in the page's list takes the touch, so a field drawn
        # over a button would otherwise swallow every tap meant for it.
        hotspot_tables: list[str] = []
        hotspots: list[str] = []
        for component in components:
            if component["type"] != "TouchCap":
                continue
            name_of_hotspot = component["objname"]
            box = hotspot_box(name, name_of_hotspot, component)
            if box is None:
                # The picture does not draw this row, so there is no place for a
                # tap area. Its event stays available to the MCU, but nothing is
                # laid over the design or over a neighbour.
                stats["rows_hidden"] = stats.get("rows_hidden", 0) + 1
                if event_file(name, name_of_hotspot):
                    stats["events"] += 1
                continue
            hidden = name_of_hotspot in HIDDEN_HOTSPOTS.get(name, [])
            rect = (
                # A tap area the picture does not draw goes to the reserve: the
                # action stays reachable for the MCU, and no stray area sits over
                # the design.
                (RESERVE_HOTSPOT_X, 8 + 26 * len(hotspots), 40, 22)
                if hidden
                else box
            )
            events = ["down", "up"]
            if hidden:
                stats["hidden_hotspots"] = stats.get("hidden_hotspots", 0) + 1
            if event_file(name, name_of_hotspot):
                stats["events"] += 1
            else:
                stats["events_from_fallback"] += 1
            hotspots.append(name_of_hotspot)
            hotspot_tables.append(hotspot_component(name_of_hotspot, rect, events))
        stats["hotspots"] += len(hotspots)

        # Tap areas for the buttons the kit does not cover. The design draws
        # them; without a hotspot the operator taps a painted shape and nothing
        # answers.
        for extra in AUTO_HOTSPOTS.get(name, []):
            rect = (extra["x"], extra["y"], extra["w"], extra["h"])
            hotspot_tables.append(hotspot_component(extra["name"], rect, ["down", "up"]))
            hotspots.append(extra["name"])
            stats["hotspots"] += 1
            stats["generated_hotspots"] += 1
            path = HMI / "events" / f"{name}_{extra['name']}.txt"
            if not path.exists():
                path.write_text(auto_event(name, extra), encoding="utf-8")
            stats["events"] += 1

        # Timers.
        timers: list[str] = []
        for component in components:
            if component["type"] == "Timer":
                body = {
                    "name": component["objname"],
                    "type": "timer",
                    "tim": component.get("tim", 500),
                    "en": component.get("en", 1),
                }
                lines = ["[[component]]"] + [f"{k} = {toml_value(v)}" for k, v in body.items()]
                lines.append('events = ["timer"]')
                tables.append("\n".join(lines))
                timers.append(component["objname"])

        # The globals live on pInit, so every page can reach them. A Variable
        # has no place on the screen, so these carry no geometry.
        if name == "pInit":
            for text_name, (_capacity, initial, txt_maxl) in GLOBAL_TEXTS.items():
                body = {
                    "name": text_name,
                    "type": "variable",
                    "vscope": 1,
                    "sta": 1,
                    "txt": initial,
                    "txt_maxl": txt_maxl,
                }
                tables.append("\n".join(["[[component]]"] + [f"{k} = {toml_value(v)}" for k, v in body.items()]))
            for var_name, start_value in GLOBALS:
                body = {
                    "name": var_name,
                    "type": "variable",
                    "vscope": 1,
                    "val": start_value,
                }
                tables.append("\n".join(["[[component]]"] + [f"{k} = {toml_value(v)}" for k, v in body.items()]))

        # Every text the contract names. A field with a place in the design goes
        # there; the rest fall back to the kit, then to a free space.
        pending: list[str] = []
        for field in entry["textComponents"]:
            if name == "pInit" and field in GLOBAL_TEXTS:
                continue
            big = field in BIG_FIELDS
            box = boxes.get(field)
            component = known.get(field)
            kit_rect = None
            if component and all(key in component for key in ("x", "y", "w", "h")):
                kit_rect = (component["x"], component["y"], component["w"], component["h"])

            if box:
                rect = (box["x"], box["y"], box["w"], box["h"])
                used_boxes.append(rect)
                stats["placed_from_design"] += 1
            elif field in SPLASH_STATUS:
                # The splash has no free space: the picture fills its panel with
                # the checklist. These four fields sit at the right end of the
                # row each one reports, which is where an operator looks for the
                # answer anyway.
                rect = SPLASH_STATUS[field]
                used_boxes.append(rect)
                stats["placed_from_design"] += 1
            elif kit_rect and field in NOT_IN_DESIGN:
                # The kit once placed this field, but the design no longer
                # draws it. A stale coordinate would sit on top of the design,
                # so it goes to the reserve with the other hidden fields.
                pending.append(field)
                continue
            elif kit_rect:
                rect = kit_rect
                used_boxes.append(rect)
                stats["placed_from_kit"] += 1
            else:
                pending.append(field)
                continue

            attributes = {}
            # The design's picture already holds the sample value, the box's
            # fill and its border. A field must therefore draw nothing but its
            # own letters when the MCU writes one, or it paints a second value
            # and a white block over the design. `sta = 3` means no background
            # at all, so the page shows through.
            #
            # The splash is the exception: its picture draws a sample checklist
            # in the exact rows these statuses occupy, so they need a background
            # of their own to sit on. The colour is the panel's own fill there.
            attributes["sta"] = 3
            if field in SPLASH_STATUS:
                attributes["sta"] = 1
                attributes["bco"] = SPLASH_PANEL
                # A sample in the same shape the MCU writes, so the built file
                # shows the splash as it looks before anything is connected.
                attributes["txt"] = SPLASH_SAMPLE.get(field, "")
                attributes["txt_maxl"] = 40
            else:
                # Empty by default: the picture already shows a sample, and the
                # MCU fills the real value.
                attributes["txt"] = ""
                attributes["txt_maxl"] = 32
            if component and "pco" in component:
                attributes["pco"] = nextion_colour(component["pco"])
            elif box and box.get("colour"):
                attributes["pco"] = nextion_colour(box["colour"])
            else:
                attributes["pco"] = "#ffffff"
            attributes["font"] = FONT_BIG if big else (FONT_BODY if (kit_rect or box) else FONT_SMALL)
            wanted = need(field)
            if wanted:
                # The design sized this box to the sample it drew; the value the
                # MCU writes needs more room, or it is cut off. Every place the
                # design draws something can stop the growth, whether or not that
                # neighbour has been placed yet.
                obstacles = used_boxes + [b for b in design_boxes_of(name) if b != rect]
                rect = widen(name, rect, wanted, obstacles)
            tables.append(text_component(field, rect, attributes))

        # The few fields the design does not show still have to exist, because
        # the MCU writes to them. They go where nothing else is drawn, and on a
        # dense page they are allowed to be narrower than a comfortable width.
        if pending:
            taken = list(used_boxes)
            for component in components:
                if component["type"] == "Picture" and component.get("w") == WIDTH:
                    continue
                # A hotspot is a transparent tap area, so a field may sit under
                # it: that is exactly how the design makes a value tappable.
                if component["type"] == "TouchCap":
                    continue
                if all(key in component for key in ("x", "y", "w", "h")):
                    taken.append((component["x"], component["y"], component["w"], component["h"]))
            flow = Flow(taken, len(pending), reserve_only=True)
            for field in pending:
                big = field in BIG_FIELDS
                rect = flow.place(0, 34 if big else 24)
                stats["placeholders"] += 1
                # These fields exist for the MCU, not for the operator: the
                # design does not draw a box for them, so drawing one would put
                # a stray value over the picture. `sta = 3` and an empty text
                # keep them invisible until the MCU writes, and they sit in the
                # reserve so they never take a touch meant for a button.
                attributes = {
                    "sta": 3,
                    "txt": "",
                    "txt_maxl": 24,
                    "pco": "#ffffff",
                    "font": FONT_BIG if big else flow.font,
                }
                tables.append(text_component(field, rect, attributes))

        (OUT / "pages" / f"{name}.page.toml").write_text("\n\n".join(tables + hotspot_tables) + "\n", encoding="utf-8")
        has_loadend = (HMI / "events" / f"{name}_postinitialize.txt").exists()
        # A timer's event is taken from the contract when it has one. The kit's
        # own `pInit_tm0.txt` is deliberately not copied: it jumps straight to
        # pUser, and navigation in this contract belongs to the MCU.
        (OUT / "pages" / f"{name}.nx").write_text(page_nx(name, hotspots, has_loadend, timers), encoding="utf-8")

    app_toml = "\n".join(
        [
            "format = 1",
            'name = "ConMT"',
            'language = "nextion_do_not_change_manually"  # use `nxwright language` to switch',
            f'screen = "{SCREEN}"',
            f"rotation = {ROTATION}",
            f'encoding = "{ENCODING}"',
            "pages = [",
            *[f"    {toml_value(page)}," for page in page_names],
            "]",
            "pictures = [",
            *[f"    {toml_value(pic)}," for pic in pictures],
            "]",
            "fonts = []",
        ]
    )
    (OUT / "app.toml").write_text(app_toml + "\n", encoding="utf-8")

    program = [
        "// Runs once at power-on: the shared variables, the settings, then the",
        "// page that opens the connection handshake.",
        "int sys0=0,sys1=0,sys2=0",
        "baud=9600",
        "dim=100",
        "recmod=0",
        "printh 00 00 00 ff ff ff 88 ff ff ff",
        "page 0",
    ]
    (OUT / "program.nx").write_text("\n".join(program) + "\n", encoding="utf-8")
    add_defaults()
    add_fonts()
    return stats


def add_defaults() -> None:
    """nxwright's own component defaults, which a source folder always carries."""
    import nxwright

    source = Path(nxwright.__file__).parent / "project" / "component_defaults.toml"
    shutil.copy2(source, OUT / "defaults.toml")


if __name__ == "__main__":
    result = build()
    print(json.dumps(result))
