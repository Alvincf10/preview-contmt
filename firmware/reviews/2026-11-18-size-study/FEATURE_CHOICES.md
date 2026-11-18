# Kandidat penyederhanaan fitur ConMT

Status: bahan keputusan pengguna. **Tidak ada fitur produksi yang dihapus.** Angka di bawah berasal dari build salinan terpisah dengan fitur sengaja dinonaktifkan untuk mengukur dampak linker. Salinan tersebut bukan firmware yang dapat dipakai atau di-flash.

## Hasil utama

Firmware dengan seluruh fitur saat ini memakai **74.618 byte** pada probe, sementara batas ATmega328P32.768byte. Kekurangannya **41.850byte**. Bahkan gabungan seluruh kandidat di bawah masih memakai **61.754byte**, atau **28.986byte di atas batas**.

Jadi, kandidat yang diukur belum cukup untuk membuat implementasi sekarang muat. Angka ini bukan batas minimum matematis bagi semua kemungkinan desain; restrukturisasi implementasi masih dapat mengubah hasilnya.

## Fitur tambahan yang paling layak ditinjau dahulu

| Prioritas kaji | Kandidat | Penghematan terukur | Konsekuensi jika kelak disetujui |
|---|---|---:|---|
|1|Metadata material: semen, air, agregat, admixture, merek dan tampilan W/C|220byte|Informasi komposisi di alat berkurang. Dalam acuan ConMT, metadata ini tidak langsung masuk rumus fit/FKZ/Fc. Tetap berguna untuk dokumentasi campuran.|
|2|Shortcut tabel lab: membuat kerangka baris awal dan mengambil suhu sensor ke row lab|870byte|Operator membuat baris dan mengisi suhu lab secara manual. Pembacaan sensor pengujian tetap diperlukan. `fillEarly` membuat kerangka waktu, bukan suhu contoh.|
|3|Penampil daftar/detail history pada layar|416byte|Penyimpanan hasil dan snapshot di SD tetap dipertahankan dalam percobaan. Pembacaan riwayat dipindah ke sarana lain; reader/exporter dan alur sesudah SAVE harus dibuat terlebih dahulu.|
|4|Editor settings di layar|898byte|Menu interval, brightness, sound dan autoSave tidak dapat diedit lewat layar. Konfigurasi yang aman harus disediakan melalui mekanisme lain. Penghematan ini untuk seluruh editor, bukan hanya buzzer/brightness.|

Dasar penilaian material: [MaterialDataScreen](../../../src/screens.tsx) menampilkan water/cement, sedangkan [maturityFit.ts](../../../src/maturityFit.ts) menghitung M, regresi dan FKZ dari suhu/waktu/data lab. Tidak ada alasan matematis untuk menghilangkan fitur inti karena metadata bahan dihilangkan. Namun, nilai dokumentasinya tetap perlu dinilai bersama klien.

## Opsi lebih besar yang mengubah cara kerja

Saya tidak menganggap dua opsi ini sekadar fitur tidak penting. Keduanya mengubah flow yang sebelumnya diminta dan memerlukan persetujuan baru.

| Kandidat | Penghematan terukur | Konsekuensi |
|---|---:|---|
|Editor checkpoint manual beserta rekonsiliasi gap manual|2.554byte|Koreksi day/tanggal/jam/suhu dan penyelesaian gap melalui observasi manual hilang. Deteksi gap tetap diperlukan. Pengujian dengan gap dapat memerlukan sesi baru atau mekanisme koreksi lain.|
|Pembuatan/edit/generate/save baseline dari alat|8.364byte|Baseline dipersiapkan di luar alat dan dimasukkan sebagai profil tervalidasi. Importer, pemeriksaan profil dan flow HMI penggantinya belum termasuk ukuran percobaan. Baseline harus membawa data kalibrasi lengkap yang diperlukan FKZ, bukan asal menyalin koefisien atau memakai data contoh.|

Opsi baseline eksternal melonggarkan aturan sebelumnya tentang seluruh proses pembuatan model di MCU. Perhitungan operasional M/FKZ/Fc tetap harus mengikuti acuan dan memakai maturitas pengujian saat ini. Belum ada perubahan tersebut pada source produksi.

## Rincian ukuran percobaan

| Varian salinan | Flash | Selisih terhadap seluruh fitur |
|---|---:|---:|
|Seluruh fitur|74.618|0|
|Tanpa shortcut lab|73.748|870|
|Tanpa metadata material|74.398|220|
|Tanpa editor checkpoint/rekonsiliasi manual|72.064|2.554|
|Tanpa penampil history|74.202|416|
|Tanpa editor settings|73.720|898|
|Tanpa pembuatan baseline pada alat|66.254|8.364|
|Gabungan seluruh kandidat|61.754|12.864|

Penghematan tiap baris **tidak boleh dijumlahkan** karena ada kode bersama dan pengaruh LTO. Gabungan diukur secara tersendiri. Pengukuran belum memasukkan biaya workflow pengganti, driver sensor/clock terverifikasi dan pipeline chart final. Varian yang sengaja tidak lengkap tidak menjalani acceptance fungsional sebagai produk.

## Yang tidak layak dipangkas untuk mengejar angka

- Rumus Nurse–Saul, regresi, FKZ tiga cabang, lookup hari berikutnya dan presisi numerik.
- Akuisisi suhu nyata, status sensor/clock/baterai yang jujur dan deteksi gap.
- SAVE yang benar, CRC/readback, recovery, snapshot immutable dan perlindungan retry agar tidak menggandakan hasil.

Menghapus file React, dokumen, test, Excel atau menggabungkan seluruh C++ menjadi satu `.ino` tidak mengurangi image MCU apabila file tersebut memang tidak tertaut. Gambar/font HMI disimpan di panel Nextion. Pipeline chart lengkap belum masuk probe sekarang, sehingga menghapusnya belum memberi penghematan pada angka saat ini.

Pilihan awal yang paling ringan secara fungsi adalah metadata material dan shortcut lab. Keduanya memberi penghematan kecil. Menghapus fitur kecil saja belum menyelesaikan defisit flash; daftar ini tidak merupakan rekomendasi menghapus seluruh kandidat.

Bukti mesin: [feature-sizes.json](feature-sizes.json). Script reproduksi: [feature_study.py](../../tools/feature_study.py). Hash source produksi sebelum/sesudah studi identik; tidak ada penghapusan fitur pada `ConMT/src`.
