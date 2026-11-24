"""Generate the K050 events and input pages for arduino/ConMT's CM1 contract."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

import tomli_w

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "nextion" / "nxsrc-K050"
PAGES = [
    "pInit", "pUser", "pMain", "pBase", "pNewB", "pMat", "pMatu", "pBaseR",
    "pSaveB", "pKuat", "pSelB", "pRT", "pStr", "pHist", "pHistD", "pSet", "pDev",
]
WEB_PAGES = set(PAGES[6:])
LAYOUT = json.loads((ROOT / "nextion" / "tools" / "layout.json").read_text(encoding="utf-8"))


def layout_button(page, text=None, cls=None, nth=0):
    """The DOM box of a button in the web screenshot, matched by its label."""
    for entry in LAYOUT.get(page, {}).get("elements", []):
        if entry.get("kind") != "button":
            continue
        label_text = (entry.get("text") or "").strip()
        classes = entry.get("cls") or ""
        if text is not None and not label_text.upper().startswith(text.upper()):
            continue
        if cls is not None and cls not in classes:
            continue
        if nth:
            nth -= 1
            continue
        return (entry["x"], entry["y"], entry["w"], entry["h"])
    return None


def layout_text(page, text, nth=0):
    for entry in LAYOUT.get(page, {}).get("elements", []):
        if entry.get("kind") != "text" or (entry.get("text") or "") != text:
            continue
        if nth:
            nth -= 1
            continue
        return (entry["x"], entry["y"], entry["w"], entry["h"])
    return None


def variable(name, value=0, capacity=None):
    item = {"name": name, "type": "variable", "vscope": 1}
    item.update({"sta": 1, "txt": value, "txt_maxl": capacity} if capacity else {"val": value})
    return item


def label(name, text, x, y, width, height=30, capacity=64, font="NotoSans16"):
    return dict(name=name, type="text", x=x, y=y, w=width, h=height, sta=1,
                bco="#1e2326", pco="#ffffff", font=font, txt=text, txt_maxl=capacity)


def button(name, text, x, y, width, height=36):
    return dict(name=name, type="button", x=x, y=y, w=width, h=height, sta=1,
                bco="#343c42", bco2="#ed792e", pco="#ffffff", pco2="#ffffff",
                font="NotoSans16", txt=text, txt_maxl=max(4, len(text)), events=["up"])


def hotspot(name, x, y, width, height, events=("up",)):
    return dict(name=name, type="hotspot", x=x, y=y, w=width, h=height, events=list(events))


def event(name, body):
    return f"on {name}:\n" + "\n".join("  " + line for line in body.splitlines()) + "\n"


def branch(condition, body):
    return f"if({condition})\n{{\n{body}\n}}"


def column(target, index, source="pInit.tData"):
    return f'spstr {source}.txt,{target}.txt,"|",{index}'


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
    lines = [
        f'pInit.tField.txt="{field}"', f'pInit.tTitle.txt="{title}"',
        f"pInit.tEdit.txt={value}.txt", f"pInit.vEditKind.val={kind}",
        f"pInit.vEditPage.val={return_page if return_page is not None else 'pInit.vPage.val'}",
        f"pInit.vMax.val={limit}",
    ]
    if index is not None:
        lines.append(f"pInit.vEditRow.val={index}")
    lines += ["page pEdit"]
    return branch("pInit.vBusy.val==0", "\n".join(lines))


def status_fields(page):
    lines = ["pInit.tStatus.txt=pInit.tData.txt", column("tClock", 1), column("tBatt", 3),
             number_column("pInit.vStorage", 4), column("pInit.tDate", 0), column("pInit.tTime", 1),
             number_column("pInit.vMask", 14), "pInit.vSensors.val=0",
             "pInit.vCount.val=pInit.vMask.val",
             branch("pInit.vCount.val>=4", "pInit.vSensors.val+=1\npInit.vCount.val-=4"),
             branch("pInit.vCount.val>=2", "pInit.vSensors.val+=1\npInit.vCount.val-=2"),
             branch("pInit.vCount.val>=1", "pInit.vSensors.val+=1")]
    if page == "pInit":
        lines += [column("pInit.tSplit", 9), "pInit.vProtocolReady.val=0",
                  branch('pInit.tSplit.txt=="1.0.1"', "pInit.vProtocolReady.val=1"),
                  branch("pInit.vProtocolReady.val==1&&pInit.vSplashStage.val==0&&tmSplash.en==0",
                         "tmSplash.en=1"),
                  number_column("pInit.vIdentity", 17),
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
    if page in ("pRT", "pStr", "pKuat"):
        lines += [column(name, i) for name, i in (("tS1", 10), ("tS2", 11), ("tS3", 12), ("tAvg", 13))
                  if name in COMPONENT_NAMES[page]]
    if page == "pSet":
        lines += [number_column("pInit.vInterval", 6), number_column("pInit.vBright", 7),
                  number_column("pInit.vFlags", 8),
                  "pInit.vTemp.val=pInit.vInterval.val/3600", "covx pInit.vTemp.val,tHour.txt,2,0",
                  "pInit.vTemp.val=pInit.vInterval.val/60%60", "covx pInit.vTemp.val,tMin.txt,2,0",
                  "pInit.vTemp.val=pInit.vInterval.val%60", "covx pInit.vTemp.val,tSec.txt,2,0",
                  "covx pInit.vBright.val,tBright.txt,0,0",
                  "pInit.vTemp.val=pInit.vFlags.val&1", 'tSound.txt="OFF"',
                  branch("pInit.vTemp.val!=0", 'tSound.txt="ON"'),
                  "pInit.vTemp.val=pInit.vFlags.val&2", "pInit.vTemp.val/=2",
                  'tAuto.txt="OFF"',
                  branch("pInit.vTemp.val!=0", 'tAuto.txt="ON"')]
    return "\n".join(lines)


MIX = {"tCem": 0, "tWat": 1, "tCoa": 2, "tFin": 3, "tRetP": 4,
       "tAccP": 5, "tFlyP": 6, "tRetB": 7, "tAccB": 8, "tFlyB": 9, "tWC": 10}
BASE = {"tName": 1, "tBase": 1, "tTarget": 2, "tDatum": 3}
RUN = {"tPDate": 4, "tPour": 5, "tNowD": 6, "tNowT": 7,
       "tInitTemp": 8, "tAvg": 8, "tElapsed": 9, "tM": 10, "tFc": 11, "tPct": 12}
COMPONENT_NAMES = {}


def assignments(page, mapping):
    return "\n".join(column(name, index) for name, index in mapping.items()
                     if name in COMPONENT_NAMES[page])


def tasks(page):
    items = [("status", None, status_fields(page))]
    if page == "pUser":
        items.append(("identity", None, assignments(page, {"tOp": 0, "tProj": 1, "tDate": 2})))
    if page in ("pBase", "pNewB", "pMatu", "pBaseR", "pRT", "pStr", "pHistD"):
        body = assignments(page, BASE)
        if page == "pNewB":
            body = assignments(page, {"tName": 1, "tFc": 2, "tTemp": 3})
        if page == "pBaseR":
            body += "\npInit.vRevision.val=pInit.nAckValue.val"
        items.append(("baseline", None, body))
    if page in ("pMat", "pBaseR"):
        items.append(("mix", None, assignments(page, MIX)))
    if page == "pBaseR":
        items.append(("model", None, assignments(page, {"tA": 0, "tB": 1, "tR2": 2, "tCount": 3,
                                                       "tOp": 6, "tProj": 7, "tDate": 8})))
    if page in ("pRT", "pStr", "pHistD", "pPoints"):
        items.append(("run", None, assignments(page, RUN) + "\n" +
                      "pInit.vRevision.val=pInit.nAckValue.val\n" + number_column("pInit.vTotal", 2)))
    if page == "pHistD":
        items.append(("detail", None, assignments(page, {"tId": 0, "tSavedAt": 1, "tOp": 3,
                                                        "tProj": 4, "tDate": 2})))
    if page == "pMatu":
        for i in range(12):
            body = assignments(page, {f"tDay{i}": 1, f"tTim{i}": 3, f"tFc{i}": 5, f"tT{i}": 4})
            body += "\npInit.vTotal.val=pInit.nAckValue.val"
            items.append(("labrow", i, body))
    if page in ("pSaveB", "pSelB"):
        for i in range(4):
            items.append(("savedrow", i, assignments(page, {f"tName{i}": 1, f"tVal{i}": 2}) +
                          f"\npInit.vId{i}.val=pInit.nAckValue.val"))
    if page == "pHist":
        items.append(("historyrow", 0, assignments(page, {"tId0": 0, "tName0": 1, "tDate0": 2,
                                                        "tVal0": 4, "tCount0": 5})))
    if page == "pHistD":
        for i in range(5):
            body = f'tLog{i}.txt="Day "\n'
            for prefix, index in (("", 0), (" ", 2), (" T ", 3), (" M ", 4), (" Fc ", 5)):
                body += column("pInit.tSplit", index) + f'\ntLog{i}.txt+="{prefix}"\ntLog{i}.txt+=pInit.tSplit.txt\n'
            items.append(("point", i, body))
    if page == "pPoints":
        for i in range(6):
            items.append(("point", i, assignments(page, {f"tDay{i}": 0, f"tDate{i}": 1,
                                                        f"tTime{i}": 2, f"tTemp{i}": 3,
                                                        f"tM{i}": 4, f"tFc{i}": 5})))
    return items


def clear_row(page, source, row):
    if source == "labrow":
        fields = [f"t{prefix}{row}" for prefix in ("Day", "Tim", "Fc", "T")]
    elif source == "savedrow":
        fields = [f"tName{row}", f"tVal{row}"]
    elif source == "historyrow":
        fields = ["tId0", "tName0", "tDate0", "tVal0", "tCount0"]
    elif source == "point":
        fields = [f"tLog{row}"] if page == "pHistD" else [f"t{kind}{row}" for kind in ("Day", "Date", "Time", "Temp", "M", "Fc")]
    else:
        return ""
    result = [f'{field}.txt=""' for field in fields]
    if source == "savedrow":
        result.append(f"pInit.vId{row}.val=0")
    return "\n".join(result)


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


def timer(page):
    items = tasks(page)
    data_handlers = []
    for i, (source, row, body) in enumerate(items, 1):
        success = branch("pInit.nAckCode.val==0", body) if body else ""
        empty = clear_row(page, source, row)
        if empty:
            success += "\nelse\n{\n" + empty + "\n}"
        data_handlers.append(branch(f"pInit.vGet.val=={i}", success))
    finish = '''pInit.vBusy.val=0
pInit.vRetry.val=0
if(pInit.nAckCode.val==4||pInit.nAckCode.val==8)
{
pInit.nBoot.val=0
pInit.vStep.val=0
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
pInit.tMsg.txt=""
}
pInit.vStep.val=1
}
}
}'''
    retry = '''pInit.vRetry.val+=1
if(pInit.vRetry.val==15)
{
prints pInit.tReq.txt,0
printh 0A
}
if(pInit.vRetry.val>=30)
{
pInit.vBusy.val=0
pInit.nBoot.val=0
pInit.vStep.val=0
pInit.tMsg.txt="No answer from MCU"
}'''
    lines = [branch("pInit.vBusy.val==1", branch("pInit.nAckSeq.val==pInit.vSeq.val", finish) +
                    "\nelse\n{\n" + retry + "\n}")]
    if page != "pBaseR":
        lines.append("tNotice.txt=pInit.tMsg.txt")
    requests = [branch("pInit.vStep.val==0", "pInit.vGet.val=0\n" + send('"PAGE_READY"'))]
    for i, (source, row, body) in enumerate(items, 1):
        command = f'pInit.tCommand.txt="GET|{source}"'
        if row is not None:
            command += f'''\npInit.vIndex.val=pInit.vOffset.val+{row}
covx pInit.vIndex.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+="|"
pInit.tCommand.txt+=pInit.tNum.txt'''
        requests.append(branch(f"pInit.vStep.val=={i}", f"pInit.vGet.val={i}\n" + command +
                               "\n" + send("pInit.tCommand.txt")))
    requests.append(branch(f"pInit.vStep.val>{len(items)}", '''pInit.vPoll.val+=1
if(pInit.vPoll.val>=5)
{
pInit.vPoll.val=0
pInit.vStep.val=1
}'''))
    current_page = "dp==20" if page == "pPoints" else "dp==pInit.vPage.val"
    lines.append(branch("pInit.vBusy.val==0&&" + current_page, "\n".join(requests)))
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


def keyboard():
    page = {"page": dict(name="pEdit", type="page", x=0, y=0, w=480, h=800, bco="#1e2326"),
            "component": [dict(name="tmEdit", type="timer", tim=250, en=1, events=["timer"]),
                          variable("vCase"),
                          label("tTitle", "", 20, 45, 440, 45, font="NotoSans28"),
                          label("tInput", "", 20, 110, 440, 90, font="NotoSans20"),
                          label("tError", "", 20, 210, 440, 45)]}
    events = {"pEdit.loadend": '''tTitle.txt=pInit.tTitle.txt
tInput.txt=pInit.tEdit.txt
tError.txt=""
vCase.val=0
vis kProbe,0
if(pInit.vEditKind.val==1&&pInit.tField.txt=="temp")
{
vis kProbe,1
}'''}
    for row, text in enumerate(("1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM-.:")):
        for col, char in enumerate(text):
            name = f"k{row}{col}"
            page["component"].append(button(name, char, 12 + col * 46, 280 + row * 60, 43, 52))
            events[name + ".up"] = branch("pInit.vBusy.val==0", f'''strlen tInput.txt,pInit.vTemp.val
if(pInit.vTemp.val<pInit.vMax.val)
{{
tInput.txt+={name}.txt
}}''')
    for item in (button("kSpace", "Space", 12, 525, 210, 50),
                 button("kDel", "Delete", 230, 525, 110, 50),
                 button("kClear", "Clear", 348, 525, 120, 50),
                 button("kCase", "Aa", 12, 585, 100, 45),
                 button("kProbe", "Use probe", 130, 585, 220, 45),
                 button("kCancel", "Cancel", 20, 650, 210, 52),
                 button("kSave", "Apply", 250, 650, 210, 52)):
        page["component"].append(item)
    events["kSpace.up"] = branch("pInit.vBusy.val==0", '''strlen tInput.txt,pInit.vTemp.val
if(pInit.vTemp.val<pInit.vMax.val)
{
tInput.txt+=" "
}''')
    events["kClear.up"] = branch("pInit.vBusy.val==0", 'tInput.txt=""')
    events["kDel.up"] = branch("pInit.vBusy.val==0", '''strlen tInput.txt,pInit.vTemp.val
if(pInit.vTemp.val>0)
{
pInit.vTemp.val-=1
substr tInput.txt,pInit.tEdit.txt,0,pInit.vTemp.val
tInput.txt=pInit.tEdit.txt
}''')
    events["kCancel.up"] = branch("pInit.vBusy.val==0", "page pInit.vEditPage.val")
    events["kProbe.up"] = indexed_request("ROW_SENSOR", "pInit.vEditRow.val")
    upper = []
    lower = []
    for row, text in enumerate(("1234567890", "QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM-.:")):
        for col, char in enumerate(text):
            if char.isalpha():
                upper.append(f'k{row}{col}.txt="{char}"')
                lower.append(f'k{row}{col}.txt="{char.lower()}"')
    events["kCase.up"] = branch("vCase.val==0", "vCase.val=1\n" + "\n".join(lower)) + \
        "\nelse\n{\nvCase.val=0\n" + "\n".join(upper) + "\n}"
    events["kSave.up"] = '''if(pInit.vEditKind.val==2)
{
if(pInit.tField.txt=="date")
{
pInit.tDate.txt=tInput.txt
}else
{
pInit.tTime.txt=tInput.txt
}
page pClock
}else
{
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
pInit.tCommand.txt+=tInput.txt
''' + send("pInit.tCommand.txt", task=1) + "\n}"
    events["tmEdit.timer"] = branch("pInit.vBusy.val==1", branch(
        "pInit.nAckSeq.val==pInit.vSeq.val", '''pInit.vBusy.val=0
if(pInit.nAckCode.val==0)
{
page pInit.vEditPage.val
}else
{
''' + error_message() + '''
tError.txt=pInit.tMsg.txt
}''') + '''
else
{
pInit.vRetry.val+=1
if(pInit.vRetry.val==15)
{
prints pInit.tReq.txt,0
printh 0A
}
if(pInit.vRetry.val>=30)
{
pInit.vBusy.val=0
tError.txt="No answer. Return and reconnect."
}
}''')
    return page, events


def clock_page():
    page = {"page": dict(name="pClock", type="page", x=0, y=0, w=480, h=800, bco="#1e2326"),
            "component": [dict(name="tmClock", type="timer", tim=250, en=1, events=["timer"]),
                          label("tTitle", "Device date and time", 20, 50, 440, 50, font="NotoSans28"),
                          label("tDateLabel", "Date YYYY-MM-DD", 30, 190, 420),
                          label("tDate", "", 30, 230, 420, 60),
                          label("tTimeLabel", "Time HH:MM:SS", 30, 340, 420),
                          label("tTime", "", 30, 380, 420, 60),
                          label("tError", "", 30, 490, 420, 50),
                          button("mCancel", "Back", 30, 650, 190, 50),
                          button("mSave", "Set clock", 250, 650, 200, 50)]}
    for c in page["component"]:
        if c["name"] in ("tDate", "tTime"):
            c["events"] = ["up"]
    events = {"pClock.loadend": 'tDate.txt=pInit.tDate.txt\ntTime.txt=pInit.tTime.txt\ntError.txt=""',
              "tDate.up": edit_value("date", "tDate", "Date YYYY-MM-DD", 2, limit=10, return_page=19),
              "tTime.up": edit_value("time", "tTime", "Time HH:MM:SS", 2, limit=8, return_page=19),
              "mCancel.up": "page pInit.vPage.val"}
    events["mSave.up"] = '''pInit.tCommand.txt="CLOCK_SET|"
pInit.tCommand.txt+=tDate.txt
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
tError.txt=pInit.tMsg.txt
}''') + "\nelse\n{\n" + retry_request("tError") + "\n}")
    return page, events


def confirmation_page():
    page = {"page": dict(name="pConfirm", type="page", x=0, y=0, w=480, h=800, bco="#1e2326"),
            "component": [dict(name="tmConfirm", type="timer", tim=250, en=1, events=["timer"]),
                          label("tTitle", "Confirm change", 30, 170, 420, 60, font="NotoSans28"),
                          label("tBody", "Replace the active session or delete this item?", 30, 260, 420, 110),
                          label("tError", "", 30, 400, 420, 60),
                          button("mNo", "Cancel", 30, 530, 190, 52),
                          button("mYes", "Confirm", 250, 530, 200, 52)]}
    events = {}
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
                          label("tTitle", "Measurement checkpoints", 20, 60, 440, 45, font="NotoSans20"),
                          label("tNotice", "", 10, 775, 460, 24, capacity=96)]}
    specs = (("Day", "day", 15, 45), ("Date", "date", 65, 110), ("Time", "clock", 175, 80),
             ("Temp", "temp", 255, 70), ("M", None, 325, 70), ("Fc", None, 395, 70))
    events = {"pPoints.loadend": "pInit.vBusy.val=0\npInit.vStep.val=0\npInit.vOffset.val=0"}
    for kind, field, x, width in specs:
        page["component"].append(label("h"+kind, kind, x, 130, width, 28))
        for i in range(6):
            name = f"t{kind}{i}"
            item = label(name, "", x, 180 + i*80, width, 32)
            if field:
                item["events"] = ["up"]
                events[name+".up"] = edit_value(field, name, field, 3,
                                                f"pInit.vOffset.val+{i}", return_page=20)
            page["component"].append(item)
    for i in range(6):
        page["component"].append(button(f"mGap{i}", "Gap", 395, 217+i*80, 65, 25))
        events[f"mGap{i}.up"] = 'pInit.tEdit.txt="0"\n' + edit_value(
            "gap", "pInit.tEdit", "Review interval, apply 0 to reconcile", 3,
            f"pInit.vOffset.val+{i}", limit=1, return_page=20)
    for name, text, x in (("mPrevious", "Previous", 15), ("mNext", "Next rows", 175), ("mBack", "Back", 335)):
        page["component"].append(button(name, text, x, 710, 130, 42))
    events["mPrevious.up"] = branch("pInit.vBusy.val==0&&pInit.vOffset.val>=6", "pInit.vOffset.val-=6\npInit.vStep.val=1")
    events["mNext.up"] = branch("pInit.vBusy.val==0", "pInit.vOffset.val+=6\npInit.vStep.val=1")
    events["mBack.up"] = branch("pInit.vBusy.val==0", "page pInit.vPage.val")
    COMPONENT_NAMES["pPoints"] = {c["name"] for c in page["component"]}
    events["tmPoll.timer"] = timer("pPoints")
    return page, events


def chart_page():
    page = {"page": dict(name="pChart", type="page", x=0, y=0, w=480, h=800, bco="#1e2326"),
            "component": [dict(name="tmChart", type="timer", tim=250, en=1, events=["timer"]),
                          label("tTitle", "Baseline curve, 0-50 MPa", 20, 40, 440, 45, font="NotoSans20"),
                          label("tError", "", 30, 660, 420, 35),
                          button("mBack", "Back", 65, 715, 350)]}
    for name in ("vPoint", "vX", "vY", "vLastX", "vLastY", "vScale"):
        page["component"].append(variable(name))
    for name in ("tNumber", "tWhole"):
        page["component"].append(variable(name, "", 32))
    events = {"pChart.loadend": '''pInit.vBusy.val=0
vPoint.val=0
line 40,140,40,620,65535
line 40,620,440,620,65535''',
              "mBack.up": branch("pInit.vBusy.val==0", "page pInit.vPage.val")}
    received = "pInit.vBusy.val=0\n" + branch("pInit.nAckCode.val==0", '''spstr pInit.tData.txt,tNumber.txt,"|",0
spstr tNumber.txt,tWhole.txt,".",0
covx tWhole.txt,vX.val,0,0
spstr pInit.tData.txt,tNumber.txt,"|",1
spstr tNumber.txt,tWhole.txt,".",0
covx tWhole.txt,vY.val,0,0
spstr pInit.tData.txt,tNumber.txt,"|",2
spstr tNumber.txt,tWhole.txt,".",0
covx tWhole.txt,vScale.val,0,0
vScale.val/=400
vScale.val+=1
vX.val/=vScale.val
vX.val+=40
if(vY.val>50)
{
vY.val=50
}
vY.val*=9
vY.val=620-vY.val
if(vPoint.val>0)
{
line vLastX.val,vLastY.val,vX.val,vY.val,64992
}
vLastX.val=vX.val
vLastY.val=vY.val
vPoint.val+=1''') + '''
else
{
vPoint.val=65
tError.txt="Select or generate a valid baseline"
}'''
    events["tmChart.timer"] = branch("pInit.vBusy.val==1", branch("pInit.nAckSeq.val==pInit.vSeq.val", received) +
                                      "\nelse\n{\n" + retry_request("tError") + "\n}") + "\n" + branch(
        "pInit.vBusy.val==0&&vPoint.val<65", '''pInit.tCommand.txt="GET|curve|"
covx vPoint.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
''' + send("pInit.tCommand.txt"))
    return page, events


def add_row_page():
    page = {"page": dict(name="pAddRow", type="page", x=0, y=0, w=480, h=800, bco="#1e2326"),
            "component": [label("tTitle", "Add row", 20, 40, 440, 45, font="NotoSans28"),
                          label("tHint", "Choose early-age temperature or a lab day.", 20, 100, 440, 30),
                          button("mEarly", "Day 0 - early temp", 20, 180, 440, 50),
                          button("mFill", "Fill 0-6 h (0.5 step)", 20, 250, 440, 50),
                          button("mLab", "Lab day", 20, 320, 440, 50),
                          button("mClose", "CANCEL", 20, 650, 440, 52)]}
    events = {
        "pAddRow.loadend": 'pInit.tMsg.txt=""',
        "mEarly.up": branch("pInit.vBusy.val==0", request("ROW_ADD_EARLY") + "\npage pInit.vPage.val"),
        "mFill.up": branch("pInit.vBusy.val==0", request("ROW_FILL_EARLY") + "\npage pInit.vPage.val"),
        "mLab.up": branch("pInit.vBusy.val==0", request("ROW_ADD_LAB") + "\npage pInit.vPage.val"),
        "mClose.up": "page pInit.vPage.val",
    }
    return page, events


def save_page(name, data, events):
    # Events precede hotspots so an input field cannot cover the last touch layer.
    data["component"].sort(key=lambda component: component["type"] == "hotspot")
    (SOURCE / "pages" / f"{name}.page.toml").write_text(tomli_w.dumps(data), encoding="utf-8")
    (SOURCE / "pages" / f"{name}.nx").write_text(
        "\n".join(event(name, body) for name, body in events.items()), encoding="utf-8")


def main():
    documents = {name: tomllib.loads((SOURCE / "pages" / f"{name}.page.toml").read_text(encoding="utf-8"))
                 for name in PAGES}
    obsolete = {
        "pUser": {"mClock", "mStorage"},
        "pDev": {"mClock", "mStorage", "tMcu", "tProtocol", "tSupply", "tStorage",
                 "tVersion", "tSensors", "tStatus"},
        "pMatu": {"mAddEarly", "mFillEarly", "tHint", "tPourDate", "tPourTime"},
        "pSaveB": {"tChosen"},
        "pSelB": {"tChosen", "mResume"},
        "pRT": {"mAddCheck", "mPoints", "tInitTemp"},
        "pBaseR": {"mCurve", "tNotice"},
        "pHistD": {"tM", "tFc", "tPct", "tStatus", "tCount", "tS1", "tS2", "tS3"},
    }
    for name, names in obsolete.items():
        documents[name]["component"] = [c for c in documents[name]["component"]
                                        if c["name"] not in names]
    init = documents["pInit"]
    for name in ("vPage", "vTask", "vGet", "vOffset", "vTotal", "vIndex", "vPoll", "vIdentity", "vProtocolReady", "vSplashStage",
                 "vStorage", "vMask", "vSensors", "vCount", "vRevision", "vToken", "vEditPage", "vEditKind", "vEditRow",
                 "vMax", "vTemp", "vInterval", "vBright", "vFlags", "vChosen", "vId0", "vId1", "vId2", "vId3"):
        update_component(init, variable(name))
    for name, capacity in (("tField", 20), ("tTitle", 48), ("tCommand", 150), ("tDate", 10),
                           ("tTime", 8), ("tStatus", 255)):
        update_component(init, variable(name, "", capacity))
    update_component(init, variable("tMsg", "", 96))
    for index, name in enumerate(PAGES):
        page = documents[name]
        page["component"] = [c for c in page["component"] if c["type"] != "hotspot" and
                             not (name == "pInit" and c["name"] == "mContinue")]
        for c in page["component"]:
            if c["name"] == "tmPoll":
                c.update(tim=250, en=1)
        if name != "pBaseR":
            # The web result page has its SAVE button at y=746..786; a notice at
            # 775 would cut it, and the page has no free row for one.
            update_component(page, label("tNotice", "", 10, 775, 460, 24, capacity=96))
    for name, item in (("pInit", label("tProgress", "0%", 350, 464, 55, 28, capacity=8)),
                       ("pSet", dict(name="tSound", type="text", x=336, y=562, w=64, h=30,
                                     sta=1, bco="#ed792e", pco="#ffffff", font="NotoSans16",
                                     txt="", txt_maxl=8)),
                       ("pSet", dict(name="tAuto", type="text", x=336, y=611, w=64, h=30,
                                     sta=1, bco="#ed792e", pco="#ffffff", font="NotoSans16",
                                     txt="", txt_maxl=8)),
                       ("pUser", hotspot("mClock", 8, 62, 100, 44)),
                       ("pDev", hotspot("mClock", 43, 81, 40, 13)),
                       ("pDev", hotspot("mStorage", 313, 589, 87, 30)),
                       ("pRT", hotspot("mAddCheck", 313, 575, 90, 34)),
                       ("pRT", hotspot("mPoints", 56, 585, 200, 30)),
                       ("pBaseR", hotspot("mCurve", 39, 445, 402, 190)),
                       ("pSelB", hotspot("mResume", 45, 170, 300, 40))):
        update_component(documents[name], item)

    # pMatu shows twelve rows in the web screenshot; add the six below the first
    # six so paging no longer leaves baked sample rows on screen.
    matu = documents["pMatu"]
    matu["component"] = [c for c in matu["component"]
                         if c["name"] not in ("tHint", "tPourDate", "tPourTime")]
    for i in range(6, 12):
        for prefix, source in (("tDay", "tDay5"), ("tTim", "tTim5"),
                               ("tFc", "tFc5"), ("tT", "tT5")):
            base = next(c for c in matu["component"] if c["name"] == source)
            item = dict(base)
            item.update(name=f"{prefix}{i}", y=248 + 39 * i, events=["up"])
            update_component(matu, item)

    # pKuat's web screenshot shows the three live sensor temperatures.
    kuat = documents["pKuat"]
    for name, prefix in (("tS1", "35.6"), ("tS2", "36.4"), ("tS3", "36.0")):
        box = next((e for e in LAYOUT.get("pKuat", {}).get("elements", [])
                    if e.get("kind") == "text" and (e.get("text") or "").startswith(prefix)), None)
        if box:
            update_component(kuat, dict(name=name, type="text", x=box["x"], y=box["y"],
                                        w=box["w"], h=box["h"], sta=0, txt="", txt_maxl=32,
                                        pco="#ffffff", font="NotoSans20", picc="09_kuat_tekan"))

    strength = documents["pStr"]
    avg_box = next((e for e in LAYOUT.get("pStr", {}).get("elements", [])
                    if e.get("kind") == "text" and (e.get("text") or "").startswith("36.0")), None)
    if avg_box:
        update_component(strength, dict(name="tAvg", type="text", x=avg_box["x"], y=avg_box["y"],
                                        w=avg_box["w"], h=avg_box["h"], sta=0, txt="",
                                        txt_maxl=32, pco="#ffffff", font="NotoSans20",
                                        picc="12_strength_result"))

    # pHistD's web screen shows the meta, baseline and log rows only; the sensor
    # and calculation sections sit below the fold and must not draw over the title.
    detail_page = documents["pHistD"]
    for name, sample in (("tId", "TEST-EXCEL-01"), ("tSavedAt", "26-10-2026"),
                         ("tDate", "08:00:00"), ("tOp", "OP001"), ("tProj", "HK Tower"),
                         ("tBase", "fc30 marunda final"), ("tTarget", "30 MPa"),
                         ("tDatum", "-20 °C")):
        box = layout_text("pHistD", sample)
        if box:
            update_component(detail_page, dict(name=name, type="text", x=box[0], y=box[1],
                                               w=box[2], h=box[3], sta=0, txt="",
                                               txt_maxl=64 if name == "tBase" else 32,
                                               pco="#ffffff", font="NotoSans20",
                                               picc="14_history_detail"))

    for page_name in WEB_PAGES:
        for field_name, sample in (("tClock", "15:00"), ("tBatt", "87%")):
            component = next((c for c in documents[page_name]["component"] if c["name"] == field_name), None)
            box = layout_text(page_name, sample)
            if component and box:
                component.update(x=box[0], y=box[1], w=max(box[2], 32 if field_name == "tBatt" else 40),
                                 h=box[3], font="NotoSans16", xcen=0)
        if page_name == "pSet":
            continue
        for component in documents[page_name]["component"]:
            if component.get("type") == "text" and component.get("sta") != 1:
                component["xcen"] = 0
            if str(component.get("name", "")).startswith("tLog"):
                component["xcen"] = 0

    update_component(documents["pInit"], dict(name="jLink", type="progress-bar", x=100, y=494, w=294, h=18,
                                             sta=0, val=0, bco="#343c42", pco="#ff8814"))
    update_component(init, dict(name="tmSplash", type="timer", tim=650, en=0, events=["timer"]))
    area = label("statusArea", "", 96, 523, 300, 141, capacity=1)
    init["component"] = [c for c in init["component"] if c["name"] != "statusArea"]
    first_status = min(i for i, c in enumerate(init["component"]) if c["name"] in
                       ("tReady", "tChkClock", "tChkSensors", "tChkDevice"))
    init["component"].insert(first_status, area)
    labels = ("Starting application: --", "Loading database: --", "Checking sensors: --", "Checking hardware: --")
    for i, name in enumerate(("tReady", "tChkClock", "tChkSensors", "tChkDevice")):
        c = next(c for c in init["component"] if c["name"] == name)
        c.update(x=98, y=525+35*i, w=295, h=30, txt=labels[i])
    pmat_boxes = {
        "tCem": (196, 306, 87, 20),
        "tWat": (196, 335, 87, 20),
        "tWC": (196, 364, 87, 20),
        "tCoa": (196, 393, 87, 20),
        "tFin": (196, 422, 87, 20),
        "tRetP": (173, 497, 66, 20),
        "tRetB": (298, 497, 112, 20),
        "tAccP": (173, 526, 66, 20),
        "tAccB": (298, 526, 112, 20),
        "tFlyP": (173, 555, 66, 20),
        "tFlyB": (298, 555, 112, 20),
    }
    for field_name, (x, y, width, height) in pmat_boxes.items():
        component = next(c for c in documents["pMat"]["component"] if c["name"] == field_name)
        component.update(x=x, y=y, w=width, h=height, font="NotoSans16", xcen=0, ycen=1)
        if field_name == "tWC":
            # The design draws W/C as a disabled light box; keep that fill and
            # use dark text so the calculated ratio stays readable.
            component.update(sta=1, bco="#494f57", pco="#20262b")
    for field_name, (x, y, width, height, font) in {
        "tOp": (80, 368, 310, 30, "NotoSans20"),
        "tProj": (80, 468, 310, 30, "NotoSans20"),
        "tDate": (80, 568, 310, 30, "NotoSans20"),
    }.items():
        component = next(c for c in documents["pUser"]["component"] if c["name"] == field_name)
        component.update(x=x, y=y, w=width, h=height, font=font, xcen=0, ycen=1)
    for field_name, (x, y, width, height, font) in {
        "tName": (80, 396, 310, 27, "NotoSans20"),
        "tFc": (80, 474, 250, 30, "NotoSans28"),
        "tTemp": (80, 552, 250, 27, "NotoSans20"),
    }.items():
        component = next(c for c in documents["pNewB"]["component"] if c["name"] == field_name)
        component.update(x=x, y=y, w=width, h=height, font=font, xcen=0, ycen=1)
    for i in range(12):
        update_component(documents["pMatu"], hotspot(f"mDelete{i}", 370, 248+39*i, 34, 30))
    for i in range(5):
        log_label = label(f"tLog{i}", "", 78, 450 + 54 * i, 320, 46, capacity=200)
        log_label["xcen"] = 0
        update_component(documents["pHistD"], log_label)
    paging = {"pMatu": (240, 270), "pSaveB": (268, 340), "pSelB": (292, 284),
              "pHist": (240, 280), "pHistD": (440, 220)}
    for name, (top, height) in paging.items():
        update_component(documents[name], hotspot("mPrevRows", 4, top, 24, height))
        update_component(documents[name], hotspot("mNextRows", 452, top, 24, height))
    for page, document in documents.items():
        COMPONENT_NAMES[page] = {c["name"] for c in document["component"]}

    backs = {"pBase": 2, "pNewB": 3, "pMat": 4, "pBaseR": 6, "pSaveB": 3, "pKuat": 2,
             "pSelB": 9, "pRT": 10, "pStr": 11, "pHist": 9, "pHistD": 13, "pSet": 2, "pDev": 2}
    actions = {
        "pUser": {"mSave": "USER_SAVE"},
        "pMain": {"mBase": "NAV|3", "mKuat": "NAV|9", "mSet": "NAV|15", "mDev": "NAV|16"},
        "pBase": {"mNew": "BASE_NEW", "mSaved": "NAV|8"},
        "pNewB": {"mNext": "NAV|5"}, "pMat": {"mNext": "NAV|6"},
        "pMatu": {"mSensor": "ROW_SENSOR|0", "mGen": "BASE_GENERATE"},
        "pKuat": {"mStart": "NAV|10", "mHist": "NAV|13"},
        "pSelB": {"mStart": "MEASURE_START"}, "pRT": {"mNext": "RESULT_PREPARE"},
        "pHist": {}, "pSet": {"mSave": "SETTINGS_SAVE"},
    }
    original_components = {}
    for name in PAGES:
        # The source before event replacement still defines the touch bounds.
        original_components[name] = tomllib.loads((SOURCE / "pages" / f"{name}.page.toml").read_text(encoding="utf-8"))["component"]
    for i in range(12):
        if not any(c["name"] == f"mDelete{i}" for c in original_components["pMatu"]):
            original_components["pMatu"].append(hotspot(f"mDelete{i}", 370, 248 + 39 * i, 34, 30))

    button_boxes = {
        "pMat": {"mBack": (67, 597, 143, 34), "mNext": (220, 597, 195, 34)},
        "pUser": {"mSave": (84, 625, 312, 57)},
        "pNewB": {"mBack": (67, 597, 168, 35), "mNext": (245, 597, 164, 35)},
    }

    def web_box(page_name, component_name):
        if page_name == "pMatu":
            if component_name == "mBack":
                return layout_button("pMatu", "BACK")
            if component_name == "mGen":
                return layout_button("pMatu", "GENERATE BASELINE")
            if component_name == "mAddDay":
                return (68, 199, 47, 45)
            if component_name == "mSensor":
                return (274, 199, 91, 45)
            if component_name.startswith("mDelete"):
                return (370, 248 + 39 * int(component_name[7:]), 34, 30)
        if page_name == "pKuat":
            return layout_button(page_name, {"mStart": "START TEST", "mHist": "HISTORY",
                                             "mBack": "BACK"}.get(component_name, ""))
        if page_name == "pBaseR":
            return layout_button(page_name, {"mBack": "BACK", "mSave": "SAVE"}.get(component_name, ""))
        if page_name == "pSaveB":
            if component_name == "mBack":
                return layout_button(page_name, "BACK")
            if component_name == "mSelect":
                return layout_button(page_name, "SELECT", cls="btn-orange")
            if component_name.startswith("mPick"):
                cards = [e for e in LAYOUT["pSaveB"]["elements"]
                         if e.get("kind") == "button" and "baseline-card" in (e.get("cls") or "")]
                index = int(component_name[5:])
                return (cards[index]["x"], cards[index]["y"], cards[index]["w"], cards[index]["h"]) if index < len(cards) else None
            if component_name.startswith("mDelete"):
                deletes = [e for e in LAYOUT["pSaveB"]["elements"]
                           if e.get("kind") == "button" and (e.get("text") or "") == "DELETE"]
                index = int(component_name[7:])
                return (deletes[index]["x"], deletes[index]["y"], deletes[index]["w"], deletes[index]["h"]) if index < len(deletes) else None
        if page_name == "pSelB":
            if component_name == "mBack":
                return layout_button(page_name, "BACK")
            if component_name == "mStart":
                return layout_button(page_name, "START")
            if component_name.startswith("mPick"):
                cards = [e for e in LAYOUT["pSelB"]["elements"]
                         if e.get("kind") == "button" and "baseline-card" in (e.get("cls") or "")]
                index = int(component_name[5:])
                return (cards[index]["x"], cards[index]["y"], cards[index]["w"], cards[index]["h"]) if index < len(cards) else None
        if page_name == "pRT":
            if component_name == "mAddCheck":
                return (313, 589, 87, 30)
            if component_name == "mPoints":
                return (56, 591, 300, 16)
            return layout_button(page_name, {"mBack": "BACK", "mNext": "NEXT"}.get(component_name, ""))
        if page_name == "pStr":
            return layout_button(page_name, {"mBack": "BACK", "mSave": "SAVE RESULT"}.get(component_name, ""))
        if page_name == "pHist":
            return layout_button(page_name, {"mBack": "BACK", "mDetail": "VIEW LOG"}.get(component_name, ""))
        if page_name == "pHistD":
            return layout_button(page_name, {"mBack": "BACK"}.get(component_name, ""))
        if page_name == "pSet":
            if component_name == "mBack":
                return layout_button(page_name, "BACK")
            if component_name == "mSave":
                return layout_button(page_name, "SAVE")
            if component_name.startswith("mTap"):
                controls = [e for e in LAYOUT["pSet"]["elements"]
                            if e.get("kind") == "button"
                            and (e.get("text") or "") in ("▴", "▾", "ON", "OFF")]
                index = int(component_name[4:])
                return (controls[index]["x"], controls[index]["y"], controls[index]["w"], controls[index]["h"]) if index < len(controls) else None
        if page_name == "pDev":
            if component_name == "mBack":
                return layout_button(page_name, "BACK")
            if component_name == "mStorage":
                return (313, 589, 87, 30)
            if component_name == "mClock":
                return (43, 81, 40, 13)
        if component_name in ("mPrevRows", "mNextRows"):
            top, height = paging[page_name]
            return (4, top, 24, height) if component_name == "mPrevRows" else (452, top, 24, height)
        return None

    for page_name, boxes in button_boxes.items():
        for component in original_components[page_name]:
            box = boxes.get(component["name"])
            if box:
                component.update(x=box[0], y=box[1], w=box[2], h=box[3])
    for page_name in WEB_PAGES:
        for component in original_components[page_name]:
            box = web_box(page_name, component["name"])
            if box:
                component.update(x=box[0], y=box[1], w=box[2], h=box[3])
    for index, name in enumerate(PAGES):
        page = documents[name]
        events = {name + ".loadend": f'''if(pInit.vPage.val!={index})
{{
pInit.vOffset.val=0
}}
pInit.vPage.val={index}
pInit.vBusy.val=0
pInit.vRetry.val=0
pInit.vStep.val=0
pInit.vPoll.val=0
pInit.tMsg.txt=""'''}
        if name == "pInit":
            events[name + ".loadend"] += '''
pInit.nBoot.val=0
pInit.vProtocolReady.val=0
pInit.vSplashStage.val=0
tmSplash.en=0
tmSplash.tim=650
jLink.val=0
tProgress.txt="0%"'''
            events["tmSplash.timer"] = splash_timer()
        if name in backs:
            events["mBack.down"] = request(f"NAV|{backs[name]}")
        if name == "pMatu":
            events["mBack.down"] = '''spstr pInit.tStatus.txt,pInit.tSplit.txt,"|",18
if(pInit.tSplit.txt=="1")
{
''' + request("NAV|8") + "\n}else\n{\n" + request("NAV|5") + "\n}"
        for control, command in actions.get(name, {}).items():
            events[control + ".down"] = request(command)
        if name == "pMatu":
            events["mAddDay.down"] = branch("pInit.vBusy.val==0", "page pAddRow")
        for c in original_components[name]:
            if c["type"] == "hotspot" and c["name"] + ".down" in events:
                page["component"].append(c)
        events["tmPoll.timer"] = timer(name)
        if name in ("pUser", "pDev"):
            events["mClock.up"] = branch("pInit.vBusy.val==0", "page pClock")
        if name == "pDev":
            events["mStorage.up"] = request("STORAGE_RETRY")
        if name == "pUser":
            for control, field, limit in (("tOp", "operator", 32), ("tProj", "project", 64), ("tDate", "date", 10)):
                input_binding(page, control, field, events, limit=limit)
        if name == "pNewB":
            for control, field in (("tName", "name"), ("tFc", "target"), ("tTemp", "datum")):
                input_binding(page, control, field, events, limit=64 if field == "name" else 24)
        if name == "pMat":
            keys = ("cement", "water", "coarse", "fine", "retarder", "accelerator", "flyAsh",
                    "retarderBrand", "acceleratorBrand", "flyAshBrand")
            for control, field in zip(list(MIX)[:-1], keys):
                input_binding(page, control, field, events, limit=32)
        if name == "pMatu":
            for i in range(12):
                events[f"mDelete{i}.up"] = indexed_request("ROW_DELETE", f"pInit.vOffset.val+{i}")
            for i in range(12):
                for prefix, field in (("Day", "day"), ("Tim", "clock"), ("Fc", "fc"), ("T", "temp")):
                    input_binding(page, f"t{prefix}{i}", field, events, kind=1,
                                  index=f"pInit.vOffset.val+{i}")
        if name in ("pBaseR", "pStr"):
            verb = "BASE_SAVE" if name == "pBaseR" else "RESULT_SAVE"
            revision = "pInit.vRevision.val"
            events["mSave.down"] = f'''pInit.tCommand.txt="{verb}|"
covx {revision},pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
''' + send("pInit.tCommand.txt", task=1)
            c = next(c for c in original_components[name] if c["name"] == "mSave")
            page["component"].append(c)
        if name in ("pSaveB", "pSelB"):
            for i in range(4):
                c = next(c for c in page["component"] if c["name"] == f"tName{i}")
                card_box = web_box(name, f"mPick{i}") or (65, c["y"] - 10, 260, 55)
                hit = hotspot(f"mPick{i}", *card_box)
                page["component"].append(hit)
                events[f"mPick{i}.up"] = f'''pInit.tCommand.txt="BASE_PICK|"
covx pInit.vId{i}.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
''' + send("pInit.tCommand.txt", task=1)
                if name == "pSaveB":
                    delete_box = web_box(name, f"mDelete{i}") or (330, c["y"] + 23, 80, 28)
                    update_component(page, hotspot(f"mDelete{i}", *delete_box))
                    events[f"mDelete{i}.up"] = indexed_request("BASE_DELETE", f"pInit.vId{i}.val")
            if name == "pSaveB":
                c = next(c for c in original_components[name] if c["name"] == "mSelect")
                page["component"].append(c)
                events["mSelect.down"] = request("BASE_OPEN")
        if name == "pHist":
            events["mDetail.down"] = '''pInit.tCommand.txt="HISTORY_PICK|"
covx pInit.vOffset.val,pInit.tNum.txt,0,0
pInit.tCommand.txt+=pInit.tNum.txt
''' + send("pInit.tCommand.txt", task=1)
            page["component"].append(next(c for c in original_components[name] if c["name"] == "mDetail"))
        if name == "pRT":
            events["mAddCheck.up"] = request("CHECK_ADD")
            events["mPoints.up"] = branch("pInit.vBusy.val==0", "page pPoints")
        if name == "pBaseR":
            events["mCurve.up"] = branch("pInit.vBusy.val==0", "page pChart")
        if name == "pSelB":
            events["mResume.up"] = request("MEASURE_RESUME")
        if name in ("pMatu", "pSaveB", "pSelB", "pHist", "pHistD"):
            size = 12 if name == "pMatu" else 1 if name == "pHist" else 5 if name == "pHistD" else 4
            events["mNextRows.up"] = branch("pInit.vBusy.val==0", f"pInit.vOffset.val+={size}\npInit.vStep.val=1")
            events["mPrevRows.up"] = branch(f"pInit.vBusy.val==0&&pInit.vOffset.val>={size}",
                                             f"pInit.vOffset.val-={size}\npInit.vStep.val=1")
        if name == "pSet":
            for i, (field, value, limit) in enumerate((("hour", "pInit.vInterval.val/3600", 24),
                                                      ("minute", "pInit.vInterval.val/60%60", 60),
                                                      ("second", "pInit.vInterval.val%60", 60),
                                                      ("brightness", "pInit.vBright.val", 101))):
                for sign, delta in ((0, 1), (1, -1)):
                    control = f"mTap{2*i+sign}"
                    page["component"].append(next(c for c in original_components[name] if c["name"] == control))
                    events[control + ".down"] = branch("pInit.vBusy.val==0", f'''pInit.vTemp.val={value}
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
''' + send("pInit.tCommand.txt", task=1))
            for i, field, mask in ((8, "sound", 1), (9, "autoSave", 2)):
                control = f"mTap{i}"
                page["component"].append(next(c for c in original_components[name] if c["name"] == control))
                events[control + ".down"] = branch("pInit.vBusy.val==0", f'''pInit.vTemp.val=pInit.vFlags.val&{mask}
pInit.tCommand.txt="SETTINGS_SET|{field}|"
if(pInit.vTemp.val==0)
{{
pInit.tCommand.txt+="1"
}}else
{{
pInit.tCommand.txt+="0"
}}
''' + send("pInit.tCommand.txt", task=1))
        save_page(name, page, events)

    for name, (document, events) in (("pEdit", keyboard()), ("pConfirm", confirmation_page()),
                                     ("pClock", clock_page()), ("pPoints", points_page()),
                                     ("pChart", chart_page()), ("pAddRow", add_row_page())):
        save_page(name, document, events)
    app_path = SOURCE / "app.toml"
    app = tomllib.loads(app_path.read_text(encoding="utf-8"))
    app["pages"] = PAGES + ["pEdit", "pConfirm", "pClock", "pPoints", "pChart", "pAddRow"]
    app_path.write_text(tomli_w.dumps(app), encoding="utf-8")


if __name__ == "__main__":
    main()
