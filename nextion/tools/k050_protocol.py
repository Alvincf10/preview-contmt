"""Generate the K050 events and input pages for arduino/ConMT's CM1 contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tomllib

import tomli_w
from k050_layout import (LAB_ROWS, SURFACE, WEB, control, crop, draw_value, geometry, layout,
                         patch_at, picture, picture_id, region)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "nextion" / "nxsrc-K050"
PAGES = [
    "pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR",
    "pSaveB", "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev",
]
POINT_COLUMNS = ("Day", "Date", "Time", "Temp", "M", "Fc")
POINT_ROWS = 6
HISTORY_ROWS = 3
SCROLL_LISTS = {
    "pMatu": ("labrow", LAB_ROWS, "pInit.vTotal.val"),
    "pSchedule": ("labrow", LAB_ROWS, "pInit.vTotal.val"),
    "pSaveB": ("savedrow", 4, "pInit.vSavedCount.val"),
    "pSelB": ("savedrow", 4, "pInit.vSavedCount.val"),
    "pHist": ("historyrow", HISTORY_ROWS, "pInit.vHistoryEnd.val"),
    "pHistD": ("point", 5, "pInit.vTotal.val"),
    "pPoints": ("point", POINT_ROWS, "pInit.vTotal.val"),
}
LIST_TICK_MS = 65


def variable(name, value=0, capacity=None):
    item = {"name": name, "type": "variable", "vscope": 1}
    item.update({"sta": 1, "txt": value, "txt_maxl": capacity} if capacity else {"val": value})
    return item


def label(name, text, x, y, width, height=30, capacity=64, font="NotoSans16"):
    return dict(name=name, type="text", x=x, y=y, w=width, h=height, sta=1,
                bco="#1e2326", pco="#ffffff", font=font, txt=text, txt_maxl=capacity)


def button(name, text, x, y, width, height=36):
    return control(name, text, x, y, width, height, font=16)


def hotspot(name, x, y, width, height, events=("up",)):
    return dict(name=name, type="hotspot", x=x, y=y, w=width, h=height, events=list(events))


def event(name, body):
    return f"on {name}:\n" + "\n".join("  " + line if line else "" for line in body.splitlines()) + "\n"


def branch(condition, body):
    return f"if({condition})\n{{\n{body}\n}}"


def rgb565(hex_color):
    color = int(hex_color.lstrip("#"), 16)
    return ((color >> 19) << 11) | (((color >> 10) & 63) << 5) | ((color >> 3) & 31)


def battery_icon(page):
    if "battery" not in WEB["pages"].get(page, {}).get("regions", {}):
        return ""
    icon = region(page, "battery")
    x, y, _, h = icon["fill"]
    return crop(page, icon["icon"]) + "\n" + branch(
        "pInit.vTemp.val>0", f"fill {x},{y},pInit.vTemp.val,{h},tBatt.pco")


def status_header(page):
    return ('tClock.txt="--:--"\ntBatt.txt="--%"\ntBatt.pco=65535\npInit.vTemp.val=0\n' +
            battery_icon(page))


def status_corners(page):
    icon = WEB["pages"].get(page, {}).get("regions", {}).get("battery")
    width = icon["fill"][2] if icon else 0
    lines = [column("pInit.tTime", 1), 'tClock.txt="--:--"',
             branch('pInit.tTime.txt!=""', "substr pInit.tTime.txt,tClock.txt,0,5"),
             column("pInit.tSplit", 3),
             'tBatt.txt="--%"', "tBatt.pco=65535", "pInit.vTemp.val=0",
             branch('pInit.tSplit.txt!=""', f"""covx pInit.tSplit.txt,pInit.vTemp.val,0,0
tBatt.txt=pInit.tSplit.txt
tBatt.txt+="%"
if(pInit.vTemp.val<=40)
{{
tBatt.pco={rgb565("#ffcc66")}
}}
if(pInit.vTemp.val<=20)
{{
tBatt.pco={rgb565("#ff6b4a")}
}}
pInit.vTemp.val*={width}
pInit.vTemp.val+=50
pInit.vTemp.val/=100""")]
    if icon:
        lines.append(battery_icon(page))
    return lines


def column(target, index, source="pInit.tData"):
    return f'spstr {source}.txt,{target}.txt,"|",{index}'


def swap_date(source, target):
    # The display uses day-month-year. The CM1 payload uses year-month-day.
    return f'''spstr {source}.txt,pInit.tNum.txt,"-",2
spstr {source}.txt,pInit.tSplit.txt,"-",1
pInit.tNum.txt+="-"
pInit.tNum.txt+=pInit.tSplit.txt
spstr {source}.txt,pInit.tSplit.txt,"-",0
pInit.tNum.txt+="-"
pInit.tNum.txt+=pInit.tSplit.txt
{target}.txt=pInit.tNum.txt'''


def display_date(target):
    return f"strlen {target}.txt,pInit.vTemp.val\n" + branch(
        "pInit.vTemp.val==10", swap_date(target, target))


def measurement(target, unit, one_decimal=False):
    lines = []
    if one_decimal:
        lines += ['pInit.tSplit.txt=""', f'spstr {target}.txt,pInit.tSplit.txt,".",1',
                  branch('pInit.tSplit.txt==""', f'{target}.txt+=".0"')]
    lines.append(f'{target}.txt+="{unit}"')
    return branch(f'{target}.txt!=""', "\n".join(lines))


def number_column(target, index):
    return column("pInit.tSplit", index) + f"\ncovx pInit.tSplit.txt,{target}.val,0,0"


def send(command, page=None, task=0):
    """Send one request. Its exact bytes remain in tReq until acknowledged."""
    origin = str(page) if isinstance(page, int) else "pInit.vPage.val" if page is None else page
    return branch("pInit.vBusy.val==0", f'''pInit.vSeq.val+=1
pInit.nAckSeq.val=0
pInit.vBusy.val=1
pInit.vRetry.val=0
pInit.vTask.val={task}
pInit.tReq.txt="CM1|"
covx pInit.nBoot.val,pInit.tNum.txt,0,0
pInit.tReq.txt+=pInit.tNum.txt
pInit.tReq.txt+="|"
covx pInit.vSeq.val,pInit.tNum.txt,0,0
pInit.tReq.txt+=pInit.tNum.txt
pInit.tReq.txt+="|"
covx {origin},pInit.tNum.txt,0,0
pInit.tReq.txt+=pInit.tNum.txt
pInit.tReq.txt+="|"
covx pInit.nView.val,pInit.tNum.txt,0,0
pInit.tReq.txt+=pInit.tNum.txt
pInit.tReq.txt+="|"
pInit.tReq.txt+={command}
prints pInit.tReq.txt,0
printh 0A''')


def request(verb, page=None):
    return send(json.dumps(verb), page=page, task=1)


def indexed_request(verb, expression):
    return f'''pInit.tCommand.txt="{verb}|"
pInit.vTemp.val={expression}
covx pInit.vTemp.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
''' + send("pInit.tCommand.txt", task=1)


def edit_value(field, value, title, kind=0, index=None, limit=24, return_page=None):
    mode = input_mode(field)
    if mode == 3:
        title, limit = "Date DD-MM-YYYY", 10
    elif mode == 4:
        title, limit = ("Time HH:MM:SS", 8) if kind != 1 else ("Time HH:MM[:SS]", 8)
    lines = [
        f'pInit.tField.txt="{field}"', f'pInit.tTitle.txt="{title}"',
        f"pInit.tEdit.txt={value}.txt", f"pInit.vEditKind.val={kind}",
        f"pInit.vEditPage.val={return_page if return_page is not None else 'pInit.vPage.val'}",
        f"pInit.vMax.val={limit}", f"pInit.vInputMode.val={mode}",
        "pInit.vEditView.val=pInit.nView.val", "pInit.vEditBoot.val=pInit.nBoot.val",
    ]
    if index is not None:
        lines.append(f"pInit.vEditRow.val={index}")
    lines += ["page pEdit" if not mode else "page pNumber"]
    return branch("pInit.vBusy.val==0", "\n".join(lines))


def input_mode(field):
    if field in ("operator", "project", "name", "retarderBrand", "acceleratorBrand", "flyAshBrand"):
        return 0
    if field in ("date", "pourDate"):
        return 3
    if field in ("clock", "time", "pourClock"):
        return 4
    if field == "datum":
        return 5
    return 2 if field == "temp" else 1


def status_fields(page):
    lists_with_storage = ("pHist", "pSaveB", "pSelB")
    lines = ["pInit.vIndex.val=pInit.vStorage.val"] if page in lists_with_storage else []
    lines += ["pInit.tStatus.txt=pInit.tData.txt", *status_corners(page),
             number_column("pInit.vStorage", 4), column("pInit.tDate", 0),
             number_column("pInit.vMask", 14), "pInit.vSensors.val=0",
             "pInit.vCount.val=pInit.vMask.val",
             branch("pInit.vCount.val>=4", "pInit.vSensors.val+=1\npInit.vCount.val-=4"),
             branch("pInit.vCount.val>=2", "pInit.vSensors.val+=1\npInit.vCount.val-=2"),
             branch("pInit.vCount.val>=1", "pInit.vSensors.val+=1")]
    if page in ("pDev", "pInit"):
        lines.append(number_column("pInit.vIdentity", 17))
    if page in ("pSaveB", "pSelB"):
        lines += ["pInit.vTemp.val=pInit.vChosen.val", number_column("pInit.vChosen", 15),
                  branch("pInit.vTemp.val!=pInit.vChosen.val", "pInit.vListDirty.val=1"),
                  number_column("pInit.vSavedCount", 19)]
    if page in lists_with_storage:
        lines.append(branch("pInit.vIndex.val!=pInit.vStorage.val", "pInit.vListDirty.val=1"))
    if page == "pSelB":
        lines += [number_column("pInit.vRun", 5),
                  visibility("mResume", "pInit.vRun.val!=0"),
                  start_hint()]
    if page == "pInit":
        lines += [column("pInit.tSplit", 9), "pInit.vProtocolReady.val=0",
                  branch('pInit.tSplit.txt=="1.0.1"', "pInit.vProtocolReady.val=1"),
                  branch("pInit.vProtocolReady.val==1&&pInit.vSplashStage.val==0&&tmSplash.en==0",
                         "tmSplash.en=1"),
                  'tChkClock.txt="Database: OK"',
                  branch("pInit.vStorage.val!=0",
                         'tChkClock.txt="Database error "\n'
                         "covx pInit.vStorage.val,pInit.tNum.txt,0,0\n"
                         "tChkClock.txt+=pInit.tNum.txt"),
                  'tChkSensors.txt="Sensors: "\n'
                  "covx pInit.vSensors.val,pInit.tNum.txt,0,0\n"
                  "tChkSensors.txt+=pInit.tNum.txt\n"
                  'tChkSensors.txt+="/3"',
                  branch("pInit.vSensors.val==0", 'tChkSensors.txt="No sensor detected"')]
        lines.append(branch("pInit.vProtocolReady.val==0", 'tReady.txt="Update MCU firmware to 1.0.1"\n'
                            'tProgress.txt="0%"\njLink.val=0\ntmSplash.en=0\npInit.vSplashStage.val=0'))
    if page in ("pRT", "pKuat", "pBase"):
        for name, index in (("tS1", 10), ("tS2", 11), ("tS3", 12), ("tAvg", 13)):
            if name in COMPONENT_NAMES[page]:
                lines += [column(name, index), measurement(name, " °C", True),
                          branch(f'{name}.txt==""', f'{name}.txt="--"')]
    if page == "pRT":
        lines += ["tNowD.txt=pInit.tDate.txt", display_date("tNowD"), "tNowT.txt=pInit.tTime.txt",
                  "tNowTemp.txt=tAvg.txt"]
    if page == "pDev":
        lines += [column("tDevVersion", 9), "covx pInit.vSensors.val,tDevSensor.txt,0,0",
                  'tDevSensor.txt+="/3 connected"', 'tDevStatus.txt="READY"',
                  'tDevHealth.txt="microSD ready"',
                  branch("pInit.vStorage.val!=0", 'tDevHealth.txt="Check the microSD card"'),
                  "tDevStatus.pco=65535",
                  branch("pInit.vSensors.val==0", 'tDevStatus.txt="NO SENSOR"'),
                  branch("pInit.vStorage.val!=0", 'tDevStatus.txt="SD ERROR"'),
                  branch('pInit.tDate.txt==""', 'tDevStatus.txt="SET CLOCK"')]
    if page == "pSet":
        lines += [number_column("pInit.vInterval", 6), number_column("pInit.vBright", 7),
                  number_column("pInit.vFlags", 8),
                  "pInit.vTemp.val=pInit.vInterval.val/3600", "covx pInit.vTemp.val,tHour.txt,2,0",
                  "pInit.vTemp.val=pInit.vInterval.val/60%60", "covx pInit.vTemp.val,tMin.txt,2,0",
                  "pInit.vTemp.val=pInit.vInterval.val%60", "covx pInit.vTemp.val,tSec.txt,2,0",
                  "covx pInit.vBright.val,tBright.txt,0,0", 'tBright.txt+="%"']
        for name, mask in (("mTap8", 1), ("mTap9", 2)):
            rect = geometry(page, name)
            lines += [f"pInit.vTemp.val=pInit.vFlags.val&{mask}",
                      branch("pInit.vTemp.val>0", crop(page, rect)) +
                      "\nelse\n{\n" + crop(page, rect, "alternate") + "\n}"]
    return "\n".join([*lines, "pInit.vStatusReady.val=1"])


MIX = {"tCem": 0, "tWat": 1, "tCoa": 2, "tFin": 3, "tRetP": 4,
       "tAccP": 5, "tFlyP": 6, "tRetB": 7, "tAccB": 8, "tFlyB": 9, "tWC": 10}
BASE = {"tName": 1, "tBase": 1, "tTarget": 2, "tDatum": 3}
RUN = {"tPDate": 4, "tPour": 5, "tNowD": 6, "tNowT": 7,
       "tInitTemp": 8, "tAvg": 8, "tElapsed": 9, "tM": 10, "tFc": 11, "tPct": 12}
COMPONENT_NAMES = {}


def assignments(page, mapping, dates=()):
    lines = []
    for name, index in mapping.items():
        if name in COMPONENT_NAMES[page]:
            lines.append(column(name, index))
            if name in dates:
                lines.append(display_date(name))
            if name in ("tTarget", "tDatum"):
                lines.append(measurement(name, " MPa" if name == "tTarget" else " °C"))
    return "\n".join(lines)


def visibility(name, condition):
    return branch(condition, f"vis {name},1\ntsw {name},1") + f"\nelse\n{{\n{hide(name)}\n}}"


def hide(name):
    return f"tsw {name},0\nvis {name},0"


def pending_actions(events, page, keys=None, list_actions=()):
    keys = keys or {}
    actions = []
    for event_name, action in list(events.items()):
        name, phase = event_name.split(".")
        if phase != "up":
            continue
        i = len(actions) + 1
        key = keys.get(name, "0")
        queue = f"""pInit.vTap.val={i}
pInit.vTapBoot.val=pInit.nBoot.val
pInit.vTapView.val=pInit.nView.val
pInit.vTapId.val={key}"""
        events[event_name] = branch("pInit.vBusy.val==0&&pInit.vStatusReady.val==1", action) + "\nelse\n{\n" + branch(
            "pInit.vTask.val==0&&pInit.vTap.val==0&&pInit.nBoot.val>0", queue) + "\n" + branch(
            "pInit.vTask.val==1", 'tNotice.txt="Please wait for the current action"') + "\n}"
        if name in list_actions:
            after_release = branch("pInit.vBusy.val==0||pInit.vTask.val==0",
                                   branch("pInit.vTap.val==0&&pInit.nBoot.val>0", queue))
            settled = branch("pInit.vTouchPhase.val==0", events[event_name])
            events[event_name] = branch(
                "vBlockTap.val==0&&pInit.vListReady.val==1&&pInit.vListShift.val==0",
                branch("pInit.vTouchPhase.val==2", after_release) + "\nelse\n{\n" + settled + "\n}")
        valid = (f"pInit.vTapId.val=={key}" if key != "0" else None)
        click = f"click {name},0"
        if valid:
            click = branch(valid, click) + '\nelse\n{\npInit.tMsg.txt="List updated. Tap the item again."\n}'
        actions.append(branch(f"pInit.vDispatch.val=={i}", click))
    if not actions:
        return ""
    dispatch = f"dp=={page}&&pInit.vBusy.val==0&&pInit.vTap.val>0&&pInit.vStatusReady.val==1"
    if list_actions:
        dispatch += "&&pInit.vTouchPhase.val==0&&pInit.vListShift.val==0"
    return branch(dispatch, """pInit.vDispatch.val=pInit.vTap.val
pInit.vTap.val=0
""" + branch("pInit.vTapView.val==pInit.nView.val&&pInit.vTapBoot.val==pInit.nBoot.val",
             "\n".join(actions)) + '\nelse\n{\npInit.tMsg.txt="View updated. Tap again."\n}')


def start_hint(target="tStartHint"):
    return f'''{target}.txt=""
if(pInit.vStorage.val!=0)
{{
{target}.txt="Check the microSD card"
}}else if(pInit.vChosen.val==0)
{{
{target}.txt="Select a baseline first"
if(pInit.vSavedCount.val==0)
{{
{target}.txt="Create a baseline first"
}}
}}else if(pInit.tDate.txt=="")
{{
{target}.txt="Set the device clock first"
}}else if(pInit.vMask.val==0)
{{
{target}.txt="Connect a temperature probe"
}}'''


def range_label(count, size):
    return f'''tPageRows.txt=""
if({count}>0)
{{
pInit.vTemp.val=pInit.vOffset.val+1
covx pInit.vTemp.val,tPageRows.txt,0,0
tPageRows.txt+="-"
pInit.vTemp.val=pInit.vOffset.val+{size}
if(pInit.vTemp.val>{count})
{{
pInit.vTemp.val={count}
}}
covx pInit.vTemp.val,pInit.tNum.txt,0,0
tPageRows.txt+=pInit.tNum.txt
tPageRows.txt+=" / "
covx {count},pInit.tNum.txt,0,0
tPageRows.txt+=pInit.tNum.txt
}}'''


def lab_fields(page, i):
    if page == "pSchedule":
        date = f"tDate{i}"
        row_art = row_artwork(page, i, "patch")
        return "\n".join([row_art, assignments(page, {f"tDay{i}": 1, date: 2, f"tTim{i}": 3}),
                          schedule_weekday(date, f"tHari{i}"), display_date(date),
                          *(f"vis {field},1" for field in schedule_cells(i))])
    fields = (f"tDay{i}", f"tTim{i}", f"tFc{i}", f"tT{i}")
    focus = f"pInit.vFocusId.val=pInit.vLab{i}.val\npInit.vFocusFirst.val=0\npInit.vFocusRow.val=0"
    return "\n".join([
        number_column(f"pInit.vLab{i}", 0),
        f"pInit.vIndex.val=pInit.vOffset.val+{i+1}",
        branch("pInit.vFocusRow.val==pInit.vIndex.val", focus),
        branch("pInit.vFocusFirst.val==1", focus) if i == 0 else "",
        branch("pInit.vTotal.val==1&&pInit.vFocusId.val==0", focus) if i == 0 else "",
        *lab_cell_pictures(i, f"pInit.vFocusId.val==pInit.vLab{i}.val"),
        assignments(page, {fields[0]: 1, fields[2]: 5, fields[3]: 4}),
        column(f"tFull{i}", 3),
        f'tTim{i}.txt=""',
        branch(f'tFull{i}.txt!=""', f"substr tFull{i}.txt,tTim{i}.txt,0,5"),
        *(f"vis {field},1\ntsw {field},1" for field in fields),
        visibility(f"mDelete{i}", "pInit.vTotal.val>3"),
    ])


def lab_cell_pictures(i, condition):
    base = picture_id(picture("pMatu", "patch"))
    active = picture_id(picture("pMatu", "alternate"))
    return [
        f"pInit.vCrop.val={base}",
        branch(condition, f"pInit.vCrop.val={active}"),
        *(f"t{prefix}{i}.picc=pInit.vCrop.val" for prefix in ("Day", "Tim", "Fc", "T")),
    ]


def lab_summary():
    return "\n".join([number_column("pInit.vTotal", 6), column("tPourTime", 5), column("pInit.tPourDate", 4),
                      'tDatumLab.txt="Datum Temperature: "', column("pInit.tSplit", 3),
                      'tDatumLab.txt+=pInit.tSplit.txt\ntDatumLab.txt+=" °C"',
                      "pInit.tPourClock.txt=tPourTime.txt", "pInit.vDraft.val=pInit.nAckValue.val"])


def lab_roster():
    lines = ["pInit.vLabSlots.val=pInit.vTotal.val-pInit.vOffset.val",
             branch("pInit.vLabSlots.val<1", "pInit.vLabSlots.val=1"),
             branch(f"pInit.vLabSlots.val>{LAB_ROWS}", f"pInit.vLabSlots.val={LAB_ROWS}"),
             branch("pInit.vDraft.val==0", "pInit.vLabSlots.val=0")]
    # A draft without rows exposes a virtual Day 0. Apply creates it in the MCU.
    lines.append(branch("pInit.vTotal.val==0&&pInit.vDraft.val>0",
                        'pInit.vFocusFirst.val=1\ntDay0.txt="0"\ntTim0.txt=""\ntFc0.txt=""\ntT0.txt=""\ntFull0.txt=tPourTime.txt\n'
                        'if(tFull0.txt!="")\n{\nsubstr tFull0.txt,tTim0.txt,0,5\n}'))
    lines.append(branch("pInit.vTotal.val==0&&pInit.vDraft.val>0", "\n".join([
        *(f"vis t{prefix}0,1\ntsw t{prefix}0,1" for prefix in ("Day", "Tim", "Fc", "T")),
        *lab_cell_pictures(0, "pInit.vFocusFirst.val==1"),
    ])))
    lines += [lab_actions_layout(), range_label("pInit.vTotal.val", LAB_ROWS)]
    return "\n".join(lines)


def lab_actions_layout():
    page = "pMatu"
    first = [visibility(name, f"pInit.vLabSlots.val=={LAB_ROWS}") for name in ("mAddDay", "mSensor")]
    strip = region(page, "maturityActions")
    for i, rect in enumerate(region(page, "rows")[1:], 1):
        y = rect[1]
        names = [*(f"t{prefix}{i}" for prefix in ("Day", "Tim", "Fc", "T")), f"mDelete{i}"]
        # The unused row shares the two hit areas beneath the last displayed row.
        actions = [
            *(f'{name}.txt=""\nvis {name},1\ntsw {name},1' for name in names),
            crop(page, rect), patch_at(page, (strip[0], y), strip),
        ]
        first.append(branch(f"pInit.vLabSlots.val=={i}", "\n".join(actions)))
    return "\n".join(first)


def saved_fields(page, i):
    name, value, datum, date = (f"{field}{i}" for field in ("tName", "tVal", "tDatum", "tSavedDate"))
    card = region(page, "cards")[i]
    selected = f"pInit.vId{i}.val==pInit.vChosen.val"
    lines = [column(name, 1), column(value, 2), measurement(value, " MPa"),
             column(datum, 3), measurement(datum, " °C"), column(date, 4), display_date(date),
             number_column(f"pInit.vId{i}", 0),
             branch(selected, crop(page, card, "alternate")) + "\nelse\n{\n" + crop(page, card, "patch") + "\n}",
             *(draw_value(page, field, field) for field in (name, value, datum, date)),
             f"tsw mPick{i},1"]
    if page == "pSaveB":
        lines += [f"tsw mPickTag{i},1", f"tsw mDelete{i},1"]
    return "\n".join(lines)


def history_cells(i):
    return tuple(f"t{name}{i}" for name in ("Id", "Name", "Val", "Date", "Count"))


def history_fields(i):
    fields = history_cells(i)
    return "\n".join([crop("pHist", region("pHist", "cards")[i], "patch"),
                      assignments("pHist", dict(zip(fields, (0, 1, 4, 2, 5))), (f"tDate{i}",)),
                      number_column(f"vHist{i}", 0), measurement(f"tVal{i}", " MPa"),
                      *(draw_value("pHist", field, field) for field in fields), f"tsw mHistory{i},1"])


def history_state():
    lines = [visibility("mDetail", "vHist0.val>0"), 'tHistEmpty.txt=""',
             branch("vHist0.val==0",
                     '\ntHistEmpty.txt="No measurements saved"\n' +
                     branch("pInit.vStorage.val!=0", 'tHistEmpty.txt="Check the microSD card"') +
                     "\n" + draw_value("pHist", "tHistEmpty", "tHistEmpty"))]
    return "\n".join(lines)


def model_fields():
    data = assignments("pBaseR", {"tA": 0, "tB": 1, "tR2": 2, "tCount": 3,
                                  "tFactor": 4, "tOp": 6, "tProj": 7, "tDate": 8}, ("tDate",))
    return data + "\n" + branch("vPlotModel.val!=pInit.nAckValue.val", f'''vPlotModel.val=pInit.nAckValue.val
{number_column("pInit.vPairs", 3)}
tEq.txt="fc = "
tEq.txt+=tA.txt
substr tB.txt,pInit.tSplit.txt,0,1
if(pInit.tSplit.txt=="-")
{{
tEq.txt+=" "
}}else
{{
tEq.txt+=" + "
}}
tEq.txt+=tB.txt
tEq.txt+=" ln(M)"
pInit.tPlotFit.txt="R2 "
pInit.tPlotFit.txt+=tR2.txt
pInit.tPlotFit.txt+="    Lab pairs "
pInit.tPlotFit.txt+=tCount.txt
{column("pInit.tSplit", 4)}
pInit.tPlotFit.txt+="    FKZ ages "
pInit.tPlotFit.txt+=pInit.tSplit.txt
{plot_begin("pBaseR")}
vPlotPhase.val=1''')


def tasks(page):
    items = [("status", None, status_fields(page))]
    if page == "pUser":
        items.append(("identity", None, assignments(page, {"tOp": 0, "tProj": 1, "tDate": 2}, ("tDate",))))
    if page in ("pBase", "pNewB", "pMatu", "pBaseR", "pRT", "pStr", "pHistD"):
        body = assignments(page, BASE)
        if page == "pNewB":
            body = assignments(page, {"tName": 1, "tFc": 2, "tTemp": 3})
        if page == "pBaseR":
            body += "\npInit.vRevision.val=pInit.nAckValue.val"
        if page == "pMatu":
            body = lab_summary()
        items.append(("baseline", None, body))
    if page in ("pMat", "pBaseR"):
        items.append(("mix", None, assignments(page, MIX)))
    if page == "pBaseR":
        items.append(("model", None, model_fields()))
        items.append(("plot", None, plot_ack(page)))
    if page in ("pRT", "pStr", "pHistD", "pPoints"):
        data = RUN if page != "pRT" else {
            name: index for name, index in RUN.items() if name not in ("tNowD", "tNowT", "tAvg")
        }
        readings = assignments(page, data, ("tPDate", "tNowD"))
        if page in ("pRT", "pStr"):
            readings += "\n" + "\n".join((measurement("tFc", " MPa", True),
                measurement("tPct", "%"), measurement("tM", " °C·h")))
        if page == "pStr":
            readings += "\n" + measurement("tAvg", " °C", True)
        if page == "pRT":
            readings += "\n" + measurement("tInitTemp", " °C", True)
        readings += "\npInit.vRevision.val=pInit.nAckValue.val\n" + number_column("pInit.vTotal", 2)
        items.append(("run", None, readings))
    if page == "pHistD":
        items.append(("detail", None, assignments(page, {"tId": 0, "tSavedAt": 1, "tOp": 3,
                                                        "tProj": 4, "tDate": 2}, ("tSavedAt",))))
    if page in ("pMatu", "pSchedule"):
        for i in range(LAB_ROWS):
            items.append(("labrow", i, lab_fields(page, i)))
    if page in ("pSaveB", "pSelB"):
        for i in range(4):
            body = saved_fields(page, i)
            items.append(("savedrow", i, body))
    if page == "pHist":
        for i in range(HISTORY_ROWS):
            items.append(("historyrow", i, history_fields(i)))
        items.append(("historyrow", HISTORY_ROWS, ""))
    if page == "pHistD":
        for i in range(5):
            body = row_artwork(page, i, "patch") + f'\nvis tLog{i},1\ntsw tLog{i},1\ntLog{i}.txt="Day "\n'
            for prefix, index in (("", 0), (" ", 2), (" T ", 3), (" M ", 4), (" Fc ", 5)):
                body += column("pInit.tSplit", index) + f'\ntLog{i}.txt+="{prefix}"\ntLog{i}.txt+=pInit.tSplit.txt\n'
            items.append(("point", i, body))
    if page == "pPoints":
        for i in range(POINT_ROWS):
            fields = point_cells(i)
            value = assignments(page, dict(zip(fields, range(len(fields)))), (f"tDate{i}",))
            row = row_artwork(page, i, "patch")
            items.append(("point", i, "\n".join([row, value,
                                                *(f"vis {field},1\ntsw {field},1" for field in fields),
                                                f"vis mGap{i},1\ntsw mGap{i},1"])))
    return items


def clear_row(page, source, row):
    if source == "labrow":
        if page == "pSchedule":
            fields = schedule_cells(row)
        else:
            return f"pInit.vLab{row}.val=0\n" + "\n".join(
                hide(f"t{prefix}{row}") for prefix in ("Day", "Tim", "Fc", "T")
            ) + "\n" + hide(f"mDelete{row}") + "\n" + row_artwork(page, row)
    elif source == "savedrow":
        fields = [f"{name}{row}" for name in ("tName", "tVal", "tDatum", "tSavedDate")]
    elif source == "historyrow":
        fields = history_cells(row)
    elif source == "point":
        fields = [f"tLog{row}"] if page == "pHistD" else point_cells(row)
    else:
        return ""
    result = [f'{field}.txt=""' for field in fields]
    if page == "pSchedule" and source == "labrow":
        result += [*(f"vis {field},0" for field in fields), row_artwork(page, row)]
    if source == "point":
        result += [*(hide(field) for field in fields), row_artwork(page, row)]
        if page == "pPoints":
            result.append(hide(f"mGap{row}"))
    if source == "savedrow":
        result += [f"pInit.vId{row}.val=0\ntsw mPick{row},0", crop(page, region(page, "cards")[row])]
        if page == "pSaveB":
            result.append(f"tsw mDelete{row},0\ntsw mPickTag{row},0")
    if source == "historyrow":
        result += [f"vHist{row}.val=0", f"tsw mHistory{row},0",
                   crop(page, region(page, "cards")[row])]
    return "\n".join(result)


def list_geometry(page):
    name = "cards" if page in ("pSaveB", "pSelB", "pHist") else "rows"
    rows = region(page, name)
    x, y, w, _ = rows[0]
    _, last_y, _, last_h = rows[-1]
    return x, y, w, last_y + last_h - y, rows[1][1] - y


def mount_scroll(page, document, events):
    _, size, _ = SCROLL_LISTS[page]
    x, y, w, h, pitch = list_geometry(page)
    for name in ("vStartX", "vStartY", "vPriorX", "vPriorY", "vDragX", "vDragY", "vBlockTap"):
        update_component(document, dict(variable(name), vscope=0))
    for i in range(size):
        update_component(document, dict(variable(f"tRowData{i}", "", 255), vscope=0))
    update_component(document, dict(name="tcList", type="touch-capture", events=["down", "up"]))
    update_component(document, dict(name="tmDrag", type="timer", tim=50, en=0, events=["timer"]))
    next(c for c in document["component"] if c["name"] == "tmPoll")["tim"] = LIST_TICK_MS
    events[f"{page}.loadend"] += """
tmDrag.en=0
vBlockTap.val=0
pInit.vTouchPhase.val=0
pInit.vListBase.val=pInit.vOffset.val
pInit.vListShift.val=0
pInit.vListReuse.val=0
pInit.vListDirty.val=1
pInit.vListReady.val=0"""
    events["tcList.down"] = f"""if(pInit.vTouchPhase.val==2)
{{
pInit.vTap.val=0
}}
tmDrag.en=0
pInit.vTouchPhase.val=0
vBlockTap.val=0
vStartX.val=tch0
vStartY.val=tch1
if(vStartX.val>={x}&&vStartX.val<{x+w+8}&&vStartY.val>={y}&&vStartY.val<{y+h})
{{
pInit.vTouchPhase.val=1
vPriorX.val=tch2
vPriorY.val=tch3
vDragX.val=0
vDragY.val=0
tmDrag.en=1
if(pInit.vListReady.val==0||pInit.vListShift.val!=0)
{{
vBlockTap.val=1
}}
}}"""
    events["tcList.up"] = branch("pInit.vTouchPhase.val==1", "pInit.vTouchPhase.val=2")
    shift = f"""pInit.vTemp.val=vDragY.val
if(pInit.vTemp.val<0)
{{
pInit.vTemp.val*=-1
}}
if(pInit.vTemp.val>=22&&pInit.vTemp.val>vDragX.val)
{{
pInit.vTemp.val+={pitch//2}
pInit.vTemp.val/={pitch}
if(pInit.vTemp.val<1)
{{
pInit.vTemp.val=1
}}
if(vDragY.val>0)
{{
pInit.vListShift.val+=pInit.vTemp.val
}}else
{{
pInit.vListShift.val-=pInit.vTemp.val
}}
vBlockTap.val=1
}}"""
    # Read the release position after the touch event returns. Keep the last live sample
    # if the panel has not advanced its last-touch coordinates.
    settled = branch("tch2!=vPriorX.val||tch3!=vPriorY.val",
                     branch("tch2>=0&&tch2<480&&tch3>=0&&tch3<800", measure_drag("tch2", "tch3")))
    finish = "\n".join([
        "tmDrag.en=0", "pInit.vTouchPhase.val=0",
        branch("tch0==0&&tch1==0", settled + "\n" + shift) + "\nelse\n{\nvBlockTap.val=1\n}",
        branch("vBlockTap.val==1", "pInit.vTap.val=0"),
    ])
    held = branch("tch0!=0||tch1!=0", measure_drag("tch0", "tch1"))
    events["tmDrag.timer"] = branch("pInit.vTouchPhase.val==1", held) + "\nelse\n{\n" + finish + "\n}"


def measure_drag(x, y):
    return f"""vDragX.val={x}-vStartX.val
if(vDragX.val<0)
{{
vDragX.val*=-1
}}
vDragY.val=vStartY.val-{y}
if(vDragX.val>=16||vDragY.val>=16||vDragY.val<=-16)
{{
vBlockTap.val=1
}}"""


def scroll_bounds(page):
    _, size, total = SCROLL_LISTS[page]
    limit = f"pInit.vListMax.val={total}-{size}\n" + branch("pInit.vListMax.val<0", "pInit.vListMax.val=0")
    if page == "pHist":
        # A successful lookahead proves there is a record at the next full-window start.
        limit += "\n" + branch(f"{total}<0", f"pInit.vListMax.val=pInit.vListBase.val+{size}")
    return limit


def apply_scroll(page, first):
    _, size, _ = SCROLL_LISTS[page]
    cache = [f"tRowData{i}.txt" for i in range(size)]
    forward = "\n".join(f"{dst}={src}" for dst, src in zip(cache, cache[1:]))
    backward = "\n".join(f"{dst}={src}" for dst, src in zip(reversed(cache[1:]), reversed(cache[:-1])))
    shift = f"""pInit.vListShift.val=pInit.vIndex.val-pInit.vListBase.val
pInit.vListBase.val=pInit.vIndex.val
pInit.vListReady.val=0
pInit.vListDirty.val=1
pInit.vListReuse.val=1
pInit.vStep.val={first}
if(pInit.vListShift.val>={size}||pInit.vListShift.val<=-{size})
{{
pInit.vListReuse.val=0
}}else
{{
while(pInit.vListShift.val>0)
{{
{forward}
{cache[-1]}=""
pInit.vListShift.val-=1
}}
while(pInit.vListShift.val<0)
{{
{backward}
{cache[0]}=""
pInit.vListShift.val+=1
}}
}}"""
    return branch("pInit.vTouchPhase.val==0&&pInit.vListReady.val==1&&pInit.vListShift.val!=0", "\n".join([
        scroll_bounds(page), "pInit.vIndex.val=pInit.vListBase.val+pInit.vListShift.val",
        branch("pInit.vIndex.val<0", "pInit.vIndex.val=0"),
        branch("pInit.vIndex.val>pInit.vListMax.val", "pInit.vIndex.val=pInit.vListMax.val"),
        branch("pInit.vIndex.val!=pInit.vListBase.val", shift),
        "pInit.vListShift.val=0",
    ]))


def stage_row(page, row):
    _, size, _ = SCROLL_LISTS[page]
    lines = []
    if page == "pHist":
        lines += [f"pInit.vIndex.val=pInit.vListBase.val+{row}",
                  branch("pInit.nAckCode.val==15&&pInit.vHistoryEnd.val!=pInit.vIndex.val",
                         "pInit.vHistoryEnd.val=pInit.vIndex.val\npInit.vListDirty.val=1"),
                  branch("pInit.nAckCode.val==0&&pInit.vHistoryEnd.val>=0&&pInit.vIndex.val>=pInit.vHistoryEnd.val",
                         "pInit.vHistoryEnd.val=-1\npInit.vListDirty.val=1")]
    if row < size:
        cache = f"tRowData{row}.txt"
        lines += [branch("pInit.nAckCode.val!=0", 'pInit.tData.txt=""'),
                  branch(f"{cache}!=pInit.tData.txt", f"{cache}=pInit.tData.txt\npInit.vListDirty.val=1")]
    return "\n".join(lines)


def read_visible_row(page, row, read):
    _, size, total = SCROLL_LISTS[page]
    index = f"pInit.vListBase.val+{row}"
    skip = "pInit.vStep.val+=1"
    cache = f"tRowData{row}.txt"
    empty = branch(f'{cache}!=""', f'{cache}=""\npInit.vListDirty.val=1') + "\n" if row < size else ""
    if row < size:
        read = branch(f'pInit.vListReuse.val==1&&tRowData{row}.txt!=""', skip) + "\nelse\n{\n" + read + "\n}"
    out_of_range = f"pInit.vIndex.val>={total}" if page != "pHist" else f"{total}>=0&&pInit.vIndex.val>{total}"
    return (f"pInit.vIndex.val={index}\n" + branch(out_of_range, empty + skip) +
            "\nelse\n{\n" + read + "\n}")


def scroll_indicator(page, size, total):
    x, y, w, h, _ = list_geometry(page)
    x += w + 4
    count = f"pInit.vIndex.val={total}"
    if page == "pHist":
        count += "\n" + branch("pInit.vIndex.val<0", f"pInit.vIndex.val=pInit.vOffset.val+{size+1}")
    return "\n".join([crop(page, (x, y, 3, h)), count, branch(f"pInit.vIndex.val>{size}", f"""
fill {x},{y},3,{h},{rgb565("#48525f")}
pInit.vTemp.val={h*size}
pInit.vTemp.val/=pInit.vIndex.val
if(pInit.vTemp.val<20)
{{
pInit.vTemp.val=20
}}
pInit.vCount.val={h}-pInit.vTemp.val
pInit.vCount.val*=pInit.vOffset.val
pInit.vIndex.val-={size}
pInit.vCount.val/=pInit.vIndex.val
pInit.vCount.val+={y}
fill {x},pInit.vCount.val,3,pInit.vTemp.val,{rgb565("#f39443")}""")])


def paint_list(page, items):
    source, size, total = SCROLL_LISTS[page]
    lines = ["pInit.vOffset.val=pInit.vListBase.val"]
    for field, row, body in items:
        if field != source or row >= size:
            continue
        cache = f"tRowData{row}.txt"
        lines.append(branch(f'{cache}!=""', f"pInit.tData.txt={cache}\n{body}") +
                     "\nelse\n{\n" + clear_row(page, source, row) + "\n}")
    if page == "pMatu":
        lines.append(lab_roster())
    elif page in ("pSaveB", "pSelB"):
        lines.append(range_label(total, size))
        if page == "pSaveB":
            lines += ['tEmptyList.txt=""', branch(f"{total}==0", 'tEmptyList.txt="No saved baselines"'),
                      branch("pInit.vStorage.val!=0", 'tEmptyList.txt="Check the microSD card"'),
                      branch('tEmptyList.txt!=""', draw_value(page, "tEmptyList", "tEmptyList"))]
    elif page == "pHist":
        lines.append(history_state())
    lines.append(scroll_indicator(page, size, total))
    return branch("pInit.vListDirty.val==1", "\n".join(lines + ["pInit.vListDirty.val=0"])) + """
pInit.vListReuse.val=0
pInit.vListReady.val=1"""


def error_message():
    return '''pInit.tMsg.txt="ConMT error "
covx pInit.nAckCode.val,pInit.tNum.txt,0,0
pInit.tMsg.txt+=pInit.tNum.txt
if(pInit.nAckCode.val==1)
{
pInit.tMsg.txt="Invalid input. Check the field format."
}
if(pInit.nAckCode.val==2)
{
pInit.tMsg.txt="Complete the required fields"
}
if(pInit.nAckCode.val==3)
{
pInit.tMsg.txt="Complete the previous step first"
if(pInit.vPage.val==8||pInit.vPage.val==10)
{
pInit.tMsg.txt="Select a baseline first"
}
}
if(pInit.nAckCode.val==15)
{
pInit.tMsg.txt="This item is no longer available"
}
if(pInit.nAckCode.val==6)
{
pInit.tMsg.txt="Check the microSD card"
}
if(pInit.nAckCode.val==9)
{
pInit.tMsg.txt="Connect a temperature probe"
}
if(pInit.nAckCode.val==10)
{
pInit.tMsg.txt="Set date/time before measurement"
}
if(pInit.nAckCode.val==11)
{
pInit.tMsg.txt="Enter at least two valid lab pairs"
}
if(pInit.nAckCode.val==12)
{
pInit.tMsg.txt="Add a later checkpoint before SAVE"
}'''


def retry_request(error_field):
    return f'''pInit.vRetry.val+=1
if(pInit.vRetry.val==15)
{{
prints pInit.tReq.txt,0
printh 0A
}}
if(pInit.vRetry.val>=30)
{{
pInit.vBusy.val=0
{error_field}.txt="No answer. Return and reconnect."
}}'''


def timer(page, pending=""):
    items = tasks(page)
    source = SCROLL_LISTS[page][0] if page in SCROLL_LISTS else None
    first = next((i for i, (field, _, _) in enumerate(items, 1) if field == source), 0)
    tick = LIST_TICK_MS if first else 250
    data_handlers = []
    for i, (field, row, body) in enumerate(items, 1):
        if field == source:
            data_handlers.append(branch(f"pInit.vGet.val=={i}", stage_row(page, row)))
            continue
        if field == "plot":
            data_handlers.append(branch(f"pInit.vGet.val=={i}", body + "\n" +
                branch("vPlotPhase.val<3", "pInit.vTemp.val=vPoint.val%8\n" +
                       branch("pInit.vTemp.val==0", "pInit.vStep.val=0") +
                       "\nelse\n{\npInit.vStep.val-=1\n}")))
            continue
        success = branch("pInit.nAckCode.val==0", body) if body else ""
        data_handlers.append(branch(f"pInit.vGet.val=={i}", success))
    action_ok = 'pInit.tMsg.txt=""\n'
    if page == "pRT":
        action_ok += column("pInit.tSplit", 5, "pInit.tReq") + "\n" + branch('pInit.tSplit.txt=="CHECK_ADD"',
            'pInit.tMsg.txt="Day saved. Tap REAL TIME MONITORING."') + "\n"
    finish = '''pInit.vBusy.val=0
pInit.vRetry.val=0
if(pInit.nAckCode.val==4||pInit.nAckCode.val==8)
{
pInit.nBoot.val=0
pInit.vStep.val=0
pInit.vTap.val=0
pInit.vStatusReady.val=0
}else
{
if(pInit.vTask.val==0)
{
''' + "\n".join(data_handlers) + '''
pInit.vStep.val+=1
}else
{
if(pInit.nAckCode.val==13)
{
pInit.vToken.val=pInit.nAckValue.val
page pConfirm
}else
{
if(pInit.nAckCode.val!=0)
{
''' + error_message() + '''
}else
{
''' + action_ok + '''
}
''' + ("pInit.vListDirty.val=1\n" if first else "") + '''pInit.vStep.val=1
}
}
}'''
    link_lost = status_header(page)
    if page == "pDev":
        link_lost += '\ntDevStatus.txt="NO LINK"\ntDevSensor.txt="--"'
    retry = f'''pInit.vRetry.val+=1
if(pInit.vRetry.val=={(3750+tick-1)//tick})
{{
prints pInit.tReq.txt,0
printh 0A
}}
if(pInit.vRetry.val>={(7500+tick-1)//tick})
{{
pInit.vBusy.val=0
pInit.nBoot.val=0
pInit.vStep.val=0
pInit.vTap.val=0
pInit.vStatusReady.val=0
pInit.tMsg.txt="No answer from MCU"
''' + link_lost + "\n}"
    lines = [branch("pInit.vBusy.val==1", branch("pInit.nAckSeq.val==pInit.vSeq.val", finish) +
                    "\nelse\n{\n" + retry + "\n}")]
    if page != "pBaseR":
        lines.append(branch('tNotice.txt!=pInit.tMsg.txt', "tNotice.txt=pInit.tMsg.txt"))
    else:
        lines += [branch('pInit.tMsg.txt!=""', "tEq.txt=pInit.tMsg.txt"), plot_actions()]
    requests = [branch("pInit.vStep.val==0", "pInit.vGet.val=0\n" + send('"PAGE_READY"'))]
    for i, (field, row, body) in enumerate(items, 1):
        if field == "plot":
            requests.append(branch(f"pInit.vStep.val=={i}", branch("vPlotPhase.val==1||vPlotPhase.val==2",
                f"pInit.vGet.val={i}\n" + plot_request()) + "\nelse\n{\npInit.vStep.val+=1\n}"))
            continue
        command = f'pInit.tCommand.txt="GET|{field}"'
        if row is not None:
            command += '''
covx pInit.vIndex.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+="|"
pInit.tCommand.txt+=pInit.tNum.txt'''
        read = f"pInit.vGet.val={i}\n" + command + "\n" + send("pInit.tCommand.txt")
        if field == source:
            read = read_visible_row(page, row, read)
            if i == first:
                read = scroll_bounds(page) + "\n" + branch("pInit.vListBase.val>pInit.vListMax.val", """
pInit.vListBase.val=pInit.vListMax.val
pInit.vListReady.val=0
pInit.vListReuse.val=0
pInit.vListDirty.val=1""".strip()) + "\n" + read
        requests.append(branch(f"pInit.vStep.val=={i}", read))
    pause = f'''pInit.vPoll.val+=1
if(pInit.vPoll.val>={(1250+tick-1)//tick})
{{
pInit.vPoll.val=0
pInit.vStep.val=1
}}'''
    if first:
        pause = paint_list(page, items) + "\n" + pause
        if page == "pHist":
            pause = scroll_bounds(page) + "\n" + branch("pInit.vListBase.val>pInit.vListMax.val", f"""
pInit.vListBase.val=pInit.vListMax.val
pInit.vListReady.val=0
pInit.vListReuse.val=0
pInit.vListDirty.val=1
pInit.vStep.val={first}""".strip()) + "\nelse\n{\n" + pause + "\n}"
    requests.append(branch(f"pInit.vStep.val>{len(items)}", pause))
    page_id = {"pPoints": 20, "pSchedule": 24}.get(page)
    if page_id is None:
        page_id = PAGES.index(page)
    if first:
        lines.append(branch(f"pInit.vBusy.val==0&&dp=={page_id}", apply_scroll(page, first)))
    if pending:
        lines.append(pending)
    lines.append(branch(f"pInit.vBusy.val==0&&dp=={page_id}", "\n".join(requests)))
    return "\n".join(lines)


def splash_timer():
    # Match the preview's four 650 ms stages, then show 100% for 700 ms.
    # Missing peripherals are reported as attention states after being checked.
    stages = '''pInit.vSplashStage.val+=1
pInit.vTemp.val=pInit.vSplashStage.val*25
jLink.val=pInit.vTemp.val
covx pInit.vTemp.val,tProgress.txt,0,0
tProgress.txt+="%"
if(pInit.vSplashStage.val==1)
{
tReady.txt="Application started"
}
if(pInit.vSplashStage.val==4)
{
tChkDevice.txt="Device responded"
tmSplash.tim=700
}'''
    rect = region("pInit", "progress")
    x, y, w, h = rect
    stages += f"""\npInit.vTemp.val=jLink.val*{w}
pInit.vTemp.val/=100
picq {x},{y},pInit.vTemp.val,{h},{picture_id(picture("pInit", "patch"))}"""
    return branch("pInit.vProtocolReady.val==1", branch("pInit.vSplashStage.val<4", stages) +
                  "\nelse\n{\n" + request("NAV|1") + "\n}")


def update_component(page, item):
    components = page["component"]
    for index, existing in enumerate(components):
        if existing["name"] == item["name"]:
            components[index] = item
            return
    components.append(item)


def input_binding(page, name, field, events, kind=0, index=None, limit=24, title=None):
    comp = next(c for c in page["component"] if c["name"] == name)
    comp["events"] = ["up"]
    comp["txt_maxl"] = max(comp["txt_maxl"], limit)
    events[name + ".up"] = edit_value(field, name, title or field, kind, index, limit)


def keyboard(numeric=False):
    name = "pNumber" if numeric else "pEdit"
    page = {"page": dict(name=name, type="page", x=0, y=0, w=480, h=800, bco=SURFACE),
            "component": [dict(name="tmEdit", type="timer", tim=250, en=1, events=["timer"]),
                          label("tTitle", "", 20, 46, 440, 54, font="NotoSans28"),
                          label("tInput", "", 20, 112, 440, 86, font="NotoSans28"),
                          label("tError", "", 20, 207, 440, 42),
                          variable("vCase"), variable("vValid"), variable("vLen"),
                          variable("vYear"), variable("vMonth"), variable("vDay"),
                          variable("vPart"), variable("vPos")]}
    components = page["component"]
    load = 'tTitle.txt=pInit.tTitle.txt\ntInput.txt=pInit.tEdit.txt\ntError.txt=""\nvCase.val=0'
    events = {}
    if numeric:
        choices = {"kN1": "-20", "kN2": "-10", "kN4": "0", "kN5": "10"}
        for i, char in enumerate("123456789-0."):
            key = "kMinus" if char == "-" else "kDot" if char == "." else "kN" + char
            components.append(control(key, char, 20 + i % 3 * 150, 261 + i // 3 * 74, 140, 66, font=28, capacity=4))
            if key in choices:
                load += "\n" + branch("pInit.vInputMode.val==5", f'{key}.txt="{choices[key]}"')
            else:
                condition = "pInit.vInputMode.val!=5"
                if key in ("kMinus", "kDot"):
                    condition = ("pInit.vInputMode.val==2" if key == "kMinus" else "pInit.vInputMode.val<=2")
                load += "\n" + visibility(key, condition)
            append = f'tInput.txt+="{char}"'
            if key == "kMinus":
                append = branch("vLen.val==0", append)
            elif key == "kDot":
                append = """vPos.val=0
vPart.val=0
while(vPos.val<vLen.val)
{
substr tInput.txt,pInit.tSplit.txt,vPos.val,1
if(pInit.tSplit.txt==".")
{
vPart.val=1
}
vPos.val+=1
}
""" + branch("vPart.val==0", append)
            else:
                append = (branch("vLen.val==2||vLen.val==5", "\n".join((
                    branch("pInit.vInputMode.val==3", 'tInput.txt+="-"'),
                    branch("pInit.vInputMode.val==4", 'tInput.txt+=":"'),
                ))) + "\n" + append)
            append = "strlen tInput.txt,vLen.val\n" + branch("vLen.val<pInit.vMax.val", append)
            if key in choices:
                append = branch("pInit.vInputMode.val==5", f"tInput.txt={key}.txt") + "\nelse\n{\n" + append + "\n}"
            events[key + ".up"] = branch("pInit.vBusy.val==0", append + '\ntError.txt=""')
    else:
        upper, lower = [], []
        for row, text in enumerate(("1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM-.:")):
            for col, char in enumerate(text):
                key = f"k{row}{col}"
                components.append(button(key, char, 10 + col * 46, 275 + row * 64, 44, 56))
                events[key + ".up"] = key_append(key + ".txt")
                if char.isalpha():
                    upper.append(f'{key}.txt="{char}"')
                    lower.append(f'{key}.txt="{char.lower()}"')
        components += [button("kSpace", "Space", 20, 554, 220, 54),
                       button("kCase", "Aa", 252, 554, 208, 54)]
        events["kSpace.up"] = key_append('" "')
        events["kCase.up"] = branch("pInit.vBusy.val==0", branch("vCase.val==0", "vCase.val=1\n" + "\n".join(lower)) +
                                    "\nelse\n{\nvCase.val=0\n" + "\n".join(upper) + "\n}")
    components += [button("kDel", "Delete", 20, 615, 140, 52),
                   button("kClear", "Clear", 170, 615, 140, 52),
                   button("kCancel", "Cancel", 20, 725, 210, 54),
                   control("kSave", "Apply", 250, 725, 210, 54, primary=True)]
    if numeric:
        components.append(button("kProbe", "Use probe", 320, 615, 140, 52))
        load += "\n" + visibility("kProbe", 'pInit.vEditKind.val==1&&pInit.tField.txt=="temp"')
        events["kProbe.up"] = editor_action(indexed_request("ROW_SENSOR", "pInit.vEditRow.val"))
    events[name + ".loadend"] = load
    events["kClear.up"] = branch("pInit.vBusy.val==0", 'tInput.txt=""\ntError.txt=""')
    events["kDel.up"] = branch("pInit.vBusy.val==0", '''strlen tInput.txt,vLen.val
if(vLen.val>0)
{
vLen.val-=1
substr tInput.txt,pInit.tEdit.txt,0,vLen.val
tInput.txt=pInit.tEdit.txt
tError.txt=""
}''')
    events["kCancel.up"] = branch("pInit.vBusy.val==0", "page pInit.vEditPage.val")
    save = keyboard_save()
    if numeric:
        save = numeric_validation() + "\n" + branch("vValid.val==1", save)
    events["kSave.up"] = editor_action(save)
    events["tmEdit.timer"] = branch("pInit.vBusy.val==1", branch(
        "pInit.nAckSeq.val==pInit.vSeq.val", '''pInit.vBusy.val=0
if(pInit.nAckCode.val==0)
{
page pInit.vEditPage.val
}else
{
''' + error_message() + "\ntError.txt=pInit.tMsg.txt\n}") +
        "\nelse\n{\n" + retry_request("tError") + "\n}")
    return page, events


def key_append(operand):
    return branch("pInit.vBusy.val==0", "strlen tInput.txt,vLen.val\n" +
                  branch("vLen.val<pInit.vMax.val", f"tInput.txt+={operand}"))


def editor_action(send_action):
    return branch("pInit.vBusy.val==0", branch(
        "pInit.vEditBoot.val==pInit.nBoot.val&&pInit.vEditView.val==pInit.nView.val", send_action) +
        '\nelse\n{\ntError.txt="View updated. Cancel and reopen the field."\n}')


def numeric_validation():
    return '''vValid.val=1
strlen tInput.txt,vLen.val
if(pInit.vInputMode.val==3)
{
vValid.val=0
tError.txt="Enter a valid date DD-MM-YYYY"
if(vLen.val==10)
{
spstr tInput.txt,pInit.tSplit.txt,"-",0
covx pInit.tSplit.txt,vDay.val,0,0
spstr tInput.txt,pInit.tSplit.txt,"-",1
covx pInit.tSplit.txt,vMonth.val,0,0
spstr tInput.txt,pInit.tSplit.txt,"-",2
covx pInit.tSplit.txt,vYear.val,0,0
vPart.val=31
if(vMonth.val==4||vMonth.val==6||vMonth.val==9||vMonth.val==11)
{
vPart.val=30
}
if(vMonth.val==2)
{
vPart.val=28
vPos.val=vYear.val%4
if(vPos.val==0)
{
vPart.val=29
vPos.val=vYear.val%100
if(vPos.val==0)
{
vPos.val=vYear.val%400
if(vPos.val!=0)
{
vPart.val=28
}
}
}
}
if(vDay.val>=1&&vDay.val<=vPart.val&&vMonth.val>=1&&vMonth.val<=12&&vYear.val>=1970&&vYear.val<=2199)
{
vValid.val=1
}
}
}
if(pInit.vInputMode.val==4)
{
vValid.val=0
tError.txt="Enter a valid time HH:MM or HH:MM:SS"
if(vLen.val==5||vLen.val==8)
{
spstr tInput.txt,pInit.tSplit.txt,":",0
covx pInit.tSplit.txt,vDay.val,0,0
spstr tInput.txt,pInit.tSplit.txt,":",1
covx pInit.tSplit.txt,vMonth.val,0,0
vPart.val=0
if(vLen.val==8)
{
spstr tInput.txt,pInit.tSplit.txt,":",2
covx pInit.tSplit.txt,vPart.val,0,0
}
if(vDay.val<24&&vMonth.val<60&&vPart.val<60)
{
vValid.val=1
}
}
}
if(vValid.val==1)
{
tError.txt=""
}'''


def keyboard_save():
    return f'''pInit.tEdit.txt=tInput.txt
{branch("pInit.vInputMode.val==3", swap_date("tInput", "pInit.tEdit"))}
if(pInit.vEditKind.val==2)
{{
if(pInit.vInputMode.val==3)
{{
pInit.tClockDate.txt=pInit.tEdit.txt
}}else
{{
pInit.tClockTime.txt=tInput.txt
}}
page pClock
}}else
{{''' + '''
pInit.tCommand.txt="FIELD_SET|"
if(pInit.vEditKind.val==1)
{
pInit.tCommand.txt="ROW_SET|"
covx pInit.vEditRow.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
pInit.tCommand.txt+="|"
}
if(pInit.vEditKind.val==3)
{
pInit.tCommand.txt="CHECK_SET|"
covx pInit.vEditRow.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
pInit.tCommand.txt+="|"
}
pInit.tCommand.txt+=pInit.tField.txt
pInit.tCommand.txt+="|"
pInit.tCommand.txt+=pInit.tEdit.txt
''' + send("pInit.tCommand.txt", task=1) + "\n}"


def clock_page():
    page = {"page": dict(name="pClock", type="page", x=0, y=0, w=480, h=800, bco="#1e2326"),
            "component": [dict(name="tmClock", type="timer", tim=250, en=1, events=["timer"]),
                          label("tTitle", "Device date and time", 30, 190, 420, 42, font="NotoSans28"),
                          label("tDateLabel", "Date DD-MM-YYYY", 30, 252, 420),
                          label("tDate", "", 30, 286, 420, 60, font="NotoSans28"),
                          label("tTimeLabel", "Time HH:MM:SS", 30, 363, 420),
                          label("tTime", "", 30, 397, 420, 60, font="NotoSans28"),
                          label("tError", "", 30, 474, 420, 52),
                          button("mCancel", "Back", 30, 584, 190, 54),
                          control("mSave", "Set clock", 250, 584, 200, 54, primary=True)]}
    for c in page["component"]:
        if c["name"] in ("tDate", "tTime"):
            c["events"] = ["up"]
    events = {"pClock.loadend": "tDate.txt=pInit.tClockDate.txt\n" + display_date("tDate") +
                              '\ntTime.txt=pInit.tClockTime.txt\ntError.txt=""',
              "tDate.up": edit_value("date", "tDate", "Date", 2, return_page=19),
              "tTime.up": edit_value("time", "tTime", "Time HH:MM:SS", 2, limit=8, return_page=19),
              "mCancel.up": branch("pInit.vBusy.val==0", "page pInit.vPage.val")}
    events["mSave.up"] = '''pInit.tCommand.txt="CLOCK_SET|"
pInit.tCommand.txt+=pInit.tClockDate.txt
pInit.tCommand.txt+="|"
pInit.tCommand.txt+=tTime.txt
''' + send("pInit.tCommand.txt", task=1)
    events["tmClock.timer"] = branch("pInit.vBusy.val==1", branch(
        "pInit.nAckSeq.val==pInit.vSeq.val", '''pInit.vBusy.val=0
if(pInit.nAckCode.val==0)
{
page pInit.vPage.val
}else
{
''' + error_message() + '''
if(pInit.nAckCode.val==6)
{
pInit.tMsg.txt="Insert microSD to set the device clock"
}
tError.txt=pInit.tMsg.txt
}''') + "\nelse\n{\n" + retry_request("tError") + "\n}")
    return page, events


def confirmation_page():
    page = {"page": dict(name="pConfirm", type="page", x=0, y=0, w=480, h=800, bco="#1e2326"),
            "component": [dict(name="tmConfirm", type="timer", tim=250, en=1, events=["timer"]),
                          label("tTitle", "Confirm change", 30, 170, 420, 60, font="NotoSans28"),
                          label("tBody", "Replace the active session or delete this item?", 30, 260, 420, 110),
                          label("tError", "", 30, 400, 420, 60),
                          button("mNo", "Cancel", 30, 721, 190, 54),
                          control("mYes", "Confirm", 250, 721, 200, 54, primary=True)]}
    events = {"pConfirm.loadend": '\n'.join([
        column("pInit.tSplit", 5, "pInit.tReq"),
        branch('pInit.tSplit.txt=="ROW_DELETE"', 'tBody.txt="Delete this maturity row?"'),
        branch('pInit.tSplit.txt=="BASE_DELETE"', 'tBody.txt="Delete this saved baseline?"'),
        branch('pInit.tSplit.txt=="MEASURE_START"', 'tBody.txt="Replace the active measurement?"'),
    ])}
    for name, verb in (("mNo", "CANCEL"), ("mYes", "CONFIRM")):
        events[name + ".up"] = f'''pInit.tCommand.txt="{verb}|"
covx pInit.vToken.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
''' + send("pInit.tCommand.txt", task=1)
    events["tmConfirm.timer"] = branch("pInit.vBusy.val==1", branch(
        "pInit.nAckSeq.val==pInit.vSeq.val", '''pInit.vBusy.val=0
if(pInit.nAckCode.val==0)
{
page pInit.vPage.val
}else
{
''' + error_message() + '''
tError.txt=pInit.tMsg.txt
}''') + "\nelse\n{\n" + retry_request("tError") + "\n}")
    return page, events


def points_page():
    page = {"page": dict(name="pPoints", type="page", x=0, y=0, w=480, h=800, bco="#1e2326"),
            "component": [dict(name="tmPoll", type="timer", tim=250, en=1, events=["timer"]),
                          label("tClock", "", 12, 15, 180), label("tBatt", "", 360, 15, 100),
                          label("tTitle", "Logged days", 20, 120, 440, 43, font="NotoSans20"),
                          label("tNotice", "", 10, 775, 460, 24, capacity=96)]}
    specs = (("Day", "day", 20, 44), ("Date", "date", 68, 91), ("Time", "clock", 163, 70),
             ("Temp", "temp", 237, 62), ("M", None, 303, 50), ("Fc", None, 357, 46))
    clear = "\n".join(clear_row("pPoints", "point", i) for i in range(POINT_ROWS))
    events = {"pPoints.loadend": "\n".join(["pInit.vBusy.val=0", "pInit.vStep.val=0",
        "pInit.vTap.val=0", "pInit.vStatusReady.val=0", clear])}
    for kind, field, x, width in specs:
        page["component"].append(label("h"+kind, kind, x, 171, width, 28))
        for i in range(POINT_ROWS):
            name = f"t{kind}{i}"
            item = label(name, "", x, 205 + i*76, width, 48)
            if field:
                item["events"] = ["up"]
                events[name+".up"] = edit_value(field, name, field, 3,
                                                f"pInit.vOffset.val+{i}", return_page=20)
            page["component"].append(item)
    for i in range(POINT_ROWS):
        page["component"].append(button(f"mGap{i}", "Gap", 407, 205+i*76, 53, 48))
        events[f"mGap{i}.up"] = 'pInit.tEdit.txt="0"\n' + edit_value(
            "gap", "pInit.tEdit", "Review interval, apply 0 to reconcile", 3,
            f"pInit.vOffset.val+{i}", limit=1, return_page=20)
    page["component"].append(button("mBack", "Back", 20, 720, 440, 52))
    events["mBack.up"] = "pInit.vOffset.val=0\npage pInit.vPage.val"
    return page, events


PLOT = {"pBaseR": (79, 464, 422, 575), "pChart": (62, 208, 428, 586)}
for name in PLOT:
    if "plot" in WEB["pages"].get(name, {}).get("regions", {}):
        x, y, w, h = region(name, "plot")
        PLOT[name] = x, y, x + w, y + h


def plot_components(page):
    for name in ("vPlotPhase", "vPoint", "vPlotAction", "vX", "vY", "vLastX", "vLastY",
                 "vMaxX", "vDiv", "vTick", "vTickStep", "vX0", "vY0", "vX1", "vY1", "vDelta"):
        update_component(page, dict(name=name, type="variable", val=0))
    update_component(page, dict(name="tWhole", type="variable", sta=1, txt="", txt_maxl=16))


def plot_begin(page):
    left, top, right, bottom = PLOT[page]
    bg = rgb565("#141a20")
    grid = rgb565("#444a53")
    regions = WEB["pages"].get(page, {}).get("regions", {})
    blank = crop(page, regions["plotSurface"]) if "plotSurface" in regions else (
        f"fill {left - 23},{top - 9},{right - left + 46},{bottom - top + 35},{bg}")
    lines = ["vPoint.val=0", "vMaxX.val=0", blank]
    for tick in range(0, 51, 10):
        y = bottom - (bottom - top) * tick // 50
        lines += [f"line {left},{y},{right},{y},{grid}",
                  f'xstr {left - 23},{y - 9},21,18,0,65535,{bg},2,1,3,"{tick}"']
    return "\n".join(lines)


def plot_x_axis(page):
    left, top, right, bottom = PLOT[page]
    return f'''vTickStep.val=vMaxX.val/40000
vTickStep.val+=1
vTickStep.val*=5000
vTick.val=0
while(vTick.val<=vMaxX.val)
{{
vX.val=vTick.val
{plot_scale_x(page)}
line vX.val,{top},vX.val,{bottom},{rgb565("#444a53")}
vX.val-=20
pInit.vTemp.val=vTick.val/1000
covx pInit.vTemp.val,pInit.tNum.txt,0,0
if(vTick.val>0)
{{
pInit.tNum.txt+="k"
}}
xstr vX.val,{bottom + 4},40,18,0,65535,0,1,1,3,pInit.tNum.txt
vTick.val+=vTickStep.val
}}
draw {left},{top},{right},{bottom},{rgb565("#858e98")}'''


def plot_scale_x(page):
    left, _, right, _ = PLOT[page]
    return f'''vDiv.val=vMaxX.val
if(vMaxX.val>5000000)
{{
vDiv.val/=1000
vX.val/=1000
}}
vX.val*={right - left}
vX.val/=vDiv.val
vX.val+={left}'''


def clip_endpoint(x, y, other_x, other_y, edge, lower):
    test, other_test = ("<", ">=") if lower else (">", "<=")
    return branch(f"{y}.val{test}{edge}&&{other_y}.val{other_test}{edge}", f'''vDelta.val={other_x}.val-{x}.val
pInit.vTemp.val={edge}-{y}.val
vDelta.val*=pInit.vTemp.val
pInit.vTemp.val={other_y}.val-{y}.val
vDelta.val/=pInit.vTemp.val
{x}.val+=vDelta.val
{y}.val={edge}''')


def plot_sample(page):
    left, top, right, bottom = PLOT[page]
    curve = ["vX0.val=vLastX.val", "vY0.val=vLastY.val", "vX1.val=vX.val", "vY1.val=vY.val"]
    for edge, lower in ((top, True), (bottom, False)):
        curve += [clip_endpoint("vX0", "vY0", "vX1", "vY1", edge, lower),
                  clip_endpoint("vX1", "vY1", "vX0", "vY0", edge, lower)]
    curve.append(branch(f"vY0.val>={top}&&vY0.val<={bottom}&&vY1.val>={top}&&vY1.val<={bottom}",
                        f"line vX0.val,vY0.val,vX1.val,vY1.val,{rgb565('#ff9a36')}"))
    curve_draw = branch("vPoint.val>0", "\n".join(curve))
    scatter_draw = branch(f"vX.val>={left}&&vX.val<={right}&&vY.val>={top}&&vY.val<={bottom}",
                          f"cirs vX.val,vY.val,3,{rgb565('#ff9a36')}\ncir vX.val,vY.val,3,65535")
    return f'''{column("pInit.tSplit", 0)}
spstr pInit.tSplit.txt,tWhole.txt,".",0
covx tWhole.txt,vX.val,0,0
{plot_scale_x(page)}
{column("pInit.tSplit", 1)}
spstr pInit.tSplit.txt,tWhole.txt,".",0
covx tWhole.txt,vY.val,0,0
if(vY.val>22000)
{{
vY.val=22000
}}
if(vY.val<-22000)
{{
vY.val=-22000
}}
vY.val*=100
spstr pInit.tSplit.txt,tWhole.txt,".",1
substr tWhole.txt,pInit.tNum.txt,0,2
covx pInit.tNum.txt,pInit.vTemp.val,0,0
substr pInit.tSplit.txt,tWhole.txt,0,1
if(tWhole.txt=="-")
{{
vY.val-=pInit.vTemp.val
}}else
{{
vY.val+=pInit.vTemp.val
}}
vY.val*={bottom - top}
vY.val/=5000
vY.val={bottom}-vY.val
if(vPlotPhase.val==1)
{{
{curve_draw}
vLastX.val=vX.val
vLastY.val=vY.val
}}else
{{
{scatter_draw}
}}'''


def plot_request():
    return '''pInit.tCommand.txt="GET|curve|"
if(vPlotPhase.val==2)
{
pInit.tCommand.txt="GET|scatter|"
}
covx vPoint.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
''' + send("pInit.tCommand.txt")


def plot_ack(page):
    message = "tEq" if page == "pBaseR" else "tError"
    sample = branch('pInit.tSplit.txt!=""', column("pInit.tSplit", 1) + "\n" +
                    branch('pInit.tSplit.txt!=""', plot_sample(page)))
    return branch("pInit.nAckCode.val==0", f'''if(vMaxX.val==0)
{{
{number_column("vMaxX", 2)}
{branch("vMaxX.val>0", plot_x_axis(page))}
}}
if(vMaxX.val>0)
{{
{column("pInit.tSplit", 0)}
{sample}
}}
vPoint.val+=1
if(vPlotPhase.val==1&&vPoint.val==65)
{{
vPlotPhase.val=2
vPoint.val=0
}}
if(vPlotPhase.val==2&&vPoint.val>=pInit.vPairs.val)
{{
vPlotPhase.val=3
}}''') + f'''
else
{{
vPlotPhase.val=3
{message}.txt="Chart data unavailable"
}}'''


def plot_actions():
    save = '''pInit.tCommand.txt="BASE_SAVE|"
covx pInit.vRevision.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
''' + send("pInit.tCommand.txt", task=1)
    return branch("pInit.vBusy.val==0&&dp==7", "\n".join((
        branch("vPlotAction.val==1", "vPlotAction.val=0\n" + request("NAV|6")),
        branch("vPlotAction.val==2&&pInit.vRevision.val>0", "vPlotAction.val=0\n" + save),
        branch("vPlotAction.val==3&&vPlotModel.val>0", "vPlotAction.val=0\npage pChart"),
    )))


def chart_page():
    page = {"page": dict(name="pChart", type="page", x=0, y=0, w=480, h=800, bco="#1e2326"),
            "component": [dict(name="tmChart", type="timer", tim=250, en=1, events=["timer"]),
                          label("tTitle", "Maturity vs Compressive Strength", 26, 127, 428, 30, font="NotoSans20"),
                          label("tAxes", "Compressive Strength (MPa)", 62, 170, 366, 24),
                          label("tMaturity", "Maturity Index, M (°C·hour)", 62, 626, 366, 22),
                          label("tFit", "", 20, 649, 440, 28),
                          label("tError", "", 20, 678, 440, 37),
                          button("mBack", "BACK", 65, 725, 350, 48)]}
    plot_components(page)
    events = {"pChart.loadend": "pInit.vBusy.val=0\nvPlotAction.val=0\nvPlotPhase.val=1\n" +
              plot_begin("pChart") + "\ntFit.txt=pInit.tPlotFit.txt",
              "mBack.up": "vPlotAction.val=1"}
    received = "pInit.vBusy.val=0\n" + plot_ack("pChart")
    events["tmChart.timer"] = branch("pInit.vBusy.val==1", branch("pInit.nAckSeq.val==pInit.vSeq.val", received) +
                                      "\nelse\n{\n" + retry_request("tError") +
                                      "\n" + branch("pInit.vBusy.val==0", "vPlotPhase.val=3") + "\n}") + "\n" + branch(
        "pInit.vBusy.val==0&&vPlotAction.val==1", "page pInit.vPage.val") + "\n" + branch(
        "dp==21&&pInit.vBusy.val==0&&vPlotPhase.val<3", plot_request())
    return page, events


def add_row_page():
    page = {"page": dict(name="pAddRow", type="page", x=0, y=0, w=480, h=800, bco="#1e2326"),
            "component": [dict(name="tmAdd", type="timer", tim=250, en=1, events=["timer"]),
                          label("tTitle", "Add day", 20, 40, 440, 45, font="NotoSans28"),
                          label("tHint", "Choose early-age temperature or a lab day.", 20, 100, 440, 30),
                          control("mEarly", "Day 0 - early temp", 20, 180, 440, 62),
                          control("mLab", "Lab day", 20, 258, 440, 62),
                          control("mFill", "Fill 0-6 h (0.5 h step)", 20, 336, 440, 62),
                          label("tError", "", 20, 435, 440, 52),
                          button("mClose", "CANCEL", 20, 723, 440, 54)]}
    added = f"""pInit.vIndex.val=pInit.vTotal.val+13
if(pInit.nAckValue.val>0&&pInit.nAckValue.val<=pInit.vIndex.val)
{{
pInit.vFocusFirst.val=0
pInit.vFocusRow.val=pInit.nAckValue.val
pInit.vTemp.val=pInit.vFocusRow.val-1
if(pInit.vTemp.val<pInit.vOffset.val)
{{
pInit.vOffset.val=pInit.vTemp.val
}}
pInit.vIndex.val=pInit.vOffset.val+{LAB_ROWS}
if(pInit.vTemp.val>=pInit.vIndex.val)
{{
pInit.vOffset.val=pInit.vTemp.val-{LAB_ROWS-1}
}}
}}
page pInit.vPage.val"""
    events = {
        "pAddRow.loadend": 'pInit.tMsg.txt=""\ntError.txt=""',
        "mEarly.up": request("ROW_ADD_EARLY"),
        "mFill.up": request("ROW_FILL_EARLY"),
        "mLab.up": request("ROW_ADD_LAB"),
        "mClose.up": branch("pInit.vBusy.val==0", "page pInit.vPage.val"),
        "tmAdd.timer": branch("pInit.vBusy.val==1", branch("pInit.nAckSeq.val==pInit.vSeq.val",
            "pInit.vBusy.val=0\n" + branch("pInit.nAckCode.val==0", added) +
            "\nelse\n{\n" + error_message() + "\ntError.txt=pInit.tMsg.txt\n}") +
            "\nelse\n{\n" + retry_request("tError") + "\n}"),
    }
    return page, events


def save_page(name, data, events):
    # Events precede hotspots so an input field cannot cover the last touch layer.
    data["component"].sort(key=lambda component: component["type"] == "hotspot")
    (SOURCE / "pages" / f"{name}.page.toml").write_text(tomli_w.dumps(data), encoding="utf-8")
    (SOURCE / "pages" / f"{name}.nx").write_text(
        "\n".join(event(name, body) for name, body in events.items()), encoding="utf-8")


def clock_open():
    return """pInit.tClockDate.txt=pInit.tDate.txt
pInit.tClockTime.txt=pInit.tTime.txt
page pClock"""


def lab_focus(i):
    return f"""pInit.vFocusId.val=pInit.vLab{i}.val
pInit.vFocusFirst.val=0
if(pInit.vTotal.val==0)
{{
pInit.vFocusFirst.val=1
}}"""


def lab_sensor():
    active = "pInit.vFocusId.val"
    lines = [branch("pInit.vTotal.val==0&&pInit.vDraft.val>0",
                    "pInit.vFocusFirst.val=1\n" + request("ROW_SENSOR|0"))]
    for i in range(LAB_ROWS):
        lines.append(branch(f"{active}>0&&{active}==pInit.vLab{i}.val",
                            indexed_request("ROW_SENSOR", f"pInit.vOffset.val+{i}")))
    lines.append(branch("pInit.vBusy.val==0", 'pInit.tMsg.txt="Select a temperature row first"'))
    return "\n".join(lines)


def reset_lab():
    return "\n".join([*(clear_row("pMatu", "labrow", i) for i in range(LAB_ROWS)),
                      "pInit.vDraft.val=0", "pInit.vLabSlots.val=-1", 'tPageRows.txt=""',
                      *(hide(name) for name in ("mAddDay", "mSensor"))])


def schedule_page():
    name = "pSchedule"
    page = {"page": dict(name=name, type="page", x=0, y=0, w=480, h=800, bco=SURFACE),
            "component": [dict(name="tmPoll", type="timer", tim=250, en=1, events=["timer"]),
                          label("tClock", "", 16, 22, 120, 44, font="NotoSans20"),
                          label("tBatt", "", 352, 22, 112, 44, font="NotoSans20"),
                          label("tTitle", "Sample schedule", 25, 95, 430, 53, font="NotoSans28"),
                          label("tPour", "", 25, 155, 430, 45, font="NotoSans20"),
                          label("tNotice", "", 15, 779, 450, 21, capacity=96),
                          variable("vYear"), variable("vMonth"), variable("vWeek"), variable("vPart"),
                          control("mClose", "CLOSE", 30, 721, 420, 54)]}
    for prefix, title, x, width in (("Day", "Day", 30, 58), ("Hari", "Hari", 96, 82),
                                     ("Date", "Date", 184, 151), ("Tim", "Time", 343, 107)):
        page["component"].append(label("h" + prefix, title, x, 216, width, 45, font="NotoSans20"))
        for i in range(LAB_ROWS):
            page["component"].append(label(f"t{prefix}{i}", "", x, 269 + i * 66, width, 54, font="NotoSans20"))
    refresh = "\n".join(clear_row(name, "labrow", i) for i in range(LAB_ROWS))
    events = {
        name + ".loadend": """pInit.vBusy.val=0
pInit.vStep.val=0
pInit.vTap.val=0
pInit.vStatusReady.val=0
tPour.txt="Set the pour start time"
if(pInit.tPourDate.txt!=""&&pInit.tPourClock.txt!="")
{
tPour.txt=pInit.tPourDate.txt
""" + display_date("tPour") + '''
pInit.tSplit.txt=tPour.txt
tPour.txt="Locked from start "
tPour.txt+=pInit.tSplit.txt
tPour.txt+=" "
tPour.txt+=pInit.tPourClock.txt
}''' + "\n" + refresh,
        "mClose.up": "pInit.vOffset.val=pInit.vMatuOffset.val\npage pMatu",
    }
    return page, events


def schedule_cells(i):
    return [f"t{prefix}{i}" for prefix in ("Day", "Hari", "Date", "Tim")]


def point_cells(i):
    return [f"t{column}{i}" for column in POINT_COLUMNS]


def row_artwork(page, row, state="picture"):
    rows = WEB["pages"].get(page, {}).get("regions", {}).get("rows")
    return crop(page, rows[row], state) if rows else ""


def schedule_weekday(source, target):
    body = f'''spstr {source}.txt,pInit.tSplit.txt,"-",0
covx pInit.tSplit.txt,vYear.val,0,0
spstr {source}.txt,pInit.tSplit.txt,"-",1
covx pInit.tSplit.txt,vMonth.val,0,0
spstr {source}.txt,pInit.tSplit.txt,"-",2
covx pInit.tSplit.txt,vWeek.val,0,0
if(vMonth.val<3)
{{
vMonth.val+=12
vYear.val-=1
}}
vMonth.val-=2
vPart.val=vMonth.val*31
vPart.val/=12
vWeek.val+=vPart.val
vWeek.val+=vYear.val
vPart.val=vYear.val/4
vWeek.val+=vPart.val
vPart.val=vYear.val/100
vWeek.val-=vPart.val
vPart.val=vYear.val/400
vWeek.val+=vPart.val
vWeek.val%=7
pInit.tSplit.txt="Min|Sen|Sel|Rab|Kam|Jum|Sab"
spstr pInit.tSplit.txt,{target}.txt,"|",vWeek.val'''
    return f'{target}.txt=""\n' + branch(f'{source}.txt!=""', body)


def settings_events(events):
    for i, (field, value, limit) in enumerate((("hour", "pInit.vInterval.val/3600", 24),
                                              ("minute", "pInit.vInterval.val/60%60", 60),
                                              ("second", "pInit.vInterval.val%60", 60),
                                              ("brightness", "pInit.vBright.val", 101))):
        for key, delta in ((2 * i, 1), (2 * i + 1, -1)):
            events[f"mTap{key}.up"] = branch("pInit.vStatusReady.val==1", f"""pInit.vTemp.val={value}
pInit.vTemp.val+={delta}
if(pInit.vTemp.val<0)
{{
pInit.vTemp.val=0
}}
if(pInit.vTemp.val>={limit})
{{
pInit.vTemp.val={limit-1}
}}
pInit.tCommand.txt="SETTINGS_SET|{field}|"
covx pInit.vTemp.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
""" + send("pInit.tCommand.txt", task=1))
    for i, field, mask in ((8, "sound", 1), (9, "autoSave", 2)):
        events[f"mTap{i}.up"] = branch("pInit.vStatusReady.val==1", f"""pInit.vTemp.val=pInit.vFlags.val&{mask}
pInit.tCommand.txt="SETTINGS_SET|{field}|"
if(pInit.vTemp.val==0)
{{
pInit.tCommand.txt+="1"
}}else
{{
pInit.tCommand.txt+="0"
}}
""" + send("pInit.tCommand.txt", task=1))


def main():
    documents = {name: tomllib.loads((SOURCE / "pages" / f"{name}.page.toml").read_text(encoding="utf-8"))
                 for name in PAGES}
    init = documents["pInit"]
    retired = {"vHistory", "vHistoryNext", "vOldSlots"}
    init["component"] = [component for component in init["component"] if component["name"] not in retired]
    scalars = ("vPage", "vTask", "vGet", "vOffset", "vTotal", "vIndex", "vPoll", "vIdentity",
               "vProtocolReady", "vSplashStage", "vStorage", "vMask", "vSensors", "vCount", "vRevision",
               "vToken", "vEditPage", "vEditKind", "vEditRow", "vEditView", "vEditBoot", "vInputMode",
               "vMax", "vTemp", "vInterval", "vBright", "vFlags", "vChosen", "vPairs", "vSavedCount",
               "vRun", "vStatusReady", "vHistoryOffset", "vHistoryEnd", "vDraft",
               "vTap", "vTapBoot", "vTapView", "vTapId", "vDispatch",
               "vFocusId", "vFocusFirst", "vFocusRow", "vMatuOffset", "vLabSlots", "vCrop",
               "vListBase", "vListShift", "vListReuse", "vListDirty", "vListReady", "vListMax", "vTouchPhase")
    for name in (*scalars, *(f"vId{i}" for i in range(4)), *(f"vLab{i}" for i in range(LAB_ROWS))):
        update_component(init, variable(name))
    for name, capacity in (("tField", 20), ("tTitle", 48), ("tCommand", 150), ("tDate", 10),
                           ("tTime", 8), ("tStatus", 255), ("tPlotFit", 96), ("tMsg", 96),
                           ("tClockDate", 10), ("tClockTime", 8), ("tPourDate", 10), ("tPourClock", 8)):
        update_component(init, variable(name, "", capacity))

    for name, page in documents.items():
        layout(name, page)

    result_page = documents["pBaseR"]
    plot_components(result_page)
    update_component(result_page, dict(name="vPlotModel", type="variable", val=0))
    update_component(result_page, dict(variable("tCount", "", 12), vscope=0))
    for i in range(LAB_ROWS):
        update_component(documents["pMatu"], dict(variable(f"tFull{i}", "", 8), vscope=0))
    for i in range(HISTORY_ROWS):
        update_component(documents["pHist"], dict(variable(f"vHist{i}"), vscope=0))
    for item in (dict(name="jLink", type="variable", val=0),
                 dict(name="tmSplash", type="timer", tim=650, en=0, events=["timer"])):
        update_component(init, item)
    labels = ("Starting application: --", "Loading database: --", "Checking sensors: --", "Checking hardware: --")
    for name, text in zip(("tReady", "tChkClock", "tChkSensors", "tChkDevice"), labels):
        next(c for c in init["component"] if c["name"] == name)["txt"] = text

    for name, page in documents.items():
        COMPONENT_NAMES[name] = {c["name"] for c in page["component"]}

    backs = {"pBase": 2, "pNewB": 3, "pMat": 4, "pKuat": 2, "pSaveB": 3, "pSelB": 9,
             "pRT": 10, "pStr": 11, "pHist": 9, "pHistD": 13, "pSet": 2}
    actions = {
        "pUser": {"mSave": "USER_SAVE"},
        "pMain": {"mBase": "NAV|3", "mKuat": "NAV|9", "mSet": "NAV|15", "mDev": "NAV|16"},
        "pBase": {"mNew": "BASE_NEW", "mSaved": "NAV|8"},
        "pNewB": {"mNext": "NAV|5"}, "pMat": {"mNext": "NAV|6"},
        "pMatu": {"mGen": "BASE_GENERATE"},
        "pKuat": {"mStart": "NAV|10", "mHist": "NAV|13"},
        "pRT": {"mNext": "RESULT_PREPARE", "mAddCheck": "CHECK_ADD"},
        "pSet": {"mSave": "SETTINGS_SAVE"},
    }
    inputs_by_page = {
        "pUser": (("tOp", "operator", 32, "Operator ID"), ("tProj", "project", 64, "Project Name"),
                  ("tDate", "date", 10, "Date")),
        "pNewB": (("tName", "name", 64, "Baseline Name"), ("tFc", "target", 24, "Target Fc' (MPa)"),
                  ("tTemp", "datum", 3, "Datum Temperature (°C)")),
        "pMat": (("tCem", "cement", 32, "Cement (kg)"), ("tWat", "water", 32, "Water (liter)"),
                 ("tCoa", "coarse", 32, "Coarse Aggregate (kg)"), ("tFin", "fine", 32, "Fine Aggregate (kg)"),
                 ("tRetP", "retarder", 32, "Retarder (%)"), ("tAccP", "accelerator", 32, "Accelerator (%)"),
                 ("tFlyP", "flyAsh", 32, "Fly Ash (%)"), ("tRetB", "retarderBrand", 32, "Retarder Brand"),
                 ("tAccB", "acceleratorBrand", 32, "Accelerator Brand"), ("tFlyB", "flyAshBrand", 32, "Fly Ash Brand")),
    }
    for index, name in enumerate(PAGES):
        page = documents[name]
        reset_focus = "pInit.vFocusId.val=0\npInit.vFocusFirst.val=0\npInit.vFocusRow.val=0" if name == "pMatu" else ""
        if name == "pHist":
            reset_focus = branch("pInit.vPage.val==14", "pInit.vOffset.val=pInit.vHistoryOffset.val")
        load = f"""if(pInit.vPage.val!={index})
{{
pInit.vOffset.val=0
{reset_focus}
}}
pInit.vPage.val={index}
pInit.vBusy.val=0
pInit.vRetry.val=0
pInit.vStep.val=0
pInit.vPoll.val=0
pInit.vTap.val=0
pInit.vStatusReady.val=0
pInit.vTask.val=0
pInit.tMsg.txt=""
{status_header(name)}"""
        events, keys = {}, {}
        for component, field, limit, title in inputs_by_page.get(name, ()):
            input_binding(page, component, field, events, limit=limit, title=title)
        if name == "pInit":
            load += '''
pInit.nBoot.val=0
pInit.vProtocolReady.val=0
pInit.vSplashStage.val=0
tmSplash.en=0
tmSplash.tim=650
jLink.val=0
tProgress.txt="0%"'''
            events["tmSplash.timer"] = splash_timer()
        if name in backs:
            events["mBack.up"] = request(f"NAV|{backs[name]}")
        for component, command in actions.get(name, {}).items():
            events[component + ".up"] = request(command)
        if name in ("pUser", "pDev"):
            events["tClock.up"] = clock_open()
            events["mClockBadge.up"] = clock_open()
        if name == "pDev":
            events["tDevStatus.up"] = branch('tDevStatus.txt=="SET CLOCK"', clock_open())
            events["mBack.up"] = branch("pInit.vIdentity.val==1", request("NAV|2")) + "\nelse\n{\n" + request("NAV|1") + "\n}"
        if name == "pMatu":
            load += "\n" + reset_lab()
            events["mBack.up"] = branch("pInit.vStatusReady.val==1",
                'spstr pInit.tStatus.txt,pInit.tSplit.txt,"|",18\n' +
                branch('pInit.tSplit.txt=="1"', request("NAV|8")) + "\nelse\n{\n" + request("NAV|5") + "\n}")
            add = branch("pInit.vDraft.val>0", "page pAddRow")
            sensor = lab_sensor()
            events["mAddDay.up"] = add
            events["mInfo.up"] = branch("pInit.vDraft.val>0", """pInit.vMatuOffset.val=pInit.vOffset.val
pInit.vOffset.val=0
page pSchedule""")
            input_binding(page, "tPourTime", "pourClock", events, limit=8, title="Start time")
            events["mSensor.up"] = sensor
            keys["mSensor"] = "pInit.vFocusId.val"
            for i in range(LAB_ROWS):
                row_id = f"pInit.vLab{i}.val"
                events[f"mDelete{i}.up"] = branch(f"pInit.vTotal.val>3&&{row_id}>0",
                                                 indexed_request("ROW_DELETE", f"pInit.vOffset.val+{i}"))
                keys[f"mDelete{i}"] = row_id
                for prefix, field in (("Day", "day"), ("Tim", "clock"), ("Fc", "fc"), ("T", "temp")):
                    component = f"t{prefix}{i}"
                    value = f"tFull{i}" if field == "clock" else component
                    title = {"temp": "Temperature (°C)", "fc": "Fc Lab (MPa)", "day": "Day", "clock": "Time"}[field]
                    edit = lab_focus(i) + "\n" + edit_value(field, value, title, kind=1, index=f"pInit.vOffset.val+{i}")
                    events[component + ".up"] = branch(f"{row_id}>0", edit)
                    if i == 0:
                        events[component + ".up"] += "\nelse\n{\n" + branch(
                            "pInit.vDraft.val>0&&pInit.vTotal.val==0", edit) + "\n}"
                    keys[component] = row_id
                if i:
                    for target, action in ((f"tDay{i}", add), (f"tTim{i}", add),
                                           (f"tFc{i}", sensor), (f"tT{i}", sensor), (f"mDelete{i}", sensor)):
                        key = target + ".up"
                        events[key] = branch(f"pInit.vLabSlots.val=={i}", action) + \
                                      "\nelse\n{\n" + events[key] + "\n}"
        if name == "pBaseR":
            load += ("\npInit.vRevision.val=0\nvPlotModel.val=0\nvPlotPhase.val=0\nvPlotAction.val=0\n" +
                     plot_begin(name))
            events.update({"mBack.up": "vPlotAction.val=1", "mSave.up": "vPlotAction.val=2",
                           "mCurve.up": "vPlotAction.val=3"})
        if name == "pStr":
            events["mSave.up"] = indexed_request("RESULT_SAVE", "pInit.vRevision.val")
        if name in ("pSaveB", "pSelB"):
            load += "\npInit.vChosen.val=0\npInit.vSavedCount.val=0\n" + "\n".join(
                clear_row(name, "savedrow", i) for i in range(4))
            for i in range(4):
                row_id = f"pInit.vId{i}.val"
                pick = f"mPick{i}"
                events[pick + ".up"] = branch(f"{row_id}>0", indexed_request("BASE_PICK", row_id))
                keys[pick] = row_id
                if name == "pSaveB":
                    tag = f"mPickTag{i}"
                    events[tag + ".up"] = events[pick + ".up"]
                    keys[tag] = row_id
                    delete = f"mDelete{i}"
                    events[delete + ".up"] = branch(f"{row_id}>0", indexed_request("BASE_DELETE", row_id))
                    keys[delete] = row_id
            if name == "pSaveB":
                events["mSelect.up"] = branch("pInit.vChosen.val>0&&pInit.vSavedCount.val>0", request("BASE_OPEN")) + \
                    '\nelse\n{\npInit.tMsg.txt="Select a baseline first"\n}'
                keys["mSelect"] = "pInit.vChosen.val"
            else:
                load += "\npInit.vRun.val=0\n" + hide("mResume")
                events["mResume.up"] = branch("pInit.vRun.val>0", request("MEASURE_RESUME"))
                events["mStart.up"] = start_hint("pInit.tMsg") + "\n" + branch(
                    'pInit.vStatusReady.val==1&&pInit.tMsg.txt==""', request("MEASURE_START"))
                keys["mStart"] = "pInit.vChosen.val"
                keys["mResume"] = "pInit.vRun.val"
        if name == "pHist":
            load += "\npInit.vHistoryEnd.val=-1\n" + hide("mDetail") + "\n" + "\n".join(
                clear_row(name, "historyrow", i) for i in range(HISTORY_ROWS))
            for i in range(HISTORY_ROWS):
                command = "pInit.vHistoryOffset.val=pInit.vOffset.val\n" + indexed_request(
                    "HISTORY_PICK", f"pInit.vOffset.val+{i}")
                target = f"mHistory{i}"
                key = f"vHist{i}.val"
                events[target + ".up"] = branch(f"{key}>0", command)
                keys[target] = key
            events["mDetail.up"] = events["mHistory0.up"]
            keys["mDetail"] = keys["mHistory0"]
        if name == "pHistD":
            load += "\n" + "\n".join(clear_row(name, "point", i) for i in range(SCROLL_LISTS[name][1]))
        if name == "pRT":
            events["mPoints.up"] = "pInit.vOffset.val=0\npage pPoints"
        if name == "pSet":
            settings_events(events)
        events[name + ".loadend"] = load
        for event_name in events:
            component_name, kind = event_name.split(".")
            if kind != "up":
                continue
            component = next(c for c in page["component"] if c["name"] == component_name)
            component["events"] = ["up"]
        list_actions = set(keys) if name in SCROLL_LISTS else set()
        if name == "pMatu":
            list_actions.add("mAddDay")
        pending = pending_actions(events, index, keys, list_actions) if name not in ("pInit", "pBaseR") else ""
        if name in SCROLL_LISTS:
            mount_scroll(name, page, events)
        events["tmPoll.timer"] = timer(name, pending)
        save_page(name, page, events)

    pages = local_pages()
    for name, (document, events) in pages.items():
        layout(name, document)
        if name in SCROLL_LISTS:
            COMPONENT_NAMES[name] = {c["name"] for c in document["component"]}
            actions = set()
            if name == "pPoints":
                actions = {key.split(".")[0] for key in events if key.endswith(".up") and key != "mBack.up"}
            keys = {name: "pInit.vOffset.val" for name in actions}
            pending = pending_actions(events, 20 if name == "pPoints" else 24, keys, actions)
            mount_scroll(name, document, events)
            events["tmPoll.timer"] = timer(name, pending)
        save_page(name, document, events)
    app_path = SOURCE / "app.toml"
    app = tomllib.loads(app_path.read_text(encoding="utf-8"))
    app["pages"] = PAGES + list(pages)
    app["pictures"] = WEB["pictures"]
    app_path.write_text(tomli_w.dumps(app), encoding="utf-8")


def local_pages():
    return {"pEdit": keyboard(), "pConfirm": confirmation_page(), "pClock": clock_page(),
            "pPoints": points_page(), "pChart": chart_page(), "pAddRow": add_row_page(),
            "pNumber": keyboard(numeric=True), "pSchedule": schedule_page()}


if __name__ == "__main__":
    if sys.argv[1:] == ["--local-layout"]:
        print(json.dumps({name: data["component"] for name, (data, _) in local_pages().items()}))
    else:
        main()
