#!/usr/bin/env python3
"""Where each tap area sits, and what it does.

The kit names the tap areas (`mBack`, `mNext`, `mSave`, ...) and the contract
gives each one a verb in the request it sends. Two things were missing:

- the box: a hotspot must cover the button the picture draws, or the operator
  taps a painted button that nothing listens to;
- the event: fourteen hotspots had no event file, so they were dead.

So this table names, per page, the design button each hotspot covers. The box
comes from the picture via `layout.json`; the event comes from the contract's
event files, and a hotspot the contract leaves silent is wired here by the verb
it should send.

A button is matched by its label, which is what the design draws on it. The
panel's own label reads the same, so one name serves both.
"""
from __future__ import annotations

# page -> hotspot name -> the design button's label, as drawn.
HOTSPOTS: dict[str, dict[str, str]] = {
    "pUser": {"mSave": "SAVE"},

    "pMain": {
        "mBase": "BASELINE",
        "mKuat": "KUAT TEKAN",
        "mSet": "SETTINGS",
        "mDev": "DEVICE INFO",
    },

    "pBase": {"mBack": "BACK", "mNew": "NEW BASELINE", "mSaved": "SAVED BASELINE"},

    "pNewB": {"mBack": "BACK", "mNext": "NEXT", "mTemp": "input -20"},

    "pMat": {"mBack": "BACK", "mNext": "NEXT"},

    "pMatu": {
        "mBack": "BACK",
        "mGen": "GENERATE BASELINE",
        "mAddDay": "+ ADD DAY",
        "mSensor": "SENSOR",
        **{f"mTemp{i}": f"row {i}" for i in range(6)},
    },

    "pBaseR": {"mBack": "BACK", "mSave": "SAVE"},

    "pSaveB": {
        "mBack": "BACK",
        # The footer's own SELECT. The card's SELECT is covered by mPick0, which
        # marks the whole card: matching by text alone would take the first
        # "SELECT" on the page, which is a card's.
        "mSelect": "footer SELECT",
        **{f"mPick{i}": f"card {i}" for i in range(6)},
        **{f"mDelete{i}": f"delete {i}" for i in range(6)},
    },

    "pKuat": {"mStart": "START TEST", "mHist": "HISTORY", "mBack": "BACK"},

    "pSelB": {
        "mBack": "BACK",
        "mStart": "START",
        **{f"mPick{i}": f"card {i}" for i in range(6)},
        "mResume": "RESUME",
        "mReplaceConfirm": "REPLACE",
    },

    "pRT": {
        "mBack": "BACK",
        "mNext": "NEXT",
        "mAddDay": "+ ADD DAY",
        "mDemo": "demo",
    },

    "pStr": {"mBack": "BACK", "mSave": "SAVE RESULT"},

    "pHist": {
        "mBack": "BACK",
        "mDetail": "VIEW LOG",
        # The design draws one card at a time; the panel's other three rows are
        # a list the MCU fills, and their tap areas come from the drawn card.
        **{f"mRow{i}": f"card {i}" for i in range(4)},
    },

    "pHistD": {"mBack": "BACK", **{f"mRow{i}": f"log {i}" for i in range(6)}},

    "pSet": {"mBack": "BACK", "mSave": "SAVE"},

    "pDev": {"mBack": "BACK"},

    "pInit": {},
}

# Hotspots whose event the contract does not supply, with the verb each sends.
# The contract lists the action on the page (`manifest.json`), so this only has
# to say the hotspot exists and where it goes; the frame itself is written by
# `nx_source.py` from that same action.
FALLBACK_VERB = {
    "pNewB.mTemp": "DATUM_PICK",
    "pMatu.mSensor": "ROW_SENSOR",
    "pRT.mDemo": "ROW_FILL_EARLY",
    "pHist.mDetail": "HISTORY_PICK",
    "pHist.mRow0": "HISTORY_PICK",
    "pHist.mRow1": "HISTORY_PICK",
    "pHist.mRow2": "HISTORY_PICK",
    "pHist.mRow3": "HISTORY_PICK",
    **{f"pMatu.mTemp{i}": "ROW_SET" for i in range(6)},
}

# Hotspots the contract names but the design's picture does not draw. The
# contract still lists their action, so they keep a tap area — but a tiny one in
# the reserve, never over the design. On pRT the design has no ADD DAY button:
# the value is added from the MCU's own checkpoint flow, and a stray tap area
# over the sensor row would open the wrong editor.
HIDDEN_HOTSPOTS = {
    "pRT": ["mAddDay", "mDemo"],
}

