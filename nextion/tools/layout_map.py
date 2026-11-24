#!/usr/bin/env python3
"""Where each contract field belongs on the design, page by page.

The preview in `src/` is the design: it loads the same background picture and
places every label and value with CSS. `extract_layout.mjs` records those places
as boxes on the 480x800 canvas, and this file says which box belongs to which
field the MCU writes.

A mapping is needed because the two agree on *position* but not on *names*: the
preview writes a sample value like "30 MPa" in its markup, while the contract
calls the text the MCU writes `tTarget`.

Two ways to name a box, both explicit:

    "tTarget": ("text", "30 MPa", 0)

the first text that reads "30 MPa" on this page. This is the preferred form: the
text is a stable handle, so adding a control elsewhere does not shift it.

    "tFc0": ("input", "", 2)

the third input in reading order, from the top down then left to right. Used
where the design shows an empty box, which has no text to match. The count is
fixed by the design's row count, so a change in the table is caught rather than
silently shifting every value one row.

Either way the build fails, naming the page and field, when the design no
longer holds what the mapping expects. A field left out falls back to automatic
placement.
"""
from __future__ import annotations

LAYOUT: dict[str, dict[str, tuple[str, str, int]]] = {
    # The splash shows no value the MCU writes; it has the status corners only.
    "pInit": {},

    "pUser": {
        "tOp": ("input", "OP001", 0),
        "tProj": ("input", "HK Tower", 0),
        "tDate": ("input", "2026-09-28", 0),
    },

    "pMain": {},
    "pBase": {},

    "pNewB": {
        "tName": ("input", "fc30 marunda final", 0),
        "tFc": ("input", "30", 0),
        "tTemp": ("input", "-20", 0),
    },

    # The material form, each box by its own sample value.
    "pMat": {
        "tCem": ("input", "385", 0),
        "tWat": ("input", "165", 0),
        "tWC": ("input", "0.43", 0),
        "tCoa": ("input", "1067", 0),
        "tFin": ("input", "725", 0),
        "tRetP": ("input", "0.92", 0),
        "tRetB": ("input", "-", 0),
        "tAccP": ("input", "0", 0),
        "tAccB": ("input", "-", 1),
        "tFlyP": ("input", "0", 1),
        "tFlyB": ("input", "-", 2),
    },

    # The lab table: four cells per row — Day, Time, Fc, Temperature — in
    # reading order. The Fc cell is empty in the design, so it is addressed by
    # position, and so is the rest of its row to keep the four together.
    "pMatu": {
        **{f"tDay{i}": ("input", "", i * 4 + 0) for i in range(6)},
        **{f"tTim{i}": ("input", "", i * 4 + 1) for i in range(6)},
        **{f"tFc{i}": ("input", "", i * 4 + 2) for i in range(6)},
        **{f"tT{i}": ("input", "", i * 4 + 3) for i in range(6)},
    },

    "pBaseR": {
        "tName": ("text", "fc30 marunda final", 0),
        "tTarget": ("text", "30 MPa", 0),
        "tDatum": ("text", "-20 °C", 0),
        "tDate": ("text", "28-09-2026", 0),
        "tOp": ("text", "OP001", 0),
        "tProj": ("text", "HK Tower", 0),
    },

    # Saved baselines: four cards, each a name, strength and date.
    "pSaveB": {
        "tName0": ("text", "fc30 marunda final", 0),
        "tVal0": ("text", "30 MPa", 0),
        "tDate0": ("text", "16-11-2026", 0),
        "tName1": ("text", "Beton Fc30 BP HKSIS Marunda", 0),
        "tVal1": ("text", "30 MPa", 1),
        "tDate1": ("text", "28-09-2026", 0),
        "tName2": ("text", "Beton Fc40 Project A", 0),
        "tVal2": ("text", "40 MPa", 0),
        "tDate2": ("text", "15-08-2026", 0),
        "tName3": ("text", "Beton Jalan Tol", 0),
        "tVal3": ("text", "35 MPa", 0),
        "tDate3": ("text", "10-07-2026", 0),
    },

    # Select baseline: the same cards, one page earlier in the flow.
    "pSelB": {
        "tName0": ("text", "fc30 marunda final", 0),
        "tVal0": ("text", "30 MPa", 0),
        "tDate0": ("text", "16-11-2026", 0),
        "tName1": ("text", "Beton Fc30 BP HKSIS Marunda", 0),
        "tVal1": ("text", "30 MPa", 1),
        "tDate1": ("text", "28-09-2026", 0),
        "tName2": ("text", "Beton Fc40 Project A", 0),
        "tVal2": ("text", "40 MPa", 0),
        "tDate2": ("text", "15-08-2026", 0),
        "tName3": ("text", "Beton Jalan Tol", 0),
        "tVal3": ("text", "35 MPa", 0),
        "tDate3": ("text", "10-07-2026", 0),
    },

    "pKuat": {
        "tS1": ("text", "35.6°", 0),
        "tS2": ("text", "36.4°", 0),
        "tS3": ("text", "36.0°", 0),
    },

    # Live measurement: every value the operator watches.
    "pRT": {
        "tBase": ("text", "fc30 marunda final", 0),
        "tTarget": ("text", "30 MPa", 0),
        "tDatum": ("text", "-20 °C", 0),
        "tM": ("text", "0", 0),
        "tFc": ("text", "0.0 MPa", 0),
        "tPct": ("text", "(0%)", 0),
        "tS1": ("text", "35.6 °C", 0),
        "tS2": ("text", "36.4 °C", 0),
        "tS3": ("text", "36.0 °C", 0),
        "tAvg": ("text", "36.0 °C", 1),
        "tPDate": ("text", "28-09-2026", 0),
        "tNowD": ("text", "28-09-2026", 1),
        "tPour": ("text", "15:00:00", 0),
        "tNowT": ("text", "15:00:00", 1),
        "tInitTemp": ("text", "—", 0),
    },

    "pStr": {
        "tBase": ("text", "fc30 marunda final", 0),
        "tTarget": ("text", "30 MPa", 0),
        "tDatum": ("text", "-20 °C", 0),
        "tFc": ("text", "0.0 MPa", 0),
        "tPct": ("text", "(0%)", 0),
        "tAvg": ("text", "36.0 °C", 0),
        "tM": ("text", "0", 0),
    },

    "pHist": {
        "tId0": ("text", "TEST-EXCEL-01", 0),
        "tName0": ("text", "fc30 marunda final", 0),
        "tVal0": ("text", "38.7", 0),
        "tDate0": ("text", "26-10-2026", 0),
        "tCount0": ("text", "41 days", 0),
    },

    "pHistD": {
        "tId": ("text", "TEST-EXCEL-01", 0),
        "tSavedAt": ("text", "26-10-2026", 0),
        "tLastT": ("text", "08:00:00", 0),
        "tOp": ("text", "OP001", 0),
        "tProj": ("text", "HK Tower", 0),
        "tBase": ("text", "fc30 marunda final", 0),
        "tTarget": ("text", "30 MPa", 0),
        "tDatum": ("text", "-20 °C", 0),
    },

    "pSet": {
        "tHour": ("text", "00", 0),
        "tMin": ("text", "05", 0),
        "tSec": ("text", "00", 1),
        "tBright": ("text", "80%", 0),
    },

    "pDev": {
        "tVersion": ("text", "V1.0.1", 0),
        "tMcu": ("text", "Nexion Touch Display", 0),
        "tProtocol": ("text", "Serial / Modbus", 0),
    },
}
