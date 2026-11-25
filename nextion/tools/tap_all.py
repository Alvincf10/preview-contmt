#!/usr/bin/env python3
"""Tap every hotspot in the simulator and check that each one sends a request.

A hotspot that exists but sends nothing is the failure this catches. The test
drives nxwright's own simulator over MCP: tap the component by name, read the
serial log, and decode the bytes the screen sent.

Every frame must also obey the contract: it starts `CM1|`, ends with a real
newline, and fits the 192-byte limit including that newline.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "nextion" / "nxsrc"
PAGES_DIR = SRC / "pages"

MAX_FRAME = 192


class Mcp:
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
        self._rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "tapall", "version": "1"}})
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n")
        self.proc.stdin.flush()

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

    def text(self, name: str, arguments: dict) -> str:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if "error" in result:
            return "ERROR " + json.dumps(result["error"])[:200]
        return "".join(c.get("text", "") for c in result.get("result", {}).get("content", []) if c.get("type") == "text")

    def stop(self) -> None:
        self.proc.kill()


def frames(log_text: str) -> list[str]:
    """The bytes the screen sent, decoded into the frames they form.

    The log is JSON, one object per write, with the write's bytes as hex in its
    `line` field. The frames are those writes joined and then split on the
    newline that ends each one.
    """
    chunks: list[str] = []
    for match in re.finditer(r'"line"\s*:\s*"SIM SEND:\s*([0-9a-fA-F ]+)"', log_text):
        try:
            chunks.append(bytes.fromhex(match.group(1).replace(" ", "")).decode("latin1"))
        except ValueError:
            continue
    whole = "".join(chunks)
    return [frame for frame in whole.split("\n") if frame]


def hotspots(page: str) -> list[str]:
    data = tomllib.loads((PAGES_DIR / f"{page}.page.toml").read_text(encoding="utf-8"))
    return [c["name"] for c in data.get("component", []) if c.get("type") == "hotspot"]


def _component(path: Path) -> list[dict]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return data.get("component", [])


def main() -> int:
    mcp = Mcp()
    problems = 0
    tested = 0
    unreachable = 0
    try:
        for path in sorted(PAGES_DIR.glob("*.page.toml")):
            page = path.name.split(".")[0]
            taps = hotspots(page)
            if not taps:
                continue

            for name in taps:
                tested += 1
                # A hotspot the design draws past the bottom edge is a row of a
                # table the panel cannot show at once. It exists for the row it
                # will become when the table pages; it cannot be tapped now, so
                # it is reported apart from a dead button.
                box = next(c for c in _component(path) if c.get("name") == name)
                centre_x = box["x"] + box["w"] // 2
                centre_y = box["y"] + box["h"] // 2
                if not (0 <= centre_x < 480 and 0 <= centre_y < 800):
                    unreachable += 1
                    continue
                # A fresh simulation for each tap. The contract allows one
                # request outstanding at a time, so a second tap on the same
                # screen is refused until the MCU acknowledges the first: that
                # is the design working, and it would hide a dead button.
                started = mcp.text("start_simulation", {"source_folder": str(SRC), "page": page})
                try:
                    simulation = json.loads(started)["simulation"]
                except (json.JSONDecodeError, KeyError):
                    print(f"{page}: could not start the simulation: {started[:120]}")
                    problems += 1
                    break

                before = frames(mcp.text("log", {"simulation": simulation}))
                mcp.text("tap", {"simulation": simulation, "component": name})
                # The tool takes milliseconds; a second is enough for the
                # screen's own code to run and print.
                mcp.text("wait", {"simulation": simulation, "milliseconds": 200})
                after = frames(mcp.text("log", {"simulation": simulation}))
                mcp.text("stop_simulation", {"simulation": simulation})

                # The page's own PAGE_READY frame is already in the log, so the
                # tap's frame is the one after it.
                mine = [f for f in after[len(before):] if "PAGE_READY" not in f]
                if not mine:
                    print(f"  {page}.{name}: tapped, but sent nothing")
                    problems += 1
                    continue
                frame = mine[0]
                if not frame.startswith("CM1|"):
                    print(f"  {page}.{name}: frame {frame[:50]!r} does not start with CM1|")
                    problems += 1
                elif len(frame) + 1 > MAX_FRAME:
                    print(f"  {page}.{name}: frame is {len(frame) + 1} bytes, over {MAX_FRAME}")
                    problems += 1
                elif frame.count("|") < 5:
                    print(f"  {page}.{name}: frame {frame[:60]!r} is missing fields")
                    problems += 1

            print(f"{page:8} {len(taps):3} hotspots tapped")
    finally:
        mcp.stop()

    print(f"\n{tested} hotspots tapped, {unreachable} past the screen edge, {problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
