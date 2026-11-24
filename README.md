# ConMT — Concrete Maturity Monitoring

Dua jalur di repo ini:

## 1. Emulator web (preview UI)

```bash
npm install
npm run dev
```

Buka http://127.0.0.1:5173/ — canvas **480×800**, font Inter.

## 2. Paket Nextion (build di Windows)

Folder [`nextion/`](nextion/README.md):

- Aset page PNG 480×800
- Definisi TouchCap + event `page ...`
- `nxsrc/` — HMI yang sama sebagai teks, yang bisa diedit Cursor dan agent
- `conmt.HMI` + `conmt.tft` — hasil build, siap dibuka di Editor / di-upload

Baca [`nextion/AGENT.md`](nextion/AGENT.md) untuk alur edit → build → compile dan
untuk aturan yang harus dijaga agent.

Lihat: [`nextion/README.md`](nextion/README.md)

---

## Acuan perhitungan (Excel)

File lab / kroscek rumus (sumber kebenaran perhitungan):

[`docs/acuan/Syarat-Kroscek-Perhitungan-ConMT-Data-Real.xlsx`](docs/acuan/Syarat-Kroscek-Perhitungan-ConMT-Data-Real.xlsx)

Sheet utama: **Buat Rumus Maturitas versi 2**, **MAPE**, **Kesimpulan**.

Implementasi di app mengikuti rumus di bawah (lihat juga `src/maturityFit.ts`).

### 1. Maturity Index — Nurse–Saul

Suhu rata-rata antar dua titik (trapezoid), dikurangi datum \(T_0\), dikali selang waktu:

\[
\Delta M_i = \left(\frac{T_i + T_{i-1}}{2} - T_0\right) \cdot \Delta t_i
\]

\[
M = \sum \Delta M_i \quad (°C·jam)
\]

- \(T\) = suhu (°C)
- \(T_0\) = datum temperature (°C)
- \(\Delta t\) = selisih umur (jam)
- Titik pertama: \(M = 0\)

Excel (kolom H→I): `H = (((E_i+E_{i-1})/2)-T0)*Δt`, `I = H + I_prev`.

### 2. Prediksi kuat tekan — regresi log

Dari pasangan lab \((M, f'c)\):

\[
f'c_{NS} = a + b \cdot \ln(M)
\]

- \(a\), \(b\) = koefisien fit (Excel: `a = F65`, `b = F64`; `J = $F$65+$F$64*LN(I)`)
- Syarat fit: \(M > 0\), \(f'c > 0\)
- \(R^2\) ideal ≥ 0,90 (syarat di sheet Kesimpulan)

### 3. Koreksi FKZ (Faktor Koreksi Zakki)

Di Excel, prediksi final memakai koreksi per umur (Hari ke-):

\[
\text{Error} = \frac{f'c_{NS} - f'c_{\text{aktual}}}{f'c_{\text{aktual}}}
\]

\[
FKZ = \frac{1}{1 + \text{Error}} = \frac{f'c_{\text{aktual}}}{f'c_{NS}}
\]

\[
f'c_{FKZ} = f'c_{NS} \cdot FKZ
\]

- Tabel FKZ disusun saat kalibrasi baseline (umur yang punya crushing test)
- Saat prediksi lapangan: pilih FKZ menurut **Day** log (exact). Jika kosong, pakai **hari kalibrasi berikutnya** (maju); contoh Day 5 & 7 ada, Day 6 kosong → × FKZ Day 7. Lewat umur terakhir → FKZ day terakhir. Tabel kosong → \(FKZ = 1\)
- Di UI: jika hasil \(f'c < 0\) ditampilkan **0**

Excel: kolom `W = T * Q` dengan `Q = 1/(1+U)`; MAPE membandingkan *fc Prediksi Maturitas* vs *fc Prediksi Koreksi FKZ*.

### 4. Alur di aplikasi

| Tahap | Rumus |
| --- | --- |
| Baseline lab | Hitung \(M\), fit \(a,b\), bangun tabel FKZ per day |
| Realtime log | Checkpoint Day + waktu + suhu → akumulasi \(M\) |
| Predicted Fc' | \(f'c_{FKZ} = \max(0,\ (a + b\ln M)\cdot FKZ)\) |

---

## Struktur singkat

- `src/` — UI React + perhitungan maturity
- `docs/acuan/` — Excel acuan rumus
- `nextion/` — paket HMI Nextion
- `public/` — aset gambar / logo
