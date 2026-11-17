# Keputusan implementasi

Acuan domain tetap preview-contmt dan klarifikasi terakhir klien. Source React/Excel tidak diubah.

- a intercept, b slope, ln natural; fit dua lintasan dengan seluruh row suhu.
- FKZ tiga kondisi, lookup next calibrated day; faktor dihitung ulang dari rows baseline immutable. Tidak menyimpan daftar faktor duplikat dalam RAM.
- Nilai numerik berkas binary64 little endian; AVR menggunakan double32 dan dikonversi eksplisit. Presisi AVR diuji pada emulator, bukan dianggap sama dengan host.
- Row/point ID tetap, viewport enam; enumerasi dan fit streaming. Jumlah record tidak dialokasikan sebagai array di MCU.
- Metadata material tidak masuk formula Fc. Draft boleh belum lengkap; baseline usable memerlukan input/model sah.
- SAVE baseline membuat ID baru. Baseline committed tidak diedit; delete hanya menyembunyikan, sehingga snapshot session/history tetap dapat mereferensikan rows immutable. Format ini belum mempunyai garbage collection.
- NEXT memakai checkpoint terakhir; prediction summary memakai M dibulatkan seperti preview. Raw M tetap disimpan. M=0 tidak diganti live M dari timestamp berbeda.
- Live acquisition memakai delta timestamp dan compensated accumulation. Gaps tidak dijembatani sebagai suhu diketahui.
- Resume setelah restart menandai gap. Reconciliation memerlukan konfirmasi, alasan dan dua observasi manual yang mengapit gap; provenance tersimpan.
- Interval settings menyimpan sampel/recovery otomatis tanpa mengarang label hari. CHECK_ADD memerlukan day eksplisit sampai kebijakan automatic day disetujui.
- Sensor average satu desimal operasional seperti sumber; raw dan valid mask disimpan.
- Draft retained pada NEW; saved SELECT membuka copy draft dan BACK kembali daftar.
- Journal append transactional di CMT.JRN menggantikan proposal banyak file. CRC header/payload, commit trailer, verified readback, operation ID dan recovery prefix diterapkan. Tidak mengandalkan rename atomic.
- Lookup journal sekarang memindai transaksi dan memvalidasi CRC. Ini menghemat RAM tetapi latency bertambah terhadap volume data; index disk dan pengukuran latency masih diperlukan sebelum produksi.
- UART CM1 + native Nextion text writes, render bertahap dan refresh pendek untuk sensor/status. Native responses yang tidak digunakan tidak dieksekusi sebagai command.
- Dummy ports hanya host/tests/tools capacity probe. Production .ino memerlukan BoardBinding terverifikasi.
- MCU tetap ATmega328P. Resource probe membuktikan implementasi lengkap saat ini tidak muat; tidak ada artifact production HEX dan tidak ada klaim siap flash.

Keputusan yang dipertegas audit17November2026:

- Default AutoSave=false, interval300detik mengikuti default offline dokumen06. Source seed true tidak mengalahkan policy eksplisit yang dikunci kemudian. Pengujian autosave mengaktifkan setting dengan sengaja.
- CM1 contract revision2: vRender milik MCU; vBusy milik panel. Panel membuka busy hanya setelah ACK boot/seq sesuai request, atau timeout eksplisit. Idle refresh tidak membuat ACK command atau mengaktifkan retry.
- Manual day/temp/Fc string disimpan terpisah dari nilai numerik agar display/reopen tidak memangkas presisi input. Angka hasil sensor tetap policy satu desimal operasional ConMT.
- Sort tabel baseline mengikuti day/time/id; integrasi tetap time/id. NEW row difokuskan dan viewport disesuaikan. Edit Day0 mempertahankan slot tersnap atau memilih slot pertama yang kosong.
- Gap merupakan rentang terurut dari observasi terakhir sampai pemulihan; beberapa gap yang belum direkonsiliasi digabung. Status error aksi dan kesehatan akuisisi dipisah.
- Timestamp pada Sensors adalah waktu sampel, bukan waktu pemanggilan writer. PreviewSensors membekukan kanal pada NEXT dan tidak ditimpa autosave sebelum SAVE RESULT.
- Mount wajib sebelum write. Committed corruption dan sequence discontinuity memblokir writer; tail parsial yang dikenali tidak diperlakukan sebagai committed data. Ini belum memulihkan setiap kerusakan media.
- Source sama diuji dengan tiga strategi compiler. Merge constants/linker relaxation adalah pilihan paling kecil yang diukur, tetapi tidak memenuhi flash/stack328P. Batas region fisik wajib diberikan eksplisit ke linker saat capacity gate; ELF region besar hanya artefak pengukuran.

Lanjutan17November: source produksi lama hanya digunakan untuk konfigurasi/penstabil baterai yang secara eksplisit ditunjuk pengguna. Rumus beton tetap acuan ConMT. Index disk adalah cache turunan yang selalu dibangun ulang saat mount; metadata A/B bukan prasyarat integritas index ini karena journal committed tetap otoritasnya. Streaming copy memakai32byte untuk mengurangi nested stack. Batas flash/stack tetap gagal dan tidak disembunyikan.

Continuation from0e45cb1: after a committed manual checkpoint edit, live acquisition replays the corrected checkpoint series, appends the current sensor endpoint and replaces its time/temperature anchors on the next valid sample. An unresolved gap remains unresolved. This follows the checkpoint replay policy and does not fabricate missing sensor readings. Clock adjustments retain a durable cause separately from reconciliation explanation. HMI output owns its component/value buffers until transmission completes; RX is independent and no active buffer is aliased. See reviews/2026-11-17-optimization.
