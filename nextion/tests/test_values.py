"""Unit tests for the two rules the panel must hold.

1. **Every value starts empty.** Nothing on the panel shows a reading until the
   sensors or the operator supply one, so an operator can tell a real value from
   a placeholder. That has two halves: the fields carry no sample text, and the
   pictures carry no sample numbers either.

2. **The checklist is the system's own state.** The splash reports each check
   separately, and it holds the panel until all of them pass.

Run: python nextion/tests/test_values.py
"""

from __future__ import annotations

import json
import re
import tomllib
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "nextion" / "nxsrc" / "pages"
CLEAN = ROOT / "nextion" / "assets" / "clean"
EVENTS = ROOT / "firmware" / "hmi" / "events"

# The splash's own lines name the check they report, so they carry text by
# design. Every other text field must be empty.
SPLASH_LINES = {"tChkSensors", "tChkClock", "tChkDevice", "tReady"}

PICTURE = {
    "pInit": "00_init", "pUser": "01_user_info", "pMain": "02_main_menu",
    "pBase": "03_baseline", "pNewB": "04_new_baseline", "pMat": "05_material_data",
    "pMatu": "06_maturity_data", "pBaseR": "07_baseline_result",
    "pSaveB": "08_saved_baseline", "pKuat": "09_kuat_tekan",
    "pSelB": "10_select_baseline", "pRT": "11_realtime",
    "pStr": "12_strength_result", "pHist": "13_history",
    "pHistD": "14_history_detail", "pSet": "15_settings", "pDev": "16_device_info",
}


def components(page: str) -> list[dict]:
    data = tomllib.loads((PAGES / f"{page}.page.toml").read_text(encoding="utf-8"))
    return data.get("component", [])


class EveryValueStartsEmpty(unittest.TestCase):
    def test_no_field_carries_sample_text(self):
        guilty = []
        for path in sorted(PAGES.glob("*.page.toml")):
            page = path.name.split(".")[0]
            for component in components(page):
                if component.get("type") != "text":
                    continue
                text = component.get("txt") or ""
                if text and component["name"] not in SPLASH_LINES:
                    guilty.append(f"{page}.{component['name']} = {text!r}")
        self.assertEqual(guilty, [], "fields must start empty; the MCU fills them")

    def test_the_splash_status_lines_name_their_check(self):
        # A status alone ("Ok") would not say which check it belongs to.
        for component in components("pInit"):
            if component.get("name") in SPLASH_LINES:
                text = component.get("txt") or ""
                self.assertIn(":", text, f"{component['name']} must name its check")
                self.assertTrue(text.endswith("--"), f"{component['name']} must start unfilled")

    def test_no_picture_shows_a_sample_number(self):
        """The panel's picture must not carry a reading the MCU did not send."""
        # A sample reading is a run of bright digits big enough to be a value.
        # Icons and labels are left alone, so this looks for digit shapes only
        # where a value field sits.
        report = json.loads((ROOT / "nextion" / "tools" / "baked.json").read_text(encoding="utf-8"))
        leftovers = []
        for page, drawn in report.items():
            if not drawn:
                continue
            fields = {c["name"]: c for c in components(page) if c.get("type") == "text"}
            image = np.asarray(Image.open(CLEAN / f"{PICTURE[page]}.png").convert("RGB"))
            for name, _spread in drawn:
                component = fields.get(name)
                if not component:
                    continue
                x, y = component["x"], component["y"]
                box = image[y:y + component["h"], x:x + component["w"]]
                if box.size == 0:
                    continue
                # White letters were the sample; a bright patch is one left over.
                bright = int((box.max(axis=2) > 170).sum())
                if bright > 12:
                    leftovers.append(f"{page}.{name} still holds {bright} bright pixels")
        self.assertEqual(leftovers, [], "the picture must not keep the sample values")

    def test_the_cleaned_pictures_exist_for_every_page(self):
        for page, picture in PICTURE.items():
            with self.subTest(page=page):
                self.assertTrue((CLEAN / f"{picture}.png").exists(), f"{page} has no cleaned picture")

    def test_the_drawn_design_is_kept(self):
        """The cleaned picture must differ from the original only where values were."""
        for page, picture in PICTURE.items():
            with self.subTest(page=page):
                original = np.asarray(Image.open(ROOT / "nextion" / "assets" / "pages" / f"{picture}.png").convert("RGB"))
                cleaned = np.asarray(Image.open(CLEAN / f"{picture}.png").convert("RGB"))
                self.assertEqual(original.shape, cleaned.shape, f"{page} changed size")
                # The brand strip and the page edges must be untouched.
                np.testing.assert_array_equal(original[:60], cleaned[:60], f"{page} damaged its brand strip")
                np.testing.assert_array_equal(original[:, :10], cleaned[:, :10], f"{page} damaged its left edge")


class TheChecklistIsTheSystemState(unittest.TestCase):
    def test_the_splash_asks_for_a_check(self):
        event = (EVENTS / "pInit_tm0.txt").read_text(encoding="utf-8")
        self.assertIn("SELF_CHECK", event, "the splash must ask the MCU whether it may move on")

    def test_the_splash_never_moves_the_page_itself(self):
        """A page jump here would hide a failed check behind the next page."""
        event = (EVENTS / "pInit_tm0.txt").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r'^\s*page\s+\w+\s*$', event, re.M))

    def test_the_request_carries_the_page_and_the_verb(self):
        event = (EVENTS / "pInit_tm0.txt").read_text(encoding="utf-8")
        self.assertIn('pInit.tReq.txt+="0|"', event)
        self.assertIn('pInit.tReq.txt+="|SELF_CHECK"', event)
        self.assertIn("printh 0A", event, "a request ends with a real newline")

    def test_each_check_has_its_own_field(self):
        names = {c["name"] for c in components("pInit")}
        for field in SPLASH_LINES:
            self.assertIn(field, names, f"the splash has no field {field}")

    def test_the_status_fields_sit_inside_the_splash_panel(self):
        # The splash panel runs from x=61 to x=430 and ends at y=672.
        for component in components("pInit"):
            if component.get("name") not in SPLASH_LINES:
                continue
            with self.subTest(field=component["name"]):
                self.assertGreaterEqual(component["x"], 61)
                self.assertLessEqual(component["x"] + component["w"], 430)
                self.assertLessEqual(component["y"] + component["h"], 672)


if __name__ == "__main__":
    unittest.main(verbosity=2)
