# Format penyimpanan v1

Satu file FAT16/32 bernama CMT.JRN, single writer. Tidak kompatibel dengan record firmware lama.

Transaksi:

| Offset header | Panjang | Isi |
|---:|---:|---|
|0|4|ASCII CMT1|
|4|2|schema1 little endian|
|6|2|algorithm1 little endian|
|8|4|sequence uint32|
|12|8|operation ID uint64,0untuk operasi internal|
|20|4|payload length|
|24|4|jumlah entry|
|28|4|CRC32 header bytes0..27|

Payload adalah entry berulang: kind1byte, field1byte, objectID4byte, index4byte, valueLength2byte, value0..128byte. Nol length merupakan tombstone. Kind/Field ID mengikuti enum Journal.h; penambahan harus append atau menaikkan schema.

Trailer8byte: CRC32 payload4byte, ASCII DONE4byte. CRC memakai reflected polynomial0xEDB88320, initial/final XOR0xFFFFFFFF. Angka integer little endian. Real di berkas binary64 IEEE754; encode/decode eksplisit, bukan sizeof(struct). String ASCII tanpa NUL akhir; null, pipe, quote dan backslash tidak diterima dari input.

ROW baseline37byte: revision4, day8, timeH8, temp8, fc8, flags1. ROW checkpoint30byte: revision4, timestampMs8, day8, temp8, validMask1, source1. Model28byte: a8,b8,r2=8,n4. Result73byte menyimpan rawM, maturityUsed, NSraw, factor, Fc, referenceDay (6×8), endMs8, initialTemp8,lastTemp8,hasReference1.

Commit: placeholder → payload → header final → sync → readback header/payload → trailer DONE → sync → verify. ACK sukses sesudah verify. Error commit membuat journal uncertain dan menolak write berikutnya sampai remount; retry tidak boleh menebak apakah commit berhasil.

Mount menerima prefix transaksi committed berurutan dan CRC valid, menghentikan pada tail parsial, serta memblokir schema tak dikenal. Tail baru dipotong saat transaksi berikutnya dimulai. CRC juga diperiksa saat lookup agar korupsi setelah mount tidak diam-diam menjadi nilai perhitungan. Rekaman sebelum tail tetap dapat dibaca; ini bukan kemampuan memulihkan semua korupsi media/FAT.

Write ditolak sebelum mount sukses. Ketika trailer DONE/header/urutan membuktikan blok seharusnya committed, korupsi tidak diperlakukan sebagai tail yang boleh dipotong. Sequence discontinuity juga memblokir writer. Batas bukti fault injection saat ini adalah100byte-budget untuk transaksi scalar host dan beberapa committed-corruption cases; bukan seluruh kerusakan yang mungkin terjadi pada FAT/media atau semua offset transaksi besar.

Sensors53byte: sampledWallMs8, sampledMonoMs4, channel[3]24, validMask1, rawAverage8, operationalAverage8. sampledWallMs berasal dari waktu sampel, bukan waktu commit. PreviewSensors memakai codec yang sama dan membekukan kanal saat NEXT; SAVE RESULT menyalin snapshot itu, bukan sampel autosave berikutnya.

DayInput/TempInput/FcInput adalah field tambahan per rowID yang menyimpan teks input lab ASCII agar display/reopen tidak mengubah presisi manual. Nilai numerik row tetap dipakai untuk perhitungan. Field tersebut ditambahkan di akhir enum, tanpa mengubah ID lama. Record yang lebih lama boleh tidak memilikinya; presenter memformat angka sebagai fallback. Ini tidak berarti ada importer untuk format firmware produksi lama.

CMT.IDX adalah index bantu di SD:64bucket×8byte berisi head offset dan CRC, lalu node26byte (key10, entryOffset4, transactionOffset4, nextOffset4, CRC4). Pointer collision selalu menuju node yang lebih lama sehingga cycle ditolak. Key yang sama di-update; tombstone tetap disimpan. Semua data ukuran tetap little endian. Index dibangun ulang setiap mount dari transaksi journal yang telah diverifikasi, tidak menjadi sumber kebenaran transaksi dan tidak perlu flush per node untuk dianggap durable. Bila write/read/CRC index gagal, lookup kembali memindai journal. Lookup indexed tetap memeriksa CRC transaksi yang menjadi sumber nilai; transaksi lain diverifikasi pada mount. Main journal tidak dipotong atau diubah karena index hilang/rusak.

Penyalinan record ke transaksi memakai buffer32byte dan CRC/commit schema yang sama. Rebuild index, chain lookup, copy/save/generate masih perlu jatah kerja per tick dan uji latency target. Index mengurangi volume read pada host tetapi belum membuktikan responsiveness alat. Tidak ada garbage collection atau penghapusan data otomatis.

Baseline immutable direferensikan oleh session dan result, ditambah snapshot coeff/target/datum/identity. Delete baseline menulis Exists=0, tidak menghapus rows yang masih diperlukan history. ID history berasal dari sessionID, sehingga SAVE RESULT berulang tidak menggandakan record.

Operation index extension at the17November handoff: kind0/field0 index keys encode the64bit operation ID in object/index. Their node references the first journal entry and its transaction. A hit verifies the committed journal CRC and operation ID before acknowledging a duplicate. Zero kind/field are rejected in journal data to prevent namespace collisions. Missing/full/corrupt sidecars retain journal-scan fallback and rebuild semantics; schema1 stays unchanged.

17November optimization: index metadata with kind0/fieldExists/object=recordKind points to a committed entry with the maximum reserved object ID. The entry transaction is CRC-verified before use; a tombstoned object ID stays reserved. Missing/full/corrupt index falls back to the common verified journal scan. ClockAdjustment is optional field41, value21bytes: cause1 (None0, Invalid1, Backward2, Forward3, SampleDelay4, Sensor5, Restart6), observed wall-before8, observed wall-after8, monotonic4, all integers little-endian. GapStart/GapEnd remain ordered; raw clock-event endpoints preserve direction. Existing record layouts remain schema1.
