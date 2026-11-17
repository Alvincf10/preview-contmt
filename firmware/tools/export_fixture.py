#!/usr/bin/env python3
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=root/'tests/fixtures/reference-vectors.json'
v=json.loads(source.read_text())['fullPrecision']
rows=[' '.join(str(v['fit'][k]) for k in ['a','b','r2','n'])]
rows += [' '.join(str(row[k]) for k in ['day','timeH','temp','fc','m','fcComputed']) for row in v['rows']]
(root/'tests/fixtures/excel.tsv').write_text('\n'.join(rows)+'\n')
