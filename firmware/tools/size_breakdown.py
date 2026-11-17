#!/usr/bin/env python3
"""Attribute linked AVR bytes without counting aliases twice."""
from pathlib import Path
import argparse
import json
import re
import subprocess

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--elf', type=Path, default=root / 'build-avr-capacity/CAPACITY_ONLY.elf')
parser.add_argument('--out', type=Path, default=root / 'releases/size-breakdown.json')
args = parser.parse_args()
tools = root.parents[1] / 'diagnosis_beton/build_firmware_original/arduino-data/packages/arduino/tools/avr-gcc/7.3.0-atmel3.6.1-arduino7/bin'
raw = subprocess.check_output([str(tools / 'avr-nm'), '-S', '--size-sort', '-C', str(args.elf)], text=True)
symbols = {}
for line in raw.splitlines():
    match = re.match(r'([0-9a-f]+) ([0-9a-f]+) ([tTbBdDrRvV]) (.+)', line)
    if not match:
        continue
    address, size, kind, name = match.groups()
    key = (int(address, 16), int(size, 16))
    if key not in symbols:
        symbols[key] = {'address': key[0], 'bytes': key[1], 'type': kind, 'names': []}
    symbols[key]['names'].append(name)
groups = {}
for symbol in symbols.values():
    if symbol['type'].lower() != 't':
        continue
    name = symbol['names'][0]
    group = next((value for value in ['Controller', 'Transport', 'Presenter', 'Repository', 'Journal', 'DiskIndex', 'SdFile', 'SdVolume', 'Sd2Card'] if value + '::' in name), None)
    if not group:
        group = 'ConMT other' if name.startswith('conmt::') else 'Runtime/SDK/constants'
    groups[group] = groups.get(group, 0) + symbol['bytes']
report = {
    'scope': 'Unique address/size symbols; LTO attribution is approximate. Unnamed padding is not attributed.',
    'textGroups': groups,
    'largestText': sorted([s for s in symbols.values() if s['type'].lower() == 't'], key=lambda s: -s['bytes'])[:40],
    'largestStatic': sorted([s for s in symbols.values() if s['type'].lower() in ('d', 'b')], key=lambda s: -s['bytes'])[:20],
    'engineeringBudget': {'flashBytesAllFeatures': 30720, 'staticSramBytes': 1280, 'physicalFlashBytes': 32768, 'physicalSramBytes': 2048},
    'stackProof': 'Non-LTO frames in avr-stack.json are not a nested call-chain or interrupt watermark.'
}
args.out.parent.mkdir(parents=True, exist_ok=True)
args.out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(groups, indent=2))
