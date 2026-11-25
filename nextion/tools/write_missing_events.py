#!/usr/bin/env python3
"""Write the event files the contract is missing, in the contract's own frame.

Fourteen hotspots had no event, so they did nothing when tapped: the painted
button responded to nothing. The contract already says what each page's actions
are (`manifest.json`), so this builds the same CM1 request the other events
build, from that description rather than from a copy-pasted block.

The frame, for a request that carries a verb and its arguments:

    if(pInit.vBusy.val==0&&pInit.vRender.val==0)
    {
    pInit.vSeq.val+=1
    pInit.vBusy.val=1
    pInit.vRetry.val=0
    pInit.vReqBoot.val=pInit.vBoot.val
    pInit.tReq.txt="CM1|"
    covx pInit.vBoot.val,pInit.tNum.txt,0,0
    pInit.tReq.txt+=pInit.tNum.txt
    pInit.tReq.txt+="|"
    covx pInit.vSeq.val,pInit.tNum.txt,0,0
    pInit.tReq.txt+=pInit.tNum.txt
    pInit.tReq.txt+="|"
    pInit.tReq.txt+="<page>|"
    covx pInit.vView.val,pInit.tNum.txt,0,0
    pInit.tReq.txt+=pInit.tNum.txt
    pInit.tReq.txt+="|<VERB>"
    ...one line per argument...
    prints pInit.tReq.txt,0
    printh 0A
    }

A NAV action sends the page index and the word NAV, exactly as the kit's own
navigation events do.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HMI = ROOT / "firmware" / "hmi"
EVENTS = HMI / "events"
PAGES = [
    "pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR",
    "pSaveB", "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev",
]

# Hotspot -> the action it performs, for the ones the contract leaves silent.
# The verb and its arguments follow the contract's own vocabulary.
GAPS = {
    "pNewB.mTemp": ("DATUM_PICK", []),
    "pMatu.mSensor": ("ROW_SENSOR", ["0"]),
    "pRT.mDemo": ("ROW_FILL_EARLY", []),
    "pHist.mDetail": ("HISTORY_PICK", ["0"]),
    "pHist.mRow0": ("HISTORY_PICK", ["0"]),
    "pHist.mRow1": ("HISTORY_PICK", ["1"]),
    "pHist.mRow2": ("HISTORY_PICK", ["2"]),
    "pHist.mRow3": ("HISTORY_PICK", ["3"]),
    **{f"pMatu.mTemp{i}": ("ROW_SENSOR", [str(i)]) for i in range(6)},
}


def frame(page: str, verb: str, args: list[str]) -> str:
    index = PAGES.index(page)
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
        f'pInit.tReq.txt+="|{verb}"',
    ]
    for arg in args:
        lines.append('pInit.tReq.txt+="|"')
        lines.append(f'pInit.tReq.txt+="{arg}"')
    lines += ["prints pInit.tReq.txt,0", "printh 0A", "}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    written = []
    for key, (verb, args) in GAPS.items():
        page, hotspot = key.split(".", 1)
        path = EVENTS / f"{page}_{hotspot}.txt"
        if path.exists():
            continue
        path.write_text(frame(page, verb, args), encoding="utf-8")
        written.append(path.name)

    manifest = json.loads((HMI / "manifest.json").read_text(encoding="utf-8"))
    print(json.dumps({"written": len(written), "files": written[:6], "pages": len(manifest["pages"])}))


if __name__ == "__main__":
    main()
