# Apakah HMI sudah sinkron dengan firmware?

Jawaban singkat: **belum.** Repo ini punya **dua firmware** yang berbicara dengan
**dua protokol berbeda**, dan panel yang saya bangun hanya bisa bicara ke salah
satunya.

Diukur dengan `python nextion/tools/check_sync.py`.

## Dua firmware, dua protokol

| | `firmware/ConMT` | `arduino/ConMT` |
| --- | --- | --- |
| Bahasa | C++ (host, AVR) | Arduino sketch |
| Panel dikendalikan lewat | `vBoot`, `vSeq`, `vAck`, `vRender` | `nBoot`, `nView`, `nAckSeq`, `tData` |
| Nilai ditampilkan lewat | satu Text per nilai (`tM`, `tFc`, `tS1`, …) | satu Text `tData` berisi kolom dipisah `|` |
| Halaman | `page 11` (nomor) | `page pRT` (nama) |
| Arah | **HMI sekarang mengikuti yang ini** | tidak cocok dengan HMI |

## Yang tidak cocok

**Variabel sinkronisasi.** Panel menulis dan membaca `vBoot/vSeq/vAck/vBusy/…`.
Arduino tidak punya satu pun dari itu; ia memakai `nBoot/nView/nAckSeq/nAckCode/nAckValue`.

**Cara nilai sampai ke layar.** Panel punya satu Text per nilai — `tM`, `tFc`,
`tS1`, `tTarget`, dan seterusnya. Arduino tidak mengisi field itu sama sekali; ia
mengirim **satu** `tData.txt` berisi semua kolom sekaligus, dan mengharapkan panel
memecahnya sendiri. Panel yang saya bangun tidak punya `tData`, dan tidak punya
kode untuk memecahnya.

**Delapan perintah tidak ada di Arduino:**

```
DATUM_PICK  GAP_RECONCILE  PAGE_ROWS  SELF_CHECK
SESSION_RESUME  SETTINGS_STEP  SETTINGS_TOGGLE  STORAGE_RESCAN
```

Termasuk `SELF_CHECK` — tanpa itu, Arduino tidak akan pernah memindahkan panel
dari splash, karena Arduino memang tidak mengenal perintahnya.

**Delapan perintah Arduino tidak dikirim panel:**

```
CLOCK_SET  CONFIRM  GET  MEASURE_RESUME  PAGE_READY  RETRY  ROW_FOCUS  STORAGE_RETRY
```

`PAGE_READY` paling penting: Arduino menunggu frame itu setiap kali halaman
berganti. Panel saya mengirimnya, tapi dalam bentuk `CM1|boot|0|0|0|PAGE_READY|2`
— Arduino mengharapkan `CM1|0|0|0|0|PAGE_READY` tanpa versi kontrak di ujung.

## Apa artinya

Kalau panel ini di-upload sekarang dan disambungkan ke Arduino dengan sketch
`arduino/ConMT`:

- panel menyala, menampilkan splash, lalu **berhenti** — `SELF_CHECK` tidak dikenali;
- kalau dilewati, halaman berpindah tapi **semua nilai tetap kosong** — Arduino
  menulis ke `tData`, yang tidak ada di panel;
- jam dan baterai tidak muncul — Arduino tidak menulis `tClock`/`tBatt`.

Jadi tidak ada satu pun nilai yang sampai ke layar.

## Tiga jalan keluar

**1. Pakai `firmware/ConMT`.** Ini yang sudah sinkron dengan panel: protokolnya
sama, nama field-nya sama, `SELF_CHECK` ada. Firmware ini sudah punya tes sendiri
(11 dari 13 lolos di sini; 2 gagal karena toolchain, bukan kode).

**2. Ubah `arduino/ConMT` agar bicara protokol panel.** Perlu:
- ganti `nBoot/nView/nAckSeq` menjadi `vBoot/vSeq/vAck`;
- kirim satu Text per nilai, bukan `tData`;
- tambahkan `SELF_CHECK`, dan tangani `SETTINGS_STEP`, `SETTINGS_TOGGLE`, `PAGE_ROWS`.

**3. Ubah panel agar mengikuti Arduino.** Perlu:
- tambah `tData` (Text 255 karakter) dan `nBoot/nView/nAckSeq` di 17 halaman;
- tulis kode Nextion untuk memecah `tData` menjadi field;
- sesuaikan seluruh event.

Jalan 3 paling mahal dan paling rapuh: memecah teks berpemisah di Nextion butuh
`substr` berantai, dan setiap kolom harus dihitung ulang bila urutannya berubah.

## Catatan

`arduino/CONTRACT.md` sudah menyebut arah yang benar untuk masa depan — ia
menunjuk ke `nextion/project.json` sebagai acuan nama halaman. Tapi isinya
menggambarkan protokol `tData` yang berbeda dari yang dipakai panel sekarang.
Dua dokumen kontrak yang hidup berdampingan adalah sumber kebingungan ini, dan
salah satunya harus jadi acuan tunggal.

Panel yang dibangun di repo ini mengikuti `firmware/hmi/manifest.json`, yang
dihasilkan dari `firmware/ConMT/src/hmi/Transport.h`.
