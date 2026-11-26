"""Exercise the K050 simulator against the production Arduino parser and engine.

Pass the compiled arduino/tests/PanelHarness.cpp executable as the first argument.
nxwright must be on PATH. This uses a raw card image and sensor inputs on the host.
"""

from pathlib import Path
import json
import subprocess
import sys
import tomllib

import panel_arduino_test as api

ROOT = Path(__file__).resolve().parents[2]
api.SRC = ROOT / "nextion" / "nxsrc-K050"
LAYOUT = json.loads((ROOT / "nextion/tools/k050_web_layout.json").read_text())["pages"]


class Link:
    def __init__(self, executable, *args):
        self.panel = api.Panel()
        self.firmware = subprocess.Popen([str(executable), *args], stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, text=True, bufsize=1)
        self.seen = 0
        self.requests = []
        self.responses = []
        self.drop_next = False
        self.dropped = None
        self.startup_progress = []
        self.panel.start("pInit")

    def core(self, frame):
        self.firmware.stdin.write(frame + "\n")
        self.firmware.stdin.flush()
        encoded = self.firmware.stdout.readline()
        if not encoded:
            raise RuntimeError("Firmware harness stopped")
        return [line.decode("latin1") for line in bytes.fromhex(encoded.strip()).split(b"\xff\xff\xff") if line]

    def pump(self, ticks=1):
        for _ in range(ticks):
            self.panel.wait(250)
            frames = self.panel.frames()
            for frame in frames[self.seen:]:
                self.requests.append(frame)
                commands = self.core(frame)
                self.responses.extend(commands)
                if self.drop_next:
                    self.drop_next = False
                    self.dropped = frame
                    continue
                for instruction in commands:
                    self.panel.text("send", {"simulation": self.panel.simulation, "instruction": instruction})
            self.seen = len(frames)
            if self.value("pInit.vPage.val") == "0":
                value = self.value("tProgress.txt")
                if value.endswith("%"):
                    self.startup_progress.append(int(value[:-1]))

    def value(self, name):
        return self.panel.value(name)

    def wait_idle(self, limit=200):
        # A request may start in the event. Let its timer process the response.
        for _ in range(limit):
            self.pump()
            if self.value("pInit.vBusy.val") == "0":
                return
        raise AssertionError("Panel did not become idle")

    def tap(self, name):
        self.wait_idle()
        self.touch(name)
        self.pump(2)

    def touch(self, name):
        reply = self.panel.text("tap", {"simulation": self.panel.simulation, "component": name})
        if "error" in reply.lower():
            raise AssertionError(reply)

    def swipe(self, page, pixels, component=None, *, before_move=0, before_release=0):
        self.wait_idle()
        start = len(self.requests)
        layout = LAYOUT[page]
        if component:
            rect = layout["boxes"][component]["rect"]
        else:
            regions = layout["regions"]
            rows = regions.get("rows", regions.get("cards"))
            rect = rows[-1 if pixels < 0 else 0]
        x, y, w, h = rect
        touch = {"simulation": self.panel.simulation}
        assert self.panel.text("press", dict(touch, x=x + w // 2, y=y + h // 2)) == "Pressed."
        if before_move:
            self.panel.wait(before_move)
        assert self.panel.text("move", dict(touch, x=x + w // 2, y=y + h // 2 + pixels)) == "Moved."
        if before_release:
            self.panel.wait(before_release)
        assert self.panel.text("release", touch) == "Released."
        self.wait_idle()
        return self.requests[start:]

    def lab_action(self, *, sensor=False):
        self.wait_idle()
        slots = int(self.value("pInit.vLabSlots.val"))
        if slots == 5:
            self.tap("mSensor" if sensor else "mAddDay")
            return
        lab = LAYOUT["pMatu"]
        _, y, _, h = lab["regions"]["rows"][slots]
        x, _, w, button_height = lab["boxes"]["mSensor" if sensor else "mAddDay"]["rect"]
        reply = self.panel.text("tap", {"simulation": self.panel.simulation,
                                       "x": x + w // 2, "y": y + min(h, button_height) // 2})
        assert "error" not in reply.lower(), reply
        self.pump(2)

    def tap_during_read(self, name):
        for _ in range(30):
            self.pump()
            if (self.value("pInit.vBusy.val") == "1" and self.value("pInit.vTask.val") == "0" and
                    self.value("pInit.vGet.val") != "0"):
                self.touch(name)
                self.touch(name)
                self.wait_idle()
                return
        raise AssertionError("No read in progress")

    def edit(self, name, value):
        self.tap(name)
        assert self.value("tTitle.txt"), (name, "keyboard did not open")
        # Value injection replaces typing, while open/apply use real touch events.
        self.panel.set_text("tInput", value)
        self.tap("kSave")
        self.wait_idle()

    def close(self):
        self.panel.stop()
        self.firmware.terminate()
        self.firmware.wait(timeout=5)


def check_startup_with_missing_peripherals(executable):
    link = Link(executable)
    try:
        link.core("!UNAVAILABLE")
        link.pump(24)
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "1"
        assert 100 in link.startup_progress
        assert link.value("pInit.vStorage.val") == "6"
        assert link.value("pInit.vMask.val") == "0"
        assert link.value("tClock.txt") == "--:--"
        assert link.value("tBatt.txt") == "--%"
        assert not any(frame.endswith("|NAV|2") for frame in link.requests)
        link.tap("tClock")
        link.edit("tDate", "29-02-2024")
        link.tap("tTime")
        link.panel.set_text("tInput", "24:00:00")
        link.tap("kSave")
        assert link.value("tError.txt") == "Enter a valid time HH:MM or HH:MM:SS"
        link.panel.set_text("tInput", "08:30:00")
        link.tap("kSave")
        link.tap("mSave")
        assert link.value("tError.txt") == "Insert microSD to set the device clock"
        assert link.value("tDate.txt") == "29-02-2024"
        link.tap("mCancel")
        link.edit("tOp", "OP-17")
        assert link.value("tError.txt") == "Check the microSD card"
        link.tap("kCancel")
        link.core("!INSERT")
        link.core("!TICK|5")
        link.pump(16)
        link.wait_idle()
        assert link.value("pInit.vStorage.val") == "0"
        link.edit("tOp", "OP-17")
        link.edit("tProj", "SD INSERTED")
        link.edit("tDate", "24-11-2026")
        link.tap("mSave")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "2"
        link.tap("mDev")
        link.wait_idle()
        assert link.value("tDevStatus.txt") == "SET CLOCK"
        link.tap("tDevStatus")
        assert link.value("tTitle.txt") == "Device date and time"
        link.tap("mCancel")
        link.wait_idle()
        link.tap("mBack")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "2"
        link.core("!RESET")
        link.pump(40)
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "1"
        assert link.value("tProj.txt") == "SD INSERTED"
        assert link.value("tDate.txt") == "24-11-2026"
        link.tap("mSave")
        link.tap("mBase")
        link.tap("mNew")
        link.tap("mNext")
        link.tap("mNext")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "6"
        assert link.value("pInit.vLabSlots.val") == "1"
        assert link.value("tDay0.txt") == "0" and link.value("tT0.txt") == ""
        link.lab_action()
        link.tap("mLab")
        link.wait_idle()
        assert link.value("pInit.vLabSlots.val") == "2"
        assert [link.value(f"tDay{i}.txt") for i in range(2)] == ["0", "1"]
        assert [link.value(f"tT{i}.txt") for i in range(2)] == ["", ""]
        assert link.value("pInit.vLab0.val") != link.value("pInit.vLab1.val")
        assert link.value("pInit.vFocusId.val") == link.value("pInit.vLab1.val")
        link.tap("mGen")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "6"
        link.lab_action(sensor=True)
        link.wait_idle()
        assert any(frame.endswith("|ROW_SENSOR|1") for frame in link.requests)
        assert "Connect a temperature probe" in link.value("tNotice.txt")
        assert link.value("tT1.txt") == ""
    finally:
        link.close()


def check_long_lists(executable):
    link = Link(executable, "--long-lists")
    try:
        link.pump(24)
        link.tap("mSave")
        link.tap("mBase")
        link.tap("mSaved")
        link.wait_idle()
        assert [link.value(f"tName{i}.txt") for i in range(4)] == [
            f"Scroll baseline {i}" for i in (6, 5, 4, 3)]
        frames = link.swipe("pSaveB", -110, "mPick3")
        assert not any("|BASE_PICK|" in frame for frame in frames)
        assert link.value("pInit.vOffset.val") == "1"
        link.swipe("pSaveB", -380, "mDelete3")
        assert link.value("pInit.vOffset.val") == "2"
        assert link.value("tName3.txt") == "Scroll baseline 1"
        link.tap("mPick3")
        link.wait_idle()
        assert link.value("pInit.vChosen.val") == link.value("pInit.vId3.val")
        link.tap("mBack")
        link.tap("mBack")
        link.tap("mKuat")
        link.tap("mStart")
        link.wait_idle()
        link.swipe("pSelB", -160)
        assert link.value("pInit.vOffset.val") == "2"
        assert link.value("tName3.txt") == "Scroll baseline 1"
        link.tap("mResume")
        link.tap("mPoints")
        link.wait_idle()
        assert link.value("tDay0.txt") == "0"
        frames = link.swipe("pPoints", -155, "tTemp5")
        assert not any("|CHECK_SET|" in frame for frame in frames)
        assert link.value("pInit.vOffset.val") == "2"
        assert link.value("tDay0.txt") == "2" and link.value("tDay5.txt") == "7"
        link.swipe("pPoints", -80)
        assert link.value("pInit.vOffset.val") == "3" and link.value("tDay5.txt") == "8"
        link.tap("tTemp5")
        assert link.value("pInit.vEditRow.val") == "8"
        link.tap("kCancel")
        link.wait_idle()
        assert link.value("pInit.vOffset.val") == "3"
        link.tap("mBack")
        link.tap("mBack")
        link.tap("mBack")
        link.tap("mHist")
        link.wait_idle()
        assert [link.value(f"tName{i}.txt") for i in range(3)] == [
            f"Scroll baseline {i}" for i in (6, 5, 4)]
        frames = link.swipe("pHist", -270, "mHistory2")
        assert not any("|HISTORY_PICK|" in frame for frame in frames)
        assert link.value("pInit.vOffset.val") == "2"
        chosen = link.value("tId2.txt")
        assert link.value("tName2.txt") == "Scroll baseline 2"
        link.tap("mHistory2")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "14" and link.value("tId.txt") == chosen
        link.swipe("pHistD", -95)
        assert link.value("pInit.vOffset.val") == "2"
        assert link.value("tLog0.txt").startswith("Day 2 ")
        link.swipe("pHistD", -190)
        assert link.value("tLog4.txt").startswith("Day 8 ")
        link.tap("mBack")
        link.wait_idle()
        assert link.value("pInit.vOffset.val") == "2" and link.value("tId2.txt") == chosen
        link.swipe("pHist", -250)
        assert link.value("pInit.vOffset.val") == "3"
        assert link.value("tName2.txt") == "Scroll baseline 1"
        link.swipe("pHist", 400)
        assert link.value("pInit.vOffset.val") == "0"
    finally:
        link.close()


def main(executable):
    check_startup_with_missing_peripherals(executable)
    link = Link(executable)
    try:
        init = tomllib.loads((api.SRC / "pages/pInit.page.toml").read_text(encoding="utf-8"))
        assert "mContinue" not in {c["name"] for c in init["component"]}
        init_events = (api.SRC / "pages/pInit.nx").read_text(encoding="utf-8")
        assert "Database: OK" in init_events and "No sensor detected" in init_events
        user = tomllib.loads((api.SRC / "pages/pUser.page.toml").read_text(encoding="utf-8"))
        user_names = {c["name"] for c in user["component"]}
        assert "mStorage" not in user_names
        assert next(c for c in user["component"] if c["name"] == "tClock")["events"] == ["up"]
        dev = tomllib.loads((api.SRC / "pages/pDev.page.toml").read_text(encoding="utf-8"))
        dev_names = {c["name"] for c in dev["component"]}
        assert {"tDevVersion", "tDevSensor", "tDevSerial", "tDevStatus"} <= dev_names
        assert "mClock" not in dev_names
        assert next(c for c in dev["component"] if c["name"] == "tClock")["events"] == ["up"]
        detail = tomllib.loads((api.SRC / "pages/pHistD.page.toml").read_text(encoding="utf-8"))
        assert "tLastT" not in {c["name"] for c in detail["component"]}
        matu = tomllib.loads((api.SRC / "pages/pMatu.page.toml").read_text(encoding="utf-8"))
        matu_names = {c["name"] for c in matu["component"]}
        assert not ({"mAddEarly", "mFillEarly"} & matu_names)
        assert (api.SRC / "pages/pAddRow.page.toml").exists()
        rt = tomllib.loads((api.SRC / "pages/pRT.page.toml").read_text(encoding="utf-8"))
        assert next(c for c in rt["component"] if c["name"] == "mAddCheck")["h"] >= 48
        saved = tomllib.loads((api.SRC / "pages/pSaveB.page.toml").read_text(encoding="utf-8"))
        pick = next(c for c in saved["component"] if c["name"] == "mPick0")
        delete = next(c for c in saved["component"] if c["name"] == "mDelete0")
        assert pick["x"] + pick["w"] <= delete["x"] and delete["h"] >= 48
        link.pump(24)
        assert any("|GET|status" in r for r in link.requests)
        link.wait_idle()
        assert link.value("pInit.vStorage.val") == "0"
        assert link.value("pInit.vMask.val") == "7"
        progress_steps = []
        for percent in link.startup_progress:
            if not progress_steps or progress_steps[-1] != percent:
                progress_steps.append(percent)
        assert progress_steps == [0, 25, 50, 75, 100], progress_steps
        assert link.value("pInit.vPage.val") == "1"
        assert any(frame.split("|")[3] == "0" and frame.endswith("|NAV|1") for frame in link.requests)
        assert not any(frame.split("|")[3] == "0" and frame.endswith("|NAV|2") for frame in link.requests)
        link.tap("mSave")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "1"
        assert link.value("tNotice.txt") == "Complete the required fields"
        link.tap("tOp")
        assert link.value("tTitle.txt") == "Operator ID"
        for key in ("k18", "k19", "k37", "k00", "k06"):
            link.tap(key)
        assert link.value("tInput.txt") == "OP-17"
        link.tap("kSave")
        link.wait_idle()
        link.edit("tProj", "K050 TEST")
        link.tap("tDate")
        assert link.value("tTitle.txt") == "Date DD-MM-YYYY"
        assert link.value("pInit.vInputMode.val") == "3"
        for digit in "31022026":
            link.tap("kN" + digit)
        link.tap("kSave")
        assert link.value("tError.txt") == "Enter a valid date DD-MM-YYYY"
        link.tap("kClear")
        for digit in "24112026":
            link.tap("kN" + digit)
        assert link.value("tInput.txt") == "24-11-2026"
        link.tap("kSave")
        link.wait_idle()
        assert any(frame.endswith("|FIELD_SET|date|2026-11-24") for frame in link.requests)
        link.pump(5)
        assert link.value("tDate.txt") == "24-11-2026"
        link.tap("tClock")
        link.edit("tDate", "24-11-2026")
        assert link.value("tDate.txt") == "24-11-2026"
        link.tap("tTime")
        for digit in "120000":
            link.tap("kN" + digit)
        assert link.value("tInput.txt") == "12:00:00"
        link.tap("kSave")
        link.tap("mSave")
        link.wait_idle()
        assert any(frame.endswith("|CLOCK_SET|2026-11-24|12:00:00") for frame in link.requests)
        link.tap("mSave")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "2", link.value("tNotice.txt")
        link.tap("mDev")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "16"
        for adc, percent, color in ((877, "0%", "64329"), (920, "38%", "65132"),
                                    (991, "100%", "65535"), (0, "--%", "65535")):
            link.core(f"!BATTERY|{adc}")
            link.pump(12)
            assert link.value("tBatt.txt") == percent
            assert link.value("tBatt.pco") == color
        link.core("!TICK|61")
        link.pump(12)
        assert link.value("tClock.txt") == "12:01"
        assert link.value("tDevVersion.txt") == "1.0.1"
        assert link.value("tDevSensor.txt") == "3/3 connected"
        assert link.value("tDevStatus.txt") == "READY"
        link.drop_next = True
        link.pump(30)
        assert link.dropped and link.requests.count(link.dropped) >= 2
        link.wait_idle()
        link.tap("mBack")
        link.wait_idle()
        before_settings = sum(f.endswith("|NAV|15") for f in link.requests)
        link.tap_during_read("mSet")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "15"
        assert sum(f.endswith("|NAV|15") for f in link.requests) == before_settings + 1
        link.tap("mTap1")
        link.wait_idle()
        link.tap("mTap8")
        link.wait_idle()
        link.tap("mTap9")
        link.wait_idle()
        assert all("toggle" not in r and "|NAV|BACK" not in r for r in link.requests)
        link.tap("mSave")
        link.wait_idle()
        link.tap("mKuat")
        link.wait_idle()
        link.tap("mStart")
        link.wait_idle()
        link.tap("mStart")
        assert link.value("tStartHint.txt") == "Create a baseline first"
        assert not any(f.endswith("|MEASURE_START") for f in link.requests)
        link.tap("mBack")
        link.wait_idle()
        link.tap("mHist")
        link.wait_idle()
        assert link.value("tHistEmpty.txt") == "No measurements saved"
        assert not any("|HISTORY_PICK|" in f for f in link.requests)
        link.tap("mBack")
        link.wait_idle()
        link.tap("mBack")
        link.wait_idle()
        link.tap("mBase")
        link.wait_idle()
        link.tap("mNew")
        link.wait_idle()
        link.edit("tName", "K050 BASE")
        link.edit("tFc", "35")
        link.edit("tTemp", "-20")
        link.tap("mNext")
        link.wait_idle()
        link.edit("tCem", "380")
        link.edit("tWat", "190")
        assert float(link.value("tWC.txt")) == 0.5
        link.tap("mNext")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "6"
        assert link.value("pInit.vTotal.val") == "0"
        assert link.value("tDay0.txt") == "0"
        assert link.value("tTim0.txt") == "12:01"
        link.lab_action(sensor=True)
        link.wait_idle()
        assert any(frame.endswith("|ROW_SENSOR|0") for frame in link.requests)
        assert link.value("pInit.vTotal.val") == "1"
        assert float(link.value("tT0.txt")) == 26
        link.tap("tT0")
        assert link.value("pInit.vInputMode.val") == "2"
        link.tap("kCancel")
        link.wait_idle()
        assert link.value("pInit.vTotal.val") == "1"
        link.edit("tT0", "26")
        link.wait_idle()
        assert link.value("pInit.vTotal.val") == "1"
        link.tap("mInfo")
        link.wait_idle()
        assert link.value("tTitle.txt") == "Sample schedule"
        assert link.value("tPour.txt").startswith("Locked from start 24-11-2026 ")
        assert link.value("tDate0.txt") == "24-11-2026"
        assert link.value("tHari0.txt") == "Sel"
        assert link.value("tDate1.txt") == ""
        link.tap("mClose")
        link.wait_idle()
        link.lab_action()
        link.wait_idle()
        link.tap("mLab")
        link.wait_idle()
        assert link.value("pInit.vFocusId.val") == link.value("pInit.vLab1.val")
        link.lab_action(sensor=True)
        link.wait_idle()
        assert any(frame.endswith("|ROW_SENSOR|1") for frame in link.requests)
        assert float(link.value("tT1.txt")) == 26
        link.lab_action()
        link.wait_idle()
        link.tap("mLab")
        link.wait_idle()
        for i in range(3):
            link.edit(f"tT{i}", "26")
        link.edit("tFc1", "10")
        link.edit("tFc2", "20")
        link.lab_action()
        link.wait_idle()
        link.tap("mLab")
        link.wait_idle()
        for i in range(2):
            link.lab_action()
            link.wait_idle()
            link.tap("mLab")
            link.wait_idle()
        assert link.value("pInit.vTotal.val") == "6"
        assert link.value("pInit.vOffset.val") == "1"
        assert link.value("pInit.vFocusId.val") == link.value("pInit.vLab4.val")
        link.swipe("pMatu", 52, "tT0")
        assert link.value("pInit.vOffset.val") == "0"
        for i in (3, 4):
            link.edit(f"tT{i}", "26")
        frames = link.swipe("pMatu", -44, "mDelete4", before_release=10)
        assert not any("|ROW_DELETE|" in frame for frame in frames)
        assert link.value("pInit.vOffset.val") == "1" and link.value("pInit.vLabSlots.val") == "5"
        assert [link.value(f"tDay{i}.txt") for i in range(5)] == ["1", "2", "3", "4", "5"]
        assert any(frame.endswith("|GET|labrow|5") for frame in frames)
        link.swipe("pMatu", 52, "tT0")
        assert link.value("pInit.vOffset.val") == "0"
        link.swipe("pMatu", -90, "tFc4", before_move=110, before_release=10)
        assert link.value("pInit.vOffset.val") == "1"
        assert link.value("tDay0.txt") == "1"
        link.tap("mInfo")
        link.wait_idle()
        assert link.value("pInit.vOffset.val") == "0"
        link.swipe("pSchedule", -44)
        assert link.value("tDay0.txt") == "1"
        assert link.value("tDay4.txt") == "5"
        link.swipe("pSchedule", -44)
        assert link.value("tDay4.txt") == "5"
        link.swipe("pSchedule", 44, before_release=65)
        assert link.value("tDay0.txt") == "0"
        link.tap("mClose")
        link.wait_idle()
        assert link.value("pInit.vOffset.val") == "1"
        link.tap("tT4")
        link.tap("kCancel")
        link.wait_idle()
        assert link.value("pInit.vOffset.val") == "1"
        link.lab_action(sensor=True)
        link.wait_idle()
        assert any(frame.endswith("|ROW_SENSOR|5") for frame in link.requests)
        assert float(link.value("tT4.txt")) == 26
        link.swipe("pMatu", 52, "tT0")
        assert link.value("pInit.vOffset.val") == "0"
        link.tap("mDelete3")
        link.wait_idle()
        assert link.value("tTitle.txt") == "Confirm change"
        link.tap("mYes")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "6"
        link.tap("mGen")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "7", link.value("tNotice.txt")
        link.pump(12)
        assert link.value("tDate.txt") == "24-11-2026"
        for _ in range(180):
            link.pump()
            if link.value("vPlotPhase.val") == "3":
                break
        assert link.value("vPlotPhase.val") == "3", link.value("vPoint.val")
        assert link.value("vMaxX.val") == "20000"
        assert "ln(M)" in link.value("tEq.txt")
        assert any(frame.endswith("|GET|scatter|1") for frame in link.requests)
        curve_start = len(link.requests)
        link.tap("mCurve")
        for _ in range(180):
            link.pump()
            if link.value("vPlotPhase.val") == "3":
                break
        assert link.value("vPlotPhase.val") == "3", link.value("tError.txt")
        assert link.value("tError.txt") == ""
        assert sum("|GET|curve|" in frame for frame in link.requests[curve_start:]) == 65
        assert sum("|GET|scatter|" in frame for frame in link.requests[curve_start:]) == 2
        link.tap("mBack")
        link.wait_idle()
        link.tap("mSave")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "8", link.value("tNotice.txt")
        assert link.value("tName0.txt") == "K050 BASE"
        link.tap_during_read("mPick0")
        assert any(f.split("|")[3] == "8" and "|BASE_PICK|" in f for f in link.requests)
        assert link.value("pInit.vChosen.val") == link.value("pInit.vId0.val")
        link.tap("mBack")
        link.wait_idle()
        link.tap("mBack")
        link.wait_idle()
        link.tap("mKuat")
        link.wait_idle()
        link.tap("mStart")
        link.wait_idle()
        link.tap("mPick0")
        link.wait_idle()
        link.tap("mStart")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "11", link.value("tNotice.txt")
        link.core("!TICK|5")
        link.pump(12)
        assert link.value("tNowT.txt") == "12:01:06"
        assert link.value("tS1.txt") == "26.0 °C"
        assert link.value("tAvg.txt") == "26.0 °C"
        link.core("!TICK|86400")
        link.tap("mAddCheck")
        link.wait_idle()
        assert link.value("tNotice.txt") == "Day saved. Tap REAL TIME MONITORING."
        link.tap("mPoints")
        link.wait_idle()
        assert float(link.value("tTemp1.txt")) == 26
        assert link.value("tDate1.txt") == "25-11-2026"
        assert link.value("tTime1.txt") == "12:01:06"
        assert link.value("tDate2.txt") == ""
        link.tap("mGap1")
        assert link.value("tTitle.txt") == "Review interval, apply 0 to reconcile"
        link.tap("kCancel")
        link.wait_idle()
        link.edit("tDate1", "25-11-2026")
        assert any(frame.endswith("|CHECK_SET|1|date|2026-11-25") for frame in link.requests)
        link.edit("tTemp1", "27")
        link.wait_idle()
        assert float(link.value("tTemp1.txt")) == 27
        link.tap("mBack")
        link.wait_idle()
        link.tap("mNext")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "12", link.value("tNotice.txt")
        fc = link.value("tFc.txt")
        assert fc.endswith(" MPa") and float(fc.split()[0]) > 0
        assert link.value("tPct.txt").endswith("%")
        assert link.value("tM.txt").endswith(" °C·h")
        link.tap("mSave")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "13", link.value("tNotice.txt")
        assert link.value("tName0.txt") == "K050 BASE"
        assert link.value("tDate0.txt") == "25-11-2026"
        link.tap("mDetail")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "14", link.value("tNotice.txt")
        assert link.value("tOp.txt") == "OP-17"
        assert link.value("tSavedAt.txt") == "25-11-2026"
        assert "27" in link.value("tLog1.txt")
        previous_progress = len(link.startup_progress)
        link.core("!RESET")
        link.pump(40)
        assert link.value("pInit.vPage.val") == "1"
        assert 100 in link.startup_progress[previous_progress:]
        visited = {int(frame.split("|")[3]) for frame in link.requests}
        assert visited == set(range(17)), sorted(visited)
        print(json.dumps(dict(status="PASS", commands=len(link.requests),
                              domainPages=len(visited),
                              startupFlow="0-25-50-75-100%, automatic User Information, SAVE to Main Menu",
                              missingPeripherals="boot without SD, insert, save, recover after reset",
                              flow="connect, identity, clock, settings, lab input, GENERATE, SAVE baseline, "
                                   "select, START, checkpoint correction, NEXT, SAVE result, history detail",
                              reliability="keyboard taps, deletion confirmation, curve, UART retry, MCU reset/reconnect")), flush=True)
    finally:
        link.close()


if __name__ == "__main__":
    executable = Path(sys.argv[1]).resolve()
    main(executable)
    check_long_lists(executable)
    print(json.dumps(dict(status="PASS", scroll_pages=["pMatu", "pSchedule", "pSaveB", "pSelB",
                                                       "pPoints", "pHist", "pHistD"])), flush=True)
