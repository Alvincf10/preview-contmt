# Firmware Arduino ConMT

Sketch berada di [ConMT.ino](ConMT/ConMT.ino). Sumber perilaku adalah [preview web](../src), [workbook klien](../docs/acuan/Syarat-Kroscek-Perhitungan-ConMT-Data-Real.xlsx), dan klarifikasi perhitungan klien dalam paket rencana lokal `docs/firmware-plan/`. [Kontrak CM1](CONTRACT.md) mencakup semua halaman Nextion dari boot sampai riwayat detail.

## Status

**Build Arduino untuk ATmega328P lulus batas flash.** Perintah build di bawah menghasilkan `arduino/out/ConMT-ATmega328P.hex`. Pengujian fisik microSD, tiga probe sekaligus, puncak stack, dan komunikasi panel masih terbuka.

HEX lokal `arduino/out/ConMT-ATmega328P-ISP.hex` untuk unit yang diuji via Arduino as ISP menyertakan instruksi lompat ke aplikasi pada alamat reset `0x7E00` yang dipilih fuse unit.

| Pengukuran | Flash | SRAM statis |
| --- | ---: | ---: |
| Build terkecil sebelumnya | 37.718 byte | 1.090 byte |
| HEX sebelum koreksi hasil dan driver board | 31.718 byte | 1.193 byte |
| **HEX hasil pipeline Arduino (raw journal)** | **30.250 byte** | **1.194 byte** |

Flash dihitung dari `.text + .data`. Profil Arduino menyediakan 32.256 byte, sehingga ruang yang tersisa adalah 2.006 byte. Kapasitas fisik chip 32.768 byte. SRAM statis mencakup `.data`, `.bss`, dan `.noinit`.

Build ini masuk kapasitas chip dan profil Arduino. Ukurannya 470 byte di bawah sasaran cadangan engineering 30.720 byte dalam paket rencana lokal.

Perubahan source memakai satu buffer sektor SD untuk mengakses record jurnal, satu area kerja untuk snapshot sesi, dan satu root transaksi yang diterbitkan setelah commit. Pipeline build menggabungkan rangkaian instruksi AVR yang identik sebelum link akhir dengan target ATmega328P. Link akhir memakai batas memori MCU dan pemeriksaan kedua terhadap batas profil Arduino.

## Perilaku yang diterapkan

- Identitas, draft persisten, nama/target/datum, resep material dan W/C, tabel lab, pembacaan sensor ke baris, jadwal, serta pengisian slot Day 0 dari 0–6 jam. Generate mengikat data lab, regresi, R², dan faktor koreksi ke satu versi. Simpan menerbitkan baseline dengan ID baru.
- START menyimpan baseline dan Day 0. Sesi memperoleh checkpoint dari suhu valid atau catatan manual operator. NEXT mengambil versi checkpoint terakhir dan SAVE RESULT menyimpan versi itu ke riwayat. Identitas, model, pengukuran, dan waktu tetap dapat dibuka setelah baseline dihapus dari daftar.
- Pengaturan interval, AutoSave, kecerahan, dan buzzer dipersistkan. Interval standar 300 detik. Nilai 0 dan AutoSave mati menonaktifkan checkpoint periodik. Perintah manual tetap disimpan. Pada layar hasil, AutoSave dijeda selama koneksi panel aktif agar versi yang ditampilkan tetap sama. Jika frame berhenti selama 10 detik, pencatatan dapat berjalan lagi dan versi hasil yang sudah digantikan harus dibuka ulang.
- Hari checkpoint sensor otomatis dihitung dari bagian bulat umur terhadap Day 0. Operator dapat mengubah label hari. Sesudah gangguan sensor, perubahan jam, atau reset saat sesi aktif, pembacaan sensor berikutnya menandai interval sebagai parsial dan integral melewati interval tersebut. Operator dapat merekonsiliasi data manual dengan meninjau titik batas dan menghapus tanda gap secara eksplisit.
- Nurse–Saul mengintegrasikan suhu dengan aturan trapesium. Regresi menggunakan pasangan M dan Fc positif. Aturan FKZ klien memilih hari yang sama, hari terkalibrasi berikutnya, atau faktor terakhir setelah jadwal kalibrasi berakhir. Checkpoint memakai M mentah. Ringkasan hasil dan SAVE RESULT menghitung Fc dari M checkpoint terakhir yang dibulatkan ke bilangan bulat sesuai preview.

Profil ini menggunakan IEEE-754 binary32 untuk integral, koefisien, dan prediksi. Input suhu/Fc dan material mendukung lima desimal, label hari tiga desimal, serta kalender lokal 1970–2199. Suhu dari sensor memakai rerata yang dibulatkan ke satu desimal untuk perhitungan, dengan nilai per kanal disimpan pada checkpoint. R² tersedia untuk penilaian baseline. Data demo workbook hanya dipakai oleh uji.

## Profil board

Pemetaan berasal dari skema Maturity Control LCD rev. 1.0 di paket rencana lokal. Pilihan build Arduino `arduino:avr:uno` menargetkan ATmega328P @ 16 MHz. Unit diuji melalui Arduino as ISP.

| Fungsi | Pin | Catatan verifikasi |
| --- | --- | --- |
| Tiga kanal suhu | D2, bus bersama | Driver memeriksa ROM, status konversi per probe, dan CRC. Pembacaan 85 °C memerlukan dua konversi berturut-turut karena register suhu juga bernilai 85 °C saat probe reset. Kanal mengikuti urutan penemuan ROM. [Datasheet DS18B20](https://www.analog.com/media/en/technical-documentation/data-sheets/DS18B20.pdf) |
| microSD | D10 CS, D11 MOSI, D12 MISO, D13 SCK | SPI membaca dan menulis sektor kartu serta memeriksa CRC transfer. [Spesifikasi SD SPI](https://www.sdcard.org/cms/wp-content/themes/sdcard-org/dl.php?f=Part1_Physical_Layer_Simplified_Specification_Ver6.00.pdf) |
| UART panel | D0 RX, D1 TX | CM1 9600 baud, 8N1 sebagai default. Konfirmasi baud dan level listrik panel pada unit. |
| Tegangan masuk | A0 | Pembagi 3:1 dengan kompensasi AVCC dari bandgap internal nominal 1.100 mV. `CONMT_BANDGAP_MV` dapat dikalibrasi per unit. Profil dengan AVCC terukur dapat menetapkan `CONMT_VIN_REF_MV`. Persentase baterai tersedia setelah ambang kosong/penuh diisi di [BoardProfile.h](ConMT/src/BoardProfile.h). |
| Buzzer | D3 | Keluaran aktif tinggi selama 60 ms. Perlu uji jenis buzzer fisik. |
| Kalender | Perintah `CLOCK_SET` | RTC cadangan daya belum terlihat pada skema. Waktu lokal harus disetel ulang setiap kali daya MCU terputus. |

## Penyimpanan SD

Firmware memakai region jurnal 1 MiB di akhir kartu, yaitu 2.048 sektor 512 byte. Tidak perlu filesystem, FAT, atau `CMTLOG.BIN`. Dua sektor pertama region adalah anchor; slot record 128 byte mengikuti, dengan kapasitas 8.184 slot. Format kartu tidak relevan karena region ditulis langsung. Gunakan kartu khusus perangkat: region ini berada di luar pembukuan partisi dan dapat menimpa data lain di kartu. Penyediaan file tidak diperlukan; validasi SD fisik masih perlu dilakukan.

Jurnal menyimpan record ber-versi dengan CRC dan commit logis yang diverifikasi sebelum menulis salah satu dari dua sektor penunjuk. Baseline dan sesi lama tetap tersedia untuk riwayat. Format record tetap, tetapi firmware berbasis file FAT lama tidak kompatibel dengan region raw ini dan datanya tidak diimpor. Format firmware lama di luar folder `arduino` juga belum memiliki jalur impor.

## Build dan uji

Gunakan [build.py](build.py) untuk menghasilkan HEX. Script memakai Arduino CLI dengan profil yang mematok Arduino AVR Boards 1.8.8 dan OneWire 2.3.8. Script menemukan instalasi Arduino IDE pada lokasi Windows standar atau menerima path CLI lewat `--arduino-cli`. Berikan path `bin` AVR GCC 16.1.0 yang dipakai untuk link. [Rilis AVR GCC 16.1.0](https://github.com/ZakKemble/avr-gcc-build/releases/tag/v16.1.0-1) · [Profil Arduino CLI](https://docs.arduino.cc/arduino-cli/sketch-project-file)

```powershell
python -B .\arduino\build.py --avr-bin 'C:\path\avr-gcc-16.1.0-x64-windows\bin' --output .\arduino\out\ConMT-ATmega328P.hex
```

Tombol Verify standar di Arduino IDE mengukur ukuran sebelum penggabungan instruksi dan masih melaporkan overflow. Perintah build di atas menghasilkan HEX yang lulus batas flash.

Uji host mengompilasi sumber yang sama untuk rumus, alur, jurnal, kartu, dan CM1. Simulasi menggantikan I/O sensor, UART, dan sektor kartu. [Fixture uji](tests/reference-vectors.json) berisi nilai pembanding dari Excel klien dan dataset preview. Jalankan dari root repositori dengan compiler C++11 dan Python.

```powershell
zig c++ -std=c++11 -O2 -I arduino/ConMT/src arduino/tests/ConMTTest.cpp arduino/ConMT/src/Domain.cpp arduino/ConMT/src/Engine.cpp arduino/ConMT/src/Journal.cpp arduino/ConMT/src/Panel.cpp arduino/ConMT/src/SdStore.cpp -o conmt-host.exe
python arduino/tests/run.py .\conmt-host.exe
```

Kedua dataset memverifikasi 41 observasi, 10 pasangan lab dan FKZ, M per checkpoint hingga toleransi 0,025 °C·jam, serta Fc hingga 0,002 MPa. Pengujian juga mencakup pembulatan M untuk hasil akhir, penolakan record FKZ dengan versi tak didukung, suhu valid 0 °C, AutoSave, koreksi gap, restart setelah commit yang ACK-nya hilang, pemulihan dua jenis putus tulis, pembacaan riwayat setelah hapus baseline, region raw pada image kartu, dan frame CM1 kedaluwarsa.

Simulator AVR menjalankan 91 pemeriksaan komponen hitung dengan 0 kegagalan. Cakupannya adalah M untuk kedua dataset, koefisien regresi, R², dan tiga kondisi fungsi FKZ.

Firmware 1.0.1 memakai alamat variabel komunikasi global di `pInit` untuk pasangan HMI K050. Paket pasangan terbaru adalah `nextion/conmt-NX8048K050-CM1-final.tft` dan `arduino/out/ConMT-ATmega328P-ISP-CM1-K050-raw.hex`. Uji integrasi menjalankan simulator panel dengan parser dan engine produksi serta image kartu raw di komputer. Riwayat 41 checkpoint tetap dapat dibaca dalam format jurnal yang sama.

Laporan SHA-256 dan batas pengujian pasangan K050 dicatat pada `nextion/conmt-NX8048K050-CM1-final.validation.json`.
