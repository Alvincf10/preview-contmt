#!/usr/bin/env python3
"""Rewrite the button events for the Arduino protocol.

Every tap area on the panel sends a request. The kit wrote those requests for
`firmware/ConMT`, whose frame carried a boot token, a render gate and a version.
The Arduino firmware wants a plainer frame and does not know some of those verbs.

This regenerates each button's event from the page's action in `manifest.json`,
so the request shape lives in one place instead of in 150 hand-written files.

The same rules apply to every request:

- One outstanding: `vBusy` guards it, and the page timer releases it.
- `vSeq` numbers it; the firmware treats a repeat of the last seq as a replay.
- The frame ends with a real newline, which is what the firmware parses.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

ROOT = TOOLS.parents[1]
HMI = ROOT / "firmware" / "hmi"
EVENTS = HMI / "events"

PAGES = [
    "pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR",
    "pSaveB", "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev",
]

# The verbs the Arduino firmware knows. A page action outside this set has to be
# translated, because sending an unknown verb gets an Invalid answer and the
# button silently does nothing.
#   panel verb        -> arduino verb, and how its arguments map
TRANSLATE = {
    "STORAGE_RESCAN": ("STORAGE_RETRY", []),
    "SELF_CHECK": ("GET", ["status"]),
    "PAGE_ROWS": ("GET", []),
    "SESSION_RESUME": ("MEASURE_RESUME", []),
    # The kit used SETTINGS_STEP with a delta; the Arduino sets an absolute value.
    "SETTINGS_STEP": ("SETTINGS_SET", []),
    "SETTINGS_TOGGLE": ("SETTINGS_SET", []),
    "GAP_RECONCILE": ("CHECK_SET", []),
    # A datum picker has no Arduino verb. The nearest useful action is to ask the
    # firmware to publish the current baseline, so the field it edits is refreshed
    # and the operator sees what they are changing.
    "DATUM_PICK": ("GET", ["baseline"]),
}


def request(page: int, verb: str, args: list[str], source_tag: int | None) -> str:
    """A CM1 request for the Arduino firmware."""
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
    if source_tag is not None:
        lines.append(f"pInit.vSource.val={source_tag}")
    lines += ["prints pInit.tReq.txt,0", "printh 0A", "}"]
    return "\n".join(lines)


def text_arg(arg) -> str | None:
    """The `.txt` path an action's argument names, when it names one."""
    if isinstance(arg, dict) and "text" in arg:
        return arg["text"].replace("pInit.", "") if arg["text"].startswith("pInit.") else arg["text"]
    return None


def build_action(page: str, index: int, verb: str, args: list) -> tuple[str, bool]:
    """The event body for one action, and whether it was translated."""
    translated = False
    if verb in TRANSLATE:
        target, extra = TRANSLATE[verb]
        if target is None:
            # No Arduino verb: send nothing rather than something it rejects.
            return (
                "// The Arduino firmware has no verb for this action: the datum is\n"
                "// edited with FIELD_SET on the field itself, so no request is sent.\n"
                "// Sending an unknown verb would only earn an Invalid answer.",
                True,
            )
        verb, args, translated = target, list(args) + extra, True

    # A NAV carries the destination page number, which both firmwares use.
    if verb == "NAV":
        destination = args[0] if args else "0"
        return request(index, "NAV", [str(destination)], None), translated

    # A FIELD_SET names a field and a value; the value is read from a Text.
    if verb == "FIELD_SET":
        field = args[0] if args else ""
        rest = args[1] if len(args) > 1 else ""
        if isinstance(rest, dict):
            # The kit passes the field's text component; the Arduino wants its
            # value, so the panel sends the text it holds.
            source = text_arg(rest) or "pInit.tEdit"
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
                f'pInit.tReq.txt+="{index}|"',
                "covx pInit.nView.val,pInit.tNum.txt,0,0",
                "pInit.tReq.txt+=pInit.tNum.txt",
                'pInit.tReq.txt+="|FIELD_SET"',
                'pInit.tReq.txt+="|"',
                f'pInit.tReq.txt+="{field}"',
                'pInit.tReq.txt+="|"',
                f"pInit.tReq.txt+={source}.txt",
                "prints pInit.tReq.txt,0",
                "printh 0A",
                "}",
            ]
            return "\n".join(lines), translated
        return request(index, "FIELD_SET", [field, str(rest)], None), translated

    flat = [str(a) for a in args if not isinstance(a, dict)]
    return request(index, verb, flat, None), translated


def main() -> None:
    manifest = json.loads((HMI / "manifest.json").read_text(encoding="utf-8"))
    written = 0
    translated_verbs: set[str] = set()

    # Every event file this run will write. Anything else in the folder belongs to
    # the previous firmware and would still carry its frame, so it is removed
    # rather than left to be picked up by the generator.
    keep: set[str] = set()

    for page in manifest["pages"]:
        index = PAGES.index(page["name"])
        for component, action in page.get("actions", {}).items():
            verb = action["verb"]
            args = action.get("args", [])
            body, was_translated = build_action(page["name"], index, verb, args)
            if was_translated:
                translated_verbs.add(verb)
            name = f"{page['name']}_{component}.txt"
            (EVENTS / name).write_text(body + "\n", encoding="utf-8")
            keep.add(name)
            written += 1

        # The page's own events, written by arduino_events.py.
        keep.add(f"{page['name']}_postinitialize.txt")
        keep.add(f"{page['name']}_tmPoll.txt")

    # Tap areas the kit names but the contract leaves silent: a tab that opens a
    # picker, a row that fills itself from a sensor. They still need an event, or
    # the button does nothing. `write_missing_events.py` used to write these for
    # the other firmware; here they are written with the request this one parses.
    import write_missing_events as missing

    for key, (verb, args) in missing.GAPS.items():
        page, component = key.split(".", 1)
        if page not in PAGES:
            continue
        body, _ = build_action(page, PAGES.index(page), verb, args)
        name = f"{page}_{component}.txt"
        (EVENTS / name).write_text(body + "\n", encoding="utf-8")
        keep.add(name)
        written += 1

    removed = []
    for path in sorted(EVENTS.glob("*.txt")):
        if path.name not in keep:
            path.unlink()
            removed.append(path.name)

    print(json.dumps({
        "events": written,
        "translated": sorted(translated_verbs),
        "removed": len(removed),
    }))


if __name__ == "__main__":
    main()
