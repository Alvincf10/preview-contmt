# ConMT — Nextion Build Kit

Paket siap rakit untuk panel **480×800**.  
Bukan file `.HMI` binary — Nextion Editor (Windows) yang membuatnya. Isi folder ini sudah lengkap supaya **tidak perlu setup desain ulang**.

## Mulai di sini

1. Baca **[BUILD.md](./BUILD.md)** — langkah New Project → page → Compile.
2. Centang **[CHECKLIST.md](./CHECKLIST.md)** saat merakit.
3. Serial MCU: **[SERIAL.md](./SERIAL.md)**.
4. Alur layar: **[FLOW.md](./FLOW.md)**.
5. Inventaris: **[MANIFEST.json](./MANIFEST.json)** + **[hotspots.csv](./hotspots.csv)**.

## Isi folder

| Path | Isi |
|------|-----|
| `project.json` | 17 page, resolusi 480×800 |
| `assets/pages/*.png` | Background tiap layar |
| `pages/*.json` | Komponen + TouchCap + event map |
| `events/*.txt` | Kode event (copy ke Editor) |
| `shared/statusCorners.json` | Template `tClock` / `tBatt` |
| `assets/_unused/` | PNG lama, jangan diimport |

## Validasi (sebelum copy ke Windows)

```bash
npm run validate:nextion
```

## Setelah .HMI ada

Simpan `ConMT.hmi` dari Editor. Update berikutnya: ganti PNG/event → Compile → `.TFT`. Tidak perlu New Project lagi.

## Catatan UI (parity React preview)

- **pRT**: ADD DAY, demo days, live M/Fc/%, logged days — tanpa elapsed.
- **pStr**: Fc + % target, avg = initial pour temp — tanpa status READY.
- **pHist/pHistD**: jumlah logged days + detail Time/Temp/M/Fc.
- Formula dihitung di **MCU**, bukan di HMI (`fc_FKZ = max(0,(a+b·ln(M))·FKZ)`).
