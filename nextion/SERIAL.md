# ConMT — Serial protocol (MCU ↔ Nextion)

Setiap perintah ke HMI diakhiri **`0xFF 0xFF 0xFF`**.

## Global (semua page)

| Arah | Command | Keterangan |
|------|---------|------------|
| MCU→HMI | `tClock.txt="14:32"` | Jam HUD |
| MCU→HMI | `tBatt.txt="87%"` | Baterai HUD |

## pNewB — New baseline

| Arah | Command | Keterangan |
|------|---------|------------|
| HMI→MCU | `TEMP` | Buka picker datum temperature |
| MCU→HMI | `tTemp.txt="-20"` | Tulis nilai yang dipilih |
| MCU→HMI | `tName.txt` / `tFc.txt` | Nama baseline & target |

## pMatu — Maturity data (baseline)

| Arah | Command | Keterangan |
|------|---------|------------|
| HMI→MCU | `SEN` | Isi suhu baris aktif `va0.val` |
| HMI→MCU | `ADD` | Tambah baris hari |
| MCU→HMI | `tT0.txt` … `tT5.txt` | Sel suhu |
| MCU→HMI | `tHint.txt="..."` | Status singkat |

## pRT — Realtime measurement

| Arah | Command | Keterangan |
|------|---------|------------|
| HMI→MCU | `ADD` | Log day berikutnya |
| HMI→MCU | `DEMO` | Isi semua day dari baseline/Excel |
| HMI→MCU | `NEXT` | Finalize; `endMs` = last log |
| MCU→HMI | `tS1/tS2/tS3/tAvg.txt` | Sensor live |
| MCU→HMI | `tM.txt` / `tFcLive.txt` / `tPctLive.txt` | Prediksi live |
| MCU→HMI | `tBaseName/tTarget/tDatum.txt` | Baseline aktif |
| MCU→HMI | `tPourDate/tPour/tInitTemp.txt` | Locked at START |
| MCU→HMI | `tCurDate/tCurTime/tCurTemp.txt` | Live |
| MCU→HMI | `tL0`…`tL3.txt` | Baris logged days |
| MCU→HMI | `tLogCount.txt` / `tHint.txt` | Meta |

## pStr — Strength result

| Arah | Command | Keterangan |
|------|---------|------------|
| HMI→MCU | `SAVE` | Persist ke history |
| MCU→HMI | `tFc.txt` / `tPct.txt` / `tAvg.txt` / `tM.txt` | Hasil |
| MCU→HMI | `tBaseName/tTarget/tDatum.txt` | Baseline |

## pHist / pHistD

| Arah | Command | Keterangan |
|------|---------|------------|
| HMI→MCU | `HSEL` | Pilih baris `vaSel.val` |
| HMI→MCU | `DETAIL` | Buka detail |
| MCU→HMI | `tH0`…`tH3.txt` | Kartu history |
| MCU→HMI | `tTestId/tDate/tTime/tOp/tProj` | Meta detail |
| MCU→HMI | `tFc/tAvg/tM` + `tL0`…`tL5` | Hasil + day logs |

## Aturan bisnis (MCU)

1. Day 0 = saat tuang, **M = 0**.
2. ADD DAY: auto temp dari baris baseline hari itu, fallback rata-rata sensor.
3. Elapsed / result **lock ke last logged checkpoint**, bukan waktu tekan NEXT.
4. `fc_FKZ = max(0, (a + b·ln(M)) · FKZ)`.
5. FKZ kosong di hari N → pakai FKZ hari berikutnya yang ada (forward fill).
6. `% = (Fc / Target) · 100`.
