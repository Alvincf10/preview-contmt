# HMI pasangan firmware ConMT

Manifest dan197event berada di sini; page0..16 mengikuti preview. Wire protocol tetap CM1, **contract revision2**. Jalankan `python3 firmware/tools/generate_hmi.py` untuk meregenerasi dari versi yang sama dengan header Transport.h. Panel contract1 ditolak.

Buat semua Text pada manifest dengan kapasitas cukup, ditambah global variables/text di pInit dengan vscope global. Input menggunakan keyboard/modal sesuai model panel; pada Apply jalankan snippet apply_*. Cancel tidak mengirim apa pun. Tanyakan konfirmasi sebelum snippet *Confirm. Pilihan datum hanya -20/-10/0/10.

Frame CM1 berakhir LF nyata (`printh 0A`), MCU→panel berakhir FF FF FF. Batas192byte menghitung LF. Field numerik wire menggunakan titik. Nama tidak boleh memuat quote/backslash/pipe/kontrol. Maksimal satu command outstanding.

Panel memiliki vBusy/vReqBoot/vSeq/tReq; MCU memiliki vRender serta vAckBoot/vAck/vStatus/vView/vBoot. Idle refresh hanya mengubah render flag. Panel membuka busy hanya bila pasangan vAckBoot/vAck cocok dengan vReqBoot/vSeq request aktif, atau setelah timeout eksplisit. ACK terlambat tidak boleh membuka request yang lebih baru.

Retry menggunakan tReq dan seq yang sama. Timer harus lebih lama daripada latency render/storage terukur; jangan menaikkan seq saat retry. Pasang layanan retry pada page aktif sesuai kemampuan model/Editor yang diverifikasi; berkas pInit_retry_timer.txt sendiri belum membuktikan timer berjalan di seluruh17page. Global text/variables harus bertahan lintas page.

MCU memegang state/navigasi. PAGE_READY pasca-inisialisasi meminta render, tidak mengeksekusi START/SAVE. Panel reset kembali handshake tanpa kehilangan session. Semua SAVE hanya sukses setelah commit.

NAV BACK/RESCAN boleh dipicu ketika data sedang dirender, dengan satu request aktif. Mutasi data menunggu vRender=0 dan membawa view yang ditampilkan. Sequence tidak boleh wrap; lakukan handshake koneksi baru sebelum batas uint32. Status unavailable memakai --, bukan angka pengganti. Manual input lab mempertahankan string asalnya.

Ini source kontrak/event yang bisa dipasang di Editor, belum file HMI/TFT. Sintaks event, keyboard, font, layout, resource model dan capture UART fisik masih perlu diverifikasi. Jangan rename JSON menjadi HMI. Chart dan layout visual lengkap masih pending; perhitungan chart di core dapat diuji tanpa panel.
