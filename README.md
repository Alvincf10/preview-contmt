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
- Panduan rakit di **Nextion Editor** → Simulate → Compile `.TFT`

File `.HMI` binary hanya bisa dibuat/disimpan oleh Nextion Editor; paket ini adalah sumber untuk dirakit di sana.

Lihat: [`nextion/README.md`](nextion/README.md)
