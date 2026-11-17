#!/usr/bin/env python3
import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
vectors=json.loads((root/'firmware/tests/fixtures/reference-vectors.json').read_text())
real32=len(sys.argv)>2 and sys.argv[2]=='1'
report={}
for name in ['fullPrecision','previewRounded']:
    fixture=vectors[name]
    data='-20 '+str(len(fixture['rows']))+'\n'+'\n'.join(' '.join(str(row[k]) for k in ['day','timeH','temp','fc']) for row in fixture['rows'])+'\n'
    result=subprocess.run([sys.argv[1]],input=data,text=True,capture_output=True,check=True)
    lines=result.stdout.splitlines(); a,b,r2,n=map(float,lines[0].split())
    tolerance=1e-4 if real32 else 1e-10
    for got,key in [(a,'a'),(b,'b'),(r2,'r2')]:
        assert abs(got-fixture['fit'][key])<=tolerance,(name,key,got,fixture['fit'][key])
    assert n==fixture['fit']['n']
    max_m=max_fc=max_factor=0
    for line,row in zip(lines[1:],fixture['rows']):
        m,fc,factor=map(float,line.split())
        max_m=max(max_m,abs(m-row['m']));max_fc=max(max_fc,abs(fc-row['fcComputed']))
        entries=fixture['fkz']
        expected=next((f['fkz'] for f in entries if f['day']>=row['day']),entries[-1]['fkz'] if entries else 1)
        max_factor=max(max_factor,abs(factor-expected))
    assert len(lines)-1==len(fixture['rows'])
    assert max_m<=(.01 if real32 else 1e-8),(name,max_m)
    assert max_fc<=(.001 if real32 else 1e-8),(name,max_fc)
    assert max_factor<=(1e-6 if real32 else 1e-10),(name,max_factor)
    report[name]={'maxMError':max_m,'maxFcError':max_fc,'maxFactorError':max_factor,'a':a,'b':b,'r2':r2}
print(json.dumps({'status':'PASS','numericProfile':'binary32-host' if real32 else 'binary64-host','datasets':report},indent=2))
