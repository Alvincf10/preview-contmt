# Implementasi ConMT

**Status: implementasi C++ sudah berjalan pada host; target produksi ATmega328P belum dapat dirilis.** Resource probe lengkap masih melebihi flash dan ruang stack belum cukup. Lihat [STATUS.md](releases/STATUS.md) dan [audit terhadap102skenario](reviews/2026-11-16-audit/README.md). Ini bukan paket firmware siap upload.

Kode domain, controller, repository dan transport dipakai bersama oleh host dan Arduino. Driver SD dan HardwareSerial nyata tersedia. Sensor/RTC/baterai belum dapat dipilih karena identitas/rangkaian tidak didefinisikan sumber. Production build memerlukan [profil board](BOARD_PROFILE_REQUIRED.md) dan tidak mempunyai fallback ke fake ports.

## Yang sudah dibuat

- Nurse–Saul, regresi ln, R2, FKZ bersyarat dan next-day lookup, prediction trace, calendar dan parsing ketat.
- Baseline draft/edit/generate/save-as-new, pemilihan, hapus logis, rows dengan ID stabil dan viewport.
- START, suhu awal, checkpoint bertanggal, edit/replay, NEXT, SAVE RESULT dan snapshot riwayat.
- Journal CRC transactional, commit/readback, retry operation ID, penanganan tail terpotong, full/absent/error, recovery sesi dengan gap.
- CM1 parser bounded, token/view validation, handshake, update Nextion bertahap, acknowledgement setelah commit dan refresh sensor/status tanpa mengirim ulang tabel lengkap tiap detik.
- [Manifest HMI](hmi/manifest.json) untuk17page dan197snippet event. Layout/keyboard/chart panel dan compile HMI/TFT masih pending.
- [Driver SD](ConMT/src/board/SdStorage.cpp) low-level FAT16/32 menggunakan SDK SD1.3.0; read/write/seek/truncate/sync mengembalikan status nyata.

## Build dan uji komputer

~~~sh
cmake -S firmware -B firmware/build-host -DCONMT_PROFILE=HOST
cmake --build firmware/build-host
ctest --test-dir firmware/build-host --output-on-failure
~~~

Untuk pemeriksaan binary32 pada host:
~~~sh
cmake -S firmware -B firmware/build-float -DCONMT_REAL32=ON
cmake --build firmware/build-float
ctest --test-dir firmware/build-float --output-on-failure
~~~

Untuk AddressSanitizer/UndefinedBehaviorSanitizer tambahkan -DCONMT_SANITIZE=ON pada build terpisah.

Enam suite test memeriksa core/codec, seluruh row dua fixture oracle, serta workflow/recovery/protocol. Fault test memakai100batas byte penulisan terputus; ini bukan100uji listrik fisik. Matriks102skenario pada plan belum seluruhnya menjadi acceptance test perangkat.

## Menjalankan controller melalui terminal

~~~sh
firmware/build-host/conmt_sim /private/tmp/conmt-session.jrn
~~~

Masukkan command domain, misalnya FIELD_SET operator OP-1, FIELD_SET project ProyekA, FIELD_SET date 2026-11-16, USER_SAVE, NAV 3, BASE_NEW. ADVANCE dan SENSOR hanya command runner host untuk menyuplai clock/sensor test; tidak ada di protokol produksi. Gunakan lokasi file baru untuk cold boot. Tidak ada baseline contoh otomatis.

## Bukti numerik AVR dan ukuran

Tooling lokal yang ditemukan kembali di diagnosis_beton/build_firmware_original digunakan hanya sebagai compiler/SDK, bukan kode aplikasi/formula lama.

~~~sh
python3 firmware/tools/avr_numeric.py
python3 firmware/tools/avr_capacity.py
~~~

Numeric probe memakai AVR GCC dan simavr pada ATmega328P; hasilnya di releases/avr-numeric.json. Capacity probe mengompilasi core/controller/presenter/SD/HardwareSerial lengkap, dengan clock/sensor/device ports pengukuran khusus. ELF CAPACITY_ONLY bukan firmware mesin. Saat linker melaporkan overflow, script membuat ELF dengan region diperbesar hanya agar besar overflow dapat dihitung; target mesin tidak diganti dan hasil tidak bisa di-upload ke328P.

[Firmware Arduino entry](ConMT/ConMT.ino) sengaja menolak build tanpa konfigurasi board. Programmer tetap USBasp; tidak ada flash, fuse write atau erase dalam pekerjaan ini.

## Batas yang belum ditutup

- Flash penuh melebihi32KB; status ini harus diselesaikan lewat implementasi yang lebih ringkas sambil mempertahankan fitur/rumus. Menghapus fitur atau mengganti MCU belum diizinkan.
- SRAM statis saja belum memasukkan semua driver nyata; nested stack membutuhkan lebih dari margin saat ini.
- BoardBinding sensor/RTC/baterai/pin/baud/clock belum tersedia.
- HMI/TFT belum dikompilasi; snippet Apply dihubungkan ke keyboard/modal Editor. Chart core tersedia tetapi renderer panel belum lengkap.
- Index disk dan pengukuran latency dataset besar belum tersedia. Full journal scan tidak boleh dianggap memenuhi respons UI di mesin.
- Automatic day assignment, endurance media dan uji daya/hardware belum selesai.

Jangan menyatakan production-ready atau semua acceptance selesai berdasarkan host tests. [Traceability](requirements.md) memisahkan bukti yang ada dari pekerjaan tersisa.

## Hasil audit17November2026

38cacat direproduksi dan dikoreksi, dengan65kasus audit PASS pada host64/host32/sanitizer. Daftar lengkap beserta bukti sebelum/sesudah ada pada [defects.md](reviews/2026-11-16-audit/defects.md). Manifest/event menggunakan CM1 contract2; panel pasangan wajib memakai revision yang sama.

Build lengkap saat ini memerlukan79.884byte flash dan1.685byte RAM statis, sehingga belum muat pada ATmega328P. [Matriks102skenario](reviews/2026-11-16-audit/coverage.md) mencatat73HOST_PASS,1EMULATED_PASS dan28skenario parsial/belum lulus. Source ini belum boleh diperlakukan sebagai release mesin.
