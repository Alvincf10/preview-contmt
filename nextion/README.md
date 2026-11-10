# ConMT — paket sumber Nextion (Windows)

Ini **bukan** file `.HMI` binary jadi. Nextion Editor hanya bisa membuat/menyimpan `.HMI` sendiri.  
Paket ini = **blueprint + aset + kode event** supaya kamu bisa rakit cepat di laptop Windows, lalu simulasikan di emulator Nextion.

## Apa yang ada di folder ini

| Path | Isi |
|---|---|
| `project.json` | Resolusi 480×800, daftar page |
| `assets/pages/*.png` | Background tiap layar (dari Figma 480×800) |
| `pages/*.json` | Komponen + koordinat TouchCap |
| `events/*.txt` | Kode event Nextion (`page xxx`) |
| `FLOW.md` | Alur navigasi |

## Cara build di Nextion Editor (Windows)

1. Install **Nextion Editor** (versi terbaru dari situs Itead).
2. **File → New** → pilih resolusi **Custom 480 × 800** (portrait).
3. Untuk tiap page di `project.json`:
   - Tambah page, rename sesuai `name` (contoh `pMain`).
   - Import PNG dari `assets/pages/` sebagai **page background** (atau komponen Picture 0,0,480,800).
   - Tambah **TouchCap** (area sentuh transparan) sesuai `x,y,w,h` di JSON.
   - Di event **Touch Press Event**, tempel isi file `events/...txt` (biasanya satu baris `page pXxx`).
4. Page pertama / boot: `pInit`.
5. Di `pInit`, aktifkan **Timer** (mis. 500ms) → setelah beberapa tick: `page pUser` (lihat `events/pInit_tm0.txt`).
6. **Debug → Simulate** untuk emulator di Windows.
7. Kalau sudah OK: **Compile** → dapat `.TFT` untuk upload ke panel.

## Catatan penting

- **HTML `select` tidak ada di Nextion.** Untuk Datum Temperature, pakai Text + list page / Number / keyboard Nextion.
- Data sensor realtime: MCU kirim perintah serial, contoh:  
  `tS1.txt="25.6"` + `0xFF 0xFF 0xFF`
- **pMatu SENSOR flow:** tap field Temperature (`mTempN` → `va0.val=N`) lalu `mSensor` mengirim `SEN` ke MCU. MCU tulis rata-rata ke `tTN.txt` (contoh `tT3.txt="25.7"`) + update `tHint.txt`. `mAddDay` mengirim `ADD`.
- Koordinat TouchCap di JSON adalah titik awal dari Figma; fine-tune 2–4px di Editor bila perlu.
- Emulator web React di root project tetap untuk preview UI; folder `nextion/` untuk target panel.

## Flow singkat (baseline)

`pInit` → `pUser` → `pMain` → `pBase` → `pNewB` → `pMat` → `pMatu` → `pBaseR` → `pSaveB`

## Flow kuat tekan

`pMain` → `pKuat` → `pSelB` → `pRT` → `pStr` → `pHist` → `pHistD`
