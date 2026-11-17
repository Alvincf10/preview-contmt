#!/usr/bin/env python3
"""Exercise the shared codec, flash helpers and formatters on emulated328P."""
from pathlib import Path
import json
import math
import re
import struct
import subprocess

root = Path(__file__).resolve().parents[1]
cache = root.parents[1] / 'diagnosis_beton/build_firmware_original'
packages = cache / 'arduino-data/packages'
compiler = packages / 'arduino/tools/avr-gcc/7.3.0-atmel3.6.1-arduino7/bin/avr-g++'
simulator = packages / 'MiniCore/tools/avrocd-tools/1.5.8/bin/simavr'
build = root / 'build-avr-precision'
build.mkdir(exist_ok=True)
patterns = [0, 1 << 63, 0x3690000000000000, 0x3690000000000001, 0x36a0000000000000,
            0x380fffffe0000000, 0x3810000000000000, 0x3ff0000010000000, 0x3ff0000030000000,
            0x47efffffe0000000, 0x47f0000000000000, 0x7ff0000000000000, 0x7ff8000000000001]
for exponent in range(865, 1160, 3):
    patterns.extend([(exponent << 52) | fraction for fraction in (0, 1, 0xfffffffffffff)])
patterns += [p | (1 << 63) for p in patterns]
rows = []
for pattern in patterns:
    value = struct.unpack('<d', struct.pack('<Q', pattern))[0]
    if not math.isfinite(value):
        expected = struct.pack('<f', math.nan)
    else:
        try:
            expected = struct.pack('<f', value)
        except OverflowError:
            expected = struct.pack('<f', math.copysign(math.inf, value))
    wire = struct.pack('<Q', pattern)
    finite = math.isfinite(struct.unpack('<f', expected)[0])
    encoded = struct.pack('<d', struct.unpack('<f', expected)[0]) if finite else b'\0' * 8
    rows.append('{' + ','.join(str(b) for b in wire + expected + encoded) + '}')
data = ',\n'.join(rows)
source = build / 'precision.cpp'
source.write_text(r'''
#include "storage/Journal.h"
#include "storage/RecordCodec.h"
#include "core/Flash.h"
#include "core/Command.h"
#include "core/Calendar.h"
#include <avr/io.h>
#include <stdlib.h>
using namespace conmt;
#ifndef CONMT_RECORD_CHECK
const uint8_t cases[][20] PROGMEM={
''' + data + r'''
};
#endif
void text(const char* value) { while(*value) { while(!(UCSR0A&_BV(UDRE0))); UDR0=*value++; } }
void failed(uint16_t line) { char digits[8]; utoa(line,digits,10); text("FAIL line "); text(digits); text("\n"); for(;;) {} }
#define fail() failed(__LINE__)
#ifdef CONMT_RECORD_CHECK
class RecordMemory : public StoragePort {
    uint8_t bytes_[384]; uint16_t size_=0;
public:
    Status size(uint32_t& n) override { n=size_; return Status::Ok; }
    Status read(uint32_t at,uint8_t* out,uint16_t n) override {
        if(at>size_||n>size_-at) return Status::Corrupt;
        memcpy(out,bytes_+at,n); return Status::Ok;
    }
    Status write(uint32_t at,const uint8_t* data,uint16_t n) override {
        if(at>sizeof(bytes_)||n>sizeof(bytes_)-at) return Status::Full;
        memcpy(bytes_+at,data,n); if(at+n>size_) size_=at+n; return Status::Ok;
    }
    Status truncate(uint32_t n) override { if(n>size_) return Status::Invalid; size_=n; return Status::Ok; }
    Status sync() override { return Status::Ok; }
};
RecordMemory recordMemory;
void records() {
    Journal journal(recordMemory);
    if(journal.mount()!=Status::Ok||journal.begin(123)!=Status::Ok) fail();
    Row row; row.revision=7; row.day=4.125; row.timeH=720; row.temp=-0.0; row.fc=31.5; row.hasTemp=row.hasFc=true;
    Point point; point.atMs=7258118399123ULL; point.day=26; point.temp=-12.5; point.validMask=5; point.source=PointSource::Import;
    Fit fit; fit.a=-29.125; fit.b=6.5; fit.r2=.9375; fit.n=41;
    Result result; result.rawM=12345.5; result.prediction.maturity=12346; result.prediction.raw=-.125;
    result.prediction.factor=1.125; result.prediction.fc=31.5; result.prediction.referenceDay=28;
    result.prediction.hasReference=true; result.endMs=7258118399123ULL; result.initialTemp=-0.0; result.lastTemp=36.5;
    if(writeRecord(journal,Key(Kind::Draft,1),RecordType::Row,&row)!=Status::Ok||
       writeRecord(journal,Key(Kind::Session,1),RecordType::Point,&point)!=Status::Ok||
       writeRecord(journal,Key(Kind::Baseline,1),RecordType::Model,&fit)!=Status::Ok||
       writeRecord(journal,Key(Kind::Result,1),RecordType::Result,&result)!=Status::Ok||journal.commit()!=Status::Ok) fail();
    Row rr; Point pp; Fit ff; Result rs;
    if(readRecord(journal,Key(Kind::Draft,1),RecordType::Row,&rr)!=Status::Ok||rr.revision!=7||rr.day!=4.125||!signbit(rr.temp)||!rr.hasFc) fail();
    if(readRecord(journal,Key(Kind::Session,1),RecordType::Point,&pp)!=Status::Ok||pp.atMs!=point.atMs||pp.source!=PointSource::Import) fail();
    if(readRecord(journal,Key(Kind::Baseline,1),RecordType::Model,&ff)!=Status::Ok||ff.a!=fit.a||ff.n!=41) fail();
    if(readRecord(journal,Key(Kind::Result,1),RecordType::Result,&rs)!=Status::Ok||rs.rawM!=result.rawM||rs.endMs!=result.endMs||!rs.prediction.hasReference||!signbit(rs.initialTemp)) fail();
}
#endif
int main() {
    UBRR0=8; UCSR0B=_BV(TXEN0); UCSR0C=_BV(UCSZ01)|_BV(UCSZ00);
#ifdef CONMT_RECORD_CHECK
    records();
#else
    for(uint16_t i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
        uint8_t row[20]; memcpy_P(row,cases[i],sizeof(row)); Real actual=getReal(row);
        uint32_t expected=get32(row+8),bits; memcpy(&bits,&actual,4);
        if((expected&0x7fffffffUL)>0x7f800000UL) { if(!isnan(actual)) fail(); }
        else if(bits!=expected) fail();
        if(finite(actual)) { uint8_t encoded[8]; putReal(encoded,actual); if(memcmp(encoded,row+12,8)) fail(); }
    }
    char value[32]; CM_TEXT(value,sizeof(value),"Flash text"); if(strcmp(value,"Flash text")) fail();
    CM_TEXT(value,5,"Truncation"); if(strcmp(value,"Trun")) fail();
    static const char prefix[] PROGMEM="tDay"; indexedName(value,sizeof(value),prefix,5); if(strcmp(value,"tDay5")) fail();
    formatStatus(value,sizeof(value),Status::ConfirmRequired); if(strcmp(value,"ConfirmRequired")) fail();
    if(commandFromText("RESULT_SAVE")!=Command::RESULT_SAVE||!allowedPage(Command::RESULT_SAVE,12)||allowedPage(Command::RESULT_SAVE,11)) fail();
    formatReal(value,sizeof(value),36.5,1); if(strcmp(value,"36.5")) fail();
    formatReal(value,sizeof(value),4.125,2); if(strcmp(value,"4.13")) fail();
    uint64_t date; if(parseDate("2024-02-29",date)!=Status::Ok) fail(); char clock[12];
    if(calendarText(date+45296000ULL,value,sizeof(value),clock,sizeof(clock))!=Status::Ok||strcmp(value,"2024-02-29")||strcmp(clock,"12:34:56")) fail();
#endif
    text("PASS\n"); for(;;) {}
}
''')
sources = [source] + [root / 'ConMT/src' / path for path in [
    'storage/Journal.cpp', 'storage/DiskIndex.cpp', 'storage/RecordCodec.cpp', 'core/Types.cpp', 'core/Flash.cpp', 'core/Command.cpp', 'core/Calendar.cpp']]
for name, defines in [('precision', []), ('records', ['-DCONMT_RECORD_CHECK=1'])]:
    command = [str(compiler), '-mmcu=atmega328p', '-Os', '-flto', '-std=gnu++11', '-fno-exceptions',
               '-fno-rtti', '-ffunction-sections', '-fdata-sections', '-I' + str(root / 'ConMT/src'),
               *defines, *map(str, sources), '-Wl,--gc-sections',
               '-Wl,--defsym=__TEXT_REGION_LENGTH__=32768,--defsym=__DATA_REGION_LENGTH__=2048',
               '-lm', '-o', str(build / (name+'.elf'))]
    subprocess.run(command, check=True, capture_output=True)
    process = subprocess.Popen([str(simulator), '-m', 'atmega328p', '-f', '16000000', str(build / (name+'.elf'))], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        raw = process.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        process.terminate()
        raw = process.communicate(timeout=2)[0]
    output = re.sub(r'\x1b\[[0-9;]*m', '', raw.decode(errors='replace'))
    (build / (name+'-result.txt')).write_text(output)
    assert 'PASS' in output and 'FAIL' not in output, output
report = {'status': 'PASS', 'target': 'Emulated ATmega328P', 'codecCases': len(rows),
          'covers': ['binary64-to-binary32 rounding', 'subnormals', 'signed zero', 'binary64 encoding',
                     'PROGMEM strings/tables', 'status/command lookup', 'decimal ties', 'leap date',
                     'schema1 record descriptors and streamed journal read/write'],
          'fullPresenterRuntimeVerified': False, 'physicalHardwareVerified': False}
(root / 'releases/avr-precision.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
