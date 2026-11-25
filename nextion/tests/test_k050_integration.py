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


class Link:
    def __init__(self, executable):
        self.panel = api.Panel()
        self.firmware = subprocess.Popen([str(executable)], stdin=subprocess.PIPE,
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
        reply = self.panel.text("tap", {"simulation": self.panel.simulation, "component": name})
        if "error" in reply.lower():
            raise AssertionError(reply)
        self.pump(2)

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
        assert not any(frame.endswith("|NAV|2") for frame in link.requests)
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
        assert next(c for c in user["component"] if c["name"] == "mClock")["type"] == "hotspot"
        dev = tomllib.loads((api.SRC / "pages/pDev.page.toml").read_text(encoding="utf-8"))
        dev_names = {c["name"] for c in dev["component"]}
        assert not ({"tSupply", "tStorage", "tMcu", "tProtocol",
                     "tVersion", "tSensors", "tStatus"} & dev_names)
        matu = tomllib.loads((api.SRC / "pages/pMatu.page.toml").read_text(encoding="utf-8"))
        matu_names = {c["name"] for c in matu["component"]}
        assert not ({"mAddEarly", "mFillEarly"} & matu_names)
        assert (api.SRC / "pages/pAddRow.page.toml").exists()
        rt = tomllib.loads((api.SRC / "pages/pRT.page.toml").read_text(encoding="utf-8"))
        assert next(c for c in rt["component"] if c["name"] == "mAddCheck")["type"] == "hotspot"
        saved = tomllib.loads((api.SRC / "pages/pSaveB.page.toml").read_text(encoding="utf-8"))
        assert next(c for c in saved["component"] if c["name"] == "mDelete0")["type"] == "hotspot"
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
        for key in ("k18", "k19", "k37", "k00", "k06"):
            link.tap(key)
        assert link.value("tInput.txt") == "OP-17"
        link.tap("kSave")
        link.wait_idle()
        link.edit("tProj", "K050 TEST")
        link.edit("tDate", "2026-11-24")
        link.tap("mClock")
        link.edit("tDate", "2026-11-24")
        link.edit("tTime", "12:00:00")
        link.tap("mSave")
        link.wait_idle()
        link.tap("mSave")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "2", link.value("tNotice.txt")
        link.tap("mDev")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "16"
        link.drop_next = True
        link.pump(30)
        assert link.dropped and link.requests.count(link.dropped) >= 2
        link.wait_idle()
        link.tap("mBack")
        link.wait_idle()
        link.tap("mSet")
        link.wait_idle()
        link.tap("mTap1")
        link.wait_idle()
        link.tap("mTap8")
        link.wait_idle()
        link.tap("mTap9")
        link.wait_idle()
        assert all("toggle" not in r and "|NAV|BACK" not in r for r in link.requests)
        link.tap("mSave")
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
        link.tap("mAddDay")
        link.wait_idle()
        link.tap("mEarly")
        link.wait_idle()
        link.tap("mAddDay")
        link.wait_idle()
        link.tap("mLab")
        link.wait_idle()
        link.tap("mAddDay")
        link.wait_idle()
        link.tap("mLab")
        link.wait_idle()
        for i in range(3):
            link.edit(f"tT{i}", "26")
        link.edit("tFc1", "10")
        link.edit("tFc2", "20")
        link.tap("mAddDay")
        link.wait_idle()
        link.tap("mLab")
        link.wait_idle()
        link.tap("mDelete3")
        link.wait_idle()
        assert link.value("tTitle.txt") == "Confirm change"
        link.tap("mYes")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "6"
        link.tap("mGen")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "7", link.value("tNotice.txt")
        link.tap("mCurve")
        for _ in range(160):
            link.pump()
            if link.value("vPoint.val") == "65":
                break
        assert link.value("vPoint.val") == "65", link.value("tError.txt")
        link.tap("mBack")
        link.wait_idle()
        link.tap("mSave")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "8", link.value("tNotice.txt")
        assert link.value("tName0.txt") == "K050 BASE"
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
        link.core("!TICK|86400")
        link.tap("mAddCheck")
        link.wait_idle()
        link.tap("mPoints")
        link.wait_idle()
        assert float(link.value("tTemp1.txt")) == 26
        link.edit("tTemp1", "27")
        link.wait_idle()
        assert float(link.value("tTemp1.txt")) == 27
        link.tap("mBack")
        link.wait_idle()
        link.tap("mNext")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "12", link.value("tNotice.txt")
        assert float(link.value("tFc.txt")) > 0
        link.tap("mSave")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "13", link.value("tNotice.txt")
        assert link.value("tName0.txt") == "K050 BASE"
        link.tap("mDetail")
        link.wait_idle()
        assert link.value("pInit.vPage.val") == "14", link.value("tNotice.txt")
        assert link.value("tOp.txt") == "OP-17"
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
                              missingPeripherals="initialization completes and opens User Information",
                              flow="connect, identity, clock, settings, lab input, GENERATE, SAVE baseline, "
                                   "select, START, checkpoint correction, NEXT, SAVE result, history detail",
                              reliability="keyboard taps, deletion confirmation, curve, UART retry, MCU reset/reconnect")), flush=True)
    finally:
        link.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
