#!/usr/bin/env python3
"""Record compiler frame estimates. These are not a runtime stack watermark."""
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[1]
cache = root.parents[1] / 'diagnosis_beton/build_firmware_original'
compiler = cache / 'arduino-data/packages/arduino/tools/avr-gcc/7.3.0-atmel3.6.1-arduino7/bin/avr-g++'
capacity = json.loads((root / 'releases/avr-capacity.json').read_text())
output = root / 'build-avr-stack'
output.mkdir(exist_ok=True)
flags = [flag for flag in capacity['compilerFlags'] if flag != '-flto']
frames = []
for group in ['core', 'storage', 'app', 'hmi']:
    for source in (root / 'ConMT/src' / group).glob('*.cpp'):
        obj = output / (source.stem + '.o')
        subprocess.run([str(compiler), *flags, '-I' + str(root / 'ConMT/src'), '-c', str(source), '-o', str(obj)], check=True)
        usage = obj.with_suffix('.su')
        for line in usage.read_text().splitlines():
            function, size, kind = line.rsplit('\t', 2)
            frames.append({'source': str(source.relative_to(root)), 'function': function, 'bytes': int(size), 'kind': kind})
frames.sort(key=lambda frame: frame['bytes'], reverse=True)
report = {'scope': 'AVR GCC non-LTO per-function frame estimates; not nested worst-case or hardware watermark', 'runtimeStackVerified': False, 'includesDriverOrInterruptStack': False, 'frames': frames}
(root / 'releases/avr-stack.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'runtimeStackVerified': False, 'largestFrames': frames[:5]}, indent=2))
