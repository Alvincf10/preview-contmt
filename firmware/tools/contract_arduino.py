"""Point the HMI contract at the Arduino firmware.

The contract named `vBoot`, `vAck`, `vAckBoot`, `vStatus` and a PAGE_READY with a
version suffix. Those belong to `firmware/ConMT`. The Arduino sketch drives the
panel differently: it publishes `nBoot`, `nView`, `nAckSeq`, `nAckCode` and
`nAckValue`, and it fills one Text, `tData`, with a page's values as
pipe-separated columns.

This rewrites the globals so the generated panel speaks that protocol, and adds
the two Texts the split needs. It also drops the old globals, because keeping
both would leave fields that nothing ever writes - and a field nothing writes
looks exactly like a field that is broken.

Run once; running it again is harmless.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "firmware" / "hmi" / "manifest.json"

# The handshake Numbers, global on pInit so every page can reach them.
# `vBusy`, `vSeq` and `vRetry` stay: they belong to the panel, not the firmware.
VARIABLES = [
    "nBoot",     # the firmware's boot token
    "nView",     # the data version
    "nAckSeq",   # the seq being answered; written last, so it means "complete"
    "nAckCode",  # 0 is OK
    "nAckValue", # the answer's value: a commit id, a token, a row count
    "vSeq",      # the panel's own request number
    "vBusy",     # one request outstanding at a time
    "vRetry",    # how many times the current request was repeated
    "vSource",   # which source the pending answer belongs to
]

# The Texts the protocol needs, and their capacity.
TEXTS = {
    "tReq": 191,     # the frame being built
    "tNum": 16,      # scratch for covx
    "tSplit": 255,   # one column, split out of tData
    "tData": 255,    # the firmware's answer, as columns
    "tEdit": 64,     # a field being typed into
    "tDayInput": 24,
}


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    manifest["protocol"] = "CM1"
    manifest["globals"]["variables"] = VARIABLES
    manifest["globals"]["texts"] = TEXTS
    manifest["globals"]["note"] = (
        "Names follow arduino/ConMT: nBoot/nView/nAckSeq/nAckCode/nAckValue, and "
        "tData holding a page's values as pipe-separated columns. The panel keeps "
        "vSeq/vBusy/vRetry for its own request, and vSource to know which answer "
        "is arriving."
    )
    manifest["notes"] = [
        "The panel speaks arduino/ConMT, not firmware/ConMT: see nextion/SYNC.md.",
        "PAGE_READY is sent without a version suffix; the Arduino firmware refuses one.",
        "nAckSeq is written last by the firmware, so its event is what splits tData.",
        "One request outstanding: vBusy guards it, nAckSeq releases it.",
        "A page asks for one source at a time because tData holds one at a time.",
    ]

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "variables": VARIABLES,
        "texts": list(TEXTS),
        "pages": len(manifest["pages"]),
    }))


if __name__ == "__main__":
    main()
