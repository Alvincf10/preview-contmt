#!/usr/bin/env python3
"""Run the panel against a stand-in Arduino MCU.

The panel speaks the protocol in `arduino/ConMT/src/Panel.cpp`. It sends a CM1
frame; the firmware answers by writing `tData` with a page's values as
pipe-separated columns, then `nAckValue`, `nAckCode`, and `nAckSeq` last.

This stands in for that firmware, so the panel can be tried without hardware. It
does not run the ConMT application: it answers with sample values shaped exactly
like the firmware's, which is enough to prove the two things that matter most:

- the panel sends a frame the firmware would accept;
- the panel splits `tData` into the right fields.

Run: python nextion/tests/panel_arduino_test.py
"""

from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "nextion" / "nxsrc"

# A page's answer, as the firmware writes it: columns joined by '|'.
#
# The values are shaped like real ones so a split that reads the wrong index
# produces something obviously wrong - a date where a number belongs, say.
ANSWERS = {
    "status": (
        "2026-09-28|08:00|5000|87|0|1|300|80|0|1.0.0"
        "|25.6|25.8|25.7|25.7|7|0|0|1|0|0"
    ),
    "identity": "OP001|HK Tower|2026-09-28",
    "baseline": "1|Beton Fc30|30.0|-20.0|2026-09-28|08:00|6|1|1",
    "savedrow": "1|Beton Fc30|30.0|-20.0|2026-09-28|08:00|6|1|1",
    "mix": "450|180|1020|780|0.8|Sika|-|Holcim|0.0|15|0.40",
    "model": "-61.9670|9.4932|0.9780|6|3|5000|OP001|HK Tower|2026-09-28",
    "labrow": "1|0|2026-09-28|08:00|27.4|5.2|0",
    "run": (
        "1|1|6|0|2026-09-28|08:00|2026-09-28|14:00|25.7|21600"
        "|1245|35.4|118"
    ),
    "detail": (
        "1|2026-09-28|14:00|OP001|HK Tower|2026-09-28"
        "|1|1|6|0|2026-09-28|08:00|2026-09-28|14:00|25.7|21600|1245|35.4|118"
    ),
    "point": "0|2026-09-28|08:00|25.7|0|0.0|0|0|25.6|25.8|25.7|25.7|7",
    "historyrow": "1|Beton Fc30|2026-09-28|14:00|35.4|6|0",
}


class Mcu:
    """A stand-in for the Arduino firmware, answering through the simulator.

    The firmware answers a request by writing `tData` with the source's columns,
    then `nAckValue` and `nAckCode`, and `nAckSeq` last. That order matters: the
    panel treats a matching `nAckSeq` as the moment the answer is complete.
    """

    def __init__(self, panel: "Panel") -> None:
        self.panel = panel
        self.answered: set[str] = set()

    def serve(self) -> bool:
        """Answer the request the panel is waiting on, if there is one."""
        frames = self.panel.frames()
        if not frames:
            return False
        if self.panel.value("pInit.vBusy.val") != "1":
            return False

        frame = frames[-1]
        parts = frame.split("|")
        if len(parts) < 6:
            return False
        seq = parts[2]
        verb = parts[5]
        source = parts[6] if verb == "GET" and len(parts) > 6 else "status"

        # Only answer each request once.
        key = f"{verb}:{seq}:{source}"
        if key in self.answered:
            return False
        self.answered.add(key)

        self.panel.set_text("pInit.tData", ANSWERS[source])
        self.panel.set_number("pInit.nAckValue", 0)
        self.panel.set_number("pInit.nAckCode", 0)
        # Written last: this is what tells the panel the answer is complete.
        self.panel.set_number("pInit.nAckSeq", int(seq or 0))
        return True

    def run(self, ticks: int = 20) -> None:
        for _ in range(ticks):
            self.serve()
            self.panel.wait(200)


class Panel:
    """The panel, driven through nxwright's simulator."""

    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            ["nxwright", "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self.next_id = 0
        self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "arduino", "version": "1"},
        })
        self.proc.stdin.write(json.dumps({
            "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
        }) + "\n")
        self.proc.stdin.flush()
        self.simulation = None

    def _rpc(self, method: str, params: dict) -> dict:
        self.next_id += 1
        payload = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise SystemExit("the simulator closed")
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") == self.next_id:
                return message

    def text(self, name: str, args: dict) -> str:
        result = self._rpc("tools/call", {"name": name, "arguments": args})
        if "error" in result:
            return "ERROR " + json.dumps(result["error"])[:200]
        return "".join(
            c.get("text", "") for c in result.get("result", {}).get("content", [])
            if c.get("type") == "text"
        )

    def start(self, page: str) -> None:
        reply = self.text("start_simulation", {"source_folder": str(SRC), "page": page})
        self.simulation = json.loads(reply)["simulation"]

    def frames(self) -> list[str]:
        log = self.text("log", {"simulation": self.simulation})
        chunks = []
        for match in re.finditer(r'"line"\s*:\s*"SIM SEND:\s*([0-9a-fA-F ]+)"', log):
            try:
                chunks.append(bytes.fromhex(match.group(1).replace(" ", "")).decode("latin1"))
            except ValueError:
                continue
        return [frame for frame in "".join(chunks).split("\n") if frame]

    def value(self, name: str) -> str:
        """Read one value from the page shown.

        The globals live on pInit, but in nxwright's simulator a page's own
        components are named without the page prefix on that page: `vBusy.val`
        while pInit shows, `pInit.vBusy.val` from anywhere else. Both spellings
        are tried, and each is asked for on its own: the simulator refuses the
        whole call when one of the names is missing, so asking for two at once
        would hide the one that exists.
        """
        candidates = [name]
        if name.startswith("pInit."):
            candidates.append(name[6:])
        else:
            candidates.append("pInit." + name)
        for candidate in candidates:
            reply = self.text("values", {"simulation": self.simulation, "names": [candidate]})
            try:
                data = json.loads(reply)
            except json.JSONDecodeError:
                continue
            if candidate in data and str(data[candidate]) != "":
                return str(data[candidate])
        return ""

    def set_text(self, name: str, value: str) -> None:
        self.text("send", {"simulation": self.simulation, "instruction": f'{name}.txt="{value}"'})

    def set_number(self, name: str, value: int) -> None:
        self.text("send", {"simulation": self.simulation, "instruction": f"{name}.val={value}"})

    def wait(self, milliseconds: int = 400) -> None:
        self.text("wait", {"simulation": self.simulation, "milliseconds": milliseconds})

    def stop(self) -> None:
        if self.simulation:
            self.text("stop_simulation", {"simulation": self.simulation})
        self.proc.kill()


class ArduinoProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.panel = Panel()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.panel.stop()

    def test_the_first_frame_is_page_ready_without_a_version(self):
        """The firmware refuses PAGE_READY that carries a version suffix."""
        self.panel.start("pUser")
        Mcu(self.panel).run(ticks=4)
        frames = self.panel.frames()
        self.assertTrue(frames, "the panel sent nothing")
        ready = [f for f in frames if "PAGE_READY" in f]
        self.assertTrue(ready, f"no PAGE_READY in {frames}")
        # CM1|boot|seq|page|view|PAGE_READY - five separators, no sixth field.
        self.assertEqual(ready[0].count("|"), 5, f"{ready[0]!r} has extra fields")

    def test_the_panel_asks_for_the_data_it_shows(self):
        self.panel.start("pUser")
        Mcu(self.panel).run(ticks=8)
        frames = self.panel.frames()
        self.assertTrue(any("GET" in f and "identity" in f for f in frames), frames)

    def test_the_split_puts_each_column_in_its_field(self):
        """A wrong index would put the wrong value in a field."""
        self.panel.start("pUser")
        Mcu(self.panel).run()
        self.assertEqual(self.panel.value("tOp.txt"), "OP001")
        self.assertEqual(self.panel.value("tProj.txt"), "HK Tower")
        self.assertEqual(self.panel.value("tDate.txt"), "2026-09-28")

    def test_the_clock_comes_from_the_status_columns(self):
        self.panel.start("pUser")
        Mcu(self.panel).run()
        self.assertEqual(self.panel.value("tClock.txt"), "08:00")
        self.assertEqual(self.panel.value("tBatt.txt"), "87")

    def test_the_busy_flag_is_released(self):
        """A request that never releases would freeze every later button."""
        self.panel.start("pUser")
        Mcu(self.panel).run()
        self.assertEqual(self.panel.value("pInit.vBusy.val"), "0")

    def test_pRT_splits_the_running_session(self):
        """The busiest page: sensors from status, the run from its own source."""
        self.panel.start("pRT")
        Mcu(self.panel).run(ticks=24)
        self.assertEqual(self.panel.value("tS1.txt"), "25.6")
        self.assertEqual(self.panel.value("tS2.txt"), "25.8")
        self.assertEqual(self.panel.value("tS3.txt"), "25.7")
        self.assertEqual(self.panel.value("tAvg.txt"), "25.7")
        # run[10] is maturity, run[11] Fc, run[12] percent.
        self.assertEqual(self.panel.value("tM.txt"), "1245")
        self.assertEqual(self.panel.value("tFc.txt"), "35.4")
        self.assertEqual(self.panel.value("tPct.txt"), "118")

    def test_pMat_splits_the_material_values(self):
        self.panel.start("pMat")
        Mcu(self.panel).run(ticks=16)
        self.assertEqual(self.panel.value("tCem.txt"), "450")
        self.assertEqual(self.panel.value("tWat.txt"), "180")
        self.assertEqual(self.panel.value("tCoa.txt"), "1020")
        self.assertEqual(self.panel.value("tWC.txt"), "0.40")

    def test_pInit_reports_the_clock_and_battery(self):
        self.panel.start("pInit")
        Mcu(self.panel).run(ticks=10)
        self.assertEqual(self.panel.value("tClock.txt"), "08:00")
        self.assertEqual(self.panel.value("tBatt.txt"), "87")


if __name__ == "__main__":
    unittest.main(verbosity=2)
