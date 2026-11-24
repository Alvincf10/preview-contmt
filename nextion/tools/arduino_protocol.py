#!/usr/bin/env python3
"""The Arduino protocol: what each page sends, and how its answer is laid out.

The panel speaks to `arduino/ConMT`. That firmware drives the screen through one
Text, `tData`, holding a page's values as pipe-separated columns, plus five
Numbers that carry the handshake. The panel's job on every answer is to split
`tData` and put each column in the field that shows it.

The column order is not a guess: it comes from the firmware's own data functions
in `arduino/ConMT/src/Panel.cpp`, quoted beside each entry. A column that moves
there must move here, or a value lands in the wrong field - which is exactly the
failure this file exists to prevent.

`GET <source>` asks for one of these. The firmware answers by writing `tData`,
then `nAckValue`, `nAckCode`, and `nAckSeq` last: `nAckSeq` is what tells the
panel the answer is complete and may be split.
"""
from __future__ import annotations

# The source name the panel asks for, per page, in the order it asks for them.
# A page that shows data from two sources lists both, and the split runs once per
# answer: `tData` holds one source at a time.
#
# `status` is listed first on every page: it carries the clock and the battery,
# which the top corners show, so a page that asked only for its own data would
# leave those two blank.
PAGE_SOURCES: dict[str, list[str]] = {
    "pInit": ["status"],
    "pUser": ["status", "identity"],
    "pMain": ["status"],
    "pBase": ["status", "baseline"],
    "pNewB": ["status", "baseline"],
    "pMat": ["status", "mix"],
    "pMatu": ["status", "baseline", "labrow"],
    "pBaseR": ["status", "model", "mix", "identity", "baseline"],
    "pSaveB": ["status", "savedrow"],
    "pKuat": ["status"],
    "pSelB": ["status", "savedrow"],
    "pRT": ["status", "run"],
    "pStr": ["status", "run"],
    "pHist": ["status", "historyrow"],
    "pHistD": ["status", "detail", "run", "point"],
    "pSet": ["status"],
    "pDev": ["status"],
}

# Columns per source, from Panel.cpp's readView and its helpers:
#
#   status      readView(Status)              timestamp, supply, battery, sd,
#                                            active, interval, brightness, flags,
#                                            version, S1, S2, S3, average, mask,
#                                            selected, result, identityReady,
#                                            draftFromSaved, baselines
#   identity    identityData()                operator, project, date
#   baseline    baseData()                    ref, name, target, datum, pour,
#                                            rows, model, identity
#   savedrow    baseData()                    same as baseline
#   mix         readView(MixView)             five quantities, three brands, W/C
#   model       readView(ModelView)           a, b, r2, pairs, factors, maxM,
#                                            operator, project, date
#   labrow      pointData()/rowData()         six rows of seven columns, read one
#                                            row at a time
#   run         runData(RunView)              ref, baseline, points, partial,
#                                            start, end, startTemp, seconds,
#                                            maturity, fc, percent
#   detail      runData(DetailView)           result, savedAt, operator, project,
#                                            date, ref, baseline, ...
#   point       pointData()                   day, at, temperature, maturity, fc,
#                                            percent, flags, S1, S2, S3, average,
#                                            mask
#   historyrow  readView(HistoryRowView)      ref, baselineName, savedAt, fc,
#                                            points, partial
SOURCES: dict[str, list[str]] = {
    # readView(Status): timestamp writes two columns, then supply, battery, sd,
    # active, interval, brightness, flags, version, then sensors() writes five
    # (S1, S2, S3, average, mask), then selected, result, identityReady,
    # draftFromSaved, baselines. Twenty in all.
    "status": [
        "date", "clock", "supply", "battery", "sdCode", "active", "interval",
        "brightness", "flags", "version", "s1", "s2", "s3", "average", "mask",
        "selected", "selectedResult", "identityReady", "draftFromSaved",
        "baselines",
    ],
    "identity": ["operator", "project", "date"],
    # baseData(): digits(ref), storedText(name), scaled(target), scaled(datum),
    # timestamp(pour) which is two columns, digits(rows), digits(model),
    # digits(identity). Eight in all.
    "baseline": ["ref", "name", "target", "datum", "pourDate", "pourClock", "rows", "model", "identity"],
    "savedrow": ["ref", "name", "target", "datum", "pourDate", "pourClock", "rows", "model", "identity"],
    # readView(MixView): five quantities, three brands, then W/C.
    "mix": [
        "cement", "water", "coarse", "fine", "retarder",
        "retarderBrand", "acceleratorBrand", "flyAshBrand",
        "accelerator", "flyAsh", "wc",
    ],
    # readView(ModelView): a, b, r2, count, factors, maxM, then identityData's
    # three. Nine in all.
    "model": ["a", "b", "r2", "pairs", "factors", "maxM", "operator", "project", "date"],
    # readView(LabRowView): id, day, then timestamp(pour+age) as date and clock,
    # temperature, Fc, age in seconds. Seven.
    "labrow": ["ref", "day", "date", "clock", "temperature", "fcLab", "age"],
    # runData(RunView): ref, baseline, points, partial, then timestamp(first.at)
    # as two columns, timestamp(last.at) as two more, startTemp, seconds,
    # maturity, Fc, percent. Thirteen.
    "run": [
        "ref", "baseline", "points", "partial", "startDate", "startClock",
        "endDate", "endClock", "startTemp", "seconds", "maturity", "fc", "percent",
    ],
    # runData(DetailView): result, timestamp(savedAt) as two, then identityData's
    # three, then ref, baseline, points, partial, two pairs of timestamps,
    # startTemp, seconds, maturity, Fc, percent. Nineteen.
    "detail": [
        "result", "savedAtDate", "savedAtClock", "operator", "project", "date",
        "ref", "baseline", "points", "partial", "startDate", "startClock",
        "endDate", "endClock", "startTemp", "seconds", "maturity", "fc", "percent",
    ],
    # pointData(): day, timestamp(at) as two, temperature, maturity, Fc, percent,
    # flags, then sensors()'s five. Twelve.
    "point": [
        "day", "atDate", "atClock", "temperature", "maturity", "fc", "percent",
        "flags", "s1", "s2", "s3", "average", "mask",
    ],
    # readView(HistoryRowView): ref, name, timestamp as two, Fc, points, partial.
    "historyrow": ["ref", "name", "savedDate", "savedClock", "fc", "points", "partial"],
}

# Which fields a page fills from which column. The key is the contract's field
# name; the value is (source, column index). A field the design does not show, or
# one the firmware never fills, is left out.
#
# These mappings are the heart of the port: a wrong index puts a temperature in a
# date field. Each one is written out rather than derived, so it can be read and
# checked against CONTRACT.md.
BINDINGS: dict[str, dict[str, tuple[str, int]]] = {
    "pInit": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
    },
    "pUser": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tOp": ("identity", 0),
        "tProj": ("identity", 1),
        "tDate": ("identity", 2),
    },
    "pMain": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
    },
    "pBase": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
    },
    "pNewB": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tName": ("baseline", 1),
        "tFc": ("baseline", 2),
        "tTemp": ("baseline", 3),
    },
    "pMat": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tCem": ("mix", 0),
        "tWat": ("mix", 1),
        "tCoa": ("mix", 2),
        "tFin": ("mix", 3),
        "tRetP": ("mix", 4),
        "tAccP": ("mix", 5),
        "tFlyP": ("mix", 6),
        "tRetB": ("mix", 7),
        "tAccB": ("mix", 8),
        "tFlyB": ("mix", 9),
        "tWC": ("mix", 10),
    },
    "pMatu": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tHint": ("baseline", 1),
    },
    "pBaseR": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tA": ("model", 0),
        "tB": ("model", 1),
        "tR2": ("model", 2),
        "tCount": ("model", 3),
        "tName": ("baseline", 1),
        "tTarget": ("baseline", 2),
        "tDatum": ("baseline", 3),
        "tCem": ("mix", 0),
        "tWat": ("mix", 1),
        "tCoa": ("mix", 2),
        "tFin": ("mix", 3),
        "tRetP": ("mix", 4),
        "tAccP": ("mix", 5),
        "tFlyP": ("mix", 6),
        "tRetB": ("mix", 7),
        "tAccB": ("mix", 8),
        "tFlyB": ("mix", 9),
        "tWC": ("mix", 10),
        "tOp": ("identity", 0),
        "tProj": ("identity", 1),
        "tDate": ("identity", 2),
    },
    "pSaveB": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tId0": ("savedrow", 0),
        "tName0": ("savedrow", 1),
        "tVal0": ("savedrow", 2),
        "tSelName": ("savedrow", 1),
        "tSelFc": ("savedrow", 2),
        "tSelT": ("savedrow", 3),
        "tSelId": ("savedrow", 0),
    },
    "pKuat": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
    },
    "pSelB": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tId0": ("savedrow", 0),
        "tName0": ("savedrow", 1),
        "tVal0": ("savedrow", 2),
        "tName1": ("savedrow", 1),
        "tVal1": ("savedrow", 2),
        "tName2": ("savedrow", 1),
        "tVal2": ("savedrow", 2),
        "tName3": ("savedrow", 1),
        "tVal3": ("savedrow", 2),
        "tSelName": ("savedrow", 1),
        "tSelFc": ("savedrow", 2),
        "tSelT": ("savedrow", 3),
        "tSelId": ("savedrow", 0),
    },
    "pRT": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tS1": ("status", 10),
        "tS2": ("status", 11),
        "tS3": ("status", 12),
        "tAvg": ("status", 13),
        "tM": ("run", 10),
        "tFc": ("run", 11),
        "tPct": ("run", 12),
        "tPDate": ("run", 4),
        "tPour": ("run", 5),
        "tInitTemp": ("run", 8),
        "tNowD": ("run", 6),
        "tNowT": ("run", 7),
        "tElapsed": ("run", 9),
    },
    "pStr": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tM": ("run", 10),
        "tFc": ("run", 11),
        "tPct": ("run", 12),
        "tBase": ("run", 0),
        "tPDate": ("run", 4),
        "tPour": ("run", 5),
        "tInitTemp": ("run", 8),
        "tElapsed": ("run", 9),
    },
    "pHist": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tId0": ("historyrow", 0),
        "tName0": ("historyrow", 1),
        "tVal0": ("historyrow", 4),
        "tCount0": ("historyrow", 5),
    },
    "pHistD": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tSavedAt": ("detail", 1),
        "tOp": ("detail", 3),
        "tProj": ("detail", 4),
        "tDate": ("detail", 5),
        "tM": ("detail", 16),
        "tFc": ("detail", 17),
        "tPct": ("detail", 18),
        "tStatus": ("detail", 14),
        "tS1": ("point", 8),
        "tS2": ("point", 9),
        "tS3": ("point", 10),
        "tCount": ("detail", 8),
    },
    "pSet": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tHour": ("status", 6),
        "tBright": ("status", 7),
    },
    "pDev": {
        "tClock": ("status", 1),
        "tBatt": ("status", 3),
        "tVersion": ("status", 9),
        "tMcu": ("status", 4),
        "tProtocol": ("status", 2),
    },
}

# The handshake Numbers the firmware writes, and what each means.
HANDSHAKE = {
    "nBoot": "the boot token, so the panel can tell one power-on from the next",
    "nView": "the data version; it changes whenever a value does",
    "nAckSeq": "the seq being answered; written last, so it means the answer is complete",
    "nAckCode": "0 is OK; see CONTRACT.md for the rest",
    "nAckValue": "the answer's value: a commit id, a token, a row count",
}

# Ack codes, from CONTRACT.md.
ACK_CODES = {
    0: "OK",
    1: "Invalid input",
    2: "Required data missing",
    3: "Not available in this state",
    4: "View or revision has changed",
    5: "Capacity full",
    6: "Storage I/O failed",
    7: "Corrupt record",
    8: "Boot token or storage version mismatch",
    9: "Temperature not available",
    10: "Clock or time order invalid",
    11: "Model cannot be formed",
    12: "New result has Day 0 or a zero interval",
    13: "Confirmation required; the value holds a token",
    14: "Another transaction is in progress",
    15: "Item not found, or end of list",
}

# The request the panel sends when a page opens, and the one it sends to move.
FRAME = "CM1|<boot>|<seq>|<page>|<view>|<verb>|<arg>..."

# What each verb does, for the panel's own reference. Kept here so the generated
# code and this note cannot drift apart.
VERBS = {
    "PAGE_READY": ("page open", "CM1|0|0|0|0|PAGE_READY - no version suffix"),
    "GET": ("read a page's data", "GET|<source>"),
    "NAV": ("move page", "NAV|<page number>"),
    "FIELD_SET": ("edit", "FIELD_SET|<field>|<value>"),
    "USER_SAVE": ("save identity", "USER_SAVE"),
    "BASE_NEW": ("new baseline", "BASE_NEW"),
    "BASE_SAVE": ("save baseline", "BASE_SAVE|<revision>"),
    "BASE_PICK": ("pick baseline", "BASE_PICK|<id>"),
    "BASE_OPEN": ("open baseline", "BASE_OPEN"),
    "BASE_DELETE": ("delete baseline", "BASE_DELETE|<id>"),
    "BASE_GENERATE": ("fit model", "BASE_GENERATE"),
    "ROW_FOCUS": ("mark active row", "ROW_FOCUS|<i>"),
    "ROW_SET": ("edit row", "ROW_SET|<i>|<field>|<value>"),
    "ROW_SENSOR": ("fill row from sensor", "ROW_SENSOR|<i>"),
    "ROW_SCHEDULE": ("row schedule", "ROW_SCHEDULE|<i>"),
    "ROW_ADD_EARLY": ("add Day 0 slot", "ROW_ADD_EARLY"),
    "ROW_ADD_LAB": ("add lab day", "ROW_ADD_LAB"),
    "ROW_FILL_EARLY": ("fill empty Day 0", "ROW_FILL_EARLY"),
    "ROW_DELETE": ("delete row", "ROW_DELETE|<i>"),
    "MEASURE_START": ("start session", "MEASURE_START"),
    "MEASURE_RESUME": ("resume session", "MEASURE_RESUME"),
    "CHECK_ADD": ("add checkpoint", "CHECK_ADD[|<day>]"),
    "CHECK_SET": ("correct checkpoint", "CHECK_SET|<i>|<field>|<value>"),
    "RESULT_PREPARE": ("freeze result", "RESULT_PREPARE"),
    "RESULT_SAVE": ("save result", "RESULT_SAVE|<revision>"),
    "HISTORY_PICK": ("pick history row", "HISTORY_PICK|<i>"),
    "SETTINGS_SET": ("change a setting", "SETTINGS_SET|<field>|<value>"),
    "SETTINGS_SAVE": ("save settings", "SETTINGS_SAVE"),
    "CLOCK_SET": ("set the clock", "CLOCK_SET|<date>|<clock>"),
    "CONFIRM": ("confirm a dialog", "CONFIRM|<token>"),
    "CANCEL": ("cancel a dialog", "CANCEL|<token>"),
    "RETRY": ("find an existing commit", "RETRY|<verb>|<revision>"),
    "STORAGE_RETRY": ("mount the SD card again", "STORAGE_RETRY"),
}
