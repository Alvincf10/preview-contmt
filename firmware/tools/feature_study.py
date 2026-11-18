#!/usr/bin/env python3
"""Measure hypothetical feature cuts only in disposable, isolated source copies."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
production=root/'ConMT/src'
build=root/'build-feature-study'
cases={
    'baseline': {},
    'row_helpers': {'stubs':['captureRow','fillEarly']},
    'material_metadata': {'material':True},
    'manual_checkpoint_editor': {'stubs':['editCheckpoint','reconcileGap']},
    'history_viewer': {'stubs':['historyAt'],'pages':['Hist','HistD']},
    'settings_editor': {'stubs':['setting'],'pages':['Set']},
    'baseline_authoring': {'stubs':['newBaseline','addRow','fillEarly','editRow','deleteRow','captureRow','generate','saveBaseline','cloneDraft','openBaseline'],
                           'pages':['NewB','Mat','Matu','BaseR'],'draft':True},
}
combined={}
for case in list(cases.values())[1:]:
    for key,value in case.items():
        if isinstance(value,list):combined[key]=sorted(set(combined.get(key,[])+value))
        else:combined[key]=value
cases['all_candidates']=combined

def digest(folder):
    result={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file()}
    return hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()

def end_brace(source,start):
    depth=0; state='code'; i=start
    while i<len(source):
        c=source[i]; pair=source[i:i+2]
        if state in ('string','char'):
            if c=='\\':i+=2;continue
            if c==('"' if state=='string' else "'"):state='code'
        elif state=='line':
            if c=='\n':state='code'
        elif state=='block':
            if pair=='*/':state='code';i+=2;continue
        elif pair=='//':state='line';i+=2;continue
        elif pair=='/*':state='block';i+=2;continue
        elif c=='"':state='string'
        elif c=="'":state='char'
        elif c=='{':depth+=1
        elif c=='}':
            depth-=1
            if not depth:return i+1
        i+=1
    raise ValueError('Unbalanced source')

def replace_method(source,name,body):
    match=re.search(r'\bStatus Controller::'+re.escape(name)+r'\(',source)
    if not match:raise ValueError('Method not found: '+name)
    start=source.index('{',match.end()); end=end_brace(source,start)
    return source[:start]+'{\n'+body+'\n}'+source[end:]

def material_rules(folder):
    path=folder/'app/FieldRules.cpp'; source=path.read_text()
    tokens=['operator','project','date','pourDate','pourClock','name','target','datum']
    source=re.sub(r'static const char tokens\[\] CM_ROM="[^"]*";',
                  lambda _: 'static const char tokens[] CM_ROM="'+'\\0'.join(tokens)+'";',source)
    start=source.index('{',source.index('static const FieldRule rules[]')); end=end_brace(source,start)
    entries=re.findall(r'R\(([^)]*)\)',source[start:end])
    keep=[entry for entry in entries if entry.split(',')[1] in ['Operator','Project','Date','Pour','Name','Target','Datum']]
    assert len(keep)==8
    source=source[:start]+'{'+','.join('R('+e+')' for e in keep)+'}'+source[end:]
    path.write_text(source)

def transform(folder,case):
    path=folder/'app/Controller.cpp'; source=path.read_text()
    for name in case.get('stubs',[]):source=replace_method(source,name,'    return Status::Unsupported;')
    if case.get('draft'):
        source=replace_method(source,'setField',
            '    FieldRule rule; if(!fieldRule(key,rule)) return Status::Invalid;\n'
            '    if(rule.kind!=Kind::User) return Status::Unsupported;\n'
            '    return mutateField(rule,value,op);')
    path.write_text(source)
    path=folder/'hmi/Presenter.cpp'; source=path.read_text()
    pages=set(case.get('pages',[]))
    if case.get('material'):
        material_rules(folder); pages.add('Mat')
        marker='else if(op==WaterCement) {'; start=source.index(marker)
        end=end_brace(source,source.index('{',start)); source=source[:start]+source[end:]
        # Keep model and identity fields contiguous when material fields are absent.
        marker='Page page=app_.page();'
        assert source.count(marker)==1
        source=source.replace(marker,marker+'\n    if(page==Page::BaseR&&i>=8) { if(i>=11) return false; i+=11; }')
    if pages:
        marker='bool Presenter::field('; start=source.index('{',source.index(marker))
        condition='||'.join('app_.page()==Page::'+p for p in sorted(pages))
        source=source[:start+1]+'\n    if('+condition+') return false;'+source[start+1:]
    path.write_text(source)

parser=argparse.ArgumentParser()
parser.add_argument('--cases',nargs='+',choices=list(cases),default=list(cases))
args=parser.parse_args()
before=digest(production); results=[]
build.mkdir(exist_ok=True)
for name in args.cases:
    folder=build/name/'src'
    if folder.exists():shutil.rmtree(folder)
    shutil.copytree(production,folder)
    transform(folder,cases[name])
    output=build/name/'build'
    command=[sys.executable,str(root/'tools/avr_capacity.py'),'--source-dir',str(folder),'--output-dir',str(output)]
    run=subprocess.run(command,capture_output=True,text=True)
    if run.returncode:
        (build/name/'error.txt').write_text(run.stdout+run.stderr)
        raise SystemExit('Study build failed: '+name+'; see '+str(build/name/'error.txt'))
    report=json.loads((output/'capacity.json').read_text())
    result={'case':name,'flashBytes':report['flashBytes'],'staticRamBytes':report['staticRamBytes'],
            'physicalLinkPassed':report['nativeLinkPassed'],'disabledOnlyInStudyCopy':cases[name],
            'sourceDigest':digest(folder)}
    results.append(result);print(json.dumps(result),flush=True)
    assert digest(production)==before,'Production source changed during isolated study'
after=digest(production); assert before==after
if results and results[0]['case']=='baseline':
    for result in results:result['savingVersusStudyBaseline']=results[0]['flashBytes']-result['flashBytes']
report={'purpose':'Hypothetical feature cuts, never production or flash artifacts',
        'baselineCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'productionSourceDigestBefore':before,'productionSourceDigestAfter':after,'productionFeaturesRemoved':False,
        'probeSourceSha256':hashlib.sha256((root/'tools/capacity_probe/probe.cpp').read_bytes()).hexdigest(),
        'capacityToolSha256':hashlib.sha256((root/'tools/avr_capacity.py').read_bytes()).hexdigest(),
        'studyToolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limitations':['LTO marginal sizes are not additive','No replacement UI/import/export workflow is included',
                      'No functionality acceptance for deliberately incomplete study copies',
                      'Sensor/clock/brightness/sound remain probe ports and chart integration remains incomplete',
                      'Physical-region limit is measured before any enlarged-region diagnostic link'],
        'cases':results}
(build/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
