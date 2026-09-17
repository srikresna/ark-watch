# Blok H — Flows & Crypto-Native (Dokumen Edukasi)

> Keluarga dokumen: `docs/explained/` (penjelasan naratif rantai hulu→hilir, untuk non-finance).
> Sumber kebenaran: [DATA-SPEC.md](../DATA-SPEC.md) v1.4 §8 (Blok H) + §0 prinsip, §2/§6/§10 kaitan silang, §11 sinyal komposit, §12–14 penyimpanan & jadwal, §17–18 jalur CME; [BUILD-PLAN.md](../BUILD-PLAN.md) v1.1 §0 taksonomi tier, §2 skema, §3 transform Blok H, §5 gerbang kebenaran.
> Kalau dokumen ini bentrok dengan spec, **spec yang benar**. Ragu = baca spec.

---

## 1. Kenapa blok ini ada — "harga naik, TAPI siapa yang beli?"

Semua blok A–G memperlakukan pasar seperti seorang dokter memeriksa tekanan darah: rate, inflasi, growth, likuiditas, vol, positioning. Blok H menanyakan hal yang lebih mendasar dan sering diabaikan ritel: **siapa yang sebenarnya keluar-masuk pintu?**

Analogi: bayangkan warung kelontong. Harga di papan naik 2%. Pertanyaan naif: "warung laris!" Pertanyaan Blok H: "kasir-nya sepi atau ramai?" Kalau harga naik tapi kasir sepi — tidak ada pembeli baru — kenaikan itu kemungkinan besar bukan *demand* sungguhan, melainkan penjual yang menarik barangnya dari etalase (supply menipis), atau pelaku short yang panik membeli kembali (short-covering). Kenaikan tanpa pembeli baru itu **rapuh** — atau sebaliknya, justru bisa jadi tanda pembeli besarnya diam-diam belanja di warung lain. Harga memberitahu *berapa*; flows memberitahu *siapa dan seberapa sungguhan*.

Blok H menjawab tiga pertanyaan besar:

1. **Demand "Barat" vs bid "struktural" (emas & silver).** Pembeli emas ada dua keluarga besar: investor Barat lewat ETF (GLD/SLV) yang beli-jual mengikuti harga dan naratif makro, dan bank sentral (China/PBoC, dll.) yang beli untuk cadangan negara — hampir tidak peduli harga, beli tiap bulan apa pun yang terjadi. Sejak ~2022 fenomena ini disebut **era decoupling**: emas bisa naik *meski* real yield naik (padahal secara teori lama, real yield naik = emas turun, karena emas tidak membayar bunga jadi makin tidak menarik). Divergensi itu hanya bisa dibaca benar kalau kita tahu central bank sedang aktif beli — dan itu data Blok H.
2. **Suhu leverage crypto.** Harga BTC/ETH di bursa perpetual futures ditentukan marginal oleh pedagang ber-leverage (pinjaman). Blok H mengukur suhunya: *funding rate* (siapa yang bayar "sewa" ke siapa) dan *open interest* (berapa posisi yang masih berdiri = bensin di dalam mesin).
3. **Ketegangan fisik vs kertas (silver & copper).** XAGUSD dan XCUUSD adalah logam yang pasarnya bisa "ketat secara fisik" — stok di gudang menipis — jauh sebelum harga meledak. Blok H memantau gudangnya langsung (LBMA London untuk silver, COMEX New York untuk copper).

Untuk crypto, Blok H juga punya satu ukuran likuiditasnya sendiri: **stablecoin supply** — total saldo "dolar elektronik" dunia crypto yang siap dipakai membeli. Ini pasangan cek-silang dari net-liquidity Blok E (sisi tradfi).

---

## 2. Glosarium

| Istilah | Arti untuk awam | Kenapa penting buat kamu |
|---|---|---|
| **ETF** (Exchange-Traded Fund) | "Loker" di bursa yang isinya emas/perak; 1 lembar saham GLD ≈ sepotong emas di brankas. Beli ETF = beli emas tanpa kirim barang | Jendela paling jernih ke demand investor Barat |
| **Holdings** | Berapa ton emas yang disimpan di loker ETF itu (GLD tiap hari, SLV tiap minggu) | Naik = ada uang Barat masuk; turun = keluar |
| **Net flow** | Selisih uang masuk vs keluar ETF dalam sehari (+$240M = ada $240 juta lebih banyak yang beli) | "Driver marginal" harga BTC pasca-ETF |
| **Creation/redemption** | Mekanisme jumlah lembar ETF bertambah/berkurang mengikuti permintaan — inilah kenapa holdings berubah | Holdings berubah = permintaan berubah, bukan manajer ETF berjudi |
| **Central bank (CB) buying** | Bank sentral negara membeli emas untuk cadangan (amanat rakyat, bukan untung cepat) | Pembeli yang tidak panik saat harga turun = lantai struktural |
| **Decoupling** | Emas berhenti "menurut" pada real yield karena CB jadi pembeli dominan | Mengubah cara membaca Blok B: RY naik tak otomatis bearish gold |
| **WGC GDT** | World Gold Council — Gold Demand Trends, laporan kuartalan permintaan emas dunia (termasuk belanja CB agregat) | Angka resmi CB global, tapi telat & direvisi |
| **SAFE / PBoC** | Badan admin devisa & bank sentral China; menerbitkan cadangan emas bulanan | Deteksi beli China lebih cepat daripada WGC |
| **万盎司 (wan ounce)** | Satuan di XLSX resmi China: 1 万盎司 = 10.000 ounce troy = **0,311034768 tonne** | Salah baca satuan = salah 3.000-an kali (pernah kejadian, lihat §7) |
| **koz** | Kilo-ounce (1.000 ounce troy), satuan data LBMA silver: 1 koz × 0,0311035 = 0,0311035 tonne | Konversi wajib lewat unit registry, jangan akal-akalan |
| **Troy ounce / tonne** | Satu timbangan logam mulia (1 ozt = 31,1035 gram). XAUUSD itu harga per troy ounce | Unit dasar semua angka blok ini |
| **TIC** | Treasury International Capital — "rekening koran" siapa negara mana menahan berapa obligasi AS | Kalau asing menarik dana → tekanan naik ke dolar (tail DXY) |
| **Perpetual futures ("perp")** | Kontrak taruhan harga tanpa tanggal kedaluwarsa, dengan dana pinjaman (leverage) | Pasar penentu harga marginal BTC/ETH 24 jam |
| **Funding rate** | "Sewa" 8-jamanan antara pihak Long dan Short. Positif = Long bayar ke Short | Termometer leverage: terlalu positif = longs crowded & rapuh |
| **Open interest (OI)** | Total kontrak yang masih berdiri (belum ditutup) | Bensin di mesin: OI besar = gerakan bisa eksplosif dua arah |
| **Long / Short** | Pemain taruhan naik / taruhan turun | Vocabulary dasar membaca funding & COT |
| **Crowded long** | Terlalu banyak orang menumpuk di posisi yang sama (naik) | Sumber "tailwind TAPI jangan chase" di brief |
| **Liquidation cascade** | Rantai posisi paksa-ditutup saat harga bergerak melawan → harga bergerak makin jauh | Kenapa funding ekstrem = alert anomali |
| **Squeeze / short squeeze** | Harga meledak naik karena short terpaksa beli; bisa dipicu barang fisik menipis | Skenario khas XAG/XCU ketika stok gudang turun |
| **Contango / backwardation** | Kurva futures: contango = harga berjangka > hari ini (normal); backwardation = hari ini PALING mahal = orang rela premium demi barang sekarang | Backwardation + stok turun = sinyal squeeze klasik |
| **COMEX stocks** | Stok logam di gudang bursa New York (copper = produk HG, id `438`) | Deteksi squeeze XCUUSD mingguan/harian |
| **LBMA vault** | Gudang grosir silver di London (asosiasi pasar London) | Stok global silver — bulanan, level + tren |
| **Stablecoin (USDT/USDC)** | Koin crypto yang nilainya dikunci 1:1 ke dolar — "saldo e-wallet" dunia crypto | Likuiditas siap-beli crypto-native |
| **Basis point (bps)** | 1 bps = 0,01%. Funding +0,01%/8j = +1 bps per 8 jam | Satuan penyimpanan funding di DB (`funding_bps`) |
| **ΔWoW** | Perubahan minggu-ini-minggu-lalu (delta week-over-week) | Bentuk sinyal stablecoin supply |
| **Gray source** | Sumber tidak-resmi (backdoor/scraping) — boleh dipakai tapi wajib punya rencana mati (§0.3 spec) | Farside & backdoor CME masuk kategori ini |
| **Tradfi** | "Traditional finance" — keuangan konvensional (bank, bursa, obligasi), lawan dari crypto-native | Istilah pembanding: net-liquidity tradfi (Blok E) vs stablecoin (Blok H) |
| **EOD** | End-of-day — nilai penutupan/akhir hari (bukan realtime) | Bentuk penyimpanan standar sistem: funding di-rata-rata jadi EOD, settlement CME juga EOD |

---

## 3. Peta data — per series

Konvensi baca: **arah yang penting** selalu dinyatakan dari sudut pandang instrumen kamu (XAUUSD, BTC, dll.).

### 3.1 GLD holdings — meteran demand emas "Barat"

| Aspek | Isi |
|---|---|
| Apa sebenarnya | Ton emas di brankas ETF GLD (SPDR), per hari. Naik-turun mengikuti creation/redemption |
| Siapa & kapan | Situs resmi GLD, XLSX arsip historis (`historical-archive?product=gld`) — harian, ikut kalender bursa AS |
| Kenapa dipilih | Sumber primer resmi penerbit sendiri; boleh single-source karena lembaga resmi **asal** freshness-check aktif (§0.1). Alternatif FMP `/sentiments` (proxy GLD.US) **digugurkan** di audit v1.4 — nilai LOW, crypto diam-diam dihapus dari response |
| Cara baca | Yang dibaca bukan level melainkan **Δ**: emas naik + GLD naik = konfirmasi demand Barat; **emas +1,2% tapi GLD flat = kenaikan BUKAN dari demand Barat** (bisa CB/Asia, bisa short-covering). Δ harian kecil = noise — yang berarti adalah tren dan lonjakan |

Contoh baris brief (contoh nilai Agt-2026): `Flows: GLD +2.1t (konfirmasi)` — artinya hari itu harga emas dan holdings searah, pembeli Barat hadir.

### 3.2 SLV holdings — versi silver, lebih kasar

| Aspek | Isi |
|---|---|
| Apa sebenarnya | Jumlah lembar saham SLV yang beredar — karena 1 lembar = sepotong perak, lembar beredar ≈ holdings (dalam lembar, bukan ton) |
| Siapa & kapan | Primer: FMP `/stable/shares-float?symbol=SLV` → field `outstandingShares` (akarnya filing SEC 10-Q); sekunder: HTML resmi iShares. Frekuensi praktis **mingguan** (W) |
| Jebakan endpoint | Field `shares-outstanding` **tidak ada** di respons itu — harus `outstandingShares`. (Ditemukan live, changelog v1.2) |
| Cara baca | Sama seperti GLD tapi resolusi kasar (mingguan): hanya perubahan besar yang bermakna. Dipakai sebagai konfirmasi demand silver Barat, bukan trigger |

### 3.3 BTC & ETH ETF net flows — driver marginal crypto

| Aspek | Isi |
|---|---|
| Apa sebenarnya | Uang bersih (beli−jual) yang masuk/keluar seluruh ETF spot BTC (dan ETH) per hari, dalam juta dolar |
| Siapa & kapan | Farside.co `/btc/` dan `/eth/` — tabel HTML server-rendered; diperbarui harian. Digabung jadi satu angka net flow per hari |
| Kenapa dipilih | Farside = standar industri untuk angka ini. Tapi statusnya **gray (T3)** — situsnya di belakang Cloudflare |
| Cara baca | Net flow positif besar = ada pembeli institusi baru (dukungan harga); negatif besar = distribusi. Angka satu hari = noise; akumulasi/tren berminggu yang berarti. Contoh output spec (contoh nilai Agt-2026): `BTC ETF +$240M` |

Persyaratan teknis (penting untuk harvester): Farside **wajib diambil pakai Python `requests` + user-agent Chrome** — PowerShell IWR dan httpx-h2 sama-sama kena 403 Cloudflare. Cadangan kalau mati: mirror BitMEX / CoinGlass, atau baris brief jadi `flow: N/A` (mode degradasi §11.4).

### 3.4 Perp funding rate — suhu leverage crypto

| Aspek | Isi |
|---|---|
| Apa sebenarnya | Di perpetual futures, tiap 8 jam pihak yang "sepi sisi" membayar ke sisi yang ramai (mekanisme menjaga harga perp nempel ke spot). Funding positif = Long membayar Short = longs lebih lapar |
| Siapa & kapan | Bybit `/v5/market/tickers` — **`fundingRate` dan `openInterest` keluar dalam SATU call** (endpoint `/funding/info` MATI 404 — jangan pakai). Historis lengkap sejak listing ~2020 via `/v5/market/funding/history` (cursor `endTime`). Frekuensi asli 8j → di sistem dirata-rata jadi harian (EOD) |
| Kenapa dipilih | Bybit satu call untuk dua sinyal; historis panjang gratis untuk kalibrasi z-score |
| Cara baca | Positif kecil = normal sehat. Positif tinggi = **long crowded → rapuh** (bukan bullish!). Negatif dalam = short crowded (bahan baku squeeze naik). Contoh brief (contoh nilai Agt-2026): `funding +0.01%/8h → long crowded` — +0,01%/8j memang hanya 1 bps (level baseline khas bursa perp, masih "sehat"), dan label "long crowded" di situ BUKAN klaim ekstremitas statistik, melainkan ARAH kemiringan: funding positif = pihak long yang membayar = sisi long lebih ramai (seberapa ramahnya diukur terpisah). "Ekstrem" yang memicu alert anomali §11.5 adalah z-score vs historisnya sendiri — parameter kalibrasi, bukan angka mutlak |

Analogi: funding itu seperti suhu ruang mesin. Mesin (harga) bisa jalan di suhu apa pun, tapi suhu tinggi terlalu lama = ada komponen (posisi leverage) yang kurang darah oksigen — satu sentimen buruk, mesin stall dan semua panik keluar bersamaan (liquidation cascade).

### 3.5 Open interest — bahan bakar squeeze

| Aspek | Isi |
|---|---|
| Apa sebenarnya | Total nilai kontrak yang masih terbuka (belum ditutup/cair). Naik = uang baru masuk bertaruh; turun = posisi ditutup |
| Siapa & kapan | Bybit `/v5/market/open-interest?intervalTime=1d` (200 baris/halaman, cursor) — harian |
| Cara baca | Kombinasi dengan harga: harga↑ + OI↑ = taruhan baru mendukung naik (trend sehat); harga↑ + OI↓ = short-covering (naik karena short kabur — kurang kuat); harga↓ + OI↑ = short baru menekan; harga↓ + OI↓ = unwinding/panik. OI tinggi saja tidak bermakna arah — ia **amplitudo potensi gerakan** |

Untuk logam, peran yang sama dimainkan OI futures CME — lihat pendamping VOI harian CME (`oiDiff` per produk, Blok G/§18.1) dan kolom konsentrasi top-4 trader COT (`conc_gross_le_4_tdr_*` untuk HG/GC, §18.3) — dua-duanya "tell squeeze" COMEX.

### 3.6 Stablecoin supply — likuiditas crypto-native

| Aspek | Isi |
|---|---|
| Apa sebenarnya | Total USDT+USDC (dan teman-temannya) yang beredar — "saldo e-wallet dolar" seluruh dunia crypto, siap dipakai membeli BTC/ETH kapan saja tanpa perlu transfer bank dulu |
| Siapa & kapan | DefiLlama `stablecoins.llama.fi/stablecoincharts/all` — total, **historis penuh 2017-11→kini dalam satu respons**; per-koin: `?stablecoin=1` (USDT) / `?stablecoin=2` (USDC). Harian |
| Jebakan endpoint | Parameter `asset=`/`coin=` tidak berfungsi — hanya `stablecoin=` |
| Cara baca | Naik (minting) = uang baru disiapkan masuk crypto = tailwind likuiditas; turun (redeem) = likuiditas ditarik. Sinyal dipakai sebagai **ΔWoW**. Contoh output spec (contoh nilai Agt-2026): `USDT+USDC +$1.2B/w`. Fungsi kedua: **cek silang** dengan net-liquidity Blok E — kalau likuiditas tradfi menyusut tapi stablecoin mengembang (atau sebaliknya), itu informasi divergensi |

### 3.7 Central bank gold — WGC kuartalan + PBoC bulanan

Dua series, dua peran:

| | WGC GDT (CB agregat dunia) | PBoC/SAFE (China saja) |
|---|---|---|
| Apa | Total beli emas bank sentral semua negara, per kuartal | Cadangan emas resmi China, per bulan |
| Siapa & kapan | World Gold Council, laporan Gold Demand Trends 4×/tahun; **input manual** via CLI `arkwatch flows add` dengan review prompt | SAFE `safe.gov.cn` (Official Reserve Assets) XLSX bulanan; emas dalam 万盎司 |
| Konversi | Sudah tonne | **× 0,311034768 = tonne** (konstanta dikoreksi 2026-08-30 — sebelumnya salah transkripsi digit; wajib unit-test vs angka WGC) |
| Peran | Elemen "regime decoupling" | Deteksi lebih cepat dari WGC (bulanan vs kuartalan) |

Contoh angka nyata dari spec (contoh nilai Agt-2026): PBoC 2026 Jan–Jul **2.286 → 2.366 tonne** (angka Indonesia: dari ±2.286 ton ke ±2.366 ton = **+±80 ton dalam 7 bulan**) — output brief: `PBoC beli 7 bulan berturut`. Ambang naratif WGC: `CB >100t/q bertahan` = regime decoupling masih hidup (pembeli struktural >100 ton per kuartal).

Cara baca untuk trading: ini **bukan** sinyal entry harian. Ini *kondisi cuaca* — selama CB terus beli, (a) korelasi historis gold↔real yield layak dicurigai, (b) dip beli cenderung ditopang. Data resmi = yang *dilaporkan*; beli yang lewat jalur non-resmi tidak kelihatan — jadi anggap ini batas bawah, bukan angka penuh.

### 3.8 TIC foreign holdings — arus dana asing ke obligasi AS

| Aspek | Isi |
|---|---|
| Apa sebenarnya | Catatan Treasury: berapa sekuritas AS dipegang investor asing (negara mana, jenis apa) |
| Siapa & kapan | `ticdata.treasury.gov/Publish/mfh.txt` — bulanan (praktisnya rilisnya telat beberapa pekan dari bulan yang dilaporkan) |
| Dipakai untuk | Foreign financing — apakah dunia masih mau membiayai defisit AS; **tail untuk DXY** |
| Cara baca | Baca *trend*, bukan lompatan bulan-tunggal: penurunan berkelanjutan = asing menarik dana dari dolar → sisi risiko bagi DXY dan suku bunga Treasury (tema fiskal Blok E) |

### 3.9 Copper fisik — COMEX stocks + kurva (squeeze XCUUSD)

| Aspek | Isi |
|---|---|
| Apa sebenarnya | Stok copper di gudang COMEX + bentuk kurva futures. Stok menipis + kurva backwardation = pasar fisik ketat |
| Siapa & kapan | Jalur **backdoor CME** untuk produk HG (product id `438`) — W/D (mingguan/harian) |
| Kenapa bukan spot EODHD | Spot XCUUSD EODHD **basi** (berhenti akhir Juni, §10) — untuk harga dipakai futures `HG=F` (Yahoo) atau FMP `historical-price-eod?symbol=HGUSD` (WAJIB `from/to` eksplisit) |
| Cara baca | Contoh output spec: `stocks turun 5 minggu + backwardation` → squeeze-watch aktif untuk XCUUSD. Normal: stok naik-turun biasa + kurva contango |

Pendamping dari blok lain untuk konfirmasi squeeze copper: OI (`voi_daily` `oiDiff`), konsentrasi top-4 trader COT HG (§18.3), dan vol implied HGVL dari CVOL (Blok F; contoh nilai Agt-2026: HGVL 26,8 — spec: vol copper tidak ada di sumber gratis mana pun selain ini).

### 3.10 LBMA silver vault — stok global silver (squeeze XAGUSD)

| Aspek | Isi |
|---|---|
| Apa sebenarnya | Total perak di gudang-gudang London (pusat grosir silver dunia) — level + tren |
| Siapa & kapan | XLSX bulanan di CDN LBMA (`cdn.lbma.org.uk`), pola nama file predictable; **121 bulan historis Jul-2016→kini**. Satuan koz → tonne (×0,0311035) |
| Jebakan implementasi | Situs lbma.org.uk memblokir PowerShell — **target CDN langsung** |
| Cara baca | Tren turun berbulan-bulan = pasar fisik menipis = bahan bakar narasi squeeze silver. Bulanan & lag ±sebulan: ini *konfirmator* untuk bias swing, bukan timing entry. Pendamping yang lebih responsif: vol silver SIVL (contoh Agt-2026: 45,9 vs gold ±24 → "sizing XAG ½ XAU") dan skew CVOL (Blok F) |

---

## 4. Logika hilir-ke-hulu — dari angka mentah ke baris brief

Konsep transform yang dipakai blok ini (semuanya sederhana, dijelaskan dulu):

- **Δ (perubahan)** — `nilai hari ini − nilai kemarin`. Holdings GLD, stok COMEX, cadangan PBoC: semua dibaca sebagai perubahan, bukan level. Analogi: yang penting bukan berapa liter air di tangki, tapi apakah sedang diisi atau disedot.
- **ΔWoW (perubahan mingguan)** — sama tapi jendela 7 hari; dipakai stablecoin supply agar noise harian mentah tidak menipu.
- **Rata-rata berbobot waktu** — funding 8-jamanan (3 titik per hari) dirata-rata jadi satu angka EOD, **tertimbang lama interval**. Contoh ilustrasi: 00:00 +0,010%, 08:00 +0,012%, 16:00 +0,008% → EOD +0,010%. (Persis seperti nilai rapor: nilai × bobot sks, dijumlah, dibagi total sks.)
- **Run-length / streak** — "turun 5 minggu berturut-turut", "beli 7 bulan berturut". Arah yang bertahan lebih informatif dari satu titik.
- **Konversi satuan teraudit** — semua satuan eksotis (万盎司, koz) dikonversi lewat unit registry terpusat dengan **unit test terhadap angka publikasi WGC**, bukan konstanta yang diketik ulang tangan per fetcher. (Alasannya sejarah bug: konstanta PBoC sempat salah satu digit.)
- **Z-score / percentile** — untuk funding "ekstrem", angka hari ini dibandingkan distribusi historisnya sendiri (`(x−mean)/σ`, window standar 5y sesuai frekuensi — aturan umum §3 BUILD-PLAN). Detail: angka ambang ekstrem = parameter kalibrasi yang tercatat, bukan angka sakti.

Pipeline per series (BUILD-PLAN §3 Blok H):

```
GLD XLSX              → Δtonnes ──┐
harga XAUUSD (§10)    → Δharga  ──┴→ bandingkan arah → label KONFIRMASI / DENIAL
Bybit tickers         → fundingRate 8j×3 → rata-rata tertimbang → funding EOD (bps)
Bybit tickers / OI    → openInterest → OI + Δ
Farside HTML          → parse tabel → btc_etf_musd, eth_etf_musd ($/hari)
DefiLlama JSON        → total & USDT/USDC → ΔWoW
SAFE XLSX (万盎司)     → ×0,311034768 → tonne → Δ bulanan + streak beli   ┐
WGC GDT (manual CLI)  → tonne/q  ─────────────────────────────────────────┴→ flag "CB-buying aktif"
LBMA CDN (koz)        → ×0,0311035 → tonne → level + tren bulanan
CME backdoor HG 438   → stok + kurva → squeeze-watch XCU
ticdata mfh.txt       → tren bulanan → tail DXY
```

Rumah datanya dua tabel (§12 spec + §2 BUILD-PLAN):

- `flows_daily` — `date, gld_tonnes, slv_shares, btc_etf_musd, eth_etf_musd, funding_bps, oi_btc, oi_eth, stablecoin_usd`
- `flows_periodic` — `(period, kind[wgc_cb|pboc_gold|lbma_silver|tic], value_raw, unit_raw, factor, value, meta_json)` — raw + hasil konversi disimpan bersama (prinsip raw+derived §0.4: derived selalu bisa dihitung ulang)

**Kontribusi ke regime score — baca hati-hati:** formula regime score (§11.1) membobotkan hanya pilar **A–F** (A .20, B .20, C .15, D .15, E .15, F .15). Blok H **tidak punya bobot langsung** di skor. Perannya empat:

1. **Anomali & alert (§11.5)**: "funding-rate ekstrem" dan "copper stocks drain" masuk daftar alert.
2. **Syarat bendera decoupling Blok B**: flag gold↔real-yield divergence hanya menyala kalau korelasi berbalik **dan CB-buying aktif** (evidensinya dari Blok H — WGC/PBoC).
3. **Kalimat konfirmasi/denial di brief** (baris Flows + catatan implikasi instrumen).
4. **Cek silang antar-blok**: stablecoin vs net-liquidity (E); squeeze watch H ↔ konsentrasi COT & OI (G) ↔ vol/skew CVOL (F).

Jadi Blok H = *lensa verifikasi*, bukan *tuas skor*. Ia mengubah cara kamu menimbang sinyal A–F, bukan menambah angka.

Jadwal fetch (§13, WIB): **06:30** flows crypto-native (Farside/Bybit/DefiLlama — saat EDT ini 19:30 sebelumnya, menangkap sesi AS yang sudah tutup); **harian (gray)**: GLD/funding/OI/stablecoin; PBoC/LBMA/WGC/TIC mengikuti rilisnya (bulanan/kuartalan) dengan freshness-stamp — lewat jadwal tanpa update = ditandai basi, bukan dipakai diam-diam (§0.2).

### 4.1 Dua hari fiktif, satu latihan membaca

Semua angka di bawah ilustrasi latihan (dibangun dari pola contoh spec, bukan hari nyata):

**Hari A — KONFIRMASI (sehat):**
```text
XAUUSD +1,2%  |  GLD +2.1t  |  PBoC streak beli ke-7  |  RY 20d turun
→ Baca: pembeli hadir di dua keluarga (Barat + struktural), searah dengan driver Blok B.
  Keyakinan naik. Kalau positioning COT belum crowded → sinyal "ikut trend" paling kuat.
```

**Hari B — DENIAL (curiga):**
```text
XAUUSD +1,2%  |  GLD −1.4t  |  funding BTC +0,09%/8j (persentil ekstrem)  |  RY 20d NAIK
→ Baca: harga naik tapi (a) investor Barat justru keluar, (b) real yield melawan.
  Kalau CB masih beli → kemungkinan bid struktural/short-covering: trend mungkin lanjut,
  tapi TANPA dukungan flows — ini skenario "tunggu pullback / jangan chase" di brief.
→ BTC: funding persentil ekstrem = alert anomali §11.5 → ukuran posisi kecil,
  siapkan skenario cascade tajam dua arah.
```

Perhatikan pola bacaannya selalu tiga lapis: **harga → flows → siapa yang hadir**. Blok A–G bilang "apa kondisinya"; Blok H bilang "apakah gerakannya punya penumpang".

### 4.2 Keterkaitan dengan blok lain (peta ringkas)

| Blok tetangga | Titik sambung |
|---|---|
| B — Real yield | Flag decoupling gold↔RY hanya menyala bila CB-buying aktif (evidensi dari H) |
| E — Likuiditas | Stablecoin ΔWoW vs net-liquidity tradfi: sepakat = konfluensi; beda = divergensi dicatat |
| F — Vol & stress | SIVL/HGVL/POVL + skew = konfirmator cepat untuk squeeze-watch XAG/XCU (data H yang lambat) |
| G — Positioning | OI VOI harian + konsentrasi top-4 COT (HG/GC) = sisi "bensin & penguasaan kemudi" dari cerita squeeze H |
| D — Growth non-US | Demand sisi copper (Caixin, USDCNY) memodifikasi seberapa serius stok COMEX menipis |

---

## 5. Cara membaca baris Blok H di brief + jebakan salah-baca

Baris khas di brief (contoh dari §14 spec, tanggal contoh Agt-2026):

```text
Flows: GLD +2.1t (konfirmasi) | BTC ETF +$240M | funding +0.01% (long crowded)
...
• XAUUSD : tailwind (RY↓, dolar melemah) TAPI crowded → tunggu pullback
```

Membacanya berlapis: (1) apa kata macro (blok A–F) → (2) apa kata harga → (3) **apa kata flows** → (4) sinkron atau divergen? Contoh di atas: XAUUSD punya tailwind dua pilar, tapi positioning (G) crowded dan GLD konfirmasi datang — brief menyarankan menunggu pullback, bukan chase. Itulah fungsi flows: menaikkan/menurunkan keyakinan, bukan membalik arah.

**Jebakan salah-baca umum:**

1. **"Flows masuk regime score" — TIDAK.** Skor hanya A–F. Baris Flows = konteks & alert.
2. **"ETF flow negatif = bearish gold" — terlalu cepat.** GLD hanya demand *Barat*. Justru kombinasi `gold naik + GLD flat/turun + CB aktif beli` = ciri era decoupling (bid struktural yang tidak terlihat di data ETF). Divergensi = informasi, bukan selalu kontradiksi yang harus "dimenangkan" salah satu.
3. **"Funding tinggi = bullish" — KEBALIKAN.** Funding tinggi positif = long crowded = posisi naik sudah penuh penumpang = rapuh terhadap cascade. Funding sehat kecil-positif yang dicari.
4. **"OI naik bagus" — netral.** OI = bensin, bukan arah. Harga+OI naik bersama yang baru informatif.
5. **"Stablecoin naik pasti BTC naik" — likuiditas ≠ pembelian.** Itu uang *siap* beli, bukan janji beli. Yang bermakna adalah tren + kesepakatannya dengan net-liquidity tradfi.
6. **Baca level, bukan Δ.** "GLD 1.100 ton" sendiri tak berkata apa-apa; "GLD +12t dalam seminggu sementara harga +1,2%" yang berarti.
7. **Angka Farside hari-berjalan bisa masih berubah** sampai sesi AS benar-benar tutup — jangan bandingkan angka siang vs malam hari yang sama.
8. **Spot copper EODHD basi** (akhir Juni) — jangan pernah pakai untuk apa pun di XCUUSD; futures HG jalannya.
9. **Jangan percaya satuan mentah**: 万盎司 ≠ tonne ≠ koz. Semua konversi lewat unit registry; angka PBoC dibaca "2.286→2.366" itu **tonne** (format ribuan Indonesia).
10. **WGC ≠ PBoC.** WGC = agregat semua CB, kuartalan, bisa direvisi; PBoC = China saja, bulanan, lebih cepat. "CB aktif beli" untuk flag decoupling memakai keduanya, bukan salah satu.
11. **LBMA & TIC telat.** Bulanan dengan lag — dipakai untuk meyakinkan bias swing, bukan timing.
12. **"Crowded" ≠ "balik arah besok".** Crowded = asimetri risiko memburuk; trigger tetap datang dari harga/event.

---

## 6. Keterkaitan spesifik per instrumen

| Instrumen | Series Blok H yang relevan | Cara memakai |
|---|---|---|
| **XAUUSD** | GLD Δ, WGC/PBoC, TIC | GLD = konfirmasi/denial hari-harian; CB-buying = alasan menoleransi divergensi vs real yield (Blok B); TIC = narasi dolar |
| **XAUEUR / XAUGBP (crosses)** | sama, via leg XAU | Flows emas hampir seluruhnya sisi-XAU; leg EUR/GBP dari Blok A/D. CB-buying non-USD justru paling relevan untuk narasi cross (de-dolarisasi) |
| **XAGUSD** | SLV (W), LBMA vault (M), + squeeze-watch | Resolusi data silver lebih kasar dari gold — gabungan stok London (tren) + vol SIVL (contoh Agt-2026: 45,9 → sizing ½ XAU) + skew |
| **XPTUSD** | (tidak ada series H khusus) | Platinum di Blok H memang tipis — andalkan COT Disagg `076651` (G) + POVL 38,9 (F, contoh Agt-2026). Jangan mengarang "vault platinum" |
| **XCUUSD** | COMEX stocks + kurva HG `438` (W/D) | Squeeze detection: stok turun berminggu-minggu + backwardation = alert; konfirmasi OI/konsentrasi (G) dan HGVL (F); sisi demand China dari Blok D (Caixin/USDCNY) |
| **BTC** | ETF flows, funding, OI, stablecoin (+net-liquidity E) | Kombinasi favorit: likuiditas ↑ + ETF flow positif + funding sehat = konfluensi; funding ekstrem = alert anomali |
| **ETH** | ETH ETF flows, funding/OI Bybit | Sama dengan BTC; positioning tambahan dari COT `146021` (Blok G) |
| **US100/500/30** | tidak langsung (TIC saja) | Blok H bukan driver indeks — jangan dipaksakan; andalkan Blok D/F/G |
| **EURUSD/GBPUSD/majors** | TIC | Tren penarikan asing = tail DXY → headwind majors; detail rate dari Blok A |
| **DXY** | TIC, (stablecoin mint sebagai minat dolar) | TIC = satu-satunya series H yang langsung bicara dolar |

---

## 7. Yang bisa salah — degradasi, kualitas data, keterbatasan

**Mode degradasi (per sumber, §0.3 + §11.4):**

| Sumber mati | Yang terjadi |
|---|---|
| Farside (gray T3) | BTC/ETH flow dari **mirror BitMEX/CoinGlass**, atau baris `flow: N/A` — tidak pernah diam-diam kosong |
| Backdoor CME (gray T3) — copper stocks/kurva | Baris squeeze-watch hilang + flag; **retensi 5 hari kerja** → harvester tak boleh bolong >3 hari trading atau data hilang permanen; wajib `curl_cffi` impersonate-chrome **dari Windows lokal** (cloud IP & PowerShell mentah = 403) |
| Bybit | Tidak ada sekunder eksternal di spec — baris funding/OI di-flag (prinsip no-silent-fallback: gagal = ERROR di `fetch_log` + flag brief, bukan angka lama dipakai terus). Redundansi internal: `/funding/history` bisa isi ulang funding yang hilang |
| GLD XLSX | Single-source resmi — dianggap boleh asal freshness-check jalan; lewat jadwal tanpa file baru = basi |
| SLV | FMP gagal → HTML iShares (sekunder resmi) |
| WGC manual | Human-in-the-loop: CLI `arkwatch flows add` dengan review prompt — salah ketik terjadi pada manusia, makanya ada prompt |
| SAFE/LBMA CDN | Lembaga resmi (T0); jebakan akses: lbma.org.uk blokir PS → selalu CDN |

**Kualitas data & keterbatasan:**

1. **Frekuensi campuran.** GLD/funding harian; SLV mingguan; PBoC/TIC/LBMA bulanan; WGC kuartalan. Jangan menuntut kecepatan sinyal squeeze dari data yang bulanan — pasangkan yang lambat (LBMA) dengan yang cepat (vol/OI).
2. **Agregasi berbeda-beda.** WGC merevisi angka kuartalan; PBoC melaporkan *resmi* (beli via jalur tak resmi tak terlihat); TIC mengalami seasonal-adjustment dan reklassifikasi — baca tren, jangan bulan-tunggal.
3. **Funding lintas bursa.** Kita pakai Bybit; bursa lain (Binance dll.) bisa sedikit beda level funding pada jam yang sama — ini pilihan sadar (satu call dua sinyal), bukan kebenaran tunggal pasar.
4. **Stablecoin total ≠ USDT+USDC.** Endpoint `all` mencakup semua stablecoin; filter `?stablecoin=1/2` untuk dua raksasa. Baris brief "USDT+USDC +$1.2B/w" itu dua-koin, bukan total.
5. **Angka flow ETF bukan volume.** Net flow = *selisih* beli-jual; hari net +$240M bisa terjadi di volume besar maupun kecil — arah uang, bukan keramaian.
6. **Gray = sewa, bukan milik.** Farside & backdoor CME bisa berubah kapan saja tanpa pemberitahuan (sudah terbukti: `/funding/info` 404, delayed-quotes CME REFUTED). Semua snapshot menyimpan raw + hasil hitung bersama supaya bisa direkonstruksi.
7. **Gerbang kebenaran tetap berlaku.** Semua series H ikut mekanisme F0 (sanity-range, depth, cross-val, karantina bila primer vs sekunder melenceng) dan unit-test konversi terhadap nilai WGC publik (BUILD-PLAN §3, §5).

---

## 8. Pertanyaan untuk menantang desain (dan jawabannya)

Pemilik sistem memang boleh — bahkan diminta — menantang keputusan desain. Daftar "kenapa bukan cara lain?" yang paling wajar muncul:

| Tantangan | Jawaban dari spec/plan |
|---|---|
| "Kenapa GLD saja? Kenapa tidak gabungan semua ETF emas?" | GLD punya arsip XLSX resmi harian dari penerbit — gratis, resmi, dalam tonne. Proxy agregat FMP `/sentiments` sudah diuji dan **digugurkan** (LOW; crypto diam-diam dihapus dari respons, §16). Kalau mau tambah agregat, harus lulus gerbang F0 dulu |
| "Kenapa funding diambil dari Bybit, bukan Binance?" | Satu call `tickers` = `fundingRate`+`openInterest` sekaligus; historis lengkap ~2020 via `funding/history`. Keputusan sadar, bukan klaim bahwa Bybit = seluruh pasar — level funding antar bursa bisa beda tipis |
| "Kenapa funding dirata-rata jadi harian? Puncak 8-jam kan lebih tajam." | Kita swing (hari–minggu), brief harian 07:00 WIB — EOD rata-rata tertimbang 3 titik cukup dan lebih tahan noise; nilai 8-jam mentah tetap ada di raw (prinsip raw+derived, bisa dihitung ulang) |
| "Kenapa WGC di-input manual? Kenapa tidak di-scrape otomatis?" | Putusan F2 (BUILD-PLAN §3-H): WGC manual via CLI dengan review prompt — data kuartalan, 4×/tahun, risiko salah-parse/angka revisi lebih mahal daripada 4× ketik setahun |
| "Kenapa stablecoin baris brief hanya USDT+USDC?" | Itu dua koin dominan; total semua stablecoin (`/all`) tetap disimpan — baris brief memilih yang paling bermakna ekonomi, bukan yang paling lengkap |
| "Blok H kok tidak diberi bobot di regime score? Bukanku flows penting?" | Flows penting sebagai *verifikasi*, tapi frekuensinya campur aduk (harikan vs kuartalan) dan sebagian gray — memasukkannya ke skor rata-rata z akan membuat skor goyang karena sumber yang basi/gray mati. Desain v1: skor dari A–F, H sebagai lensa + alert. Ini keputusan yang boleh di-revisit kalau kalibrasi menunjukkan nilai tambah |
| "Angka CB beli bisa dipercaya?" | Sebagian: itu angka *yang dilaporkan*. Karena itu dipakai sebagai **bendera regime** (aktif/tidak aktif beli), bukan sebagai angka input presisi ke formula |

---

*Akhir dokumen Blok H. Rantai lengkap hulu→hilir dapat dijelajah via `arkwatch explore block H` / `arkwatch explore series ... --trace` (BUILD-PLAN §8).*
