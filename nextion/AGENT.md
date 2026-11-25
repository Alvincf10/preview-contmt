# ConMT HMI — source yang bisa diedit agent

Untuk pasangan Arduino 1.0.1 dan NX8048K050, gunakan `nxsrc-K050` serta generator `tools/k050_protocol.py`. Protokol pasangan ini mengikuti `arduino/CONTRACT.md`. Variabel komunikasi global berada di `pInit`. Generator, manifest, dan perintah `hmi:source` pada uraian lama di bawah memakai target awal yang terpisah. Petunjuk pasangan K050 tercatat pada `NX8048K050-README.txt`.

`.HMI` adalah biner tertutup: tidak bisa di-diff, tidak bisa diedit Cursor, dan tidak
bisa dibaca agent. Folder `nextion/nxsrc/` adalah HMI yang sama sebagai teks. Agent
(dan kamu) mengedit teks itu; `nxwright` membangunnya kembali menjadi `.HMI`, atau
langsung menjadi `.TFT` untuk panel.

## Alurnya

```
preview React (src/)          desain: sumber kebenaran posisi dan navigasi
      |
      |  npm run hmi:layout
      v
nextion/tools/layout.json     kotak tiap elemen di kanvas 480x800
nextion/tools/nav.json        tujuan tiap tombol
      |
      |  npm run hmi:source
      v
nextion/assets/clean/         PNG tanpa angka contoh       <- yang dipakai panel
nextion/nxsrc/                teks: page, komponen, event  (dihasilkan)
      |
      |  npm run hmi:build
      v
nextion/conmt.HMI             project file untuk Nextion Editor
      |
      |  npm run hmi:compile
      v
nextion/conmt.tft             yang di-upload ke panel
```

Yang diedit adalah **sumbernya** — desain (`pages/`, `assets/pages/`), kontrak
(`firmware/hmi/`), atau peta di `nextion/tools/`. `nxsrc/` dihasilkan dari itu,
dan `npm run hmi:source` menimpanya. Mengedit `nxsrc/` langsung hanya aman bila
kamu tidak akan menjalankan `hmi:source` lagi.

Agent masuk lewat dua pintu:

1. **File teks** — `nxsrc/pages/*.page.toml` (komponen) dan `*.nx` (event).
2. **MCP** — `nxwright mcp` menyimulasikan app, menekan tombol, dan mengembalikan
   gambar layar. Agent bisa melihat akibat perubahannya, bukan menebak.

## Nilai default kosong, diisi sistem

Tidak ada satu pun nilai di panel yang tampil sebelum sistem mengisinya. Itu
berlaku dua lapis, dan keduanya diperiksa otomatis:

**Lapis 1 — field.** Setiap `Text` bernilai kosong saat dibangun. Yang berisi teks
hanya empat baris status splash, dan itu pun berbentuk `Checking Sensors: --`,
supaya jelas belum ada jawaban.

**Lapis 2 — gambar.** Desain aslinya **menggambar angka contoh** ke dalam PNG:
`35.4 MPa`, `1,245`, `03:25:10`. Field transparan tidak menutupinya, jadi operator
akan melihat angka palsu yang tak bisa dibedakan dari bacaan asli. `clean_pictures.py`
menghapus 30.000+ piksel teks contoh itu dari salinan gambar, dengan aturan:

- hanya piksel putih (teks contoh) yang dihapus; ikon oranye, garis, dan gradien
  panel tetap utuh;
- hanya di dalam kotak field yang memang duduk di atas angka contoh;
- celah huruf diisi dari piksel tetangganya, jadi gradien panel tetap mulus.

Gambar asli disimpan di `assets/pages/`, hasil bersih di `assets/clean/`, dan build
memakai yang bersih.

**Lapis 3 — lebar.** Desain memberi kotak seukuran contoh yang digambarnya, dan
contoh seperti `—` jauh lebih pendek daripada `25.7 °C`. `find_narrow.py` menghitung
lebar yang dibutuhkan tiap field, dan generator melebarkan kotak ke kanan sampai
cukup — berhenti di apa pun yang digambar desain di sebelahnya.

## Checklist dibaca dari sistem

Splash tidak mencentang apa pun sendiri. Timer `tm0` mengirim `SELF_CHECK`, MCU
memeriksa sensor, clock, dan hardware, lalu mengembalikan status masing-masing.
Empat baris di splash menampilkan hasil itu, dan panel **tetap di splash** selama
ada yang gagal.

| Yang diperiksa | Gagal bila |
| --- | --- |
| Sensor | tidak ada bacaan segar (< 5 detik) |
| Clock | RTC belum tahu waktu |
| Hardware | perangkat melaporkan error |

## Unit test

```bash
python nextion/tests/test_values.py     # 10 tes: nilai kosong + checklist
python firmware/tools/host_tests.py     # tes firmware, termasuk splash
```

Yang diperiksa `test_values.py`: tidak ada field berisi teks contoh; gambar bersih
ada untuk 17 page; gambar bersih tidak merusak brand strip atau tepi halaman; splash
bertanya ke MCU; splash tidak pernah melompat halaman sendiri; tiap cek punya field
sendiri; dan field status berada di dalam panel splash.

## Yang sudah terbukti, bukan diklaim

| Pemeriksaan | Hasil |
| --- | --- |
| `nxwright check` | 0 error, 0 warning |
| Unit test nilai & checklist | **10/10 lolos** |
| Field berisi teks contoh | **0** (kecuali 4 baris status splash) |
| Piksel angka contoh di gambar | **0** |
| Tombol di layar punya tap area | **76/76** |
| Hotspot meleset dari tombolnya | **0** (diukur per kotak) |
| Hotspot bertumpuk | **0** |
| Jam & baterai di 17 page | **17/17** |
| Hotspot ditekan di simulator | **83/83 mengirim frame valid** |
| Firmware: tes splash | **6/6 lolos** |
| `.TFT` | 8,6 MB, series P |

## Splash memeriksa sebelum pindah halaman

Panel menyala di `pInit` dan **tidak** pindah sendiri. Timer `tm0` mengirim
`SELF_CHECK` berulang; MCU memeriksa tiga hal dan baru memindahkan halaman kalau
ketiganya siap:

| Yang diperiksa | Gagal bila |
| --- | --- |
| Sensor | tidak ada bacaan segar (< 5 detik) |
| Clock | RTC belum tahu waktu |
| Hardware | perangkat melaporkan error |

Empat field di splash menampilkan hasilnya, dan status yang gagal **menahan**
panel di splash — jadi sensor mati terlihat, bukan tersembunyi di balik halaman
berikutnya.

Karena PNG splash sudah penuh dengan checklist contoh, keempat status itu
menggantikan barisnya (latar solid sewarna panel). Tanpa itu, angka contoh akan
bertumpuk dengan status asli.

Firmware menjalankan tesnya sendiri:

```bash
python firmware/tools/host_tests.py            # semua
python firmware/tools/host_tests.py splash     # hanya self-check
```

Dua tes gagal karena lingkungan, bukan kode: `audit` tidak bisa di-build dengan
zig (nama `finite` bentrok dengan glibc), dan `disk_index` butuh file descriptor
asli yang tidak tersedia di WSL.

## Perintah

```bash
npm run hmi:layout     # baca ulang desain dari preview (perlu `npm run dev` hidup)
npm run hmi:source     # regenerasi nxsrc dari desain + kontrak
npm run hmi:check      # cek nxwright + layout + navigasi
npm run hmi:test       # tekan semua hotspot di simulator
npm run hmi:build      # nxsrc -> conmt.HMI
npm run hmi:compile    # nxsrc -> conmt.tft
npm run hmi:render     # render 17 page jadi PNG untuk dibandingkan dengan desain
npm run hmi:serve      # MCP server untuk agent
```

Sekali saja, pasang toolchain-nya:

```bash
git clone https://github.com/nixiewright/nxwright
cd nxwright && pip install -e .
npx playwright install chromium   # untuk membaca layout dari preview
```

## Tombol: label dan aksinya di kotak yang sama

Panel digambar sebagai foto dengan area sentuh tak terlihat di atasnya. Area yang
duduk **di samping** tombolnya, bukan di atasnya, adalah kegagalan yang paling
cepat terasa: tombol terlihat, ditekan, dan tidak terjadi apa-apa.

`check_hotspot_fit.py` mengukur setiap area sentuh terhadap tombol yang digambar
dan melaporkan yang menutupi kurang dari 55% tombolnya. Hasilnya **0**.

Dua kesalahan yang sempat membuat tombol meleset, dan cara memperbaikinya:

**1. Dua sumber koordinat yang berbeda.** `extract_nav.mjs` mengklik tombol untuk
mencatat tujuannya, dan klik itu mengubah data contoh di `localStorage` — kartu
bertambah, daftar bergeser. Pembacaan berikutnya memberi posisi yang berbeda 38px.
Sekarang setiap pemuatan mengosongkan `localStorage`, jadi kedua extractor
membaca layar yang sama.

**2. Tombol yang digambar di luar layar.** `nav.json` memuat baris tabel yang
desainnya menggambar sampai y=1800. Area sentuh untuk baris itu hanya bisa
diletakkan di atas tombol nyata, jadi `plan_hotspots.py` melewatinya. Tombol di
layar tetap mendapat area sentuh: **76/76**.

## Jam dan baterai

Kedua field ada di **17 page**, di (14,70) dan (378,70), tanpa latar. Isinya
kosong saat dibangun karena **MCU yang mengisinya** — `Transport::renderField`
mengirim `tClock` dan `tBatt` di setiap halaman.

Konsekuensinya: di Nextion Editor, tanpa MCU terhubung, kolom itu **tampak
kosong**. Itu bukan field yang hilang. `check_corners.py` memeriksa kedua hal itu
di 17 page.

## Cara kerja penempatan

Posisi tidak ditebak dari piksel PNG. `extract_layout.mjs` membuka preview di
browser, lalu mencatat kotak setiap elemen teks, input, dan tombol relatif kanvas
480×800. Jam dan angka acak dibekukan supaya hasilnya sama setiap kali dijalankan.

`layout_map.py` memetakan nama field kontrak (`tTarget`, `tCem`) ke elemen desain
lewat **teks contohnya** (`"30 MPa"`, `"385"`), bukan lewat urutan. Kalau desain
berubah sehingga teks itu hilang, build gagal dengan nama page dan field — bukan
memindahkan nilai ke tempat yang salah tanpa suara.

### Tiga aturan yang menentukan hasilnya

**1. Field yang tidak digambar desain tidak mendapat tempat di layar.**
Field seperti `tMsg`, `tMsg`, dan `tRid*` ada karena MCU menulis ke namanya, tapi
desain tidak menggambar kotak untuknya. Semuanya masuk **reserve**: kolom di luar
tepi kanan, dengan `sta = 3` (tanpa latar) dan teks kosong. Kalau ditaruh di layar,
layar penuh kotak putih dan tombol di bawahnya mati.

**2. Hotspot harus ditulis paling akhir.**
Komponen yang lebih akhir menerima sentuhan. Hotspot yang ditulis sebelum sebuah
field akan tertutup, dan tombolnya mati. Generator menulis semua hotspot di akhir
daftar.

**3. Hotspot baris hanya menutupi selnya sendiri.**
Menekan kolom Fc tidak boleh membuka editor temperature. `mTemp*` di `pMatu`
karena itu hanya menutupi sel Temperature (87 px), bukan seluruh baris.

Baris daftar yang desainnya tidak gambar (kartu riwayat ke-2 dan seterusnya)
**tidak** mendapat hotspot baru: menaruhnya di mana pun akan menutupi sesuatu.
Aksinya tetap tersedia lewat `HISTORY_PICK` dari baris yang terlihat.

## Aturan yang harus dijaga agent

- **Jangan edit `conmt.HMI` atau `conmt.tft`.** Keduanya hasil build. Yang diedit
  selalu `nxsrc/`.
- **Nama komponen adalah kontrak.** MCU menulis ke `tClock.txt`, `tM.txt`,
  `vSeq.val` lewat nama itu. Ganti nama = MCU berhenti bicara ke field tersebut.
- **Kapasitas teks.** `txt_maxl` harus memuat nilai terpanjang yang mungkin dikirim
  MCU.
- **Hotspot harus di akhir daftar komponen.** Komponen yang lebih akhir menerima
  sentuhan, jadi hotspot yang ditulis sebelum sebuah field akan tertutup dan
  tombolnya mati. Generator sudah mengurus ini; jangan diubah manual.
- **Satu request aktif.** Snippet event memakai `vBusy`/`vSeq`; jangan menambah
  command kedua sebelum yang pertama di-ACK.
- **Frame maksimal 192 byte** termasuk LF.
- **Jalankan `npm run hmi:check` dan `npm run hmi:test` sebelum build.**
- **Splash tidak boleh pindah sendiri.** Panel menunggu `SELF_CHECK` dijawab `Ok`
  oleh MCU. Jangan tambahkan event yang melompat halaman dari `pInit`: itu
  menyembunyikan sensor mati di balik halaman berikutnya.

## Batas yang jujur

- **64 hotspot berada di luar tepi layar.** Itu baris tabel `pHistD` dan `pMatu`
  yang desainnya menggambar sampai ke bawah; panel 800 px tidak menampilkannya
  sekaligus. Tombolnya ada dan berfungsi saat baris itu masuk layar, tetapi
  paginasi belum dibuat — itu pekerjaan berikutnya, di firmware dan HMI bersama.
- **Belum diuji di panel fisik.** Yang terbukti: `.TFT` valid, dibaca balik oleh
  `nxwright tft-read`, dan setiap hotspot mengirim frame yang benar di simulator.
  Perilaku UART, timing ACK, dan timer retry baru terbukti di hardware.
- **Timer retry hanya ada di `pInit`.** Kontrak meminta timer di page aktif.
- **Waktu di layar berasal dari MCU.** HMI tidak punya RTC; `tClock` dan `tNowT`
  menampilkan apa yang dikirim MCU.
- **Navigasi maju ditentukan firmware.** Panel mengirim verb (`RESULT_SAVE`,
  `MEASURE_START`); `Controller.cpp` yang memindahkan page setelah aksinya
  berhasil. Tabel `back[]` di sana yang menentukan tujuan BACK, dan sudah cocok
  dengan desain.
