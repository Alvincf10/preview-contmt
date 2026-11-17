#!/usr/bin/env python3
"""Compare public workflows and fault traces with an immutable Git checkpoint."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--baseline',default='520a74f')
parser.add_argument('--current',type=Path,default=root/'build-host/conmt_transaction_trace')
parser.add_argument('--write-fixture',action='store_true')
parser.add_argument('--real32',action='store_true')
args=parser.parse_args()
commit=subprocess.check_output(['git','rev-parse',args.baseline],cwd=root,text=True).strip()
build=root/'build-checkpoint-trace'/(commit[:12]+('-real32' if args.real32 else ''))
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'--','firmware/ConMT/src','firmware/host'],cwd=root.parent,text=True).splitlines()
for name in paths:
    if not name.endswith(('.cpp','.h')): continue
    target=build/Path(name).relative_to('firmware'); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(subprocess.check_output(['git','show',commit+':'+name],cwd=root.parent))
source=root/'tests/transaction_trace.cpp'
binary=build/'baseline'
sources=list((build/'ConMT/src').rglob('*.cpp'))+[build/'host/HostPorts.cpp',source]
subprocess.run(['c++','-std=c++11','-O1',*(['-DCONMT_REAL32=1'] if args.real32 else []),'-I'+str(build/'ConMT/src'),'-I'+str(build/'host'),*map(str,sources),'-o',str(binary)],check=True)
expected=subprocess.check_output([str(binary)])
actual=subprocess.check_output([str(args.current)])
if actual!=expected:
    (build/'expected.txt').write_bytes(expected); (build/'actual.txt').write_bytes(actual)
    raise SystemExit('Checkpoint trace mismatch; see '+str(build))
report={'status':'PASS','baselineCommit':commit,'traceSourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'traceSha256':hashlib.sha256(expected).hexdigest(),'lines':len(expected.splitlines()),
        'realBits':32 if args.real32 else 64,
        'scope':'Public workflows including schema1 bytes/status/navigation and120write-cut scenarios, indexed and unindexed. Not hardware.'}
if args.write_fixture:
    name='transaction-trace'+('-real32' if args.real32 else '')
    (root/('tests/fixtures/'+name+'.txt')).write_bytes(expected)
    (root/('tests/fixtures/'+name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
