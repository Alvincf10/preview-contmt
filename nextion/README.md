# ConMT — Nextion HMI

Panel **480×800**, 17 page. Ada tiga lapis, dan penting tahu mana yang diedit:

- **`pages/` + `assets/pages/`** — build kit awal: koordinat, PNG desain. Ini
  sumber desain. Jangan diedit kecuali desainnya berubah.
- **`assets/clean/`** — salinan PNG tanpa angka contoh. Dihasilkan
  `clean_pictures.py`, dan ini yang dipakai panel.
- **`nxsrc/`** — HMI sebagai teks, **dihasilkan** `nx_source.py` dari ketiga
  sumber di atas. Build membaca folder ini.

`.HMI` dan `.TFT` adalah hasil build, bukan sumber.

> **`nxsrc/` ditimpa setiap `npm run hmi:source`.** Untuk mengubah tampilan,
> ubah sumbernya (desain, kontrak di `firmware/hmi`, atau peta di
> `nextion/tools/`), lalu regenerasi. Mengedit `nxsrc/` langsung hanya aman
> bila kamu tidak akan menjalankan `hmi:source` lagi.

## Mulai di sini

1. **[AGENT.md](./AGENT.md)** — alur edit → build → compile, perintah, dan aturan
   yang harus dijaga agent. Baca ini dulu.
2. **[SERIAL.md](./SERIAL.md)** — protokol MCU ↔ panel.
3. **[FLOW.md](./FLOW.md)** — alur layar.
4. **[BUILD.md](./BUILD.md)** — cara merakit manual di Nextion Editor, bila perlu.

## Isi folder

| Path | Isi |
|------|-----|
| `nxsrc/` | **Hasil generate**: page `.toml`, event `.nx`, gambar, font |
| `conmt.HMI` | project file untuk Nextion Editor, hasil `npm run hmi:build` |
| `conmt.tft` | firmware panel, hasil `npm run hmi:compile` |
| `pages/*.json` | koordinat + TouchCap dari build kit |
| `assets/pages/*.png` | background desain, apa adanya |
| `assets/clean/*.png` | background tanpa angka contoh, yang dipakai panel |
| `events/*.txt` | kode event versi kit |
| `tools/nx_source.py` | generator `nxsrc/` dari kit + `firmware/hmi` |
| `tools/clean_pictures.py` | hapus angka contoh dari PNG desain |
| `tools/rebuild.py` | jalankan generator + pembersihan dalam urutan benar |
| `project.json` | 17 page, resolusi 480×800 |
| `shared/statusCorners.json` | template `tClock` / `tBatt` |
| `assets/_unused/` | PNG lama, jangan diimport |

## Alur kerja

```bash
npm run hmi:source    # regenerasi nxsrc + bersihkan gambar (dua putaran)
npm run hmi:check     # validasi: layout, navigasi, lebar field, nilai kosong
npm run hmi:test      # tekan semua hotspot di simulator
npm run hmi:build     # nxsrc -> conmt.HMI
npm run hmi:compile   # nxsrc -> conmt.tft
npm run hmi:serve     # MCP: agent bisa mensimulasikan dan menekan layar
```

`npm run hmi:source` menulis ulang `nxsrc/` dari nol, jadi jangan dipakai setelah
mengedit `nxsrc/` secara manual. Untuk perubahan tetap, ubah sumbernya lalu
regenerasi.

## Catatan UI (parity React preview)

- **pRT**: ADD DAY, demo days, live M/Fc/%, logged days — tanpa elapsed.
- **pStr**: Fc + % target, avg = initial pour temp — tanpa status READY.
- **pHist/pHistD**: jumlah logged days + detail Time/Temp/M/Fc.
- Formula dihitung di **MCU**, bukan di HMI (`fc_FKZ = max(0,(a+b·ln(M))·FKZ)`).
