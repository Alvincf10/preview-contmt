# Kontrak firmware dan Nextion CM1

Firmware menyediakan nilai, kalkulasi, dan aksi untuk 17 halaman ConMT. Panel menentukan tata letak, memetakan kolom ke komponen, dan menggambar chart. Nama halaman mengikuti [proyek preview](../nextion/project.json). Baud awal 9600, 8 bit data, tanpa parity, 1 stop bit.

## Frame dan sinkronisasi

```text
CM1|boot|seq|page|view|verb|arg1|arg2<LF>
```

- Batas frame 192 byte termasuk LF. ASCII, dengan CR opsional tepat sebelum LF. Frame yang tak lengkap dibuang setelah 1,2 detik. Parameter teks menerima spasi dan melarang karakter kontrol, pipa, kutip ganda, dan backslash. Operator dan merek maksimum 32 karakter. Project dan nama baseline maksimum 64 karakter.
- Setiap halaman membutuhkan Number `nBoot`, `nView`, `nAckSeq`, `nAckCode`, `nAckValue`, dan Text `tData` dengan kapasitas sedikitnya 255 karakter. Firmware mengirim penugasan Nextion, `page <nama>`, atau `dim=<angka>`, masing-masing dengan tiga byte `FF`. Panel membaca `nAckSeq` sebagai penanda bahwa update respons selesai. `tData.txt` adalah nilai kolom berpemisah pipa. Data boleh memiliki kolom kosong, termasuk di awal dan di akhir.
- Saat boot, panel mengirim `CM1|0|0|0|0|PAGE_READY` dari `pInit`. Firmware menerbitkan `nBoot` dan `nView` lalu menerima `GET|status`. Lanjut ke `pUser` melalui `NAV|1`, atau `pMain` melalui `NAV|2` bila identitas telah disimpan. `nAckValue` saat READY berisi ID commit SD yang terbaca, atau 0 jika belum tersedia.
- Setiap perpindahan page diawali ACK pada halaman lama. Sesudah instruksi `page`, halaman baru mengirim `PAGE_READY` dengan ID halaman barunya. Saat panel terhubung ulang, READY dengan boot 0 memulai nomor urut koneksi lagi. Bila ID halaman berbeda, firmware mengirim halaman yang sedang aktif.
- Kirim satu frame per permintaan. Tunggu ACK dan gunakan `nView` terbaru untuk frame berikutnya. `seq` positif dan naik dalam koneksi sampai 2.147.483.647. Frame yang sama persis dengan `seq` terakhir boleh dikirim ulang pada halaman yang sama. Untuk SAVE dengan ACK hilang saat berpindah halaman atau reset, gunakan `RETRY` dengan revisi input yang sama.
- Saat AutoSave menerbitkan checkpoint, firmware memperbarui `nView`. Jika meminta halaman dengan data yang sudah berubah, baca ulang menggunakan `GET`. Untuk konfirmasi, simpan token pada `nAckValue`, lalu kirim `CONFIRM|token` atau `CANCEL|token` dengan versi tampilan yang sama. Buang dialog lama setelah perubahan `nView`.

## Halaman

| ID | Nextion | Aksi utama |
| --- | --- | --- |
| 0 | pInit | READY, status, lanjut ke identitas atau menu |
| 1 | pUser | Edit identitas, USER_SAVE |
| 2 | pMain | Menu baseline, kuat tekan, settings, perangkat, identitas |
| 3 | pBase | BASE_NEW, daftar tersimpan |
| 4 | pNewB | Edit nama, Fc target, datum, tanggal/jam mulai |
| 5 | pMat | Edit material, takaran dan merek. Baca W/C |
| 6 | pMatu | Edit tabel lab dan waktu mulai, sensor, jadwal, tambah, isi, hapus, generate |
| 7 | pBaseR | Baca model, chart, material dan identitas. BASE_SAVE |
| 8 | pSaveB | Daftar, pilih dan buka baseline sebagai draft, hapus |
| 9 | pKuat | Pilih baseline, lanjutkan sesi, atau buka riwayat |
| 10 | pSelB | Pilih baseline, lihat model, MEASURE_START/RESUME |
| 11 | pRT | Sensor, run, checkpoint, koreksi waktu/suhu/umur, NEXT |
| 12 | pStr | Review run pada revisi checkpoint akhir dan RESULT_SAVE |
| 13 | pHist | Daftar hasil dan HISTORY_PICK |
| 14 | pHistD | Detail hasil, identitas, model dan seluruh checkpoint |
| 15 | pSet | Interval HH:MM:SS, brightness, sound, AutoSave |
| 16 | pDev | Versi firmware, status SD, jam, kanal suhu dan tegangan |

Untuk naik/turun halaman gunakan `NAV|id`. Draft dari daftar `pSaveB` kembali ke halaman tersebut dari `pMatu`. Draft dari `pMat` kembali ke `pMat`. BACK dari `pRT` kembali ke `pSelB` dan sesi tetap dapat dilanjutkan. BACK dari `pStr` membuka kembali sesi.

## Perintah

Indeks baris dimulai dari 0. Panel dapat mengelompokkan enam baris per tampilan sesuai preview. Kirim indeks absolut, misalnya indeks 6 untuk slot pertama di tampilan kedua.

| Perintah | Parameter dan efek |
| --- | --- |
| `PAGE_READY` | Sinkronisasi halaman dan koneksi |
| `NAV\|id` | Pindah melalui jalur halaman yang sah |
| `FIELD_SET\|field\|value` | Edit identitas atau draft |
| `USER_SAVE` | Validasi identitas dan buka menu |
| `BASE_NEW` | Pertahankan isi draft, ambil konteks identitas dan waktu awal |
| `ROW_FOCUS\|i` | ACK memuat ID baris |
| `ROW_SET\|i\|field\|value` | Ubah baris lab dan urutkan hasil. Indeks 0 pada draft kosong membuat baris Day 0 dalam transaksi yang sama |
| `ROW_SENSOR\|i` | SENSOR pada keypad Temperature menyimpan rerata kanal yang valid ke baris yang sedang diedit. Indeks 0 pada draft kosong dapat menyimpan pembacaan pertama ke Day 0. Bila suhu belum tersedia, ACK 9 dan isian tetap |
| `ROW_SCHEDULE\|i` | Format `labrow` dengan tanggal/jam jadwal |
| `ROW_ADD_EARLY` | Tambah slot Day 0 berikutnya dari 0–6 jam. Nilai ACK adalah posisi baris baru mulai dari 1 |
| `ROW_FILL_EARLY` | Tambah slot Day 0 yang kosong tanpa mengganti data. Nilai ACK adalah posisi baris pertama yang ditambah, atau 0 bila semua slot sudah ada |
| `ROW_ADD_LAB` | Tambah hari lab positif yang berikutnya tersedia. Draft kosong menyimpan Day 0 kosong bersama hari baru dalam satu transaksi. Nilai ACK adalah posisi baris hari baru mulai dari 1 |
| `ROW_DELETE\|i` | Meminta konfirmasi. Tabel dipertahankan minimal tiga baris |
| `BASE_GENERATE` | Buka `pBaseR` setelah ada satu baris lengkap dengan Fc Lab positif dan semua baris lab yang mulai diisi lengkap. ACK 2 dengan nilai positif menunjukkan isian yang kurang. `nAckValue / 2` adalah posisi baris mulai dari 1, nilai genap untuk suhu dan ganjil untuk Fc Lab |
| `BASE_SAVE\|revision` | Simpan revisi hasil Generate dari `GET\|baseline`. Hasil tanpa model disimpan sebagai Draft. ACK memuat ID baseline tersimpan |
| `BASE_PICK\|id` | Pilih ID dari `savedrow` |
| `BASE_OPEN` | Buka baseline terpilih sebagai draft |
| `BASE_DELETE\|id` | Meminta konfirmasi hapus dari daftar |
| `MEASURE_START` | Mulai rekaman dari baseline terpilih dengan model valid. Draft harus dilengkapi hingga model tersedia. Sesi yang sedang aktif memerlukan konfirmasi |
| `MEASURE_RESUME` | Buka lagi sesi yang tersimpan |
| `CHECK_ADD` atau `CHECK_ADD\|day` | Catat suhu nyata pada jam perangkat. Opsional label hari |
| `CHECK_ADD\|day\|date\|clock\|temp` | Tambah observasi historis manual |
| `CHECK_SET\|i\|field\|value` | Koreksi checkpoint. Integral dihitung ulang memakai urutan waktu baru |
| `RESULT_PREPARE` | Bekukan revisi sesi dan buka hasil. ACK memuat revisi tersebut |
| `RESULT_SAVE\|revision` | Simpan hasil revisi yang sedang ditinjau dan buka riwayat |
| `HISTORY_PICK\|i` | Pilih baris riwayat berdasarkan indeks dari `historyrow` |
| `SETTINGS_SET\|field\|value` | Ubah dan simpan pengaturan |
| `SETTINGS_SAVE` | Kembali ke menu utama setelah pengaturan tersimpan |
| `CLOCK_SET\|date\|clock` | Simpan catatan koreksi waktu dan atur kalender lokal |
| `RETRY\|BASE_SAVE\|revision` atau `RETRY\|RESULT_SAVE\|revision` | Cari ID hasil commit yang sudah ada |
| `CONFIRM\|token`, `CANCEL\|token` | Selesaikan dialog yang masih aktif |
| `STORAGE_RETRY` | Coba mount SD lagi dan sinkronkan sesi |
| `GET\|source[\|i]` | Baca data tampilan tanpa mutasi |

### Field yang dapat diubah

- Identitas di `pUser` memakai `operator`, `project`, `date`. Draft di `pNewB` memakai `name`, `target`, `datum`, `pourDate`, `pourClock`. Datum menggunakan -20, -10, 0, atau 10 °C.
- Material di `pMat` memakai `cement`, `water`, `coarse`, `fine`, `retarder`, `accelerator`, `flyAsh`, `retarderBrand`, `acceleratorBrand`, `flyAshBrand`. Tiga merek boleh kosong. `pMatu` menerima `pourDate` dan `pourClock`.
- Lab memakai `day`, `clock`, `age`, `temp`, `fc`. `age` adalah jam relatif dan dapat ditulis dengan empat desimal. `clock` mengikuti tanggal/jam awal serta label hari. Temperatur atau Fc kosong mengosongkan nilai. Temperatur 0 °C adalah nilai valid.
- Checkpoint memakai `date`, `clock`, `timestamp`, `day`, `temp`. `timestamp` memberi tanggal dan waktu sekaligus dalam bentuk `YYYY-MM-DDTHH:MM:SS`. Kolom `gap` dengan nilai `0` menghapus penanda interval hilang sesudah titik tersebut dikoreksi secara manual. Konfirmasi operator sebaiknya menjelaskan bahwa kedua titik batas akan dipakai pada integral.
- Settings memakai `interval` dalam detik 0–86.399, atau `hour`, `minute`, `second`. `brightness` 0–100. `sound` dan `autoSave` memakai 0/1.
- Format tanggal `YYYY-MM-DD`, jam `HH:MM[:SS]`, dan desimal menggunakan titik. Label hari mendukung tiga angka desimal. Pengamatan suhu, angka uji tekan, dan material mendukung lima angka desimal yang tersimpan.

### Respons GET

Format `tData` berikut memiliki kolom berurutan dari kiri ke kanan. Tanggal dan jam adalah dua kolom. `settingsFlags` memuat sound pada bit 0 dan AutoSave pada bit 1.

| Sumber | Kolom `tData` |
| --- | --- |
| `status` | Tanggal perangkat, jam perangkat, Vin mV, baterai %, kode SD, revisi sesi aktif, interval, brightness, settingsFlags, versi firmware, S1, S2, S3, rerata, mask kanal valid, baseline terpilih, hasil terpilih, identitas siap, draft dari daftar, jumlah baseline |
| `identity` | Operator, project, tanggal identitas |
| `baseline`, `savedrow\|i` | Revisi/ID baseline, nama, target, datum, tanggal tuang, jam tuang, jumlah baris, ID model, ID identitas. `baseline` memakai pilihan di daftar, draft di editor, dan model sesi di halaman ukur/hasil |
| `mix` | Cement, water, coarse, fine, retarder, accelerator, flyAsh, tiga merek dalam urutan sama, W/C |
| `model` | a, b, R², jumlah pasangan, jumlah faktor, M lab maksimum, operator, project, tanggal identitas baseline. Jika model belum tersedia, enam kolom pertama kosong dan ACK bernilai 0 |
| `labrow\|i` | ID, hari, tanggal jadwal, jam jadwal, suhu, Fc lab, umur dalam detik. ACK memuat jumlah baris |
| `run` | Revisi sesi, ID baseline, jumlah checkpoint, status parsial, tanggal mulai, jam mulai, tanggal akhir, jam akhir, suhu awal, elapsed detik, M, Fc, persen target |
| `point\|i` | Hari, tanggal, jam, suhu operasional, M, Fc, persen target, flags checkpoint, S1, S2, S3, rerata kanal, mask kanal valid. ACK memuat jumlah checkpoint |
| `historyrow\|i` | ID hasil, nama baseline, tanggal simpan, jam simpan, Fc, jumlah checkpoint, parsial. ACK memuat ID hasil |
| `detail` | ID hasil, tanggal simpan, jam simpan, operator, project, tanggal identitas. Baca juga `baseline`, `run` dan `point` pada halaman detail |
| `curve\|i`, `scatter\|i` | M, Fc, batas maksimum sumbu X. Kurva berisi indeks 0–64 dengan sumbu X minimal 20.000 dan grid 5.000. Scatter berisi pasangan uji lab. Sumbu Y 0–50 MPa mengikuti preview |

Flags checkpoint menggunakan bit 0 untuk koreksi/input manual, bit 1 untuk gap, dan bit 2 untuk AutoSave. Nilai M dan persen target ditampilkan bulat. Angka prediksi Fc ditampilkan sampai satu desimal. Ringkasan `pStr` memprediksi Fc dengan M checkpoint terakhir yang dibulatkan. Nilai ringkasan yang tersimpan dipakai kembali di riwayat. R² ditampilkan sampai empat desimal. HMI dapat menambah nol, pemisah ribuan, satuan, dan label sumber.

## Status ACK

| Kode | Makna |
| --- | --- |
| 0 | OK |
| 1 | Input tidak valid |
| 2 | Data wajib belum lengkap |
| 3 | Aksi belum tersedia pada keadaan saat ini |
| 4 | Tampilan atau revisi sudah berubah |
| 5 | Kapasitas slot, daftar, atau penyimpanan habis |
| 6 | I/O penyimpanan gagal |
| 7 | Record penyimpanan rusak |
| 8 | Versi penyimpanan atau token boot tidak cocok |
| 9 | Suhu belum tersedia |
| 10 | Jam atau urutan waktu tidak valid |
| 11 | Model belum dapat dibentuk |
| 12 | Hasil baru mempunyai Day 0 atau interval nol |
| 13 | Konfirmasi diperlukan. Nilai ACK berisi token |
| 14 | Transaksi lain sedang berlangsung |
| 15 | Item tidak ditemukan atau akhir daftar |
