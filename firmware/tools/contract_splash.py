"""Add the splash self-check fields to the HMI contract.

The splash screen checks the sensors, the clock and the hardware, and shows what
it found before the panel moves on. That needs four fields the contract did not
have, and one request the panel sends back when the check passes.

This edits `firmware/hmi/manifest.json` in place and adds the event files the
splash needs, so the generator has something to read.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HMI = ROOT / "firmware" / "hmi"
PAGES = [
    "pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR",
    "pSaveB", "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev",
]

NEW_FIELDS = ["tChkSensors", "tChkClock", "tChkDevice", "tReady"]


def frame(page: str, verb: str, args: list[str], wait_for_render: bool) -> str:
    """A CM1 request, in the same shape the contract's other events use."""
    index = PAGES.index(page)
    gate = "pInit.vBusy.val==0" + ("&&pInit.vRender.val==0" if wait_for_render else "")
    lines = [
        f"if({gate})",
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
    manifest = json.loads((HMI / "manifest.json").read_text(encoding="utf-8"))
    splash = next(page for page in manifest["pages"] if page["name"] == "pInit")

    for field in NEW_FIELDS:
        if field not in splash["textComponents"]:
            splash["textComponents"].append(field)

    # The splash asks the MCU whether it may move on, and repeats the request on
    # its timer until the answer is Ok, because a sensor may take a moment.
    splash["actions"]["mSelfCheck"] = {"verb": "SELF_CHECK", "args": []}
    splash["notes"] = (
        "The panel boots on this page and leaves only when SELF_CHECK answers Ok. "
        "tChkSensors/tChkClock/tChkDevice/tReady show each check, so a fault stays visible."
    )

    (HMI / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    events = HMI / "events"
    body = frame("pInit", "SELF_CHECK", [], False)
    # The button, if the design ever draws one, and the timer that asks again
    # while the splash is still waiting.
    (events / "pInit_mSelfCheck.txt").write_text(body, encoding="utf-8")
    (events / "pInit_tm0.txt").write_text(body, encoding="utf-8")

    print(json.dumps({
        "added_fields": NEW_FIELDS,
        "actions": list(splash["actions"]),
        "events": ["pInit_mSelfCheck.txt", "pInit_tm0.txt"],
    }))


if __name__ == "__main__":
    main()
