# Integrasi Arduino dan Nextion K050

Pasangan aktif memakai firmware Arduino 1.0.1 dan HMI conmt-NX8048K050-CM1-final.tft yang dibangun dari nxsrc-K050. Kontrak frame, field, revisi, dan error mengikuti [kontrak Arduino](../arduino/CONTRACT.md).

Firmware mengalamatkan seluruh variabel handshake dan data dengan awalan pInit. Panel mengirim satu request pada satu waktu, menunggu nAckSeq, memeriksa nAckCode, dan memakai nView terbaru. Permintaan yang kehilangan balasan dikirim ulang dengan nomor urut dan payload yang sama.

Splash mengikuti urutan preview ConMT. Sesudah handshake MCU, empat tahap berjalan setiap 650 ms hingga 100%. Panel menampilkan 100% selama 700 ms, lalu otomatis membuka User Information. SAVE pada User Information membuka Main Menu. Angka 85% pada gambar ditutup dengan progres dinamis. Status sensor atau penyimpanan yang perlu perhatian tetap ditampilkan saat pemeriksaan selesai. Versi MCU yang perlu diperbarui ditampilkan secara eksplisit.

Keyboard mengirim nilai operator, proyek, tanggal, baseline, material, dan lab melalui perintah produksi. Penyimpanan baseline serta hasil mengirim revisi yang sedang ditinjau. Konfirmasi memakai token dari MCU. Pemilihan baseline memakai ID balasan, dan BACK mempertahankan konteks draft atau sesi.

Panel menampilkan dan menerima tanggal dalam format DD-MM-YYYY. Keyboard memakai tombol angka dan tanda hubung yang sudah ada saat kolom tanggal disentuh. Panel mengonversi tanggal ke YYYY-MM-DD untuk komunikasi CM1.

Indikator pojok menampilkan HH:MM dan persentase baterai dari MCU. Teks jam di User Information dan Device Info membuka penyetelan jam yang sama. Grafik baseline memakai 65 sampel kurva dan pasangan uji lab dari MCU. Sentuh grafik untuk melihatnya lebih besar beserta R² dan jumlah pasangan.

Halaman utama memakai ID 0–16. Delapan halaman lokal menangani keyboard teks dan angka, konfirmasi, jam, koreksi checkpoint, kurva, penambahan baris, dan Sample schedule. Frame dari halaman lokal memakai ID domain asal di MCU. Daftar yang melebihi area tampilan bisa digulir per baris. Panel memuat baris yang baru terlihat melalui GET CM1 dan memakai ulang baris yang masih terlihat.

Uji integrasi menggunakan simulator K050 dan parser, engine, serta jurnal Arduino yang sebenarnya, dengan image kartu raw dan sensor/jam terkontrol di komputer. Cakupannya meliputi input sampai SAVE dan riwayat, koreksi checkpoint, grafik, konfirmasi hapus, balasan serial hilang, dan MCU reset/reconnect. Laporan build dan checksum ada di conmt-NX8048K050-CM1-final.validation.json.

Firmware dipasang lewat Arduino CLI dan lolos baca-balik seluruh flash. TFT terbaru tersedia untuk pemasangan ke layar. Pemeriksaan fisik baterai, UART panel, dan baca/tulis microSD dicatat terpisah dari hasil simulator. [Petunjuk file dan build](NX8048K050-README.txt)
