#!/usr/bin/env python3
"""Run shared numeric C++ on emulated ATmega328P; no physical peripheral claim."""
import json,re,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
workspace=root.parents[1]
cache=workspace/'diagnosis_beton/build_firmware_original'
packages=cache/'arduino-data/packages'
tools=packages/'arduino/tools/avr-gcc/7.3.0-atmel3.6.1-arduino7/bin'
core=packages/'arduino/hardware/avr/1.8.8/cores/arduino'
sim=packages/'MiniCore/tools/avrocd-tools/1.5.8/bin/simavr'
build=root/'build-avr-numeric';build.mkdir(exist_ok=True)
vectors=json.loads((root/'tests/fixtures/reference-vectors.json').read_text())
reports={}
for name in ['fullPrecision','previewRounded']:
    source=build/(name+'.cpp')
    raw=',\n'.join('{'+','.join(repr(row[k]) for k in ['day','timeH','temp','fc'])+'}' for row in vectors[name]['rows'])
    source.write_text('''#include "core/Math.h"
#include <avr/io.h>
#include <avr/pgmspace.h>
#include <stdlib.h>
using namespace conmt;
struct Raw { float day,h,t,fc; };
const Raw data[] PROGMEM={'''+raw+'''};
class Rows : public RowSource {
    uint8_t i;
public:
    Rows():i(0){}
    void reset() override { i=0; }
    Status next(Row& row) override {
        if(i>=sizeof(data)/sizeof(data[0])) return Status::Missing;
        Raw r; memcpy_P(&r,data+i,sizeof(r)); row.day=r.day; row.timeH=r.h; row.temp=r.t; row.fc=r.fc; row.hasTemp=true; row.hasFc=r.fc>0; ++i; return Status::Ok;
    }
};
void ch(char c){while(!(UCSR0A&_BV(UDRE0)));UDR0=c;}
void text(const char* s){while(*s)ch(*s++);}
void number(double n){char b[24];dtostrf(n,0,8,b);text(b);ch(' ');}
int main(){UBRR0=8;UCSR0B=_BV(TXEN0);UCSR0C=_BV(UCSZ01)|_BV(UCSZ00);
Rows rows; Fit fit; if(fitRows(rows,-20,fit)!=Status::Ok){text("FAIL\\n");for(;;);}
text("FIT ");number(fit.a);number(fit.b);number(fit.r2);ch('\\n');
Accumulator acc; Row row; rows.reset();
for(uint8_t i=0;i<sizeof(data)/sizeof(data[0]);++i){Raw x;memcpy_P(&x,data+i,sizeof(x));acc.add(x.h,x.t,-20);Selection s;lookupRows(rows,-20,fit,x.day,s);text("ROW ");number(acc.maturity());number(predict(acc.maturity(),fit.a,fit.b,s.factor));ch('\\n');}
text("DONE\\n");for(;;);}
''')
    cmd=[str(tools/'avr-g++'),'-mmcu=atmega328p','-Os','-flto','-std=gnu++11','-fno-exceptions','-fno-rtti','-ffunction-sections','-fdata-sections','-I'+str(core),'-I'+str(root/'ConMT/src'),str(source),str(root/'ConMT/src/core/Math.cpp'),str(root/'ConMT/src/core/Types.cpp'),str(cache/'build/core/core.a'),'-Wl,--gc-sections','-lm','-o',str(build/(name+'.elf'))]
    subprocess.run(cmd,check=True,capture_output=True)
    process=subprocess.Popen([str(sim),'-m','atmega328p','-f','16000000',str(build/(name+'.elf'))],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    try: rawoutput=process.communicate(timeout=12)[0]
    except subprocess.TimeoutExpired:
        process.terminate();rawoutput=process.communicate(timeout=2)[0]
    clean=re.sub(r'\x1b\[[0-9;]*m','',rawoutput.decode(errors='replace'))
    (build/(name+'.txt')).write_text(clean)
    matches=re.findall(r'ROW\s+([-0-9.]+)\s+([-0-9.]+)',clean)
    assert len(matches)==len(vectors[name]['rows']),(name,len(matches),clean[-1000:])
    max_m=max(abs(float(pair[0])-row['m']) for pair,row in zip(matches,vectors[name]['rows']))
    max_fc=max(abs(float(pair[1])-row['fcComputed']) for pair,row in zip(matches,vectors[name]['rows']))
    assert max_m<=.01 and max_fc<=.001,(name,max_m,max_fc)
    reports[name]={'maxMError':max_m,'maxFcError':max_fc,'rows':len(matches)}
report={'status':'PASS','target':'ATmega328P emulated, AVR double=32-bit','datasets':reports,'physicalSensorsOrStorageTested':False}
(root/'releases/avr-numeric.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
