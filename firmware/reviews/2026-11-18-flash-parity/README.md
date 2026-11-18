# Optimasi flash ConMT dan pemeriksaan regresi

Pembandingnya adalah `main` pada `ded9b7d`. Implementasi ada di `optimize/conmt-flash-parity`, dengan tiga commit yang mempertahankan kontrak CM1, 17 halaman, schema1 dan rumus ConMT.

| Checkpoint | Commit | Flash | Delta flash | SRAM statis |
|---|---|---:|---:|---:|
| Pembanding | `ded9b7d` | 74.618 | | 1.532 |
| Dispatch CM1 dan retry | `4d30fff` | 74.558 | −60 | 1.532 |
| Pembaca jurnal bersama | `85a64da` | 74.164 | −394 | 1.532 |
| Formatter dan penghitung RX | `8932004` | 74.082 | −82 | 1.531 |
| Penghematan total | | | **536** | **1** |

Angka dalam byte menggunakan probe, toolchain dan flags yang sama. Link pada region fisik ATmega328P gagal. Probe memakai SD, indeks, UART dan baterai nyata serta port pengukuran untuk sensor, RTC, brightness dan sound. Chart panel final juga masih di luar pengukuran. [Pengukuran flash](../../releases/avr-capacity.json), [atribusi simbol](../../releases/size-breakdown.json)

## Perubahan yang dipertahankan

- Transport meneruskan perintah yang sudah diterjemahkan dan status boot/page/view ke satu dispatcher. Retry yang tersimpan tetap dipulihkan sebelum penolakan berdasarkan boot atau view. ACK memakai boot dan sequence asal. Pengecekan opID saat memulai transaksi baru tetap aktif. Pada simulasi retry `BASE_SAVE` setelah reset sebelum ACK, jumlah panggilan baca jurnal turun dari 278 ke 139 tanpa indeks, dan dari 92 ke 46 dengan indeks. Jumlah baca indeks turun dari 4 ke 2. Angka ini berasal dari satu eksekusi `poll` pada storage host. Byte jurnal dan sequence tetap sama selama retry. [Uji baseline dan hasil](../../tests/session_edges.cpp)
- Pencarian field, opID dan ID terbesar memakai satu loop verifikasi transaksi dengan jalur indeks dan fallback. Validasi panjang header record dipakai bersama oleh lookup, verifikasi CRC dan rebuild indeks. Rebuild memakai opID yang sudah diverifikasi. Susunan byte schema1, pembedaan korupsi dari tail parsial, serta read-back sebelum dan sesudah footer commit tetap diuji. [Jurnal](../../ConMT/src/storage/Journal.cpp), [uji indeks](../../tests/disk_index.cpp), [uji record](../../tests/record_codec.cpp)
- Tampilan tanggal atau jam membentuk satu keluaran langsung, dan stamp history memakai kombinasi yang sama. Format koefisien mempertahankan pembulatan serta tampilan nol lama dengan memeriksa hasil formatnya. Penghitung RX memakai satu byte karena indeksnya berada dalam buffer 192 byte. Tes mengirim 191 karakter data yang valid dan menguji penolakan saat satu karakter melebihi kapasitas. [Uji teks](../../tests/text.cpp), [uji parser UART](../../tests/workflow.cpp)

## Estimasi stack

| Frame non-LTO | Pembanding | Revisi |
|---|---:|---:|
| `Transport::accept` | 48 | 40 |
| Dispatcher pada jalur UART | 55 | 52 |
| `Transport::renderField` | 63 | 25 |
| Helper jam panel | | 25 |
| `calendarText` | 38 | 34 |
| `Journal::verify` | 68 | 68 |

Jalur berindeks memakai frame bersama yang lebih besar. Estimasi jumlah frame untuk pencarian field berindeks sampai `verify` berubah dari 136 menjadi 177 byte, sedangkan fallback scan turun dari 207 menjadi 177 byte karena satu loop. Varian jurnal 74.134 byte memiliki frame lookup dan scan yang sama-sama aktif saat fallback. Varian 74.164 byte dipilih demi batas frame yang lebih rendah. Estimasi ini mencakup fungsi yang disebut dan masih memerlukan validasi stack bersarang bersama driver serta interrupt. SRAM statis menyisakan 517 byte sebelum stack. [Laporan frame AVR](../../releases/avr-stack.json)

## Validasi acuan dan perilaku

- Seluruh 15 suite lulus pada host64, host32 dan ASan/UBSan. Jejak 300 baris per presisi identik dengan `ded9b7d`, termasuk 120 skenario write terputus, status, navigasi, ID dan CRC byte jurnal. Edit baseline → Generate → Save → reset → retry lulus dengan dan tanpa indeks. Retry simpan hasil juga lulus.
- Snapshot keluaran UART 17 halaman tetap identik, dengan SHA-256 `13126308db2e5e367bd83b9fbf99dcd57f778840cdf0cd5cf24b5e3a211d6812`. Fixture dan sumber Nextion tetap sama dengan `main`. [Fixture UART](../../tests/fixtures/hmi-wire.txt)
- Uji AVR lulus pada dua dataset 41 baris serta 620 kasus presisi codec. Berkas matematika dan fixture FKZ sama dengan `main`. [Uji numerik AVR](../../releases/avr-numeric.json), [uji presisi AVR](../../releases/avr-precision.json)
- Verifikator plan melaporkan satu hash berbeda pada `.gitignore`. Isinya identik dengan `main` dan selisih sudah ada sebelum optimasi. Sebanyak 137 berkas referensi lainnya serta kedua referensi klien cocok dengan hash manifest.

## Keputusan kapasitas

Probe penuh masih melebihi batas fisik sebesar **41.314 byte** dan target engineering sebesar **43.362 byte**. Subset diagnostik SD/I/O, matematika/codec dan storage, diukur dengan skenario yang sama dari kedua commit, turun dari 42.642 ke 42.208 byte. Subset ini membantu memperkirakan skala pekerjaan dan biaya antar-subset dipengaruhi LTO. Penghematan ratusan byte mendukung mempertahankan perubahan yang teruji, dengan keputusan desain ukuran selanjutnya tetap membutuhkan percobaan tingkat arsitektur.

Preprocessor sketch produksi berhenti karena `BoardBinding.h` yang terverifikasi belum tersedia. Pemasangan fisik, latency dan watermark stack masih terbuka. Status 24 acceptance yang belum lengkap tetap berlaku. Seluruh uji memakai host atau emulasi AVR. [Status produksi](../../releases/STATUS.md)
