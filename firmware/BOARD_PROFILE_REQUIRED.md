# Konfigurasi yang belum tersedia dari sumber

MCU target ATmega328P; programmer USBasp. Tidak ada izin flash dalam pekerjaan ini.

File `ConMT/src/board/BoardBinding.h` dan implementasinya harus diisi dari bukti mesin:

- FQBN/core, clock/fuse, upload settings; verifikasi signature.
- Nextion model, baud dan routing UART/level listrik.
- SD chip-select dan SPI rate. SdStorage memakai library SD 1.3.0 (utility SdFat) yang tersedia lokal; tidak memakai File wrapper dengan append-only mode.
- Model sensor, bus/pin/address, waktu konversi, valid/disconnected/error. Implementasikan SensorPort nonblocking.
- RTC/sumber waktu/timezone: ClockPort wall-clock valid serta monotonic millis.
- Baterai: pin/rangkaian ADC, referensi dan kalibrasi nyata. DevicePort harus mengembalikan status unavailable jika pembacaan tidak sah.
- Buzzer/brightness yang memang tersedia.

BoardBinding menyediakan `CONMT_BOARD_VERIFIED=1`, `CONMT_UART_BAUD`, `CONMT_SD_CS`, `CONMT_SD_SPI_RATE`, serta fungsi produksi conmtClock/conmtSensors/conmtDevices/conmtBoardBegin.

Tidak disediakan file binding berisi tebakan. Production build sengaja gagal sebelum profil diisi. Header/implementasi port dan driver SD/UART telah disiapkan; sensor/RTC/battery tidak dapat dipilih tanpa identitas hardware. Host tests tidak mengubah kondisi tersebut.

Target resource probe memakai compiler lokal dan dummy I/O hanya dalam direktori tools untuk mengukur kode. Probe bukan firmware produksi, tidak mempunyai file HEX rilis, dan tidak boleh di-upload.
