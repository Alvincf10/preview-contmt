# Penyesuaian panel ke protokol Arduino

Daftar persis apa yang berubah, dan apa yang tidak. Tidak ada perubahan desain.

## Yang TIDAK berubah

| | |
| --- | --- |
| PNG latar | tidak disentuh |
| Posisi, ukuran, font, warna semua field | tetap |
| Semua area sentuh dan aksinya | tetap |
| Tampilan yang dilihat operator | identik |

## Yang ditambah (tersembunyi, di luar layar)

Ditaruh di **reserve** — kolom di x≥484, tidak pernah tergambar, seperti `tMsg`
yang sudah ada di sana sejak awal.

| Nama | Tipe | Isi |
| --- | --- | --- |
| `tData` | Text 255 | semua nilai halaman itu, dipisah `\|` dari Arduino |
| `nBoot` | Number | token boot dari Arduino |
| `nView` | Number | versi data; berubah saat data berubah |
| `nAckSeq` | Number | seq yang di-ACK; **penanda data siap** |
| `nAckCode` | Number | kode status (0 = OK) |
| `nAckValue` | Number | nilai balasan (ID, token, jumlah baris) |

Kelima Number ini menggantikan `vBoot`, `vAck`, `vAckBoot`, dan `vStatus` yang
dipakai sekarang. `vSeq`, `vBusy`, `vRetry`, `vReqBoot`, `vRender` tetap dipakai —
itu milik panel sendiri, bukan Arduino.

## Yang berubah pada event

### 1. Menunggu data siap

Sekarang: panel membuka `vBusy` lalu menunggu `vAckBoot`/`vAck`.

Menjadi: panel membuka `vBusy`, Arduino menjawab dengan `nAckValue`, `nAckCode`,
lalu `nAckSeq`. Event `nAckSeq` yang menutup `vBusy`.

### 2. Memecah data

Event baru di setiap halaman, jalan saat `nAckSeq` berubah:

```
// Contoh pRT, kolom run: revisi|baseline|jml|parsial|tglMulai|jamMulai|...
spstr tData.txt,pInit.tNum.txt,"|",8
tM.txt=pInit.tNum.txt
spstr tData.txt,pInit.tNum.txt,"|",9
tFc.txt=pInit.tNum.txt
```

Satu pasang `spstr`+assign per kolom. `pRT` punya 13 kolom.

### 3. Request ke Arduino

Panel sekarang mengirim `CM1|boot|seq|page|view|VERB|arg`.

Arduino mengharapkan bentuk yang sama, **tapi**:
- `page` dikirim sebagai **nomor** (0–16) — Arduino menerima nomor, lalu memakai
  nama halaman sendiri. Ini sudah cocok.
- `PAGE_READY` harus `CM1|0|0|0|0|PAGE_READY` — **tanpa** `|2` di ujung. Sekarang
  panel mengirim `|2` (versi kontrak). Harus dihapus.

### 4. Perintah yang harus ditambah ke panel

Arduino butuh delapan perintah yang panel belum kirim:

| Perintah | Kapan | Untuk apa |
| --- | --- | --- |
| `GET\|source` | setelah PAGE_READY | minta isi halaman |
| `PAGE_READY` | tiap halaman dibuka | sudah ada, formatnya diperbaiki |
| `CLOCK_SET\|date\|clock` | pSet | set jam |
| `CONFIRM\|token` | dialog | konfirmasi hapus |
| `RETRY\|VERB\|rev` | setelah SAVE gagal | cari commit yang sudah ada |
| `ROW_FOCUS\|i` | pMatu | tandai baris aktif |
| `MEASURE_RESUME` | pStr | lanjutkan sesi |
| `STORAGE_RETRY` | pDev/pUser | coba mount SD lagi |

### 5. Perintah yang harus dihapus dari panel

Delapan perintah panel yang tidak dikenal Arduino:

| Perintah | Diganti dengan |
| --- | --- |
| `SELF_CHECK` | `GET\|status` |
| `DATUM_PICK` | tidak perlu — datum diedit lewat `FIELD_SET` |
| `GAP_RECONCILE` | `CHECK_SET` dengan kolom `gap` |
| `PAGE_ROWS` | `GET` dengan indeks absolut |
| `SESSION_RESUME` | `MEASURE_RESUME` |
| `SETTINGS_STEP` | `SETTINGS_SET` dengan nilai baru |
| `SETTINGS_TOGGLE` | `SETTINGS_SET` dengan 0/1 |
| `STORAGE_RESCAN` | `STORAGE_RETRY` |

## Skala pekerjaan

| Halaman | Field nilai | Kolom tData | Kerja |
| --- | --- | --- | --- |
| pInit | 4 | 19 | sedang |
| pUser | 3 | 3 | kecil |
| pNewB | 5 | 9 | kecil |
| pMat | 11 | 11 | sedang |
| pMatu | 31 | 30 | besar |
| pBaseR | 22 | 26 | besar |
| pSaveB | 24 | 8 | sedang |
| pSelB | 24 | 8 | sedang |
| pRT | 47 | 13 | besar |
| pStr | 11 | 13 | sedang |
| pHist | 30 | 7 | sedang |
| pHistD | 51 | 30 | besar |
| pSet | 7 | 3 | kecil |
| pDev | 3 | 3 | kecil |
| pMain, pBase, pKuat | 0 | 1 | kecil |

**273 field, sekitar 546 baris kode pemecah, di 17 halaman.**

## Urutan yang saya usulkan

1. **pInit + pUser + pMain** — buktikan handshake dan pemecahan bekerja, dengan 3
   kolom saja. Kalau ini benar, sisanya mekanis.
2. **pSelB** — daftar baseline, untuk membuktikan `ROW_*` dan `nAckValue`.
3. **pRT** — kasus terberat yang sering dipakai (13 kolom).
4. Sisanya.

Saya berhenti dan melapor setelah langkah 1, supaya kamu bisa memeriksa sebelum
saya lanjut ke 17 halaman.
