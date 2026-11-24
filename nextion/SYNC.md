# Integrasi Arduino dan Nextion K050

Pasangan aktif memakai firmware Arduino 1.0.1 dan HMI conmt-NX8048K050-CM1-final.tft yang dibangun dari nxsrc-K050. Kontrak frame, field, revisi, dan error mengikuti [kontrak Arduino](../arduino/CONTRACT.md).

Firmware mengalamatkan seluruh variabel handshake dan data dengan awalan pInit. Panel mengirim satu request pada satu waktu, menunggu nAckSeq, memeriksa nAckCode, dan memakai nView terbaru. Permintaan yang kehilangan balasan dikirim ulang dengan nomor urut dan payload yang sama.

Splash mengikuti urutan preview ConMT. Sesudah handshake MCU, empat tahap berjalan setiap 650 ms hingga 100%. Panel menampilkan 100% selama 700 ms, lalu otomatis membuka User Information. SAVE pada User Information membuka Main Menu. Angka 85% pada gambar ditutup dengan progres dinamis. Status sensor atau penyimpanan yang perlu perhatian tetap ditampilkan saat pemeriksaan selesai. Versi MCU yang perlu diperbarui ditampilkan secara eksplisit.

Keyboard mengirim nilai operator, proyek, tanggal, baseline, material, dan lab melalui perintah produksi. Penyimpanan baseline serta hasil mengirim revisi yang sedang ditinjau. Konfirmasi memakai token dari MCU. Pemilihan baseline memakai ID balasan, dan BACK mempertahankan konteks draft atau sesi.

Halaman utama mempertahankan ID 0–16. Lima halaman lokal menangani keyboard, konfirmasi, jam, koreksi checkpoint, dan kurva. Frame dari halaman lokal tetap memakai ID domain asal di MCU. Seluruh baris dapat dibaca melalui paginasi.

Uji integrasi menggunakan simulator K050 dan parser, engine, serta jurnal Arduino yang sebenarnya, dengan image kartu raw dan sensor/jam terkontrol di komputer. Cakupannya meliputi input sampai SAVE dan riwayat, koreksi checkpoint, grafik, konfirmasi hapus, balasan serial hilang, dan MCU reset/reconnect. Laporan build dan checksum ada di conmt-NX8048K050-CM1-final.validation.json.

Firmware raw sudah di-upload ke unit uji lewat COM12 (Arduino as ISP); verifikasi flash, fuse, lock, dan EEPROM lulus. Upload TFT final ke panel, pengoperasian fisik pasangan baru, kestabilan probe, serta baca/tulis dan recovery microSD masih memerlukan pengujian pada unit. [Petunjuk file dan build](NX8048K050-README.txt)
