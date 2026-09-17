# Blok G — Positioning (COT) — Panduan Edukasi

> Bagian dari seri `docs/explained/`. Ditulis untuk pembelajar non-finance yang ingin paham menyeluruh
> sampai bisa menantang keputusan desain. Rujukan teknis: DATA-SPEC.md §7 (Blok G) + §18.1 (VOI harian),
> §18.3 (dataset Disagg); BUILD-PLAN.md §2 (skema `cot_raw`/`cot_snapshots`/`voi_daily`) + §3 (pipeline Blok G).
> Semua kode kontrak dan perilaku endpoint di bawah = hasil live-test 2026-08-29/30, bukan teori.

---

## 1. Kenapa blok ini ada

Semua blok A–F menjawab satu pertanyaan: **"kondisi dunia seperti apa sekarang?"** (rate, yield riil,
inflasi, pertumbuhan, likuiditas, stress). Blok G menjawab pertanyaan yang berbeda dan sama pentingnya
untuk seorang swing trader:

> **"Siapa saja yang sudah masuk pasar ini, dan seberapa penuh lift-nya?"**

### Analogi lift

Harga itu seperti lift. Blok A–F memberitahu Anda arah gravitasi (fundamental). Tapi ada satu hal yang
fundamental tidak bisa beri tahu: **berapa orang yang sudah ada di dalam lift**.

- Kalau lift sudah padat penumpang yang semuanya mau naik (*crowded long*), sekali ada satu orang
  berteriak "kebakaran!" — semua menekan tombol turun bersamaan dan lift jatuh lebih cepat dari
  gravitasinya sendiri. Ini yang disebut *long liquidation* / flushing.
- Sebaliknya, kalau lift penuh orang yang berharap turun (*crowded short*) lalu harga naik sedikit
  saja, mereka panik dan ikut naik — lift melonjak tajam ke atas (*short squeeze*).

Blok G tidak memprediksi arah gravitasi. Blok G mengukur **kerumunan** — dan kerumunan menentukan
seberapa kasar perjalanannya, bukan ke mana akhirnya.

### Kenapa ini bisa diukur?

Karena di pasar futures AS, **pedagang besar wajib lapor posisinya ke regulator** setiap minggu.
CFTC (Commodity Futures Trading Commission — "polisi bursa futures AS") mengumpulkan laporan itu dan
mempublikasikannya dalam bentuk agregat (bukan per nama). Laporan ini bernama **COT — Commitments of
Traders**. Ibaratnya: Anda tidak boleh tahu isi rekening orang, tapi tiap Jumat pemerintah menerbitkan
"foto udara parkiran" — Anda lihat parkiran penuh motor (banyak spekulan long), tanpa perlu tahu nama
pemiliknya.

### Posisi blok G dalam arsitektur (ini keputusan desain — silakan tantang)

Perhatikan bobot regime score di §11: A .20, B .20, C .15, D .15, E .15, F .15 — total 1.00.
**Blok G bukan pilar regime score.** Ini disengaja: positioning itu *kondisi pasar*, bukan
*fundamental*. Ia tidak mengubah arah bias regime; ia mengubah **cara Anda mengeksekusi bias itu** —
"tailwind TAPI crowded → jangan chase, tunggu pullback" (persis contoh brief di §14). Blok G masuk ke
sistem sebagai (1) filter eksekusi per instrumen, (2) sumber anomali/alert (§11.5: "COT crowded"),
(3) tell squeeze. Kalau Anda keberatan positioning dinaikkan jadi pilar — itu diskusi kalibrasi yang
sah, tapi argumennya harus menjawab: kenapa "kerumunan" harus mengubah *arah* regime, bukan cuma
*eksekusinya*?

---

## 2. Glosarium istilah blok ini

| Istilah | Arti untuk awam | Kenapa penting untuk Anda |
|---|---|---|
| **Futures** | Kontrak janji beli/jual suatu aset di tanggal tertentu di masa depan, dengan **uang jaminan kecil** (margin, misal 5–10% nilai kontrak). Asalnya untuk petani & pembeli gandum mengunci harga panen; lalu trader ikut bermain kontrak yang sama tanpa mau barangnya — cukup jual balik kontrak sebelum jatuh tempo | Semua data blok G adalah data pasar futures; XAUUSD spot yang Anda trading "di bawahnya" ada pasar GC futures yang jauh lebih besar dan ter-regulasi |
| **Long / short** | Long = posisi untung kalau harga naik. Short = untung kalau harga turun (pinjam dulu, jual sekarang, beli balik nanti) | COT melaporkan jumlah kontrak long & short per kelompok trader |
| **Open interest (OI)** | Jumlah kontrak yang **masih terbuka / belum ditutup**. Setiap kontrak butuh satu pembeli DAN satu penjual. OI naik = pemain baru masuk; OI turun = pasangan long-short saling menutup dan keluar dari pasar | Ini "jumlah penumpang di lift", bedakan dari volume |
| **Volume** | Berapa banyak kontrak berpindah tangan hari itu | Volume = lalu lintas; OI = populasi. VOI harian memberi keduanya |
| **Net position** | Long − short. +50.000 artinya kelompok itu bersih long 50 ribu kontrak | Ini angka utama yang di-z-score. JEBAKAN: jangan baca kolom "long" saja tanpa mengurangi "short" |
| **Margin / margin call** | Uang jaminan; kalau kerugian menggerus jaminan, broker memaksa tambal atau tutup posisi paksa | Bahan bakar squeeze: pemain besar yang kena margin call terpaksa menutup posisi serentak |
| **COT (Commitments of Traders)** | Laporan mingguan CFTC: siapa (kelompok mana) pegang berapa | Inti blok G |
| **Legacy report** | Format COT lama: Noncommercial (spekulan) / Commercial (pengguna riil) / Nonreportable (kecil) | Kita pakai terbatas (mis. copper legacy `085691`); FMP hanya punya format ini → ditolak sebagai primer (§16) |
| **Disaggregated (Disagg)** | Format COT yang lebih rinci untuk komoditas: Producer/Merchant/Processor/User (pengguna riil), Swap Dealers, **Managed Money**, Other Reportables. Dataset Socrata `72hh-3qpy` (194 kolom) | Format utama kita untuk metals (gold/silver/copper/platinum) |
| **TFF (Traders in Financial Futures)** | Format COT untuk instrumen finansial: Dealer/Intermediary, **Asset Manager/Institutional**, **Leveraged Funds**, Other Reportables | Format utama kita untuk FX, indeks, BTC, ETH |
| **Managed Money (MM)** | (Di Disagg) dana yang mengelola uang klien secara aktif — praktiknya hedge fund & CTA pengguna strategi trend/momentum. "Uang cepat" di komoditas | Kelompok yang kita z-score untuk metals — merekalah "kerumunan" yang mendorong trend XAU/XAG/XCU/XPT |
| **Leveraged Funds (Lev)** | (Di TFF) dana yang memakai leverage tinggi — hedge fund makro/trend. Secara semangat mirip MM, tapi kategori TFF dengan definisi berbeda | Kaki "fast money" untuk FX/indeks/crypto. JANGAN digabungkan dalam satu z dengan MM — beda klasifikasi |
| **Asset Manager/Institutional (AM)** | (Di TFF) pengelola aset riil: dana pensiun, asuransi, reksa — "real money", lambat, orientasi jangka panjang, cenderung beli saat murah | Kaki "uang riil". Divergensi AM vs Lev di euro FX = sinyal "uang cepat vs uang riil tidak sepakat" |
| **Commercial** | Pemain yang futures-nya untuk bisnis riil (penambang hedging produksi, pabrik membeli bahan) | Konteks: mereka sisi "penenang" pasar, bukan target z kita |
| **z-score** | Jarak suatu angka dari rata-rata historisnya, diukur dalam satuan simpangan baku. z +1.8 = "1,8 langkah lebih long dari normal" | Cara standar menyatakan "crowded". Detail transform di §4 |
| **Crowded** | Posisi net suatu kelompok sudah di ekstrem historisnya (|z| > 1,5 menurut aturan blok ini) | Bukan sinyal balik arah otomatis — lihat §5 jebakan #1 |
| **Squeeze** | Gerakan harga eksplosif karena pemain ekstrem dipaksa keluar serentak (short squeeze saat naik; long flush saat turun) | Yang ingin kita cium lebih awal via konsentrasi top-4 + VOI + blok H |
| **Konsentrasi top-4** | Berapa persen OI reportable dipegang hanya 4 trader terbesar (kolom `conc_gross_le_4_tdr_*` di Disagg) | Kalau segelintir tangan pegang mayoritas posisi → satu keputusan mereka menggerakkan pasar = tell squeeze |
| **VOI** | Volume & Open Interest harian per produk CME (endpoint `VoiTotals/V2`, §18.1) | "Denyut nadi" harian — menutup celah antar-Jumat COT |
| **Preliminary vs Final** | VOI hari-H terbit *Preliminary*, diganti *Final* di H+1 | Aturan baca: selalu prefer *Final* per (tanggal, produk) — jangan bandingkan Preliminary kemarin dengan Final hari ini |
| **Release lag** | COT memotret posisi per **hari Selasa**, tapi baru dirilis **Jumat 15:30 ET** (= Sabtu 02:30 WIB saat EDT) | Data berumur 3 hari saat Anda membacanya — implikasi besar, lihat §5 |
| **CTA** | Commodity Trading Advisor — manajer dana yang mengelola uang klien dengan strategi sistematis trend/momentum di futures | Penyusun utama "Managed Money": sinyal tren serentak mereka membuat trend metals bergerak — dan berbalik — kasar |
| **COMEX / NYMEX** | Dua bursa kontrak dalam grup CME: COMEX (metal: gold/silver/copper) dan NYMEX (energi + platinum) | Menentukan kode kontrak COT yang benar — GC/SI/HG di COMEX, platinum justru di NYMEX (`076651`) |
| **OTC** | Over-the-counter: transaksi langsung antar-pihak di luar bursa terorganisasi (tanpa clearing house pusat) | Pasar spot London untuk gold adalah OTC — jauh lebih besar dari futures tapi tak terlihat di COT (§7.3) |

---

## 3. Peta data — apa, siapa, kapan, kenapa

### 3.1 Siapa menerbitkan & jadwalnya

- **Penerbit**: CFTC (regulator futures AS) — **Tier 0 institusi resmi** dalam taksonomi kita. Diakses
  via portal data Socrata CFTC (dataset laporan publik, bukan scraping). Karena resmi, boleh
  single-source asal freshness-check aktif (§0.1–0.2).
- **Siklus**: posisi difoto per **Selasa** (akhir hari), dirilis **Jumat 15:30 ET**. Saat EDT (Mar–Nov)
  = **Sabtu 02:30 WIB**; saat EST = Sabtu 03:30 WIB.
- **Operasional kita**: fetch **Sabtu 03:00 WIB** + terbit *brief positioning akhir pekan* (§13).
  Sabtu pagi pasar tutup — Anda dapat waktu tenang membaca sebelum buka Senin.
- **Sekunder**: EODHD event "CFTC … net positions" (rilis Jumat 19:30 WIB) — dipakai untuk
  *verifikasi arah*, bukan angka penuh (gerbang F2: "arah cocok EODHD CFTC-events"). Catatan anomali
  jadwal: 19:30 WIB Jumat itu ±7 jam SEBELUM rilis resmi CFTC (Sabtu 02:30 WIB) — angka EODHD
  kemungkinan rekonstruksi/estimasi yang terbit lebih awal; salah satu alasan ia hanya dipakai
  verifikasi arah, bukan sebagai sumber angka.
- **Alternatif yang ditolak**: FMP COT — hanya format legacy, tidak punya Disagg/TFF yang justru
  format kita pakai → dinilai tier 3 (§16), tidak dipakai.

### 3.2 Tiga jenis laporan — dan kenapa kita pakai dua di antaranya

| Laporan | Untuk apa dibuat | Kelompok yang dilaporkan | Kita pakai untuk |
|---|---|---|---|
| **Legacy** | Format klasik (Noncomm/Comm/Nonreportable) | Spekulan vs pengguna riil, kasar | Copper legacy saja (`085691`); FMP cuma punya ini → ditolak |
| **Disaggregated (Disagg)** | Memecah komoditas lebih jernih: siapa pengguna riil, siapa swap dealer, siapa dana aktif | Prod/Merch/Processor/User · Swap Dealers · **Managed Money** · Other Reportables | **Semua metals** (GC/SI/HG/PL) — MM net → z |
| **TFF (Financial Futures)** | Membedakan uang riil vs uang leveraged di instrumen finansial | Dealer · **Asset Manager/Institutional** · **Leveraged Funds** · Other | **FX, DXY, indeks, BTC, ETH** |

Logika pemilihan: untuk komoditas, yang paling informatif adalah melihat *Managed Money* — kerumunan
yang menggerakkan trend metals. Untuk instrumen finansial, yang informatif adalah ketegangan antara
*Leveraged Funds* (cepat, leverage tinggi) dan *Asset Manager* (riil, lambat) — dua jenis pemain yang
berbeda cara kerjanya. Satu pengecualian struktural: **platinum tidak tersedia di TFF** (terverifikasi;
spec lama salah tulis legacy-only — bugfix v1.3) — jadi jangan mencari TFF platinum; Disagg-lah yang ada.

Dataset Socrata yang dipakai: Disagg = `72hh-3qpy` (194 kolom; bonus `pct_of_oi`, `change_in_*`,
**`conc_gross_le_4_tdr_*`** = konsentrasi gross ≤4 trader terbesar — bahan flag squeeze HG/GC);
combined futures+opsi = `kh3c-gbw2` / `yw9f-hn96` untuk GC/SI.

### 3.3 Daftar kontrak (semua kode live-verified 2026-08-29)

| Instrumen Anda | Kontrak COT | Kode | Report | Output di brief |
|---|---|---|---|---|
| XAUUSD | Gold COMEX | `088691` | Disagg MM net → z-3y | "z+1.8 crowded long — jangan chase" *(contoh nilai Agt-2026)* |
| XAGUSD | Silver COMEX | `084691` | Disagg MM | idem |
| XCUUSD | Copper COMEX | `085692` ⚠️ Disagg; `085691` hanya legacy | Disagg MM | z + flag conc top-4 |
| XPTUSD | Platinum NYMEX | `076651` | Disagg MM (TFF tidak ada) | z |
| BTC | BTC CME | `133741` | TFF | z |
| ETH | Ether cash-settled | `146021` (micro `146022`) | TFF | z |
| EURUSD | Euro FX | `099741` | TFF **Lev vs AM** | divergensi fast vs real money |
| USDJPY / majors | Japanese Yen | `097741` | TFF | untuk majors |
| GBPUSD / XAGGBP kaki GBP | British Pound | `096742` | TFF | leg GBP |
| AUDUSD | Australian Dollar | `232741` | TFF | risk proxy Asia |
| DXY | **ICE DXY futures** | `098662` | TFF | positioning dolar itu sendiri |
| US500 | S&P 500 consolidated | `13874+` | TFF | index |
| US100 | Nasdaq 100 E-mini | `209742` (resmi "NASDAQ MINI"); consolidated `20974+` (URL-encode `%2B`); micro `209747`; full `209741` **MATI 2015 — jangan pakai** | TFF | index |
| US30 | — (tidak ada di daftar COT kita) | — | — | hanya VOI (YM terverifikasi di VOI) |

Dua bekas luka bugfix v1.3 yang wajib diingat: (1) copper `085691` di Disagg mengembalikan **0 baris** —
kode Disagg yang benar `085692`; (2) platinum **tersedia** di Disagg (dulu salah ditulis legacy-only).
Karena itu bootstrap pipeline (BUILD-PLAN §3-G) melakukan **verifikasi by-name** semua kode kontrak
sekali saja terhadap kolom `market_and_exchange_names`, lalu hasilnya di-cache — "088691" harus
benar-benar baris GOLD COMEX, bukan sekadar cocok angka.

### 3.4 VOI harian CME — denyut nadi antar-Jumat

COT hanya mingguan. Untuk tahu apa yang terjadi *hari ini*, kita pakai **VOI harian** dari backdoor CME
(§18.1; **Tier 3 gray** — sumber tidak resmi-dokumenter, jadi wajib degradable):

```
GET  /CmeWS/mvc/VoiTotals/V2/TradeDates
POST /CmeWS/mvc/VoiTotals/V2/AssetClass/{kode}   body: {tradeDate, excludeExchanges:[]}
     kode: 2=Agrikultur, 3=FX, 4=Equity, 6=IR, 7=Energy, 8=Metals
```

Memberi **volume, OI, dan `oiDiff`** (perubahan OI, bertanda) per produk per hari — GC/SI/PL/HG/BTC/
ES/NQ/YM/6E/6B/ZQ/SR1/SR3 semuanya terverifikasi jalan. Sifat-sifat teknis yang menentukan cara pakai:

- Hari-H terbit **Preliminary**, diganti **Final** H+1 → aturan baca: prefer *Final* per (tanggal,
  produk); jangan bandingkan angka Preliminary kemarin dengan Final hari ini.
- Angka dikirim sebagai **string ber-koma** — harus diparse, bukan di-cast langsung.
- XLS `V2/Download?tradeDate=` tersedia anonim (cadangan).
- Karena ini keluarga backdoor CME: sifat gray (retensi endpoint pendek, gerbang F2 mensyaratkan
  snapshot tidak bolong >3 hari kerja), dan fallback OI sudah tersedia alami dari endpoint
  **settlements** CME (§17: satu-satunya jalur lain yang mengembalikan openInterest).

Cara baca angka (nilai normal vs ekstrem): OI emas biasanya bergerak lambat (persentase per hari kecil);
yang dicari bukan levelnya tapi **pola kombinasi harga × arah oiDiff** — matriks interpretasi di §4.4.

---

## 4. Logika hulu-ke-hilir: dari laporan mentah ke kalimat di brief

Arah baca: **raw legs → net → z-score → state → kalimat brief / alert**. Konsep transform dijelaskan
dulu, baru mesinnya.

### 4.1 Konsep: "net" — menyatukan long dan short

Laporan mentah (`cot_raw`) menyimpan *legs* terpisah per kategori: `long`, `short`, `spread`, plus
`open_interest_all`, `pct_of_oi`, `conc_top4_long`, `conc_top4_short`. Net untuk kategori c =
`long − short` (posisi spread tidak masuk net arah). Kenapa raw disimpan terpisah, bukan cuma net?
Prinsip §0.4: **raw + derived terpisah** — derived harus selalu bisa dihitung ulang dari raw, dan
suatu hari Anda mungkin ingin mengganti definisi (mis. net-long-ratio sebagai pengganti net) tanpa
kehilangan sejarah.

### 4.2 Konsep: z-score untuk awam

z-score menjawab: "angka ini aneh tidak, dibanding kebiasaannya sendiri?" Rumus: `(x − rata-rata) / σ`
di mana σ (simpangan baku) = seberapa lebar penyebaran normalnya.

- Bayangkan suhu hari ini 33°C. Di Jakarta itu biasa (z ≈ 0); di Bandung itu panas ekstrem (z ≈ +2)
  — angka yang sama, makna berbeda, karena "normal"-nya beda. z-score menormalkan itu.
- z = 0 → persis rata-rata historis. z = +1.8 → 1,8 kali "lebar normal" di atas rata-rata.
- **Window blok G khusus: 3 tahun** (±150 minggu data COT), beda dari spesifikasi umum 5 tahun blok
  A–F. Alasannya praktis: komposisi trader dan regime positioning berubah; 3 tahun cukup memuat
  satu siklus penuh tanpa dicemari era yang sudah lampau. Min-obs 150 minggu — kalau datanya kurang
  dari itu, state = INSUFFICIENT, bukan angkar-angkuran.
- σ dipakai versi **populasi** (σ populasi, konsisten dengan spesifikasi umum).
- Sepupu z: **percentile** (`z_pct` di `cot_snapshots`) = "dari semua minggu historis, minggu ini
  lebih long dari berapa persen?" Persentil 95 ≈ z tinggi, tapi lebih tahan terhadap pencilan.

### 4.3 Konsep: kenapa "crowded" dibaca kontrarian — dan kenapa HANYA di ekstrem

Mekanisme ekonominya, bukan takhayul:

1. **Bahan bakar habis.** Harga naik butuh pembeli *baru* terus-menerus. Kalau MM sudah super-long
   (z +1.8), artinya mayoritas dana cepat yang *mau* beli *sudah* beli. Sisa pembeli tipis → setiap
   kenaikan selanjutnya lebih sulit. (Lift penuh.)
2. **Pintu keluar sempit.** Posisi itu bisa ditutup hanya dengan satu cara: menjual. Kalau semua
   pemegang long menjual bersamaan (dipicu data buruk / margin call), jatuhnya tajam dan cepat —
   ini *long liquidation*.
3. **Kebalikannya: short squeeze.** Kerumunan short yang kena harga naik dipaksa beli balik
   (stop-loss tergantung otomatis) → rally jadi eksplosif ke atas.

TAPI — dan ini kunci — **crowded bukan sinyal jual**. Trend bisa bertahan berminggu-minggu bahkan
berbulan di kondisi crowded; dana besar justru menumpuk di trend panjang. Karena itu aturan state
blok G hanya menyalakan di **ekstrem** (|z| > 1.5), dan kalimatnya berupa peringatan eksekusi
("jangan chase"), bukan pembalikan ("jual"). Z tinggi menaikkan *risiko amplitudo*, bukan
memprediksi *waktu* pembalikan.

### 4.4 Pipeline lengkap (BUILD-PLAN §3-G)

```
raw legs (Socrata, per Selasa)
  → net per kategori (mm/lev/am)                       [cot_raw → cot_snapshots]
  → z-3y = (net − mean_3y) / σ_3y,  σ populasi, min-obs 150 minggu
  → state: |z| > 1.5 → CROWDED-LONG / CROWDED-SHORT; else NEUTRAL
  → ΔWoW (perubahan net mingguan — arah akumulasi)
  → conc_top4 flag squeeze (fokus HG/GC — metals COMEX yang datanya terisi)
  → VOI harian pendamping (volume/OI/oiDiff; prefer Final)
  → anomali §11.5 ("COT crowded") + baris implikasi per instrumen di brief
```

VOI dibaca dengan matriks harga × arah OI (kerangka baca umum, bukan angka spec):

| Harga | OI (oiDiff) | Arti umum | Sikap swing |
|---|---|---|---|
| naik | naik | long baru masuk — rally punya bahan bakar | trend sehat, ikuti |
| naik | turun | *short covering* — naik karena short kabur, bukan pembeli baru | rally rapuh, jangan kejar |
| turun | naik | short baru menekan — distribusi aktif | hindari menangkap pisau |
| turun | turun | *long liquidation* — pemegang lama menyerah | flushing, tunggu habis |

Kombinasikan dengan COT: COT bilang "kerumuman sudah ekstrem" (foto mingguan), VOI bilang "hari ini
bensin masuk atau keluar" (denyut harian). Contoh sinergi: COT gold MM z+1.8 + VOI beberapa hari
berturut harga naik tapi oiDiff negatif = rally yang digerakkan covering → makin kuat alasan menunggu
pullback, bukan chase.

### 4.5 Konsentrasi top-4 — tell squeeze

Kolom `conc_gross_le_4_tdr_long/short` (Disagg) menjawab: "dari seluruh OI reportable, berapa persen
dipegang 4 trader terbesar saja?" Analogi: di meja poker kecil, kalau 4 pemain memegang mayoritas
chip, satu pemain *all-in* mengubah jalannya permainan semua orang. Pasar dengan konsentrasi tinggi
berarti harga bisa bergerak bukan karena kondisi dunia berubah, tapi karena **satu tangan besar
mengambil keputusan** (atau dipaksa margin call) — itu beda "tell squeeze" dengan z crowded: z
menunjukkan *berapa banyak* kerumunan, konsentrasi menunjukkan *seberapa terkonsentrasi* — dua hal
berbeda (bisa banyak tapi tersebar, bisa segelintir tapi raksasa). Spec membatasi flag ini untuk
HG/GC — untuk kontrak non-metals kolom ini memang struktural kosong (kebijakan null F0: struktural-OK).

### 4.6 Kontribusi ke sistem

Blok G **tidak menambah poin regime score** (lihat §1). Ia menyumbang: (a) filter kalimat implikasi
per instrumen ("tailwind TAPI crowded"), (b) daftar anomali/alert, (c) tell squeeze (dengan blok H
fisik — stocks drain copper, LBMA vault). Kalau suatu hari hasil backtest F4 menunjukkan z-COT
menambah hit-rate secara signifikan, itu jalur resmi mengubah keputusan ini — dengan bukti, bukan selera.

---

## 5. Cara membaca baris blok G di brief + jebakan salah-baca

### 5.1 Contoh cara baca (dari contoh brief §14, waktu Agt-2026)

```
Positioning (COT, rilis 02:30 tadi):
• Gold MM z+1.8 → crowded long — jangan chase
• Dolar: ICE DXY futures net short menipis
```

Cara membaca: "z+1.8" = net Managed Money gold sekarang 1,8 simpangan baku di atas rata-rata 3
tahunnya → kerumunan long ekstrem. Kalimatnya peringatan *eksekusi*: bias XAU boleh saja tailwind
(blok A–F), tapi membeli di kondisi ini = bayar tiket mahal dengan risiko flush. "Net short DXY
menipis" = bearish-dolar yang sempat ramai mulai bubar → dukungan dolar bisa kembali → kontra-headwind
untuk metals. Perhatikan juga: z dan ΔWoW di-update **sekali seminggu** (Sabtu) — jangan heran angka
baru muncul Senin pagi pun masih dari foto Selasa.

### 5.2 Sepuluh jebakan salah-baca (urut dari paling sering)

1. **"Crowded = pasti balik arah".** Salah. Z tinggi menaikkan risiko amplitudo; trend bisa lanjut.
   Reaksi yang benar: jangan chase / kecilkan sizing / pasang rencana kalau flush terjadi — bukan
   langsung short melawan trend.
2. **Lupa umur data.** Foto Selasa, dibaca Sabtu. Peristiwa Rabu–Jumat (CPI, FOMC, speech) bisa sudah
   mengubah total posisinya. Untuk swing harian-mingguan masih sangat berguna; untuk intraday hari
   Senin, VOI-lah yang relevan.
3. **Membaca "long" tanpa "short".** Selalu net. Long besar + short lebih besar = crowded short.
4. **Mencampur kategori antar-laporan.** MM (Disagg) ≠ Leveraged Funds (TFF) ≠ Noncommercial
   (legacy) — mirip secara semangat, beda definisi resmi. Z masing-masing dihitung terhadap
   historisnya sendiri; jangan dibuat satu garis.
5. **Salah kode kontrak.** Copper Disagg = `085692` (`085691` di Disagg = 0 baris); NQ full-size
   `209741` mati sejak 2015 (pakai `209742` / `20974+`); suffix `+` wajib di-URL-encode `%2B`.
6. **Mencari TFF platinum.** Tidak ada — platinum hanya Disagg (bugfix v1.3).
7. **Membandingkan Preliminary vs Final VOI.** Preliminary hari-H digantikan Final H+1; selalu
   samakan versi sebelum menghitung Δ.
8. **VOI angka string ber-koma** dipakai mentah → parsing salah (mis. "1,234" dibaca 1.234) —
   parser wajib menangani format ini; ini alasan kolom dicek fixture-first.
9. **z window tertukar.** Blok G pakai 3y; blok lain 5y. Kalau Anda menghitung ulang manual dengan
   window beda, angka tidak akan cocok — itu bukan bug, itu spesifikasi.
10. **Lupa bahwa ini hanya futures.** XAUUSD spot yang Anda trading ≠ keseluruhan dunia gold (lihat §7).

---

## 6. Keterkaitan spesifik per instrumen Anda

| Instrumen | Kaitan positioning | Catatan praktis |
|---|---|---|
| **XAUUSD** | GC MM z-3y + conc top-4 GC | Instrumen utama; "z+1.8 crowded long — jangan chase" *(contoh nilai Agt-2026)* adalah kalimat baku brief. Cross-check demand barat: GLD flows (blok H) — crowded tapi GLD terus serap = bid struktural, berbeda cerita dengan crowded tanpa flow |
| **XAGUSD** | SI MM z + conc top-4 | Pasar silver lebih kecil → positioning lebih mudah ekstrem & squeeze lebih kasar. Padukan LBMA vault (blok H) dan SIVL vs GCVL (blok F): crowded long + vault menipis + vol silver relatif tinggi = profil squeeze kompleks |
| **XPTUSD** | PL Disagg MM (TFF tak ada) | Likuiditas platinum tipis → z gampang "ekstrem" secara statistik meski pergerakan dana tidak besar — baca dengan hemat, utamakan arah ΔWoW |
| **XCUUSD** | HG `085692` Disagg MM + **conc top-4 = tell squeeze COMEX** | Gabungkan copper fisik (blok H: stocks drain + backwardation). Copper adalah kontrak squeeze klasik — konsentrasi tinggi + stok turun = kondisi yang menghasilkan gerakan vertikal |
| **BTC / ETH** | BTC `133741` TFF, ETH `146021` TFF | COT crypto = hanya sisi institusional CME. Untuk denyut harian crypto, funding & OI Bybit (blok H) jauh lebih hidup — COT crypto dibaca sebagai lapisan institusional, bukan kerumunan perp |
| **US100 / US500** | NQ `209742`/`20974+`, SPX `13874+` (TFF) | US30 tidak punya baris COT di setup kita — hanya VOI (YM). Kontras dengan rasio VXN/VIX (blok F) untuk preferensi 500 vs 100 |
| **EURUSD** | 6E `099741` **Lev vs AM** | Sinyal unik blok ini: divergensi. Lev short tapi AM long = uang cepat bearish, uang riil menunggangi — biasanya resolusinya tell tentang siapa yang kena bila harga bergerak. Kaitkan ekspektasi ECB (blok A) untuk kaki EUR |
| **GBPUSD, AUDUSD, USDJPY** | `096742`, `232741`, `097741` (TFF) | AUD = proxy risk Asia — positioning AUD ramai saat risk-on/off; cocok dikaitkan China PMI (blok D) |
| **DXY** | ICE DXY futures `098662` TFF | Satu-satunya cara melihat "positioning dolar itu sendiri" — cross-check dollar smile (blok A). DXY net short menipis saat dolar mulai naik = konfirmasi dini rotasi |
| **XAUEUR / XAGGBP / crosses** | Tidak ada COT langsung | Baca dua kakinya: XAU positioning + 6E (leg EUR) / 6B (leg GBP). Cross "bersih" kalau dua kaki searah; divergensi kaki = sumber gerak sendiri |

---

## 7. Yang bisa salah — degradasi, kualitas data, keterbatasan

### 7.1 Mode degradasi

| Kegagalan | Reaksi sistem | Yang hilang |
|---|---|---|
| CFTC Socrata mati | Sekunder EODHD "CFTC net positions" events (Jumat 19:30 WIB) — dipakai untuk **arah** pergerakan, bukan basis z | z-score & conc top-4 (butuh legs penuh); brief menampilkan arah dengan label sumber |
| VOI backdoor mati | Fallback OI dari settlements CME (juga mengembalikan openInterest, §17) | `oiDiff` per-produk serapi VOI; denyut jadi lebih kasar |
| Keduanya mati | COT mingguan tetap hidup (sumber resmi terpisah) | Hanya resolusi harian hilang — blok tidak mati total |
| Rilis mundur (libur AS / shutdown) | Freshness stamp §0.2: lewat jadwal tanpa update → ditandai basi, tidak dipakai diam-diam | Sabtu tanpa brief positioning; z minggu lalu tetap tampil dengan umur jelas |

### 7.2 Kualitas data & jebakan teknis

- **Umur struktural 3 hari** (Selasa→Jumat) — bukan bug, sifat produk; kolom `release_ts` di
  `cot_raw` menjaga backtest dari look-ahead 3 hari (memakai data Selasa seolah tahu di hari Selasa).
- **VOI = Tier 3 gray**: endpoint tidak dijamin stabil, retensi pendek → harvester tidak boleh
  bolong >3 hari kerja atau data hilang; Preliminary→Final adalah revisi normal, bukan anomali.
- **Reklasifikasi trader oleh CFTC** sesekali terjadi → z bisa "melompat" tanpa pergerakan pasar
  sungguhan. Obatnya: baca bersama ΔWoW dan VOI; lompatan tanpa konfirmasi VOI = curiga klasifikasi.
- **Platinum & pasar tipis**: angka ekstrem di pasar kecil lebih sering mencerminkan sedikitnya
  pemain daripada kerumunan besar.
- **ETH `146021` vs micro `146022`** adalah kontrak berbeda — jangan diagregasi sembarangan.

### 7.3 Keterbatasan fundamental (kenapa blok ini pelengkap, bukan pengganti)

1. **COT hanya melihat futures yang dilaporkan ke CFTC.** Dunia gold juga hidup di pasar spot London
   (OTC), ETF, dan belanja bank sentral (blok H: PBoC, WGC). Kerumunan MM futures ≠ seluruh pasar.
2. **Ambang batas pelaporan.** Hanya trader di atas ukuran tertentu yang dilaporkan per kategori;
   sisanya jadi "Other/Nonreportable" — pemain kecil tak terlihat per individu.
3. **Agregat, bukan niat.** Kita tahu berapa, tidak tahu kenapa — hedging vs spekulasi bisa berwajah
   sama di angka net. (Disagg mengurangi masalah ini dengan memisahkan pengguna riil — alasan kita
   memilihnya untuk metals.)
4. **Satu foto per minggu.** Pergerakan Kamis setelah foto Selasa tidak akan tampak sampai Jumat
   depan; VOI menambal, tapi tanpa rincian kategori.
5. **Bukan prediktor waktu.** Semua sinyal blok ini bercerita tentang risiko amplitudo dan struktur
   pasar — kapan flush terjadi tidak bisa diketahui dari sini. Itu pekerjaan blok kalender (I) dan
   vol (F) sebagai pemicu.

---

*Terkait: `docs/explained/` blok F (vol — ukuran risiko), blok H (flows — demand fisik yang
menemani positioning), blok A (dollar smile — kaki DXY). Rantai teknis penuh: DATA-SPEC.md §7 & §18.1,
BUILD-PLAN.md §2–§3.*
