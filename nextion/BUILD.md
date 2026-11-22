# ConMT Nextion — Build Kit (Windows)

Paket `nextion/` sudah lengkap: aset PNG, koordinat TouchCap, event code, serial map.  
Tujuan: di laptop Windows **tinggal rakit → Simulate → Compile**. Tidak perlu desain ulang.

> Format `.HMI` hanya bisa dibuat/disimpan oleh **Nextion Editor** (proprietary).  
> Linux/CI tidak bisa emit binary `.HMI`. Setelah sekali dirakit di Editor, file `.HMI` disimpan dan next update = buka project → Compile.

---

## 0. Prasyarat (sekali saja)

1. Install [Nextion Editor](https://nextion.tech/nextion-editor/) di Windows.
2. Copy seluruh folder `nextion/` ke Windows (USB/zip `conmt-nextion-kit.zip`).
3. Model panel: sesuaikan di New Project (Enhanced / Discovery). Resolusi wajib **480 × 800** portrait.

---

## 1. Buat project (sekali)

1. **File → New** → Custom → **480 × 800**.
2. Rename page default jadi `pInit`.
3. Tambah page baru sampai total **17**, nama persis:

| # | Page name | Background PNG |
|---|-----------|----------------|
| 0 | `pInit` | `assets/pages/00_init.png` |
| 1 | `pUser` | `assets/pages/01_user_info.png` |
| 2 | `pMain` | `assets/pages/02_main_menu.png` |
| 3 | `pBase` | `assets/pages/03_baseline.png` |
| 4 | `pNewB` | `assets/pages/04_new_baseline.png` |
| 5 | `pMat` | `assets/pages/05_material_data.png` |
| 6 | `pMatu` | `assets/pages/06_maturity_data.png` |
| 7 | `pBaseR` | `assets/pages/07_baseline_result.png` |
| 8 | `pSaveB` | `assets/pages/08_saved_baseline.png` |
| 9 | `pKuat` | `assets/pages/09_kuat_tekan.png` |
| 10 | `pSelB` | `assets/pages/10_select_baseline.png` |
| 11 | `pRT` | `assets/pages/11_realtime.png` |
| 12 | `pStr` | `assets/pages/12_strength_result.png` |
| 13 | `pHist` | `assets/pages/13_history.png` |
| 14 | `pHistD` | `assets/pages/14_history_detail.png` |
| 15 | `pSet` | `assets/pages/15_settings.png` |
| 16 | `pDev` | `assets/pages/16_device_info.png` |

4. Set **boot page** = `pInit`.

---

## 2. Per page (copy-paste mechanical)

Untuk **setiap** page di `pages/<name>.json`:

1. **Background** — Import PNG sebagai Picture `bg` di `x=0 y=0 w=480 h=800`, atau set sebagai page background.
2. **Status HUD** — Salin `tClock` + `tBatt` dari `shared/statusCorners.json` (sudah ada di tiap page JSON).
3. **Text / Number / Variable** — Tambah semua komponen non-TouchCap sesuai JSON (`objname` harus sama persis — MCU memakai nama ini).
4. **TouchCap** — Untuk tiap `type: TouchCap`, buat hotspot dengan `x,y,w,h` dari JSON (atau dari `hotspots.csv`).
5. **Event** — Di Touch Press Event, tempel isi file di kolom `events` (path `events/*.txt`). Jangan tulis ulang — copy verbatim.
6. **Timer di pInit** — Tambah Timer `tm0` (mis. 500 ms). Timer Event = isi `events/pInit_tm0.txt`.

Referensi cepat koordinat semua tombol: **`hotspots.csv`**.

---

## 3. Simpan & uji

1. **File → Save As** → `ConMT.hmi` (simpan di folder yang sama dengan kit, atau `build/`).
2. **Debug → Simulate** — klik tiap tombol; pastikan navigasi sesuai `FLOW.md`.
3. **Compile** → hasilkan `.TFT`.
4. Upload `.TFT` ke panel (microSD / USB / Editor upload tool sesuai model).

---

## 4. Setelah .HMI sudah ada (update berikutnya)

1. Ganti PNG di Picture Resource bila UI berubah.
2. Sesuaikan koordinat TouchCap dari `hotspots.csv` bila perlu.
3. Update event text dari `events/*.txt`.
4. **Compile** ulang → `.TFT` baru.

Tidak perlu New Project lagi.

---

## 5. Validasi kit sebelum bawa ke Windows

Di repo (Linux/Mac):

```bash
npm run validate:nextion
```

Harus exit 0: semua page, asset, event file, dan hotspot lengkap.

---

## Formula (MCU, bukan HMI)

HMI hanya tampil. MCU hitung:

- Nurse–Saul **M** dari checkpoint suhu
- `fc_NS = a + b · ln(M)`
- `fc_FKZ = max(0, fc_NS · FKZ)` — FKZ missing → pakai next day forward
- `% = (fc_FKZ / TargetFc) · 100`

Acuan Excel: `docs/acuan/`. Detail serial: `SERIAL.md`.
