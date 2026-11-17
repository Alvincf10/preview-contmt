# Cakupan 102 acceptance scenario

Audit 16–17 November 2026. Ini penilaian implementasi dan bukti tes, bukan plan baru. **HOST_PASS hanya berarti skenario host; bukan kelulusan perangkat produksi.** EMULATED_PASS hanya numerik AVR/simavr. PARTIAL berarti ada implementasi/pembuktian yang belum lengkap. FAIL berarti gate rilis belum lulus.

Axx/Cxx adalah ID dalam [audit.cpp](../../tests/audit.cpp). Bukti lain: [workflow](../../tests/workflow.cpp), [fixture workflow](../../tests/reference_workflow.cpp), [math cases](../../tests/math_cases.cpp) dan [comparator](../../tools/compare_reference.py).

Jumlah per status: HOST_PASS=73, EMULATED_PASS=1, PARTIAL=20, NOT_IMPLEMENTED=3, HARDWARE_PENDING=3, FAIL=2.

| ID | Skenario plan | Status | Bukti | Hasil / batas |
|---|---|---|---|---|
| N01 | Tprev36, Tnow36.97, T0−20, dt0.5h | HOST_PASS | tests.cpp; math_cases.cpp | Delta28.2425 diuji langsung. |
| N02 | Tprev30, Tnow30, T00, dt0 | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N03 | dt negatif atau suhu nonfinite pada fungsi parity | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N04 | Titik (0h,10),(1h,10),(2h,−18), T00 | HOST_PASS | tests.cpp | Interval negatif dikurangi dari M lalu akumulasi dibatasi minimum nol. |
| N05 | Lanjut titik (3h,−18) dari N04 | HOST_PASS | tests.cpp | Interval negatif dikurangi dari M lalu akumulasi dibatasi minimum nol. |
| N06 | Titik pertama pada2h, kedua3h, T10/T00 | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N07 | Timestamp input acak, suhu identik fixture | HOST_PASS | audit C15 | Input stored acak diintegrasikan secara kronologis. |
| N08 | Timestamp kembar | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N09 | Full41 baris Excel | HOST_PASS | reference_parity; full_reference_workflow | Dua fixture41baris, a/b/R2/n, M/Fc/FKZ dibanding oracle TS per titik. |
| N10 | Full41 baris preview rounded | HOST_PASS | reference_parity; full_reference_workflow | Dua fixture41baris, a/b/R2/n, M/Fc/FKZ dibanding oracle TS per titik. |
| N11 | Full Excel regression | HOST_PASS | reference_parity; full_reference_workflow | Dua fixture41baris, a/b/R2/n, M/Fc/FKZ dibanding oracle TS per titik. |
| N12 | Fit kurang2pasangan atau semua M sama | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N13 | Fc sama pada dua M berbeda | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N14 | Fc/M nonpositive pada input fit | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N15 | e0.2,0,−0.099,−0.1,−0.2 | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N16 | Daftar faktor day5=.9, day7=1.1; query6 | HOST_PASS | math_cases.cpp; full_reference_workflow | 4→5,6→7,26→28 mengambil faktor saja; prediksi tetap memakai M pengujian. |
| N17 | Query di atas hari terakhir | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N18 | Faktor empty/invalid; day nonfinite | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N19 | Day sama beberapa valid lab rows | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N20 | M0, model invalid, raw Fc negatif | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N21 | Full Excel day1/day28 | HOST_PASS | reference_parity; full_reference_workflow | Dua fixture41baris, a/b/R2/n, M/Fc/FKZ dibanding oracle TS per titik. |
| N22 | Full Excel day3 vs W69 | HOST_PASS | audit-reference.mjs; workbook-evidence.json | Pengecualian sel Excel day3 sebesar0.000620700083 dicatat; tidak di-hardcode ke rumus. |
| N23 | Target30, Fc38.7033333 | HOST_PASS | math_cases.cpp | Assertion edge cases untuk guard, filter, clamp, fit, lookup dan format. |
| N24 | Water165/cement385 | HOST_PASS | audit C07 | Water165/cement385 ditampilkan0.43. |
| N25 | Ubah material saja; data lab identik | HOST_PASS | audit C08 | Perubahan material tidak mengubah fit. |
| N26 | Recompute fit dua-pass streaming | HOST_PASS | reference_parity; full_reference_workflow | Dua fixture41baris, a/b/R2/n, M/Fc/FKZ dibanding oracle TS per titik. |
| N27 | serialize/decode koefisien + FKZ + replay | HOST_PASS | workflow.cpp; full_reference_workflow | Fit/replay/snapshot setelah save/restart sama dalam toleransi; FKZ dihitung dari baseline immutable. |
| N28 | Result M raw vs Math.round(M) | HOST_PASS | audit C05 | M raw960.5 dan summary961 menghasilkan prediksi berbeda sesuai policy. |
| N29 | Target binary float/double | EMULATED_PASS | releases/avr-numeric.json | AVR GCC/simavr2×41titik; bukan pengujian chip/peripheral fisik. |
| N30 | Graph sampling | PARTIAL | core/Chart.h; math_cases.cpp | Sampler raw ln(M) ada; pipeline chart lab/panel belum lengkap. |
| V01 | Suhu kosong vs “0” | HOST_PASS | tests.cpp; workflow.cpp | String kosong berbeda dari suhu nol yang valid. |
| V02 | “36.5x”, “36,5”, NaN, Infinity, overflow | HOST_PASS | math_cases.cpp | Parse parsial, koma, NaN/Infinity, suffix dan overflow ditolak. |
| V03 | Nama panjang/delimiter/quote/control | PARTIAL | math_cases.cpp; Parser | Aturan core/codec/parser tersedia; keyboard dan batas input visual panel belum dibuktikan. |
| V04 | Target kosong/0/negatif | HOST_PASS | audit C09 | Target kosong/nol/negatif ditolak dan nilai committed bertahan. |
| V05 | Model absent/incomplete | PARTIAL | workflow.cpp; validateDraft/model | Tidak mengambil model baseline lain; importer incomplete belum lengkap. |
| B01 | NEW → material → maturity → generate → save | HOST_PASS | workflow.cpp; full_reference_workflow | NEW/input/GENERATE/SAVE benar-benar menghasilkan record committed. |
| B02 | SAVED SELECT → maturity → BACK | HOST_PASS | workflow.cpp | Saved SELECT membuka maturity; BACK kembali ke daftar saved. |
| B03 | Edit saved → generate → save | HOST_PASS | workflow.cpp; audit C03 | Edit saved menghasilkan draft dan SAVE ID baru; baseline lama utuh. |
| B04 | SAVE retransmit | HOST_PASS | workflow.cpp | Retry operation ID yang sama tidak menambah baseline duplikat. |
| B05 | ADD DAY0/FILL0..6 | HOST_PASS | audit C01,A29,A42 | FILL mempertahankan data, repeatable dan slot Day0 sesuai snapping sumber. |
| B06 | Slot awal lengkap | HOST_PASS | audit C10 | Seluruh48slot penuh mengembalikan Capacity. |
| B07 | ADD LAB setelah day1,2,4 | HOST_PASS | audit C02 | Day3 mengisi celah day1,2,4; minimum3baris dan confirm penghapusan diuji. |
| B08 | Delete pada3row | HOST_PASS | audit C02 | Day3 mengisi celah day1,2,4; minimum3baris dan confirm penghapusan diuji. |
| B09 | Sensor request lalu delete/sort/pagination | PARTIAL | audit C11,A21 | Stale view/revision overflow dilindungi; driver sensor asynchronous fisik belum ada. |
| B10 | Dua baseline nama sama | HOST_PASS | audit A01,A02,A40; workflow.cpp | Nama sama tetap ID berbeda; pilihan dan penghapusan berdasar ID. |
| B11 | 41 baris dan lebih | HOST_PASS | full_reference_workflow; audit A41 | 41baris, penambahan ke42, viewport kedua/akhir dan fokus row baru diuji. |
| B12 | GENERATE lalu edit draft sebelum SAVE | HOST_PASS | audit C12 | Edit setelah GENERATE menghapus model lama dan menolak SAVE stale. |
| S01 | START valid | HOST_PASS | workflow.cpp | START membekukan model/waktu/suhu awal dan satu Day0. |
| S02 | START tanpa kanal valid atau jam invalid | HOST_PASS | audit C06 | Tanpa sensor/jam valid tidak membuat sesi palsu. |
| S03 | Suhu kanal0C valid | HOST_PASS | math_cases.cpp | Suhu0C valid; average hanya kanal valid, operasional satu desimal sesuai sumber. |
| S04 | Satu/dua/tiga valid | HOST_PASS | math_cases.cpp | Suhu0C valid; average hanya kanal valid, operasional satu desimal sesuai sumber. |
| S05 | No valid/stale | HOST_PASS | audit A04,A05,A07,A16; workflow.cpp | No sensor/stale/unavailable ditandai sebagai gap, tanpa data random. |
| S06 | BACK/forward/redraw/reset HMI | HOST_PASS | audit C13; workflow.cpp | Redraw/reset panel tidak memulai ulang sesi. |
| S07 | START kedua saat sesi aktif | HOST_PASS | workflow.cpp | START kedua perlu confirm dan penolakan mempertahankan sesi. |
| S08 | Edit checkpoint suhu/jam | HOST_PASS | audit C17 | Edit suhu/jam checkpoint melakukan replay dan invalidasi preview. |
| S09 | Edit Day0 | PARTIAL | audit C17; editCheckpoint | Perubahan suhu awal ada; koreksi waktu Day0 terhadap anchor akuisisi live belum diterima end-to-end. |
| S10 | NEXT dengan hanya Day0 | HOST_PASS | workflow.cpp; audit C05 | NEXT mengunci waktu checkpoint; Day0 saja M0, tanpa liveM dari waktu lain. |
| S11 | NEXT saat waktu sekarang >checkpoint | HOST_PASS | workflow.cpp; audit C05 | NEXT mengunci waktu checkpoint; Day0 saja M0, tanpa liveM dari waktu lain. |
| S12 | SAVE RESULT lalu History | HOST_PASS | workflow.cpp; audit A19,C19 | History dibuat setelah commit, sensor NEXT dibekukan, history terpilih. |
| S13 | Hapus/ganti baseline sesudah result | HOST_PASS | full_reference_workflow | History identik sesudah restart dan penghapusan logis baseline. |
| S14 | Record import tanpa snapshot | PARTIAL | model/checkpointResult | Tidak ada lookup by-name; jalur import legacy/incomplete belum lengkap. |
| S15 | Produksi ADD DAY | HOST_PASS | audit A22; full_reference_workflow | ADD memakai sensor/waktu saat ini dan day eksplisit; future observation ditolak. |
| T01 | Pour23:30, Day0 clock00:00 | HOST_PASS | tests.cpp | Pour23:30→Day0 clock00:00 =0.5h. |
| T02 | Pour23:30, Day1 clock00:00 | HOST_PASS | math_cases.cpp | Pour23:30→Day1 clock00:00 =24.5h. |
| T03 | Calendar tanggal mustahil | HOST_PASS | math_cases.cpp; audit A36 | Tanggal mustahil dan jadwal di luar range ditolak/unavailable. |
| T04 | Clock rollback/forward saat aktif | PARTIAL | audit A17,A18; markGap | Discontinuity menghasilkan gap terurut; event cause RTC terpisah belum lengkap. |
| T05 | Loop stall1.7detik | HOST_PASS | audit C16 | Stall1.7detik memakai delta sampel sebenarnya. |
| T06 | Counter monotonic rollover | HOST_PASS | audit C20; math_cases.cpp | Acquisition dan freshness lolos rollover uint32. |
| T07 | Restart dengan gap | HOST_PASS | workflow.cpp; audit A04,A18 | Restart mengembalikan committed record dan menandai gap yang belum selesai. |
| T08 | Urutan day dan timestamp bertentangan | HOST_PASS | audit C21 | Day/waktu bertentangan ditolak sebelum model/checkpoint baru diterima. |
| W01 | Codec all fields roundtrip | PARTIAL | workflow.cpp; full_reference_workflow; audit A15,A23,A24 | Codec/replay/snapshot diuji, belum roundtrip setiap field/nilai ekstrem schema secara terpisah. |
| W02 | Tail file terpotong tiap offset penting | PARTIAL | workflow failures; audit A38,C14 | 100byte-budget transaksi scalar dan committed corruption diuji; belum setiap offset transaksi baseline/result besar. |
| W03 | CRC/length/schema invalid | PARTIAL | workflow corruptionAndTime; audit A38 | Guard CRC/length/flag/finite ada; kombinasi schema/length rusak belum seluruhnya menjadi executable test. |
| W04 | Putus pada setiap langkah commit | PARTIAL | workflow failures | Atomicity transaksi kecil diuji host; seluruh tahap baseline/result dan daya SD fisik belum diterima. |
| W05 | Metadata/index hilang | NOT_IMPLEMENTED | storage/Journal | Index disk, metadata A/B dan rebuild index belum diimplementasikan. |
| W06 | SD absent/full/remove during save | PARTIAL | workflow failures; audit A27,C19 | Absent/full/sync/rescan host tersedia; remove/reinsert media fisik belum diuji. |
| W07 | Commit sukses, ACK hilang, retry | HOST_PASS | workflow.cpp | Operation ID durable dan retry SAVE RESULT tidak membuat duplikat. |
| W08 | autoSave false | HOST_PASS | audit A19,A43,C19; workflow.cpp | AutoSave default false; manual SAVE tetap commit dan periodic recovery dapat diaktifkan eksplisit. |
| W09 | Banyak history/checkpoint | PARTIAL | StoredRows,nextPoint,Journal | RAM tidak berupa array seluruh database; index/latency/volume history besar belum lulus. |
| W10 | First boot/reboot | HOST_PASS | workflow cold boot | Cold boot/reboot tidak memasukkan demo seeds. |
| H01 | Frame satu byte per tick, terpecah | HOST_PASS | workflow protocol; Parser | Parser incremental/fragment/timeout dan TX credit terbatas diuji. |
| H02 | Dua frame sekaligus | HOST_PASS | audit A44 | Frame terkoalesensi mendapat respons berurutan; stale command kedua diberi ACK penolakan. |
| H03 | Overflow, noise, field count salah | HOST_PASS | workflow protocol; audit A08,A09 | Overflow/noise/arity dan recovery delimiter diuji. |
| H04 | Stale view/page/token | HOST_PASS | audit C11,A12,A26,A28 | View/page/boot/operation melindungi mutasi; BACK tidak bergantung view data lama. |
| H05 | Sensor refresh tinggi + rapid BACK | PARTIAL | audit A10,A13,A39,A44 | Refresh/ACK correlation diperbaiki; burst nyata dan starvation selama operasi SD besar belum lulus. |
| H06 | Reset panel saat active/save | HOST_PASS | audit A11,A12,C13 | PAGE_READY/reset panel mempertahankan ACK dan sesi aktif di host. |
| H07 | Reset MCU saat ACK hilang | PARTIAL | workflow durable retries | Repository replay lintas reboot diuji; full UART reset MCU tepat sesudah commit belum diuji. |
| H08 | Model/versi protokol mismatch | PARTIAL | audit A32; HmiContractVersion=2 | Contract mismatch ditolak; identitas/model panel belum diketahui. |
| H09 | Actual SEN/ADD bytes | HARDWARE_PENDING | hmi/events | Belum ada capture byte panel pasangan; LF snippet bukan bukti UART fisik. |
| H10 | Native panel response bercampur | HOST_PASS | audit C18 | Native touch/string response sintetis tidak menjadi AppCommand. |
| U01 | Seluruh 17 halaman | PARTIAL | hmi/manifest.json; Controller | 17page dan197event tersedia; acceptance visual seluruh panel belum ada. |
| U02 | Save gagal | HOST_PASS | audit C19 | SAVE gagal mempertahankan page; tidak membuat history palsu; BACK/retry berhasil. |
| U03 | Font/unit/desimal/nama panjang | HARDWARE_PENDING | hmi/README.md | Font/unit/desimal/nama panjang/layout belum dibuktikan pada panel pasangan. |
| U04 | Datum/keyboard/date modal cancel | NOT_IMPLEMENTED | hmi apply_* events | Keyboard/date/datum/modal/Cancel visual belum dirakit; Apply saja belum memenuhi U04. |
| U05 | Empty baseline/history | HOST_PASS | workflow cold boot/new baseline | Empty baseline/history dapat memulai flow tanpa seed. |
| U06 | Chart dan hasil dataset sama | NOT_IMPLEMENTED | core/Chart.h | Renderer panel lab points/axis/kurva dan acceptance terhadap React belum lengkap. |
| U07 | Settings brightness/sound/interval | PARTIAL | audit A20,A31,C04 | Port settings dan rollback commit gagal diuji; efek fisik driver belum terverifikasi. |
| U08 | Battery/splash/deviceInfo | PARTIAL | DevicePort; BoardBinding gate | Tidak ada battery87%/random/sukses palsu; baterai dan splash panel nyata belum selesai. |
| P01 | Build target | FAIL | releases/avr-capacity.json | Flash lengkap melebihi ATmega328P; BoardBinding produksi belum tersedia. |
| P02 | RAM/stack/buffers bersama | FAIL | releases/avr-capacity.json; avr-stack.json | Margin stack bersama driver/interrupt belum dibuktikan; SRAM statis saja bukan kelulusan. |
| P03 | Storage latency dan UART traffic | PARTIAL | Journal get/StoredRows; Transport poll | Full scan/GENERATE/SAVE masih sinkron; worst-case latency dan prioritas layanan belum memenuhi gate produksi. |
| P04 | Soak run dan power cycle | HARDWARE_PENDING | releases/status.json | Belum ada soak/power cycle perangkat fisik; day26 virtual bukan run26hari. |

Teks acceptance asli juga ada pada [CSV](coverage.csv) dan [JSON](coverage.json). Source acuan tidak diubah.
