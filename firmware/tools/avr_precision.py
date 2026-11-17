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
#include "core/Flash.h"
#include "core/Command.h"
#include "core/Calendar.h"
#include <avr/io.h>
#include <stdlib.h>
using namespace conmt;
const uint8_t cases[][20] PROGMEM={
''' + data + r'''
};
void text(const char* value) { while(*value) { while(!(UCSR0A&_BV(UDRE0))); UDR0=*value++; } }
void failed(uint16_t line) { char digits[8]; utoa(line,digits,10); text("FAIL line "); text(digits); text("\n"); for(;;) {} }
#define fail() failed(__LINE__)
int main() {
    UBRR0=8; UCSR0B=_BV(TXEN0); UCSR0C=_BV(UCSZ01)|_BV(UCSZ00);
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
    text("PASS\n"); for(;;) {}
}
''')
sources = [source] + [root / 'ConMT/src' / path for path in [
    'storage/Journal.cpp', 'storage/DiskIndex.cpp', 'core/Types.cpp', 'core/Flash.cpp', 'core/Command.cpp', 'core/Calendar.cpp']]
command = [str(compiler), '-mmcu=atmega328p', '-Os', '-flto', '-std=gnu++11', '-fno-exceptions',
           '-fno-rtti', '-ffunction-sections', '-fdata-sections', '-I' + str(root / 'ConMT/src'),
           *map(str, sources), '-Wl,--gc-sections', '-lm', '-o', str(build / 'precision.elf')]
subprocess.run(command, check=True, capture_output=True)
process = subprocess.Popen([str(simulator), '-m', 'atmega328p', '-f', '16000000', str(build / 'precision.elf')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    raw = process.communicate(timeout=5)[0]
except subprocess.TimeoutExpired:
    process.terminate()
    raw = process.communicate(timeout=2)[0]
output = re.sub(r'\x1b\[[0-9;]*m', '', raw.decode(errors='replace'))
(build / 'result.txt').write_text(output)
assert 'PASS' in output and 'FAIL' not in output, output
report = {'status': 'PASS', 'target': 'Emulated ATmega328P', 'codecCases': len(rows),
          'covers': ['binary64-to-binary32 rounding', 'subnormals', 'signed zero', 'binary64 encoding',
                     'PROGMEM strings/tables', 'status/command lookup', 'decimal ties', 'leap date'],
          'fullPresenterRuntimeVerified': False, 'physicalHardwareVerified': False}
(root / 'releases/avr-precision.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
