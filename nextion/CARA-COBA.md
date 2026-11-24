# Cara mencoba HMI

Ada empat cara, dari yang paling cepat sampai yang paling mendekati kenyataan.
Kolom "terbukti" menunjukkan apa yang benar-benar sudah saya jalankan, bukan
perkiraan.

| Cara | Butuh | Bisa klik? | Terbukti |
| --- | --- | --- | --- |
| 1. Lihat render 17 page | Python | tidak | ya |
| 2. Editor: buka `.HMI` | Nextion Editor | ya, di Editor | ya |
| 3. Simulator: tekan tombol | nxwright + MCP | ya, dan dibaca frame-nya | ya |
| 4. Panel fisik | panel + kabel | ya, sungguhan | belum |

---

## 1. Lihat tampilannya (paling cepat)

```bash
npm run hmi:render
```

Menulis 17 PNG ke `%TEMP%\pages\`. Buka dan bandingkan dengan desain. Ini yang
saya pakai untuk memverifikasi tata letak; tidak butuh Editor, tidak butuh panel.

Untuk membandingkan satu halaman dengan gambar desainnya:

```bash
python nextion/tools/compare_page.py pMat
```

Menulis gambar berdampingan: kiri desain, kanan hasil build.

---

## 2. Buka dan lihat di Nextion Editor

```bash
start "" "C:\Program Files (x86)\Nextion Editor\Nextion Editor.exe" nextion\conmt.HMI
```

Yang bisa kamu lakukan:

- **Lihat setiap page.** Pilih di panel Page di kanan. 17 page sudah ada.
- **Lihat setiap komponen.** Panel Attribute menunjukkan `objname`, posisi, ukuran,
  dan isi teks. Ini cara memastikan nama field sesuai kontrak (`tClock`, `tM`, …).
- **Jalankan simulator Editor.** Klik **Debug → Simulate**. Kamu bisa menekan
  tombol dan melihat halaman berpindah.

**Penting — kenapa simulator Editor terasa "macet":** panel ini menunggu MCU.
Halaman `pInit` sengaja tidak punya tombol: kontrak menetapkan bahwa MCU yang
memegang navigasi. Tanpa MCU menjawab, panel menyala, menampilkan splash, dan
berhenti di situ. Itu **bukan kerusakan**.

Kalau ingin menelusuri layar tanpa MCU, buka page yang dituju langsung di Editor,
lalu **Debug → Simulate** dari page itu.

---

## 3. Tekan semua tombol tanpa hardware

```bash
npm run hmi:test
```

Ini menjalankan simulator nxwright, menekan **setiap** hotspot di **setiap** page,
lalu membaca byte yang dikirim layar. Hasil yang benar:

```
153 hotspots tapped, 66 past the screen edge, 0 problem(s)
```

Artinya setiap tombol yang terlihat mengirim request CM1 yang sah. Ini uji yang
saya pakai untuk membuktikan tombol berfungsi.

Untuk melihat satu halaman secara visual sambil menekannya, pakai MCP:

```bash
npm run hmi:serve
```

Lalu di Cursor, agent bisa memanggil `start_simulation`, `screen`, dan `tap`.
Ini bukan untuk kamu klik manual, tapi untuk memeriksa perilaku.

---

## 4. Panel fisik

Belum ada panel terhubung ke komputer ini (`nxwright ports` tidak menemukan port).
Kalau panel sudah tersambung:

```bash
# cek panel terdeteksi
nxwright ports

# upload firmware
nxwright upload nextion\conmt.tft --port COM5

# atau, kalau port belum jelas
nxwright upload nextion\conmt.tft --port COM5 --find
```

Setelah upload, panel akan menyala dan menampilkan splash. Untuk benar-benar
memakainya, panel butuh MCU di ujung kabel serial — firmware ConMT di
`firmware/ConMT/`.

---

## Yang perlu kamu tahu sebelum mencoba

**Nilai di layar berasal dari MCU.** HMI tidak menghitung apa pun. `tM`, `tFc`,
`tClock` semuanya diisi oleh perintah serial. Tanpa MCU, field tetap kosong.

**Gambar desain sudah memuat angka contoh.** PNG-nya punya `35.4 MPa`, `1,245`,
`03:25:10` tercetak. Field di HMI transparan dan kosong, jadi saat MCU menulis
nilai asli, **angkanya bertumpuk** dengan angka contoh di gambar. Ini keterbatasan
pendekatan image-based: gambar latar tidak bisa diubah saat runtime.

Kalau nanti angka bertumpuk mengganggu, ada dua jalan keluar:
- gambar ulang PNG tanpa angka contoh (paling bersih), atau
- beri field latar solid sewarna panel agar menutupi angka contoh di belakangnya.

**Yang belum bisa saya pastikan:** tampilan di panel fisik. Semua bukti di atas
dari render dan simulator. Font, warna 565, dan ketepatan sentuh baru terbukti
saat `.tft` benar-benar jalan di layar.

---

## Urutan yang saya sarankan

1. `npm run hmi:render` — lihat 17 halaman, cocokkan dengan desain.
2. Buka di Editor, klik-klik antar page untuk memeriksa nama dan posisi komponen.
3. `npm run hmi:test` — pastikan semua tombol mengirim.
4. Kalau sudah ada panel: upload, lalu sambungkan MCU dan uji handshake CM1.
