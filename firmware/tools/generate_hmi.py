#!/usr/bin/env python3
"""Emit a reviewable Nextion contract/events, not a binary HMI/TFT."""
import json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
version=int(re.search(r'HmiContractVersion=(\d+)',(root/'ConMT/src/hmi/Transport.h').read_text()).group(1))
out=root/'hmi';events=out/'events';events.mkdir(exist_ok=True)
pages=['pInit','pUser','pMain','pBase','pNewB','pMat','pMatu','pBaseR','pSaveB','pKuat','pSelB','pRT','pStr','pHist','pHistD','pSet','pDev']
fields={
'pInit':[], 'pUser':['tOp','tProj','tDate'], 'pMain':[], 'pBase':[],
'pNewB':['tName','tFc','tTemp','tPDate','tPClock'],
'pMat':['tCem','tWat','tCoa','tFin','tRetP','tRetB','tAccP','tAccB','tFlyP','tFlyB','tWC'],
'pMatu':[f'{prefix}{i}' for i in range(6) for prefix in ['tDay','tTim','tFc','tT','tRid']]+['tHint'],
'pBaseR':['tName','tTarget','tDatum','tA','tB','tR2','tCount','tEq','tCem','tWat','tCoa','tFin','tRetP','tRetB','tAccP','tAccB','tFlyP','tFlyB','tWC','tOp','tProj','tDate'],
'pSaveB':[f'{p}{i}' for i in range(6) for p in ['tId','tName','tVal']]+['tSelName','tSelFc','tSelT','tSelR2','tSelId','tSelDate'],
'pKuat':[], 'pSelB':[f'{p}{i}' for i in range(6) for p in ['tId','tName','tVal']]+['tSelName','tSelFc','tSelT','tSelR2','tSelId','tSelDate'],
'pRT':['tS1','tS2','tS3','tAvg','tNowD','tNowT'], 'pStr':[], 'pHist':[f'{p}{i}' for i in range(6) for p in ['tId','tName','tVal','tDate','tCount']],
'pHistD':[], 'pSet':['tInterval','tBright','tSound','tAuto','tHour','tMin','tSec'], 'pDev':['tVersion','tMcu','tProtocol']}
summary=['tBase','tTarget','tDatum','tPDate','tPour','tInitTemp','tM','tFc','tPct','tElapsed','tRefDay']
for page in ['pRT','pStr','pHistD']:
    fields[page]+=summary
    if page!='pStr':fields[page]+=[f'{p}{i}' for i in range(6) for p in ['tDay','tAt','tTmp','tCm','tCf']]
fields['pHistD']+=['tOp','tProj','tDate','tSavedAt','tLastT','tStatus','tS1','tS2','tS3','tCount']
actions={p:{} for p in pages}
def action(page,component,verb,*args):actions[page][component]={'verb':verb,'args':list(args)}
for page in pages[3:]:action(page,'mBack','NAV','BACK')
for page in ['pUser','pDev']:action(page,'mRetry','STORAGE_RESCAN')
for name,dest in [('mBase',3),('mKuat',9),('mSet',15),('mDev',16)]:action('pMain',name,'NAV',str(dest))
action('pUser','mSave','USER_SAVE');action('pBase','mNew','BASE_NEW');action('pBase','mSaved','NAV','8')
action('pNewB','mNext','NAV','5');action('pMat','mNext','NAV','6')
action('pMatu','mGen','BASE_GENERATE');action('pMatu','mAddDay','ROW_ADD_LAB');action('pMatu','mAddEarly','ROW_ADD_EARLY');action('pMatu','mFill','ROW_FILL_EARLY')
action('pBaseR','mSave','BASE_SAVE');action('pSaveB','mSelect','BASE_OPEN');action('pSaveB','mDeleteConfirm','BASE_DELETE','1')
action('pKuat','mStart','NAV','10');action('pKuat','mHist','NAV','13')
action('pSelB','mStart','MEASURE_START');action('pSelB','mReplaceConfirm','MEASURE_START','1');action('pSelB','mResume','SESSION_RESUME')
action('pRT','mNext','RESULT_PREPARE');action('pRT','mAddDay','CHECK_ADD',{'text':'pInit.tDayInput'})
action('pRT','mGapConfirm','GAP_RECONCILE','1',{'text':'pInit.tEdit'});action('pStr','mSave','RESULT_SAVE');action('pSet','mSave','SETTINGS_SAVE')
for page in ['pMatu','pRT','pHistD','pSaveB','pSelB','pHist']:
    action(page,'mPrev','PAGE_ROWS','PREV');action(page,'mMore','PAGE_ROWS','NEXT')
for i in range(6):
    action('pMatu',f'mSensor{i}','ROW_SENSOR',str(i))
    action('pMatu',f'mDeleteConfirm{i}','ROW_DELETE',str(i),'1')
    action('pMatu',f'mSchedule{i}','ROW_SCHEDULE',str(i))
    for field in ['day','clock','timeH','temp','fc']:action('pMatu',f'apply_{field}_{i}','ROW_SET',str(i),field,{'text':'pInit.tEdit'})
    for page in ['pSaveB','pSelB']:action(page,f'mPick{i}','BASE_PICK',str(i))
    action('pHist',f'mPick{i}','HISTORY_PICK',str(i))
    for field in ['day','clock','date','temp']:action('pRT',f'apply_{field}_{i}','CHECK_SET',str(i),field,{'text':'pInit.tEdit'})
for page,bind in {
'pUser':{'tOp':'operator','tProj':'project','tDate':'date'},
'pNewB':{'tName':'name','tFc':'target','tTemp':'datum','tPDate':'pourDate','tPClock':'pourClock'},
'pMat':{'tCem':'cement','tWat':'water','tCoa':'coarse','tFin':'fine','tRetP':'retarderPct','tRetB':'retarderBrand','tAccP':'acceleratorPct','tAccB':'acceleratorBrand','tFlyP':'flyAshPct','tFlyB':'flyAshBrand'}}.items():
    for component,key in bind.items():action(page,f'apply_{component}','FIELD_SET',key,{'text':'pInit.tEdit'})
for key,step in [('hour','1'),('minute','1'),('second','1'),('brightness','5')]:
    action('pSet',f'm_{key}_plus','SETTINGS_STEP',key,step)
    action('pSet',f'm_{key}_minus','SETTINGS_STEP',key,'-'+step)
for key in ['sound','autoSave']:action('pSet',f'm_{key}_toggle','SETTINGS_TOGGLE',key)
for key in ['interval','hour','minute','second','brightness','sound','autoSave']:action('pSet',f'apply_{key}','SETTINGS_SET',key,{'text':'pInit.tEdit'})

def script(page,definition):
    # Strings use one append per line; LF is emitted as a byte, never a C escape.
    lines=['if(pInit.vBusy.val==0'+('' if definition['verb'] in ['NAV','STORAGE_RESCAN'] else '&&pInit.vRender.val==0')+')','{','pInit.vSeq.val+=1','pInit.vBusy.val=1','pInit.vRetry.val=0','pInit.vReqBoot.val=pInit.vBoot.val','pInit.tReq.txt="CM1|"']
    for name in ['vBoot','vSeq']:
        lines += [f'covx pInit.{name}.val,pInit.tNum.txt,0,0','pInit.tReq.txt+=pInit.tNum.txt','pInit.tReq.txt+="|"']
    lines += [f'pInit.tReq.txt+="{pages.index(page)}|"','covx pInit.vView.val,pInit.tNum.txt,0,0','pInit.tReq.txt+=pInit.tNum.txt',f'pInit.tReq.txt+="|{definition["verb"]}"']
    for arg in definition['args']:
        lines+=['pInit.tReq.txt+="|"']
        lines += [f'pInit.tReq.txt+={arg["text"]}.txt'] if isinstance(arg,dict) else [f'pInit.tReq.txt+="{arg}"']
    lines+=['prints pInit.tReq.txt,0','printh 0A','}']
    return '\n'.join(lines)+'\n'
manifest={'protocol':'CM1','schema':version,'contractRevision':version,'maxFrameBytes':192,'frameLimitIncludesLf':True,'numericDecimal':'.','reservedCharacters':['|','"','\\','CR','LF'],'panelCompileVerified':False,'hardwareBaud':None,'pages':[],'globals':{'page':'pInit','scope':'global','variables':['vBoot','vSeq','vView','vAck','vStatus','vBusy','vRetry','vRender','vAckBoot','vReqBoot'],'texts':{'tReq':191,'tNum':16,'tEdit':64,'tDayInput':24}},'notes':['apply_* snippets run after keyboard Apply; Cancel sends nothing','Confirmation widgets must ask before calling *Confirm events','vSeq must not wrap; reconnect before UINT32_MAX','retry current tReq on timer while vBusy and no ACK; do not increment vSeq','PAGE_READY never resets MCU session','vBusy is client-owned; clear only when vAckBoot/vAck match vReqBoot/vSeq or explicit timeout','vRender is MCU-owned and must not arm retry','Active-page retry timer placement requires Editor/model verification','Editor/model validation pending; this manifest is not HMI/TFT']}
for i,page in enumerate(pages):
    ready='prints "CM1|",0\ncovx pInit.vBoot.val,pInit.tNum.txt,0,0\nprints pInit.tNum.txt,0\n'+f'prints "|0|{i}|0|PAGE_READY|{version}",0\nprinth 0A\n' 
    (events/f'{page}_postinitialize.txt').write_text(ready)
    for component,definition in actions[page].items():(events/f'{page}_{component}.txt').write_text(script(page,definition))
    manifest['pages'].append({'id':i,'name':page,'textComponents':['tClock','tBatt','tMsg']+fields[page],'actions':actions[page],'postinitialize':f'events/{page}_postinitialize.txt'})
(events/'pInit_retry_timer.txt').write_text('if(pInit.vBusy.val==1)\n{\nif(pInit.vAckBoot.val==pInit.vReqBoot.val&&pInit.vAck.val==pInit.vSeq.val)\n{\npInit.vBusy.val=0\npInit.vRetry.val=0\n}else\n{\npInit.vRetry.val+=1\nif(pInit.vRetry.val<7)\n{\nprints pInit.tReq.txt,0\nprinth 0A\n}else\n{\npInit.vBusy.val=0\ntMsg.txt="Connection timeout"\n}\n}\n}\n')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'pages':len(pages),'events':len(list(events.glob('*.txt'))),'binaryHmiBuilt':False}))
