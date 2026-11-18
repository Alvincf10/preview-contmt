# Uji kapasitas penyimpanan ConMT tanpa perangkat

Pengukuran memakai branch `optimize/conmt-flash-parity`, dengan `f7aea07` sebagai pembanding dan `7e8daa1` sebagai implementasi teruji. Kedua build memakai toolchain AVR, profil ATmega328P, dan skenario link diagnostik yang sama.

| Pengukuran | Sebelum | Sesudah | Hemat |
|---|---:|---:|---:|
| Flash SD, matematika, codec, dan penyimpanan | 42.208 | 41.606 | 602 |
| SRAM statis blok tersebut | 1.163 | 1.163 | 0 |
| Flash probe penuh | 74.082 | 73.394 | 688 |
| SRAM statis probe penuh | 1.531 | 1.531 | 0 |

Angka dalam byte. Probe penuh menautkan aplikasi, UART, baterai, dan adapter SD nyata. Konfigurasi board terverifikasi dan driver fisik yang masih terbuka belum masuk pengukuran. Link dengan region flash fisik gagal pada kedua build penuh. [Ukuran AVR](../../releases/avr-capacity.json), [atribusi simbol](../../releases/size-breakdown.json)

## Implementasi yang dipertahankan

- Jurnal memakai representasi kunci 10 byte yang sama untuk lookup nilai, opID, dan ID maksimum. Rebuild indeks meneruskan byte kunci dari entry schema1. Ini menghindari decode lalu encode ulang pada setiap entry.
- Baca dan tulis indeks memakai pencarian bucket dan rantai node yang sama. Layout indeks, CRC, verifikasi jurnal, fallback scan, dan urutan commit tetap mengikuti implementasi sebelumnya.
- Codec fixed-width menyalin byte integer 16, 32, dan 64 bit pada target little-endian. Jalur portabel mempertahankan urutan byte yang sama. Record bertipe dan scalar repository memakai mekanisme tersebut untuk identitas dan timestamp. Representasi binary64, teks manual, dan perhitungan ConMT tetap sama.

| Percobaan | Flash blok SD/matematika/storage | Flash probe penuh |
|---|---:|---:|
| Kunci dan pencarian indeks bersama | 41.920 | 73.688 |
| Tambah codec integer little-endian | 41.672 | 73.458 |
| Baca/salin langsung dan helper scalar | 41.672 | 73.520 |
| Rangkaian akhir, dengan `ValueReader`, helper scalar dan codec record | **41.606** | **73.394** |

Percobaan baca dan salin langsung menambah 62 byte pada probe penuh. `ValueReader` dipertahankan. Varian yang menyusun kunci di dalam lookup memakai 73.530 byte, sehingga representasi serial dari caller dipilih.

## Regresi dan stack

- Seluruh 15 suite lulus pada host64, host32, dan ASan/UBSan. Jejak 300 baris pada masing-masing presisi identik dengan `f7aea07`, termasuk byte jurnal, status dan 120 skenario write terputus. Uji indeks dan codec juga lulus ketika jalur byte portabel dipaksa pada salinan tes host.
- Dua dataset masing-masing 41 baris dan 620 kasus presisi lulus di emulasi AVR. Rumus, fixture acuan, dan sumber HMI identik dengan pembanding. Snapshot UART 17 halaman lulus dengan hash fixture yang sama. [Uji angka](../../releases/avr-numeric.json), [uji presisi](../../releases/avr-precision.json), [fixture UART](../../tests/fixtures/hmi-wire.txt)
- Estimasi frame non-LTO `findEntry` turun dari 91 ke 82 byte dan `indexTransaction` turun dari 84 ke 74 byte. `findOperation` naik dari 14 ke 33 byte. Jumlah frame `findOperation` dan `findEntry` naik 10 byte. `verify` tetap 68 byte. SRAM statis probe penuh menyisakan 517 byte sebelum stack dan interrupt. Pengukuran stack pada perangkat masih terbuka. [Estimasi frame AVR](../../releases/avr-stack.json)

## Hasil ambang kapasitas

Blok gabungan masih 20.614 byte di atas anggaran desain 20.992 byte. Subset diagnostik SD/I/O, matematika dan codec memakai **26.112 byte** tanpa jalur penyimpanan lengkap. Angka subset memakai link terpisah dan dipengaruhi LTO. Hasil ini menunjukkan biaya implementasi SD dan utilitas numerik perlu diturunkan bersama biaya penyimpanan untuk mengejar anggaran tersebut.

Probe penuh melampaui kapasitas ATmega328P sebesar **40.626 byte**. Gate ukuran untuk perluasan controller dan kesiapan flash belum lulus. Seluruh validasi dilakukan offline. Sensor, RTC, kompatibilitas panel, latency SD dan stack bersarang masih memerlukan profil board dan pengujian fisik. [Status rilis](../../releases/STATUS.md)
