# Optimasi lanjutan dan studi fitur

Optimasi dari checkpointc1ebca9 tersimpan pada881dbc8. Seluruh fitur produksi dipertahankan. Dua loop replay checkpoint disatukan, buffer verifikasi jurnal dipakai bergantian setelah header selesai dibaca, dan temporary replay dibatasi dengan scope.

## Ukuran dan koreksi probe

| Pengukuran dengan probe yang sama | Flash | SRAM statis probe |
|---|---:|---:|
|Source sebelum optimasi, c1ebca9|75554|1532|
|Source setelah optimasi,881dbc8|74618|1532|
|Penghematan kode|936|0|

Probe diperkuat agar frame sensor benar-benar diisi dari input volatile dan clock memiliki rentang32/64bit penuh. Sebelumnya sensor probe tidak mengisi frame dan clock diturunkan dari satu byte. Input baru menambah140byte kode pengukuran dan30byte data. Karena itu angka baru tidak dibandingkan langsung sebagai delta kode terhadap75.414/1.502yang dilaporkan sebelumnya. Kedua checkpoint dikompilasi ulang dengan probe yang sama untuk tabel ini.

Pada probe lama, optimasi yang sama mengubah75.414menjadi74.478byte. Hasil terukur dengan probe baru adalah74.618byte. Data input pengukuran sendiri memakai31byte SRAM; angka1.532tetap memasukkannya, tidak menguranginya untuk menyatakan target aman.

Batas fisik tetap32.768byte; probe saat ini masih melebihi batas sebesar41.850byte. Sensor/clock/brightness/sound masih port pengukuran, clock16MHz hanya asumsi probe, chart final belum tertaut dan nested stack/ISR belum dibuktikan. Tidak ada HEX produksi atau flashing.

## Validasi yang dijalankan

- Seluruh15suite lulus pada host64, host32 dan ASan/UBSan. Snapshot UART17page dan300baris perbandingan workflow terhadap520a74f tetap sama; expected fixture tidak diubah.
- Uji baru memeriksa replay hingga checkpoint tertentu, endpoint yang tidak ditemukan, penggunaan input/output point yang sama dan urutan day yang tidak sah.
- Emulator AVR lulus620kasus codec, PROGMEM, formatting, schema1 streamed records dan replay checkpoint termasuk cutoff/alias. Perhitungan Nurse–Saul/FKZ tidak diganti.
- Frame individual `Journal::verify` turun112→68byte dan replay110→58byte. Frame checkpointResult125byte menggantikan rantai checkpointResult123 + replayResult128byte; helper replayResult sudah dihapus. Ini bukan bukti final stack aman.

## Studi kandidat pemangkasan

[Daftar kandidat dan konsekuensinya](FEATURE_CHOICES.md) merupakan bahan keputusan, belum diterapkan. Delapan varian diukur dalam `firmware/build-feature-study`, memakai salinan source terpisah. Hash source produksi sebelum/sesudah identik. Bahkan gabungan kandidat masih membutuhkan61.754byte.

Script tidak mengeluarkan firmware produk yang fungsional: beberapa handler dalam salinan sengaja mengembalikan Unsupported dan halaman tertentu disembunyikan. Workflow pengganti/importer serta driver yang belum ada tidak termasuk penghematan. Angka marginal tidak dapat dijumlahkan dan bukan batas minimum semua kemungkinan implementasi.

Lihat [feature-sizes.json](feature-sizes.json), [normalized-baseline-size.json](normalized-baseline-size.json) dan [optimization-ledger.json](optimization-ledger.json). Pengukuran fitur dengan probe sebelumnya disimpan sebagai sejarah dan ditandai superseded.

Status acceptance tetap77HOST_PASS,1EMULATED_PASS,17PARTIAL,2NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL:24skenario belum lengkap. Pekerjaan bounded storage/jobs/cursors, seluruh driver/HMI, final stack dan integrasi fisik belum selesai.
