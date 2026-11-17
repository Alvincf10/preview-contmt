# Status implementasi ConMT — 17 November 2026

**Belum selesai sebagai firmware produksi ATmega328P.** Core/controller/storage/protokol benar-benar diimplementasikan, tetapi ukuran target belum muat, driver sensor/RTC/baterai belum tersedia dan HMI pasangan belum dikompilasi. Tidak ada HEX produksi atau flash perangkat.

Audit terhadap plan, TS, workbook dan referensi klien menemukan dan mengoreksi38cacat:4Kritikal,17Tinggi,17Sedang.65kasus audit lulus;27di antaranya kontrol yang tidak dihitung sebagai bug. Enam suite CTest lulus pada host64,host32 dan sanitizer. Lihat [audit lengkap](../reviews/2026-11-16-audit/README.md) dan [102skenario](../reviews/2026-11-16-audit/coverage.md).

| Build | Flash | RAM statis |
|---|---:|---:|
|Pembanding terakhir, ELF29September2026|31.288byte|1.249byte|
|Source sekarang, flags baseline|80,708byte|1,693byte|
|Source sama, flags merge/relax|79,884byte|1,685byte|
|Source sama, inline-small + relax|83,072byte|1,685byte|

Pembanding lama menyisakan968byte dari batas aplikasi32256byte atau1480byte dari flash fisik32768. Kode aplikasi lama tidak digunakan sebagai acuan.

Build baru terbaik yang diukur masih melebihi flash fisik sebanyak47,116byte dan hanya menyisakan363byte RAM statis sebelum semua driver/stack. Non-LTO frame prepareResult235byte dan checkpointResult205byte dapat bersarang. Itu estimasi compiler, bukan watermark build LTO. Gate stack belum lulus.

Fixed buffers, streaming fit/iteration, PROGMEM, LTO/Os/shared prologues, refresh HMI pendek dan merge/relax sudah diterapkan. Optimasi flags menghemat824byte flash serta8byte RAM pada source yang sama; belum menyelesaikan overflow. Perubahan MCU atau penghapusan fitur tidak dilakukan.

73skenario berstatus HOST_PASS,1EMULATED_PASS,20PARTIAL,3NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL. Status ini tidak boleh disingkat menjadi semua acceptance lulus.

Wajib diselesaikan: kapasitas/stack; index dan latency SD; adapter sensor/RTC/baterai serta BoardBinding terverifikasi; assembly keyboard/modal/font/chart HMI/TFT; recovery/import/clock acceptance yang masih parsial; capture UART dan pengujian alat/soak.

Numerik AVR GCC/simavr lulus dua fixture41titik. Maksimum error M≈0.0025C·jam dan Fc≈0.0000082353MPa pada fixture penuh. Ini bukan pengujian sensor/SD fisik. Fault injection100byte-budget hanya transaksi scalar host, bukan seluruh offset transaksi besar atau100power cut mesin.

Linker memakai region fisik32768/2048 pada pemeriksaan pertama dan gagal. CAPACITY_ONLY.elf setelah region diperbesar hanya untuk pengukuran overflow, bukan firmware yang dapat dijalankan/di-upload pada328P. Baud/clock probe16MHz hanya asumsi pengukuran, bukan profil mesin.
