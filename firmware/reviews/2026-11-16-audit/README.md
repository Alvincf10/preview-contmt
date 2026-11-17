# Audit implementasi ConMT — 16–17 November 2026

**Belum lulus sebagai firmware produksi ATmega328P.** Audit ini mengoreksi implementasi yang sudah ada, bukan mengganti plan dengan plan baru. Core, repository, workflow dan transport mempunyai kode nyata, tetapi ukuran target, driver yang belum teridentifikasi dan proyek HMI masih menghalangi rilis.

## Hasil yang dapat dibuktikan

- **38 cacat direproduksi dan dikoreksi:** 4 Kritikal, 17 Tinggi, 17 Sedang. [Daftar masalah dan koreksi](defects.md), [CSV](defects.csv), [JSON](defects.json).
- 65 kasus audit lulus pada host binary64, host binary32 serta AddressSanitizer/UndefinedBehaviorSanitizer. 38 dari kasus itu mempunyai FAIL sebelum koreksi; 27 lainnya kasus kontrol. Jangan menjumlahkan 65 sebagai 65 bug.
- Enam suite CTest lulus pada ketiga konfigurasi. Suite mencakup domain/storage, parity oracle, workflow/fault/HMI, audit regressions, workflow41row dan edge cases matematika.
- **102 skenario plan dipetakan satu per satu:** 73 HOST_PASS, 1 EMULATED_PASS, 20 PARTIAL, 3 NOT_IMPLEMENTED, 3 HARDWARE_PENDING, 2 FAIL. [Matriks lengkap](coverage.md), [CSV](coverage.csv), [JSON](coverage.json). HOST_PASS tidak berarti pengujian perangkat produksi selesai.
- Source asli138file dan dua referensi klien tetap cocok dengan hash acuan. Workbook enam sheet/2651cached cell serta fixture41row diperiksa; workbook tidak dihitung ulang oleh Excel. Bukti: [source](verify-source.json), [workbook](verify-workbook.json), [oracle TS](reference-ts.json).

## Kesesuaian rumus dan flow

Nurse–Saul memakai trapezoid dan clamp akumulasi sesudah setiap interval. Regresi memakai ln(M), a sebagai intercept dan b sebagai slope. FKZ mempunyai tiga cabang error, dan hari yang tidak tersedia mengambil faktor hari berikutnya, bukan mengganti M pengujian.

Dua fixture berbeda dibanding terpisah, masing-masing41titik. Full Excel Makhir33738.1425; preview rounded33738.7675. Koefisien, R2, M, Fc serta faktor dibanding pada setiap titik. Sel day3 Excel memakai faktor manual yang dibulatkan sehingga berbeda0.000620700083MPa dari TS penuh; algoritma umum tidak diubah untuk mengejar satu sel. Target30/35 tetap input, bukan konstanta global.

Workflow lengkap41row→GENERATE→SAVE→reopen→pengukuran day4/6/26→NEXT→SAVE RESULT→restart→delete baseline telah dijalankan. Faktor acuan5/7/28 dipakai pada M aktual4320/6960/28560. History tetap identik setelah baseline dihapus logis. Bukti angka: [workflow klien](reference-workflow.txt), [binary64](host-reference.json), [binary32](binary32-reference.json).

Presisi input lab manual dipertahankan pada tampilan dan reopen. Average sensor operasional tetap satu desimal menurut sumber ConMT. Result summary memakai M bulat; checkpoint memakai M raw. Tidak mengambil rumus atau kebijakan tampilan firmware lama.

Koreksi flow mencakup saved BACK, selection tersimpan, fallback sesudah delete, fokus row baru/viewport, edit slot Day0, snapshot sensor NEXT, larangan future observation, pemulihan gap, settings rollback dan default AutoSave=false dari dokumen06. Parser/presenter contract2 menangani korelasi boot/seq, stale view, render generation, reset panel, ACK, arity dan frame yang datang bersamaan.

## Kapasitas target: gagal

| Pengukuran | Flash | RAM statis | Status |
|---|---:|---:|---|
|Pembanding lama, ELF terakhir yang ditemukan|31.288byte|1.249byte|Hanya pembanding ukuran; kode aplikasi lama tidak menjadi acuan|
|Kode ConMT sekarang, flags baseline|80,708byte|1,693byte|Melebihi flash|
|Kode sama, merge constants + linker relax|79,884byte|1,685byte|Pilihan terkecil yang diukur, tetap gagal|
|Kode sama, small-function inline + relax|83,072byte|1,685byte|Lebih besar|

Merge/relax menghemat 824byte flash dan 8byte RAM terhadap flags baseline pada source yang sama. Flash masih lebih besar 47,116byte dari32768byte. Tidak mengganti MCU dan tidak menghapus fitur.

RAM statis menyisakan363byte sebelum semua driver nyata dan stack/interrupt. Estimasi compiler non-LTO menemukan frame prepareResult235byte dan checkpointResult205byte yang dapat bersarang. Ini menunjukkan kebutuhan optimasi stack; **bukan watermark LTO atau bukti runtime fisik**. Laporan: [kapasitas](../../releases/avr-capacity.json), [stack](../../releases/avr-stack.json).

Link pertama sekarang diberi region fisik32768/2048 secara eksplisit. AVR linker SDK tidak boleh dipercaya menyaring batas ini hanya dari -mmcu. Sesudah kegagalan link fisik, ELF dengan region diperbesar dibuat hanya untuk mengukur overflow. CAPACITY_ONLY.elf tidak dapat dipakai sebagai firmware328P dan tidak ada HEX produksi.

## Kewajiban yang belum tertutup

| Tingkat | Kewajiban | Kondisi kode saat ini |
|---|---|---|
|Kritikal|Flash dan SRAM/stack ATmega328P|Masih gagal kapasitas; perlu implementasi lebih ringkas tanpa menghapus kontrak|
|Kritikal|Respons sensor/menu saat data SD besar|Lookup CRC memindai seluruh journal; fit/copy/save masih sinkron; belum ada index disk atau jatah kerja menyeluruh|
|Tinggi|Sensor, RTC, baterai dan BoardBinding nyata|Identitas/pin/clock/baud/kalibrasi tidak tersedia dalam sumber yang diizinkan; hanya kontrak port dan gate produksi yang ada|
|Tinggi|HMI17page yang dapat digunakan|Manifest197event tersedia; keyboard/modal/font/layout/renderer chart dan HMI/TFT belum dirakit/dikompilasi|
|Tinggi|Recovery dan import lengkap|Atomicity transaksi kecil host ada; metadata A/B/index rebuild, importer incomplete dan fault setiap offset transaksi besar belum lengkap|
|Tinggi|Koreksi waktu dan gap menyeluruh|Gap bounds/suspend/replay diperbaiki; koreksi waktu Day0 terhadap anchor live dan event cause RTC belum diterima end-to-end|
|Tinggi|Integrasi perangkat|Capture UART pasangan, sensor/SD/power/battery test, soak dan worst-case timing belum dilaksanakan|

Interval dapat menyimpan sampel pemulihan tanpa mengarang label hari. Day checkpoint tetap input eksplisit sampai Automatic DayAssignmentPolicy ditetapkan; bukan otomatis mengambil suhu/jadwal lab. MAPE/CV/sertifikat kualitas yang memang didefer oleh D03 tidak dinyatakan sebagai fitur firmware yang sudah ada atau kewajiban yang diam-diam dihapus.

SD adapter FAT16/32 dan HardwareSerial benar-benar menggunakan API hardware. Keduanya belum membuktikan perifer mesin bekerja. Production .ino menolak build tanpa BoardBinding terverifikasi. FakeClock/RecordedSensor/MemoryStorage hanya berada pada host/test atau alat pengukuran kapasitas.

## Bukti yang disimpan

- Log *before*.txt: reproduksi sebelum masing-masing koreksi. [host-after](host-after.txt), [binary32-after](binary32-after.txt), [sanitizer-after](sanitizer-after.txt):65kasus sesudah koreksi.
- [Host CTest](../../releases/host-tests.txt), [binary32 CTest](../../releases/binary32-tests.txt), [sanitizer CTest](../../releases/sanitizer-tests.txt), [numerik AVR emulasi](../../releases/avr-numeric.json).
- [Environment](environment.txt), [status terstruktur](../../releases/status.json), [hash source sesudah audit](../../releases/source-sha256.json). Hash sebelum audit ada di before-sha256.json.

Tidak ada upload, erase atau fuse write pada audit ini. Status yang sah saat ini adalah **implementasi host diuji, firmware produksi belum selesai**.
