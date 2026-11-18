# Traceability implementasi

| Kebutuhan | Sumber | Implementasi | Bukti / status |
|---|---|---|---|
|Nurse–Saul/log/R2/FKZ|src/maturityFit.ts, Excel|core/Math|Dua fixture41row pada host64/host32 dan AVR emulator PASS|
|Parser/zero/missing/calendar|screens.tsx, D18|core/Types, Calendar|Unit tests PASS; driver-range belum diketahui|
|Baseline save/copy/delete/back|screens.tsx baseline flow|app/Controller|Workflow save-as-new/reopen/delete/min3/draft missing PASS|
|START/NEXT/result/history|screens.tsx realtime/result|app/Controller|Checkpoint waktu terkunci, save/restart/snapshot PASS|
|Storage integrity/recovery|arsitektur09|storage/Journal, Repository|100power-cut byte budgets, CRC corrupt, sync failure, absent/full PASS host|
|SD produksi|dokumen07|board/SdStorage|Compile AVR SDK berhasil; media fisik belum diuji|
|UART protocol|kontrakHMI02|hmi/Transport|Parser/overflow/handshake/retry durable PASS host; capture panel pending|
|HMI17page|project.json/React|hmi/manifest + events|197snippet tersedia; layout/keyboard/font/chart/TFT pending|
|Sensor/RTC/battery|dokumen07|port contracts + required BoardBinding|Belum ada identitas/rangkaian; driver belum selesai|
|Gap/settings|D04–D10|Controller policies|Stale/gap/suspended tested; reconciliation field coverage/endurance pending|
|Chart|components.tsx|core/Chart.h|Sampler tersedia; renderer panel pending|
|Bounded memory/performance|arsitektur10|streaming/fixed buffers/flash strings|Tidak ada array seluruh data di MCU; latency besar/index disk pending|
|Target capacity|dokumen07|AVR size probe|FAIL: flash79.884byte; RAM statis1.685byte; stack belum diterima|
|Production release|P7–P9|ConMT.ino + board gate|Belum lulus, tidak ada HEX produksi atau flash perangkat|

Tabel ini bukan klaim seluruh102acceptance scenario sudah dieksekusi. Detail command dan log test tersimpan di releases.

Audit17November2026: [matriks per102ID](reviews/2026-11-16-audit/coverage.md) menggantikan asumsi bahwa semua acceptance selesai. [38koreksi](reviews/2026-11-16-audit/defects.md) mempunyai reproduksi sebelum/sesudah. Enam suite dan65kasus audit lulus pada tiga konfigurasi host; status produksi tetap gagal.

Pembaruan17November setelah snapshot0b55090: driver baterai dan index/rebuild SD sudah diimplementasikan,9suite host lulus. Status terkini dan batas W05/W09/U08 berada pada [lanjutan audit](reviews/2026-11-17-production/README.md); tabel awal di atas adalah kondisi audit sebelumnya.

Current Sol handoff supersedes the historical resource figures above:80,748flash /1,582static SRAM,10CTest suites on each host profile, operation-ID index and17page wire snapshot.28acceptance scenarios remain incomplete; see [handoff](reviews/2026-11-17-handoff/README.md).

Current continuation from0e45cb1:78,274flash /1,502static SRAM;12CTest suites pass on host64/host32/sanitizer. S09/T04/H07 now have executable host acceptance;76HOST_PASS and1EMULATED_PASS leave25scenarios incomplete. Shared presenter/controller/index traversal and streamed TX are implemented; O0–O5, capacity, bounded storage, driver/HMI and physical release remain incomplete. [Current review](reviews/2026-11-17-optimization/README.md).

Current flash-fit continuation from520a74f supersedes those historical figures:75,414flash /1,502static SRAM.15suites pass on each host profile, including wire-compatible streaming record codecs,800multi-record cuts and executable checkpoint comparison. W01all-field/native-extreme roundtrip is HOST_PASS;77HOST_PASS and1EMULATED_PASS leave24scenarios incomplete. P0/P1/P2/P5 are partly implemented; P3bounded jobs/cursors, P4schema evaluation, P6stack/full driver link and hardware/HMI gates remain open. [Current review](reviews/2026-11-17-flash-fit/README.md).

18November update supersedes resource figures above:74,618flash/1,532static SRAM using the strengthened sensor/time probe. The previous source is75,554/1,532under the same probe, establishing936bytes of further code savings.15suites and AVR precision/replay pass; acceptance counts remain77HOST_PASS/1EMULATED_PASS with24incomplete. No features were removed. [Current review and feature study](reviews/2026-11-18-size-study/README.md).
