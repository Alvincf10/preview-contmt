#!/usr/bin/env python3
"""Write the Nextion events that speak the Arduino protocol.

The panel is drawn as 17 pages of invisible fields over a picture. The firmware
gives it one Text, `tData`, holding a page's values as pipe-separated columns,
plus five Numbers that carry the handshake.

A Variable has no events in Nextion, so `nAckSeq` cannot run code when the
firmware writes it. The panel therefore polls from a timer: the same timer that
splits a finished answer asks for the next thing the page needs.

That order matters. A page cannot send `PAGE_READY` and then a `GET` in the same
event: the panel allows one request outstanding, so the second is refused because
the first has not been answered. The page's steps therefore run one per timer
tick, driven by `vStep`:

    0  send PAGE_READY
    1  ask for the first source
    2  ask for the next source, and so on
    n  done: nothing left to ask

Each tick either sends the next request or, when the answer to the last one has
arrived, splits `tData` into the fields bound to that source.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from arduino_protocol import BINDINGS, PAGE_SOURCES, SOURCES  # noqa: E402

ROOT = TOOLS.parents[1]
EVENTS = ROOT / "firmware" / "hmi" / "events"

PAGES = [
    "pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR",
    "pSaveB", "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev",
]

SCRATCH = "pInit.tSplit"
PENDING = "pInit.vSource"
STEP = "pInit.vStep"

SOURCES_ORDER = list(SOURCES)


def source_tag(source: str) -> int:
    return SOURCES_ORDER.index(source) + 1


def send(page: int, verb: str, args: list[str], tag: int) -> list[str]:
    """Build and send one CM1 frame, if no request is outstanding."""
    lines = [
        "if(pInit.vBusy.val==0)",
        "{",
        "pInit.vSeq.val+=1",
        "pInit.vBusy.val=1",
        "pInit.vRetry.val=0",
        'pInit.tReq.txt="CM1|"',
        "covx pInit.nBoot.val,pInit.tNum.txt,0,0",
        "pInit.tReq.txt+=pInit.tNum.txt",
        'pInit.tReq.txt+="|"',
        "covx pInit.vSeq.val,pInit.tNum.txt,0,0",
        "pInit.tReq.txt+=pInit.tNum.txt",
        'pInit.tReq.txt+="|"',
        f'pInit.tReq.txt+="{page}|"',
        "covx pInit.nView.val,pInit.tNum.txt,0,0",
        "pInit.tReq.txt+=pInit.tNum.txt",
        f'pInit.tReq.txt+="|{verb}"',
    ]
    for arg in args:
        lines.append('pInit.tReq.txt+="|"')
        lines.append(f'pInit.tReq.txt+="{arg}"')
    lines.append(f"{PENDING}.val={tag}")
    lines += ["prints pInit.tReq.txt,0", "printh 0A", "}"]
    return lines


def split_for(page: str, source: str, depth: str) -> list[str]:
    """The lines that put one source's columns into the fields that show them."""
    pairs = [(f, i) for f, (s, i) in BINDINGS.get(page, {}).items() if s == source]
    if not pairs:
        return []
    lines = [f"{depth}// {source}: {len(SOURCES[source])} columns"]
    for field, index in sorted(pairs, key=lambda pair: pair[1]):
        lines.append(f'{depth}spstr pInit.tData.txt,{SCRATCH}.txt,"|",{index}')
        lines.append(f"{depth}{field}.txt={SCRATCH}.txt")
    return lines


def page_load(page: str, index: int) -> str:
    """On load, reset the step counter. The timer does the asking."""
    return (
        "// The page starts its conversation at step 0; the timer carries it.\n"
        "if(pInit.vBusy.val==0)\n"
        "{\n"
        f"{STEP}.val=0\n"
        "}\n"
    )


def page_timer(page: str, index: int) -> str:
    """The poll: answer handling, then the next request.

    Runs on the page's timer. When an answer is complete it is split, and the
    step advances so the next tick asks for the next thing. A `vBusy` that has
    been set too long is retried, because the firmware drops an incomplete frame
    after 1.2 seconds.
    """
    sources = PAGE_SOURCES.get(page, [])
    lines = ["// One step per tick: split a finished answer, then ask for the next."]

    # 1. Finish the request that is outstanding.
    lines += [
        "if(pInit.vBusy.val==1)",
        "{",
        "if(pInit.nAckSeq.val==pInit.vSeq.val)",
        "{",
    ]
    with_fields = [s for s in sources if split_for(page, s, "")]
    if with_fields:
        first = True
        for source in with_fields:
            body = split_for(page, source, "    ")
            if first:
                lines.append(f"if({PENDING}.val=={source_tag(source)})")
                first = False
            else:
                lines.append(f"else if({PENDING}.val=={source_tag(source)})")
            lines.append("{")
            lines += body
            lines.append("}")
    lines += [
        f"{STEP}.val+=1",
        "pInit.vBusy.val=0",
        "pInit.vRetry.val=0",
        "}else",
        "{",
        "pInit.vRetry.val+=1",
        "if(pInit.vRetry.val<6)",
        "{",
        "prints pInit.tReq.txt,0",
        "printh 0A",
        "}else",
        "{",
        "pInit.vBusy.val=0",
        "pInit.vRetry.val=0",
        f"{STEP}.val+=1",
        'pInit.tMsg.txt="No answer from MCU"',
        "}",
        "}",
        "}",
    ]

    # 2. Ask for the next thing, one per tick.
    lines.append("// Ask for the next thing this page needs.")
    lines.append(f"if(pInit.vBusy.val==0&&{STEP}.val>=0)")
    lines.append("{")

    # Step 0: PAGE_READY.
    lines.append(f"if({STEP}.val==0)")
    lines.append("{")
    lines += ["  " + l for l in send(index, "PAGE_READY", [], source_tag(sources[0]))]
    lines.append("}")

    # Steps 1..n: one GET per source beyond the first.
    step = 1
    for source in sources[1:]:
        lines.append(f"else if({STEP}.val=={step})")
        lines.append("{")
        lines += ["  " + l for l in send(index, "GET", [source], source_tag(source))]
        lines.append("}")
        step += 1

    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> None:
    count = 0
    for index, page in enumerate(PAGES):
        (EVENTS / f"{page}_postinitialize.txt").write_text(page_load(page, index), encoding="utf-8")
        # The generator looks for `<page>_<timer name>.txt`, and every page's timer
        # is called tmPoll.
        (EVENTS / f"{page}_tmPoll.txt").write_text(page_timer(page, index), encoding="utf-8")
        count += 2
    print(f"wrote {count} event files for {len(PAGES)} pages")


if __name__ == "__main__":
    main()
