#!/usr/bin/env python3
"""Render the dated manual assessment against every acceptance ID in plan04."""
from pathlib import Path
import collections
import csv
import json
import re

root = Path(__file__).resolve().parents[1]
output = root / 'reviews/2026-11-16-audit'
plan = root.parent / 'docs/firmware-plan/04_IMPLEMENTATION.md'
cases = {}
for line in plan.read_text().splitlines():
    match = re.fullmatch(r'\|\s*([A-Z]\d{2})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|', line)
    if match:
        cases[match[1]] = (match[2], match[3])

statuses = dict(H='HOST_PASS', E='EMULATED_PASS', P='PARTIAL', N='NOT_IMPLEMENTED', D='HARDWARE_PENDING', F='FAIL')
assessment = {}
data = """N01|H|tests.cpp; math_cases.cpp|Delta28.2425 diuji langsung.
N02,N03,N06,N08,N12,N13,N14,N15,N17,N18,N19,N20,N23|H|math_cases.cpp|Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format.
N04,N05|H|tests.cpp|Interval negatif dikurangi dari M lalu akumulasi dibatasi minimum nol.
N07|H|audit C15|Input stored acak diintegrasikan secara kronologis.
N09,N10,N11,N21,N26|H|reference_parity; full_reference_workflow|Dua fixture41baris, a/b/R2/n, M/Fc/FKZ dibanding oracle TS per titik.
N16|H|math_cases.cpp; full_reference_workflow|4→5,6→7,26→28 mengambil faktor saja; prediksi tetap memakai M pengujian.
N22|H|audit-reference.mjs; workbook-evidence.json|Pengecualian sel Excel day3 sebesar0.000620700083 dicatat; tidak di-hardcode ke rumus.
N24|H|audit C07|Water165/cement385 ditampilkan0.43.
N25|H|audit C08|Perubahan material tidak mengubah fit.
N27|H|workflow.cpp; full_reference_workflow|Fit/replay/snapshot setelah save/restart sama dalam toleransi; FKZ dihitung dari baseline immutable.
N28|H|audit C05|M raw960.5 dan summary961 menghasilkan prediksi berbeda sesuai policy.
N29|E|releases/avr-numeric.json|AVR GCC/simavr2×41titik; bukan pengujian chip/peripheral fisik.
N30|P|core/Chart.h; math_cases.cpp|Sampler raw ln(M) ada; pipeline chart lab/panel belum lengkap.
V01|H|tests.cpp; workflow.cpp|String kosong berbeda dari suhu nol yang valid.
V02|H|math_cases.cpp|Parse parsial, koma, NaN/Infinity, suffix dan overflow ditolak.
V03|P|math_cases.cpp; Parser|Aturan core/codec/parser tersedia; keyboard dan batas input visual panel belum dibuktikan.
V04|H|audit C09|Target kosong/nol/negatif ditolak dan nilai committed bertahan.
V05|P|workflow.cpp; validateDraft/model|Tidak mengambil model baseline lain; importer incomplete belum lengkap.
B01|H|workflow.cpp; full_reference_workflow|NEW/input/GENERATE/SAVE benar-benar menghasilkan record committed.
B02|H|workflow.cpp|Saved SELECT membuka maturity; BACK kembali ke daftar saved.
B03|H|workflow.cpp; audit C03|Edit saved menghasilkan draft dan SAVE ID baru; baseline lama utuh.
B04|H|workflow.cpp|Retry operation ID yang sama tidak menambah baseline duplikat.
B05|H|audit C01,A29,A42|FILL mempertahankan data, repeatable dan slot Day0 sesuai snapping sumber.
B06|H|audit C10|Seluruh48slot penuh mengembalikan Capacity.
B07,B08|H|audit C02|Day3 mengisi celah day1,2,4; minimum3baris dan confirm penghapusan diuji.
B09|P|audit C11,A21|Stale view/revision overflow dilindungi; driver sensor asynchronous fisik belum ada.
B10|H|audit A01,A02,A40; workflow.cpp|Nama sama tetap ID berbeda; pilihan dan penghapusan berdasar ID.
B11|H|full_reference_workflow; audit A41|41baris, penambahan ke42, viewport kedua/akhir dan fokus row baru diuji.
B12|H|audit C12|Edit setelah GENERATE menghapus model lama dan menolak SAVE stale.
S01|H|workflow.cpp|START membekukan model/waktu/suhu awal dan satu Day0.
S02|H|audit C06|Tanpa sensor/jam valid tidak membuat sesi palsu.
S03,S04|H|math_cases.cpp|Suhu0C valid; average hanya kanal valid, operasional satu desimal sesuai sumber.
S05|H|audit A04,A05,A07,A16; workflow.cpp|No sensor/stale/unavailable ditandai sebagai gap, tanpa data random.
S06|H|audit C13; workflow.cpp|Redraw/reset panel tidak memulai ulang sesi.
S07|H|workflow.cpp|START kedua perlu confirm dan penolakan mempertahankan sesi.
S08|H|audit C17|Edit suhu/jam checkpoint melakukan replay dan invalidasi preview.
S09|P|audit C17; editCheckpoint|Perubahan suhu awal ada; koreksi waktu Day0 terhadap anchor akuisisi live belum diterima end-to-end.
S10,S11|H|workflow.cpp; audit C05|NEXT mengunci waktu checkpoint; Day0 saja M0, tanpa liveM dari waktu lain.
S12|H|workflow.cpp; audit A19,C19|History dibuat setelah commit, sensor NEXT dibekukan, history terpilih.
S13|H|full_reference_workflow|History identik sesudah restart dan penghapusan logis baseline.
S14|P|model/checkpointResult|Tidak ada lookup by-name; jalur import legacy/incomplete belum lengkap.
S15|H|audit A22; full_reference_workflow|ADD memakai sensor/waktu saat ini dan day eksplisit; future observation ditolak.
T01|H|tests.cpp|Pour23:30→Day0 clock00:00 =0.5h.
T02|H|math_cases.cpp|Pour23:30→Day1 clock00:00 =24.5h.
T03|H|math_cases.cpp; audit A36|Tanggal mustahil dan jadwal di luar range ditolak/unavailable.
T04|P|audit A17,A18; markGap|Discontinuity menghasilkan gap terurut; event cause RTC terpisah belum lengkap.
T05|H|audit C16|Stall1.7detik memakai delta sampel sebenarnya.
T06|H|audit C20; math_cases.cpp|Acquisition dan freshness lolos rollover uint32.
T07|H|workflow.cpp; audit A04,A18|Restart mengembalikan committed record dan menandai gap yang belum selesai.
T08|H|audit C21|Day/waktu bertentangan ditolak sebelum model/checkpoint baru diterima.
W01|P|workflow.cpp; full_reference_workflow; audit A15,A23,A24|Codec/replay/snapshot diuji, belum roundtrip setiap field/nilai ekstrem schema secara terpisah.
W02|P|workflow failures; audit A38,C14|100byte-budget transaksi scalar dan committed corruption diuji; belum setiap offset transaksi baseline/result besar.
W03|P|workflow corruptionAndTime; audit A38|Guard CRC/length/flag/finite ada; kombinasi schema/length rusak belum seluruhnya menjadi executable test.
W04|P|workflow failures|Atomicity transaksi kecil diuji host; seluruh tahap baseline/result dan daya SD fisik belum diterima.
W05|N|storage/Journal|Index disk, metadata A/B dan rebuild index belum diimplementasikan.
W06|P|workflow failures; audit A27,C19|Absent/full/sync/rescan host tersedia; remove/reinsert media fisik belum diuji.
W07|H|workflow.cpp|Operation ID durable dan retry SAVE RESULT tidak membuat duplikat.
W08|H|audit A19,A43,C19; workflow.cpp|AutoSave default false; manual SAVE tetap commit dan periodic recovery dapat diaktifkan eksplisit.
W09|P|StoredRows,nextPoint,Journal|RAM tidak berupa array seluruh database; index/latency/volume history besar belum lulus.
W10|H|workflow cold boot|Cold boot/reboot tidak memasukkan demo seeds.
H01|H|workflow protocol; Parser|Parser incremental/fragment/timeout dan TX credit terbatas diuji.
H02|H|audit A44|Frame terkoalesensi mendapat respons berurutan; stale command kedua diberi ACK penolakan.
H03|H|workflow protocol; audit A08,A09|Overflow/noise/arity dan recovery delimiter diuji.
H04|H|audit C11,A12,A26,A28|View/page/boot/operation melindungi mutasi; BACK tidak bergantung view data lama.
H05|P|audit A10,A13,A39,A44|Refresh/ACK correlation diperbaiki; burst nyata dan starvation selama operasi SD besar belum lulus.
H06|H|audit A11,A12,C13|PAGE_READY/reset panel mempertahankan ACK dan sesi aktif di host.
H07|P|workflow durable retries|Repository replay lintas reboot diuji; full UART reset MCU tepat sesudah commit belum diuji.
H08|P|audit A32; HmiContractVersion=2|Contract mismatch ditolak; identitas/model panel belum diketahui.
H09|D|hmi/events|Belum ada capture byte panel pasangan; LF snippet bukan bukti UART fisik.
H10|H|audit C18|Native touch/string response sintetis tidak menjadi AppCommand.
U01|P|hmi/manifest.json; Controller|17page dan197event tersedia; acceptance visual seluruh panel belum ada.
U02|H|audit C19|SAVE gagal mempertahankan page; tidak membuat history palsu; BACK/retry berhasil.
U03|D|hmi/README.md|Font/unit/desimal/nama panjang/layout belum dibuktikan pada panel pasangan.
U04|N|hmi apply_* events|Keyboard/date/datum/modal/Cancel visual belum dirakit; Apply saja belum memenuhi U04.
U05|H|workflow cold boot/new baseline|Empty baseline/history dapat memulai flow tanpa seed.
U06|N|core/Chart.h|Renderer panel lab points/axis/kurva dan acceptance terhadap React belum lengkap.
U07|P|audit A20,A31,C04|Port settings dan rollback commit gagal diuji; efek fisik driver belum terverifikasi.
U08|P|DevicePort; BoardBinding gate|Tidak ada battery87%/random/sukses palsu; baterai dan splash panel nyata belum selesai.
P01|F|releases/avr-capacity.json|Flash lengkap melebihi ATmega328P; BoardBinding produksi belum tersedia.
P02|F|releases/avr-capacity.json; avr-stack.json|Margin stack bersama driver/interrupt belum dibuktikan; SRAM statis saja bukan kelulusan.
P03|P|Journal get/StoredRows; Transport poll|Full scan/GENERATE/SAVE masih sinkron; worst-case latency dan prioritas layanan belum memenuhi gate produksi.
P04|D|releases/status.json|Belum ada soak/power cycle perangkat fisik; day26 virtual bukan run26hari.
"""
for line in data.splitlines():
    ids, status, evidence, note = line.split('|', 3)
    for key in ids.split(','):
        assert key not in assessment, key
        assessment[key] = dict(status=statuses[status], evidence=evidence, note=note)
assert len(cases) == 102 and set(cases) == set(assessment), (len(cases), set(cases) ^ set(assessment))
for profile in ['host', 'binary32', 'sanitizer']:
    result = json.loads((output / (profile + '-result.json')).read_text())
    assert result['ctestExitCode'] == result['auditExitCode'] == 0, profile
rows = [dict(id=key, scenario=scenario, acceptance=acceptance, **assessment[key]) for key, (scenario, acceptance) in cases.items()]
counts = dict(collections.Counter(row['status'] for row in rows))
with (output / 'coverage.csv').open('w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=['id', 'scenario', 'acceptance', 'status', 'evidence', 'note'])
    writer.writeheader()
    writer.writerows(rows)
(output / 'coverage.json').write_text(json.dumps(dict(assessmentDate='2026-11-17', source=str(plan.relative_to(root.parent)), total=len(rows), counts=counts, scenarios=rows), ensure_ascii=False, indent=2) + '\n')
lines = ['# Cakupan 102 acceptance scenario', '', 'Audit 16–17 November 2026. Ini penilaian implementasi dan bukti tes, bukan plan baru. **HOST_PASS hanya berarti skenario host; bukan kelulusan perangkat produksi.** EMULATED_PASS hanya numerik AVR/simavr. PARTIAL berarti ada implementasi/pembuktian yang belum lengkap. FAIL berarti gate rilis belum lulus.', '', 'Axx/Cxx adalah ID dalam [audit.cpp](../../tests/audit.cpp). Bukti lain: [workflow](../../tests/workflow.cpp), [fixture workflow](../../tests/reference_workflow.cpp), [math cases](../../tests/math_cases.cpp) dan [comparator](../../tools/compare_reference.py).', '', 'Jumlah per status: ' + ', '.join(f'{key}={value}' for key, value in counts.items()) + '.', '', '| ID | Skenario plan | Status | Bukti | Hasil / batas |', '|---|---|---|---|---|']
for row in rows:
    lines.append('| ' + ' | '.join(str(row[key]).replace('|', '\\|') for key in ['id', 'scenario', 'status', 'evidence', 'note']) + ' |')
lines.extend(['', 'Teks acceptance asli juga ada pada [CSV](coverage.csv) dan [JSON](coverage.json). Source acuan tidak diubah.'])
(output / 'coverage.md').write_text('\n'.join(lines) + '\n')
print(json.dumps(dict(scenarios=len(rows), counts=counts)))
