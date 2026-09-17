# Blok B — Real Yield (Driver #1 Gold)

> Dokumen edukasi ark-watch, ditulis untuk pemilik sistem: trader ritel swing (hari–minggu) yang BUKAN orang finance.
> Pasangan resmi: [DATA-SPEC.md](../DATA-SPEC.md) §2 (Blok B), §0 (prinsip), §11 (sinyal komposit), §13–§14 (jadwal & contoh brief), §16 (audit sumber), [BUILD-PLAN.md](../BUILD-PLAN.md) §0 (prinsip dev), §3-B (transform Blok B), §6.3 (identitas harian).
> Konvensi angka: angka bertanda **(contoh nilai Agt-2026)** diambil persis dari spec. Angka bertanda *(konteks umum)* adalah konteks sejarah untuk edukasi — BUKAN angka resmi spec.

---

## 1. Kenapa blok ini ada — cerita di balik angkanya

### 1.1 Masalah intinya: emas tidak membayar bunga

Bayangkan Anda punya dua pilihan menyimpan kekayaan selama 10 tahun:

1. **Emas di brankas.** Cantik, tidak berkarat, diakui di mana-mana — tapi diam. Setahun berapa bunganya? **Nol.** Tidak ada kupon, tidak ada dividen, tidak ada bunga. Satu-satunya cara untung: orang lain mau membelinya lebih mahal dari harga Anda beli.
2. **Obligasi pemerintah AS (Treasury).** Setahun sekali (secara teknis dua kali) membayar bunga pasti, dalam dolar.

Investor besar (dana pensiun, hedge fund, bank sentral) menghadapi pilihan ini setiap hari. Ketika obligasi menjanjikan penghasilan nyata yang besar, uang mengalir ke situ dan emas kehilakan daya tarik. Ketika obligasi nyaris tidak menjanjikan apa-apa — atau malah menyusutkan daya beli — emas tiba-tiba jadi pilihan paling masuk akal untuk "parkir" kekayaan.

Yang menentukan siapa yang menang bukan bunga tertulis di brosur, melainkan **bunga setelah dipotong inflasi**. Itulah *real yield* — dan itulah seluruh alasan blok ini ada. Dalam istilah ekonomi: emas punya **opportunity cost** (biaya kesempatan) berupa bunga riil yang Anda lewatkan karena memilih brankas. Real yield adalah harga dari memegang emas.

### 1.2 Tiga bersaudara: nominal, inflasi, real — plus "taruhan pasar"

Pakai analogi sehari-hari:

| Konsep | Analogi sehari-hari | Angka nyata |
|---|---|---|
| **Yield nominal** (bunga tertulis) | Bunga deposito yang besar di brosur bank: "5% setahun!" | DGS10 = 4.67% (contoh nilai Agt-2026, golden anchor F0) |
| **Inflasi** | Kenaikan harga bakso/nasi goreng per tahun. Bunga 5% tapi bakso naik 6%? Daya beli Anda justru turun. | (inflasi aktual = urusan Blok C, bukan blok ini) |
| **Yield real** (bunga sejati) | Bunga brosur **dipotong** kenaikan harga. Inilah yang benar-benar Anda "rasakan". | DFII10 = 2.34% (contoh nilai Agt-2026) |
| **Breakeven** | "Kepercayaan pasar pada inflasi" — seperti **odds di taruhan**: berapa persen inflasi yang dipercaya pasar akan terjadi. | Breakeven 2.31% (contoh nilai Agt-2026) |

Hubungan ketiganya adalah identitas klasik (persamaan Fisher):

```
nominal ≈ real + ekspektasi inflasi pasar
DGS10 ≈ DFII10 + T10YIE
4.67% ≈ 2.34% + 2.33%   (hitungan: 4.67 − 2.34 = 2.33; T10YIE tercatat 2.31;
                          selisih 2bps → jauh di dalam toleransi verifikasi ±25bps — lihat §4.4)
```

Dari mana angka "real" didapat? Bukan dari menghitung inflasi yang sudah terjadi (itu mundur ke belakang), tapi dari **instrumen pasar sungguhan**: TIPS — obligasi Treasury AS yang kontraknya otomatis menyesuaikan dengan inflasi (pokok pinjamannya naik ikut CPI). Karena inflasi sudah "dimasukkan" ke dalam kontrak, yield TIPS **langsung** memberi tahu berapa bunga riil yang pasar tuntut hari ini. Tidak perlu menebak inflasi — pasar yang menjawab.

Dan breakeven? Beda harga antara obligasi biasa dan obligasi anti-inflasi ini = jumlah "inflasi" yang tersirat dalam harga. Kalau Anda yakin inflasi akan lebih tinggi dari breakeven, Anda beli TIPS; kalau yakin lebih rendah, Anda beli obligasi biasa. Jutaan keputusan seperti itu menghasilkan angka 2.31% — **konsensus taruhan pasar**, bukan survei opini.

### 1.3 Kenapa DFII10 disebut driver #1 XAUUSD

Dari semua indikator makro di mesin ini, hubungan real yield 10 tahun ↔ harga emas adalah yang paling konsisten dan paling sering dijelaskan secara mekanis (bukan kebetulan statistik):

- **Real yield = "harga duduk" di emas.** Momen DFII10 berada di 2.34% (contoh nilai Agt-2026), siapa pun yang memegang emas melewatkan 2.34% per tahun penghasilan riil yang nyaris bebas risiko (di atas inflasi!). Itu rintangan (hurdle) yang tinggi. Semakin tinggi rintangan → semakin mahal "harga" emas → tekanan turun.
- **Sebaliknya, saat real yield jatuh ke nol atau negatif**, obligasi aman pun tak mampu melindungi daya beli — uang "membakar diri" bila disimpan di instrumen berbunga. Saat itulah emas bersinar sebagai penyimpan nilai terakhir.
- *(konteks umum)* Sejarah kasar: real yield 10Y sempat di bawah nol (~0 s/d −0,5%) pada 2011–2012, lalu lebih dalam (sekitar −1%) pada 2021–2022 — dua era di mana emas mencetak puncak historisnya; kemudian naik ke kisaran 2.4–2.5% pada 2023–2025, wilayah tertinggi sejak instrumen TIPS ada. Angka 2.34% Agt-2026 berarti kita masih di era "rintangan tinggi".

Karena hubungan ini begitu sentral, Blok B diberi **bobot 20% dari regime score** — sama besar dengan Blok A (Policy & Dollar), terbesar bersama. Untuk book Anda yang inti logamnya XAUUSD/XAGUSD, baris Blok B adalah baris pertama yang harus dibaca setiap pagi.

### 1.4 Twist era sekarang: bank sentral membeli emas begitu banyak sehingga aturan lama melentur

Sejak 2022 ada pemain baru yang mengubah permainan: **bank sentral** (Tiongkok, Polandia, Turki, India, dll) membeli emas fisik ratusan ton per tahun — bukan untuk profit, tapi untuk **mendiversifikasi cadangan DeV dari dolar** (motif geopolitik). Pemain ini **tidak peduli opportunity cost**. Mereka tidak membandingkan emas dengan bunga Treasury; mereka membandingkan dolar dengan "bukan-dolar".

Akibatnya, sekitar 2022–2026 harga emas mampu **naik justru saat real yield naik** — mematahkan korelasi terbalik berabad-abad. Perilaku "salah arah" seperti ini justru informasi berharga: kalau emas naik meski real yield naik, artinya ada *bid struktural* (permintaan lapis bawah yang terus-menerus) yang menopang harga — dan logika driver #1 harus dipakai dengan lebih hati-hati. Blok B karena itu punya sinyal khusus **divergence gold↔RY** (§3.4 dan §4.5), yang menggabungkan data bank sentral dari Blok H.

### 1.5 Apa yang dihasilkan blok ini di brief harian

| Output di brief | Dari series mana |
|---|---|
| "DFII10 2.34% FALLING (−15bps/20d) → tailwind gold" | DFII10 + momentum 20d + z-score 5y |
| "DFII10 2.34% (−3bps) → tailwind gold" *(baris "Berubah semalam")* | DFII10, Δ harian |
| "RealYield=FALLING" *(baris Pilar)* | state Blok B |
| "breakeven 2.31%" | T5YIE/T10YIE |
| Level 5y5y vs target 2% | T5YIFR |
| "gold naik meski RY naik = bid struktural" *(baris Anomali)* | sinyal divergence computed |

### 1.6 Keputusan desain yang layak Anda tantang

Anda berhak — dan sebaiknya — menantang keputusan berikut, karena semuanya kalibrasi v1, bukan hukum alam (spec §11: "kalibrasi bisa berubah, dihitung ulang dari raw"):

| Keputusan | Alasan v1 | Kapan seharusnya diganggu |
|---|---|---|
| Bobot Blok B = 0.20 (setara Blok A, terbesar) | Real yield adalah mekanisme paling langsung ke emas | Bila era CB-buying terbukti membuat hubungan RY↔gold lemah bertahun-tahun, bobot divergence/pilar lain naik |
| Headline memakai DFII10 (bukan DFII5) | 10Y = standar literatur & paling likuid | Bila siklus bergerak sangat cepat, DFII5 memberi sinyal lebih dulu — pantau keduanya |
| Ekspektasi pasar (TIPS), bukan inflasi aktual | Trading bereaksi pada apa yang *dihargai ke depan*, bukan yang sudah lewat | Untuk validasi jangka panjang, bandingkan dengan Blok C (inflasi aktual) — selisahnya sendiri informatif |
| Window z 5 tahun | Kompromi: cukup panjang untuk stabil, cukup pendek untuk relevan | 10 tahun lebih stabil tapi lambat bereaksi pada pergantian era; risiko terjebak era lama |
| Single-source FRED tanpa sekunder permanen | Tier 0 resmi + freshness-check aktif (diizinkan §0.1) | Sudah berlapis: failover EODHD + identitas Fisher harian — tiga jaring penangkap |
| Divergence butuh DUA syarat (korelasi ≥ +0.3 DAN CB aktif) | Anti false-positive; korelasi positif sendiri bisa terjadi saat vol rendah | Bila muncul korelasi positif tanpa CB buying, itu justru temuan menarik untuk ditelusuri |

---

## 2. Glosarium — istilah Blok B dari nol

| Istilah | Artinya untuk orang awam | Kenapa penting untuk trading Anda |
|---|---|---|
| **Yield / suku bunga obligasi** | Bunga tahunan yang janjikan peminjam (pemerintah AS) kepada pemegang obligasi. Yield naik = harga obligasi turun (dua sisi koin yang sama). | Bahasa dasar seluruh pasar modal; hampir semua aset dihargai relatif terhadapnya. |
| **Nominal yield** | Bunga tertulis, belum dipotong apa pun. Di AS diukur DGS10 (10 tahun), DGS2, DGS30. | Kaki penyusun identitas; tinggal di Blok A tapi dipakai verifikasi Blok B. |
| **Real yield** | Bunga setelah dipotong inflasi. Inilah daya beli yang benar-benar bertambah. | Driver #1 XAUUSD — "harga" memegang emas. |
| **TIPS** | Treasury Inflation-Protected Securities: obligasi AS yang pokok pinjamannya naik ikut inflasi (CPI). | Sumber angka real yield langsung dari harga pasar, tanpa perlu menebak. |
| **DFII10 / DFII5** | Yield TIPS tenor 10 / 5 tahun buatan Fed (constant maturity — dirangkai dari banyak obligasi agar selalu mewakili "tenor 10 tahun", bukan satu obligasi tua). | Series utama Blok B. |
| **Breakeven inflation** | Selisih nominal − real = inflasi yang "dipertaruhkan" pasar. Angka konsensus pasar, bukan survei. | Membedakan "emas naik karena bunga turun" vs "emas naik karena inflasi ditakuti" — dua regime berbeda. |
| **5y5y forward** | Breakeven untuk jendela tahun ke-5 s/d ke-10 ke depan; inflasi jangka panjang murni, kebal terhadap guncangan minyak jangka pendek. | Deteksi "jangkar inflasi bergeser" — hal yang paling ditakuti Fed. |
| **bps (basis point)** | Satuan perubahan bunga: 1% = 100 bps. Jadi −15bps = −0.15 persen poin. | Bahasa standar perubahan yield; dipakai di seluruh brief. |
| **Momentum (20d)** | Selisih level hari ini vs 20 hari bursa lalu. Spedometer: seberapa cepat dan ke arah mana. | Arah lebih menentukan regime daripada level; contoh: −15bps/20d → FALLING. |
| **z-score (5y)** | "Seberapa tidak wnormalnya" angka hari ini dibanding rata-rata 5 tahun terakhir, dalam satuan simpangan baku (σ). z = (x − mean) / σ. | Mengubah persen mentah jadi bahasa "tinggi/rendah versi era sendiri" — adil terhadap pergantian era bunga. |
| **Percentile** | Peringkat historis: "persentil 80" = lebih tinggi dari 80% waktu dalam 5 tahun. | Alternatif z yang lebih intuitif; dipakai blok lain (mis. HY spread). |
| **σ populasi** | Cara menghitung lebar "pita normal" memakai seluruh data window (bukan sampel). Detail teknis anti perdebatan antar-developer. | Menjamin dua orang menghitung z yang sama persis. |
| **State** | Label diskrit hasil pipeline: FALLING / FLAT / RISING (arah), dsb. | Bahasa ringkas yang dipakai regime score dan brief. |
| **Pilar** | Kelompok series satu blok; nilai pilar = rata-rata z anggotanya. | Blok B adalah satu pilar dari ±6 pilar regime score. |
| **Regime score** | Skor komposit −2…+2 dari seluruh pilar; bobot Blok B = 0.20 (20%). | Ringkasan satu angka "angin sekarang bertiup ke mana". |
| **Opportunity cost** | Biaya kesempatan: penghasilan yang Anda lewatkan karena memilih aset lain. | Alasan mekanis kenapa real yield menggerakkan emas (§1.1). |
| **QE / QT** | Quantitative Easing / Tightening: Fed MEMBELI obligasi (mencetak uang → likuiditas melimpah, QE) atau MEMBIARKAN portofolionya menyusut (QT). | Penjelas kenapa real yield bisa lama di nol/negatif (era QE) lalu melonjak (era QT) di peta §3.1. |
| **Stagflasi** | Kombinasi jahat: ekonomi STAGNAN (growth lemah) + inFLASI tinggi. | Regime "RY turun karena BE naik" (§3.2): bullish gold, tapi cerita berbeda dari pelonggaran sehat. |
| **Tailwind / headwind** | Angin sakal-lawan olahraga: tailwind = dorongan menguntungkan; headwind = lawan. | Label arah cepat di brief ("tailwind gold"). |
| **Korelasi** | Ukuran seberapa sering dua hal bergerak bersama (−1 s/d +1). | Dasar sinyal divergence: normalnya gold↔RY negatif. |
| **Divergence** | Dua hal yang biasanya berlawanan arah tiba-tiba bergerak searah. | Penanda era bank sentral; mengubah cara membaca driver #1. |
| **Bid struktural** | Permintaan yang terus ada lapis bawah terlepas harga/ bunga. | Penjelasan kenapa emas bisa naik saat RY naik. |
| **CB buying** | Pembelian emas bank sentral (data Blok H: WGC kuartalan + PBoC bulanan). | Syarat kedua sinyal divergence. |
| **FRED** | Perpustakaan data ekonomi Federal Reserve St. Louis — sumber resmi (Tier 0) seluruh series Blok B. | Gratis, otoritatif, stabil; jarang sekali salah. |
| **Failover** | Sumber cadangan otomatis bila primer bermasalah. Untuk Blok B: EODHD `/ust/real-yield-rates` (satu call, seluruh kurva real yield). | Menjamin brief tetap terbit saat FRED gangguan. |
| **Identitas harian** | Cek silang otomatis tiap hari: DFII10 ≈ DGS10 − T10YIE dalam ±25bps. | Penjaga anti data-jelek-diam-diam (§4.4). |

---

## 3. Peta data — series per series

Ringkasan dulu, lalu bedah satu per satu:

| Series | Apa | Sumber (tier) | Freq | Peran |
|---|---|---|---|---|
| `DFII10` | Real yield 10Y | FRED (T0) → failover EODHD (T1) | D | **Driver #1 XAUUSD**; z 5y + momentum 20d |
| `DFII5` | Real yield 5Y | FRED (T0) → idem | D | Pendamping tenor pendek; kaki breakeven 5Y |
| `T5YIE` | Breakeven 5Y | FRED (T0) → idem | D | Taruhan inflasi pasar 5 tahun |
| `T10YIE` | Breakeven 10Y | FRED (T0) → idem | D | Idem, 10 tahun; kaki identitas verifikasi |
| `T5YIFR` | 5y5y forward BE | FRED (T0) → idem | D | Jangkar inflasi jangka panjang vs target 2% |
| `SYN:RYDIV` *(computed)* | Divergence gold↔RY | internal (T4) | D | Flag era decoupling / bid struktural |

### 3.1 `DFII10` & `DFII5` — si penggerak utama

**Apa sebenarnya.** Yield (bunga tahunan) obligasi TIPS 10 tahun, versi *constant maturity*: Fed merangkai obligasi TIPS yang beredar supaya angkanya selalu mewakili tenor 10 tahun penuh — jadi angka hari ini dan angka 2007 masih "apel dibanding apel". DFII5 sama persis untuk tenor 5 tahun.

**Siapa menerbitkan, kapan.** Federal Reserve (H.15) via FRED, **setiap hari bursa AS (Senin–Jumat)**; nilainya mengunci pada penutupan pasar AS (konvensi `et_close`). Mesin kita memungutnya pukul **06:00 WIB** (jadwal §13), menyimpan UTC, menampilkan WIB. Libur AS = tidak ada baris baru; itu *null struktural* yang dianggap wajar, bukan error.

**Kenapa dipilih (dan apa yang tidak dipakai).**
- FRED = Tier 0 (institusi resmi). Aturan §0.1: sumber resmi boleh single-source asal freshness-check aktif — dan aktif (mekanisme `series/updates` §18.2 otomatis menandai basi).
- Failover resmi: **EODHD `/ust/real-yield-rates`** (diterima di audit §16) — satu call untuk seluruh kurva; toleransi silang **±2bps**.
- Yang ditunda: ekspektasi inflasi model Cleveland (`EXPINF1YR/10YR`) tercatat *nice-later* §18.4 — kelak jadi pembanding "model vs pasar", bukan pengganti pasar.
- Yang bukan alternatif: CPI aktual (Blok C) itu inflasi yang **sudah terjadi**; real yield adalah harga pasar tentang **yang akan datang**. Keduanya saling melengkapi, tidak saling menggantikan.
- Kenapa 10 tahun, bukan 30? 10Y adalah acuan standar pasar dan literatur gold; DFII5 dipelihara sebagai pendamping untuk melihat ujung siklus yang lebih sensitif.

**Cara baca angka.**

| Yang Anda lihat | Arti | Efek ke XAUUSD |
|---|---|---|
| Level **2.34%** (contoh nilai Agt-2026) | Rintangan riil 2.34%/thn — tinggi secara sejarah TIPS | Headwind level (tapi lihat arahnya dulu — baris berikut) |
| Level positif besar (≥ ~2%, *konteks umum*) | Era "brankas mahal" | Menekan emas… kecuali ada bid struktural (§3.4) |
| Level mendekati 0 / negatif | Uang parkir di obligasi kehilangan daya beli | Historis = lingkungan emas terbaik |
| **−15bps / 20d** (contoh nilai Agt-2026) | Momentum: turun 0.15pp dalam sebulan bursa → state **FALLING** | **Tailwind gold** — inilah baris paling berharga |
| +15bps / 20d | Momentum naik → RISING | Headwind gold (periksa divergence dulu) |
| Δ semalam **−3bps** (contoh brief 2026-08-29) | Perubahan harian | Sinyal lemah — noise; jangan bangun tesis dari satu hari |

Aturan praktis untuk swing trader: **arah (momentum) lebih menentukan daripada level**. Emas bisa saja terus naik selama turunannya melandai, meski level RY masih tinggi. Tapi jangan baca arah dari satu hari (−3bps itu kecil); yang menentukan state adalah jendela 20 hari.

**Peta era kasar DFII10** *(konteks umum — bahan intuisi, bukan angka spec)*:

| Era | Kisaran DFII10 | Cerita besar | Emas saat itu |
|---|---|---|---|
| 2011–2012 | 0 s/d −0,5% | Pasca-krisis, Fed QE besar-besaran, inflasi ditakuti | Puncak pertama ~$1.900 |
| 2013–2019 | 0 s/d +1% | Normalisasi pelan; inflasi tenang | Sideways–turun, lalu rebound |
| 2020–2022 | turun hingga ~−1% (terdalam 2021–22) | COVID: rate nol + QE maksimal | Menembus $2.000 |
| 2023–2026 | +1.8 s/d +2.5% | Inflasi tinggi + QT: rintangan emas tertinggi sepanjang sejarah TIPS | **Naik terus** — justru di sinilah era CB buying mengubah aturan (§1.4) |

Peta ini juga menjawab "kenapa pakai z-score": tanpa z, angka 2.34% tahun 2016 akan terbaca "ekstrem" dan tahun 2026 "biasa" — padahal persentasenya sama. Era menentukan makna; z mengukur terhadap era.

### 3.2 `T5YIE` & `T10YIE` — breakeven, "taruhan inflasi pasar"

**Apa sebenarnya.** Selisih yield obligasi nominal vs TIPS pada tenor yang sama (5Y dan 10Y). Angka ini adalah inflasi tahunan rata-rata yang pasar "beli" untuk periode itu — hasil jutaan transaksi, bukan hasil wawancara.

**Penerbit & jadwal.** FRED (dihitung dari pasangan DGS−DFII), harian, konvensi sama seperti §3.1.

**Kenapa dipilih.** Satu-satunya ukuran ekspektasi inflasi yang berbasis **harga uang sungguhan**. Survei konsumen (`MICH`) memang ada tapi itu opini — dipakai di Blok C sebagai jangkar yang berbeda. Breakeven juga kaki identitas verifikasi harian (§4.4): nominal − real harus kembali ke breakeven.

**Cara baca angka** *(ambang kualitatif di bawah = konteks umum, bukan angka spec)*:

| Level T10YIE/T5YIE | Cara membaca |
|---|---|
| **2.31%** (contoh nilai Agt-2026) | Sedikit di atas target 2% Fed — pasar percaya inflasi "hampir" terkendali |
| Kisaran ~2.0–2.5% | Zona normal era modern |
| Menanjak menembus ~2.5% dan terus naik | Pasar mulai meragukan komitmen/ kemampuan Fed → bias lama: emas & logam disukai, obligasi dijual |
| Jatuh di bawah ~1.8% | Ketakutan pertumbuhan/deflasi → bias risk-off; emas biasanya tetap terbantu hanya jika RY ikut jatuh lebih dalam |

Trik membaca pasangan RY+BE: dua kabar "RY turun" dengan makna berbeda —
- **RY turun karena nominal (DGS10) turun lebih cepat dari BE** → pasar mempercayai Fed akan melonggarkan; biasanya dolar ikut melemah; kombinasi paling klasik untuk rally emas.
- **RY turun karena BE naik lebih cepat dari nominal** → pasar takut inflasi (stagflasi ringan); emas naik, tapi regime berbeda — pantau Blok C dan 5y5y (§3.3) untuk melihat apakah ketakutannya serius.

### 3.3 `T5YIFR` — 5y5y forward: jangkar jangka panjang

**Apa sebenarnya.** Breakeven untuk jendela **tahun ke-5 sampai ke-10** dari sekarang (dihitung forward dari kurva 5Y dan 10Y). Karena lima tahun pertama "dibuang", guncangan sesaat — lonjakan minyak, satu rilis CPI buruk — tersaring. Yang tersisa adalah kepercayaan pasar pada **kebijakan moneter jangka panjang**. Analogi: suhu sesaat vs suhu inti tubuh.

**Penerbit & jadwal.** FRED, harian, konvensi sama.

**Kenapa dipilih.** Spec menyebutnya "lebih murni dari point BE" — inilah angka yang secara tradisi dipantau Fed sendiri untuk menjawab: *apakah jangkar ekspektasi inflasi masih terpasang di 2%?*

**Cara baca.** Bandingkan dengan **target 2%**:
- Nempel di ~2% → jangkar aman; spike inflasi sesaat akan lewat; Blok C boleh panik, Anda tidak perlu.
- Bergeser naik bertahan (mis. >2.3–2.4% berbulan-bulan, *konteks umum*) → pasar kehilangan kepercayaan pada "inflasi kembali ke 2%"; lingkungan struktural bullish emas dalam sejarah modern.
- Bergeser turun persisten → deflasi jangka panjang ditakuti; emas butuh RY jatuh dalam sebagai kompensasi.

### 3.4 Sinyal divergence gold↔RY — penjaga era bank sentral

**Apa sebenarnya.** Bukan series unduhan, melainkan **sinyal computed** (Tier 4, bisa dihitung ulang dari raw — prinsip §0.4): korelasi bergulir antara return emas dan perubahan DFII10.

- Formula (BUILD-PLAN §3-B): `corr( z(ret XAU, 60d), z(ΔDFII10, 60d) )` — korelasi 60 hari bursa antara return XAU (dalam z) dan perubahan DFII10 (dalam z).
- **Flag menyala bila keduanya terpenuhi:** (1) korelasi ≥ **+0.3** padahal normal historisnya **negatif**, **dan** (2) pembelian bank sentral sedang aktif menurut Blok H.
- Ambang +0.3 sengaja ditulis sebagai **parameter terkalibrasi** (bukan kata kabur "signifikan") — bisa direvisi lewat re-kalibrasi kuartalan.

**Kenapa penting.** Ini alarm "aturan main driver #1 sedang tidak berlaku penuh". Kalau emas naik *bersama* RY naik dan bank sentral sedang rakus membeli → harga ditopang **bid struktural**, bukan sekadar sentimen. Konsekuensi praktis di brief: tailwind/headwind RY dibaca dengan bobot lebih rendah, dan sinyal crowded positioning (Blok G) menjadi penentu timing yang lebih penting.

**Bahan baku & jadwal.** Harga XAU (matriks instrumen §10 — EODHD primer untuk spot) + DFII10 + status CB Blok H: **WGC kuartalan** (kriteria historis: >100 ton/kuartal bertahan = "aktif") dan **PBoC bulanan** via SAFE — contoh data nyata dari spec: cadangan PBoC 2.286 → 2.366 tonne sepanjang Jan–Jul 2026, artinya **beli 7 bulan berturut-turut** (contoh nilai Agt-2026). Output baris anomali: *"gold naik meski RY naik = bid struktural"*.

---

## 4. Logika hilir-ke-hulu — dari angka mentah ke regime score

Arah baca tabel ini dari kiri (hulu, mentah) ke kanan (hilir, keputusan); CLI `arkwatch explore series FRED:DFII10 --trace` menampilkan rantai yang sama (§8 BUILD-PLAN).

```
raw FRED (append-only, UTC)
  → fresh/sanity check (06:00 WIB)
    → momentum 20d  +  z-score 5y      [transform §4.1]
      → state (FALLING/FLAT/RISING)
        → pilar B = rata-rata z anggota
          → × bobot 0.20 → REGIME SCORE (−2…+2, flip ±0.5)
  → identitas harian DFII≈DGS−BE (§4.4)   [jalur verifikasi paralel]
  → divergence gold↔RY (§4.5)             [jalur anomali paralel]
```

### 4.1 Empat konsep transform, dijelaskan dulu

1. **Basis point (bps)** — penggaris perubahan bunga. 1% = 100 bps. "−15bps" = turun 0.15 persen poin. Kenapa tidak tulis persen saja? Karena menghindari kebingungan "turun 0.15%" vs "turun 15% dari nilai".
2. **Momentum-N** — selisih hari ini vs N hari bursa lalu. *Spedometer, bukan odometer*: 2.34% memberi tahu posisi; **−15bps/20d** memberi tahu kecepatan dan arah. Untuk series harian seperti Blok B, N = 20 hari bursa (±1 bulan kalender) — pas untuk horizon swing Anda. Spec umum: momentum series D dihitung dalam **hari bursa**, bukan hari kalender.
3. **z-score** — "berapa lebar dari normal". Rumusnya `z = (x − mean) / σ` pada **level** series, window **5 tahun sesuai frekuensi** (harian = 1.260 observasi bursa), σ populasi, dan minimal 80% data harus ada — kalau kurang, state = `INSUFFICIENT` (jujur mengaku buta, bukan mengarang angka). Contoh intuisi: z = +1 artinya "lebih tinggi dari rata-rata 5 tahun sejauh satu pita normal" — jarang tapi bukan anomali; z = +2.5 ke atas mulai historis. Kenapa pakai z dan bukan persen mentah? Karena "2.34% tinggi" tergantung era: di era 2010-an itu ekstrem, di era 2023–2026 biasa saja. z membandingkan selalu terhadap 5 tahun terakhir — adil terhadap pergantian era.
4. **Rata-rata berbobot** — cara pilar-pilar digabung jadi satu skor. Seperti nilai rapor: semua mata pelajaran dinilai lalu dikalikan bobot masing-masing. Blok B berbobot **0.20 dari regime score total** (−2…+2); pilar B sendiri = rata-rata z anggotanya (DFII10, DFII5, T5YIE, T10YIE, T5YIFR). Antar anggota berfrekuensi beda dipertemukan lewat *as-of join* — "nilai terakhir yang benar-benar sudah dirilis pada tanggal sinyal" (pakai `release_ts`, anti look-ahead).

### 4.2 Pipeline langkah demi langkah

1. **06:00 WIB** — harvester FRED mengambil DFII10/DFII5/T5YIE/T10YIE/T5YIFR terbaru → ditulis ke `raw_observations` **append-only** (revisi = baris baru, tak pernah menimpa; prinsip §0.5).
2. **Gerbang segar & waras** — nilai lewat jadwal rilisnya tanpa update → ditandai **basi** dan tidak dipakai diam-diam (§0.2); nilai di luar sanity-range → ditolak.
3. **Momentum 20d** dihitung pada level: `DFII10(hari ini) − DFII10(20 hari bursa lalu)`.
4. **z 5y** dihitung pada level (σ populasi, min-obs 80%).
5. **State** ditetapkan dari momentum — kosakata: **FALLING / FLAT / RISING** (contoh nyata: −15bps/20d → FALLING; baris brief §14 mencetak persis "RealYield=FALLING"). Ambang FLAT mengikuti konvensi serupa Blok A (±10bps/20d — **asumsi v1, belum terkunci di BUILD-PLAN**) dan **tercatat sebagai parameter kalibrasi di registry** — bukan hukum alam, bisa diperbaiki saat re-kalibrasi kuartalan.
6. **Pilar & skor** — rata-rata z anggota → state flip regime di ±0.5 → dikalikan bobot 0.20 → masuk label regime (mis. contoh brief Agt-2026: "EASING + LIQUIDITY EXPANDING, score +1.2 → risk-on").
7. Secara paralel: **identitas harian** dicek (§4.4) dan **divergence** dihitung (§4.5) sebagai baris anomali bila menyala.

### 4.3 Contoh baca menyeluruh: "DFII10 2.34% FALLING (−15bps/20d) → tailwind gold"

*(angka mean/σ di bawah ILUSTRASI mekanisme — bukan angka spec; mekanisme sesuai BUILD-PLAN §3)*

- Level 2.34%, misal rata-rata 5 tahun 1.90% dan σ 0.45% → z = (2.34−1.90)/0.45 ≈ **+0.98** → "masih tinggi untuk era sendiri".
- Momentum −15bps/20d → **FALLING**.
- Gabungan dua kalimat itu inti Blok B: *"rintangannya masih tinggi, tapi sedang runtuh."* Untuk emas, kalimat kedua yang menggerakkan harga jangka swing — pasar membeli **perubahan**, bukan level → dicetak **"tailwind gold"**.
- Kalau besok barisnya jadi "2.31% (−3bps)" seperti brief 2026-08-29: level turun, momentum tetap FALLING, tailwind bertahan — hanya lebih pelan.
- Kalau dua minggu kemudian barisnya "2.20% (−2bps/20d)": momentum praktis nol → state FLAT → tailwind **hilang** meski level turun. Inilah jebakan #1 di §5.

**Bagaimana sebuah state lahir — empat snapshot momen** *(ILUSTRASI mekanisme; angka akhir persis dari spec)*:

| Hari bursa | DFII10 | Momentum 20d (vs hari awal 2.49%) | State | Baris brief |
|---|---|---|---|---|
| H+5 | 2.44% | −5bps | FLAT (belum menembus ambang) | "DFII10 2.44% FLAT" |
| H+10 | 2.41% | −8bps | FLAT | "DFII10 2.41% FLAT" |
| H+15 | 2.37% | −12bps | **FALLING** (ambang terlampaui) | "DFII10 2.37% FALLING (−12bps/20d)" |
| H+20 | 2.34% | −15bps | FALLING | "DFII10 2.34% FALLING (−15bps/20d) → tailwind gold" |

Perhatikan dua hal: (1) level turun mulus, tapi **state tidak berganti sebelum momentum menembus ambang** — mencegah brief "berubah pikiran" karena noise kecil; (2) tailwind gold baru dicetak saat state berganti, bukan sejak hari pertama turun. Keterlambatan seperti ini disengaja: swing trading butuh arah yang terkonfirmasi, bukan reaksi kilat.

### 4.4 Verifikasi bawaan — kenapa angka blok ini bisa dipercaya

| Pemeriksaan | Aturan | Contoh kerja |
|---|---|---|
| **Identitas Fisher** | `DFII10 ≈ DGS10 − T10YIE`, toleransi **±25bps**; dicek **tiap hari** sebagai gerbang brief (§6.3 BUILD-PLAN) | 4.67 − 2.34 = 2.33 vs T10YIE 2.31 → selisih 2bps ✅ *(tanggal anchor berdekatan, Agt-2026)* |
| **Cross-val failover** | FRED vs EODHD `/ust/real-yield-rates`, toleransi **±2bps**; bila langgar → **keduanya dikarantina** + baris flag di brief — tidak ada fallback diam-diam (§0.6) | — |
| **Golden anchors (F0)** | Nilai harapan terkunci per series dari riset; mismatch = gerbang F0 gagal, proyek tidak maju | Mekanisme yang sama yang mengunci DGS10=4.67@2026-08-27 |
| **Kenapa toleransi 25bps, bukan 0?** | TIPS punya lag indeksasi (~3 bulan, *konteks umum*) dan premium likuiditas berbeda dari obligasi nominal — identitas ini **tidak pernah eksak secara struktural**. 25bps = lebar aman yang menangkap kesalahan data tanpa salah tuduh pasar | — |

### 4.5 Logika sinyal divergence (untuk awam)

Korelasi 60 hari antara "emas naik/turun" dan "RY naik/turun" biasanya **negatif** (cermin: RY turun ↔ emas naik). Sinyal menyala bila korelasi berbalik **≥ +0.3** — artinya selama ~3 bulan terakhir emas justru bergerak **searah** RY — **dan** Blok H melaporkan pembelian CB aktif (mis. PBoC beli bulanan berturut, WGC >100t/q). Dua syarat sekaligus, supaya tidak salah tuduh: korelasi positif sendiri bisa terjadi saat volatilitas rendah; bukti pembeli struktural yang membuat kesimpulannya kokoh. Flag ini masuk daftar **Anomali & alert** §11.5 dan mengubah bobot baca RY di baris implikasi book.

**Contoh kerja sinyal (ILUSTRASI alur, angka CB dari spec)**:
1. Bulan-bulan normal: korelasi 60d antara return XAU dan ΔDFII10 duduk di sekitar −0.6 → aturan lama berlaku, RY dibaca penuh sebagai driver #1.
2. Selama satu kuartal, emas mencetak swing high baru **bersamaan** RY naik dari 2.1% ke 2.34% → korelasi 60d merayap ke +0.45 → syarat pertama terpenuhi.
3. Blok H konfirmasi: PBoC **beli 7 bulan berturut-turut** (cadangan 2.286 → 2.366 tonne, Jan–Jul 2026 — contoh nilai Agt-2026) dan WGC melaporkan pembelian CB kuartalan >100 ton → syarat kedua terpenuhi.
4. Brief mencetak baris anomali: **"gold naik meski RY naik = bid struktural"** — dan mulai hari itu, baris "RY RISING = headwind gold" dibaca dengan bobot lebih rendah; timing lebih diserahkan ke positioning (Blok G: "crowded long — jangan chase") dan flows (Blok H).
5. Saat salah satu syarat padam (mis. korelasi kembali negatif, atau CB berhenti beli), flag mati sendiri dan driver #1 kembali berlaku penuh.

---

## 5. Membaca baris Blok B di brief — anatomi & jebakan

Anatomi dua baris standar (contoh nilai Agt-2026, brief 2026-08-29):

```text
• DFII10 2.34% (−3bps) → tailwind gold          ← kolom "Berubah semalam"
Pilar : RealYield=FALLING | ...                   ← ringkasan state
• XAUUSD : tailwind (RY↓, dolar melemah) TAPI crowded → tunggu pullback   ← implikasi book
```

Yang perlu dicermati: baris "semalam" (Δ1 hari = deteksi perubahan) vs baris Pilar (momentum 20d = keputusan regime). Keputusan trading berbasis baris Pilar; baris semalam hanya radar.

**Kamus lima baris yang paling sering muncul → bacaan cepat:**

| Baris brief yang Anda lihat | Cara membacanya dalam 10 detik |
|---|---|
| `DFII10 2.34% FALLING (−15bps/20d) → tailwind gold` | Konfigurasi standar bullish gold — rintangan tinggi tapi runtuh; cari konfirmasi dolar & positioning |
| `DFII10 2.40% RISING (+12bps/20d)` | Headwind gold — tapi CEGAT dulu: adakah flag divergence? Dan penyebabnya BE naik atau nominal naik? |
| `DFII10 2.34% FLAT (−3bps/20d)` | Tailwind **habis** meski level sama — pasar menunggu arah; jangan carry-over tesis lama |
| `Anomali: gold↔RY divergence ON (bid struktural)` | Bobot baca RY diturunkan; pindahkan fokus ke COT (Blok G) dan flows CB (Blok H) |
| `Flag: cross-val FRED↔EODHD >2bps — karantina` | Angka hari ini dicurigai; TIDAK untuk dasar keputusan sampai flag hilang |

**Tujuh salah-baca paling umum:**

| # | Jebakan | Cara membaca yang benar |
|---|---|---|
| 1 | "Level masih 2.34%, tinggi → emas pasti tertekan" | Arah mengalahkan level untuk horizon swing: FALLING = tailwind meski level tinggi (§4.3) |
| 2 | Membangun tesis dari Δ semalam (−3bps) | Satu hari = noise; state memakai 20 hari bursa |
| 3 | Menganggap semua "RY turun" sama | Cek penyebabnya: nominal turun (dovish, klasik bullish gold) vs BE naik (takut inflasi — bullish gold juga tapi regime stagflasi; perlakukan berbeda, cek §3.2 & 5y5y) |
| 4 | Double counting dengan blok lain | DGS10 (nominal) milik Blok A, CPI aktual milik Blok C — jangan dijumlahkan seolah tiga sinyal independen; DFII sudah "mengandung" nominal & ekspektasi |
| 5 | Lupa z-score itu relatif era | z dihitung vs 5 tahun terakhir; di era RY tinggi seperti 2023–2026, z "normal" tetap berarti level yang secara 20 tahun tergolong ekstrem |
| 6 | Mengabaikan flag divergence | Saat "gold naik meski RY naik = bid struktural" menyala, hubungan terbalik dicurigai putus — baca RY dengan bobot lebih rendah, prioritize positioning (Blok G) & flows (Blok H) |
| 7 | Percaya buta saat pasar panik | Breakeven/RY berbasis TIPS bisa terdistorsi premium likuiditas saat krisis (kasus klasik Mar-2020, *konteks umum*: BE anjlok bukan karena pasar yakin deflasi, tapi TIPS dilempar) — saat Blok F menunjukkan stress ekstrem, angka BE baca dengan curiga |

---

## 6. Keterkaitan spesifik per instrumen Anda

| Instrumen | Kanal pengaruh Blok B | Arah & catatan |
|---|---|---|
| **XAUUSD** | Langsung: opportunity cost memegang emas | **Driver #1**. RY FALLING = tailwind; RISING = headwind — kecuali flag divergence menyala. Kombinasi emas paling kuat: RY↓ **dan** dolar melemah (DTWEXBGS, Blok A) — seperti contoh implikasi brief Agt-2026 |
| **XAGUSD** | Ikut kanal emas (silver = "emas dengan beta lebih tinggi") + sisi industri (Blok D: China PMI, copper) | Tailwind RY yang sama, amplifikasi — naik lebih dalam saat bullish, jatuh lebih keras saat reversal; sizing mengikuti vol (Blok F CVOL) |
| **XPTUSD** | Kanal logam mulia sama, tetapi platinum lebih industrial (auto/katalis) | Pengaruh RY lebih tipis dari XAU; growth (Blok D) relatif lebih menentukan |
| **XCUUSD** | Kanal discount-rate umum + dolar | Paling sedikit "logam mulia" dari semua — RY hanya latar; fokus utama: China, stok COMEX, squeeze (Blok D/H) |
| **XAUEUR, XAGEUR, XAGGBP, XAUGBP** | RY AS menggerakkan **kaki XAU/XAG** dan (tak langsung) **kaki FX** | Aritmetika membantu: XAUEUR = XAUUSD ÷ EURUSD. Karena EURUSD ada di **penyebut**, EUR yang menguat justru MEREDAM XAUEUR — saat RY AS turun → emas naik **dan** dolar melemah (EURUSD naik), XAUEUR naik LEBIH SEDIKIT daripada XAUUSD (kaki EUR-nya menyerap sebagian gerakan; EUR kaku → XAUEUR tertinggal XAUUSD). Kaki EUR/GBP sendiri diblok A/D (kebijakan ECB/BoE, HICP EA) |
| **BTC / ETH** | Kanal discount-rate: RY turun = kondisi finansial melonggar → aset risk-on dihargai lebih tinggi | **Bukan driver utama** — untuk crypto yang ada di blok E (net liquidity) & H (flow/funding). Saat RY negatif, narasi "digital gold" menguat dan BTC cenderung bergerak lebih mirip emas |
| **US100 / US500 / US30** | Valuasi ekuitas = arus laba masa depan didiskontokan dengan yield riil | RY turun = discount rate turun → mendukung harga, **paling sensitif US100** (pertumbuhan jarak jauh/durasi panjang); RY naik cepat = tekanan valuasi, terutama US100 |
| **EURUSD & majors** | Diferensial yield riil antarnegara mengarahkan arus modal | RY AS turun (tanpa ECB ikut) → dolarmelemah → EURUSD naik. Cross-check selalu dengan Blok A (DTWEXBGS, ekspektasi ECB dari futures ESR) |
| **DXY** | Cermin kanal FX di atas | RY AS jatuh relatif dunia = headwind dolar — ingat Blok A memakai DTWEXBGS (trade-weighted, lebih jujur) sebagai first-class |

**Urutan baca pagi (5 langkah, ±2 menit) untuk book logam Anda:**

1. **Baris Pilar dulu**: state `RealYield=FALLING/FLAT/RISING` — ini arah angin hari ini.
2. **Penyebabnya**: buka Blok A (DGS10 nominal) & Blok C — RY turun karena nominal turun (dovish klasik) atau BE naik (stagflasi)? Dua skenario bullish gold yang berbeda umur.
3. **Flag**: adakah baris anomali divergence atau karantina data? Kalau ada, sesuaikan bobot baca sebelum lanjut.
4. **Gabungkan dua angin lain**: dolar (DTWEXBGS momo-20d, Blok A) dan positioning (COT gold, Blok G) — contoh nyata brief Agt-2026: *"XAUUSD: tailwind (RY↓, dolar melemah) TAPI crowded → tunggu pullback"* = angin bagus, kapal penuh, jangan mengejar.
5. **Baru baca implikasi book** — yang paling bawah di brief, karena sudah menggabungkan semua di atas.

---

## 7. Yang bisa salah — degradasi, kualitas data, keterbatasan

### 7.1 Mode degradasi (apa yang terjadi saat sumber bermasalah)

| Skenario | Perilaku sistem | Yang Anda lihat di brief |
|---|---|---|
| FRED lambat/lewat jadwal | Freshness stamp menandai **basi** (prinsip §0.2) — tidak dipakai diam-diam | Baris Blok B memakai nilai terakhir yang sah + tanda basi |
| FRED mati total | **Failover EODHD `/ust/real-yield-rates`** (audit §16) — satu call seluruh kurva real yield | Brief tetap terbit; sumber dicatat |
| Primer vs sekunder selisih > 2bps | **Keduanya dikarantina** + baris flag (no silent fallback, §0.6 BUILD-PLAN) | Baris flag eksplisit — jangan trading dari angka yang sedang dicurigai |
| Identitas DFII≈DGS−BE pecah > 25bps | Gerbang harian gagal → investigasi; bisa berarti data rusak **atau** dislokasi likuiditas ekstrem | Flag di brief; angka BE/RY dibaca hati-hati |
| Data historis < 80% window z | State = `INSUFFICIENT`, bukan angka ngawur | Label jujur "data kurang" |

### 7.2 Kualitas data — jebakan operasional

- **Satuan**: seluruh series Blok B dalam **persen** (2.34 = dua koma tiga empat persen, bukan 0.0234). Registry menyimpan `value_format='pct'` justru untuk mencegah mixup seperti ini (kasus nyata di spec: DGS10=46.7 vs MICH=0.042 pernah hampir kecampur).
- **Null struktural vs error**: weekend & libur AS = wajar tidak ada baris; null di hari bursa = FAIL dan dicatat eksplisit (kebijakan F0).
- **Revisi**: yield pasar praktis tidak direvisi (bukan data survei), jadi mekanisme vintage ALFRED tidak kritis di blok ini — tapi append-only tetap dipertahankan untuk audit.
- **Timestamp**: disimpan UTC (`et_close`), ditampilkan WIB dengan kesadaran EDT/EST (selisih 11/12 jam) — brief 07:00 WIB memakai penutupan sesi AS yang berakhir ~03:00 WIB saat EDT (~04:00 WIB saat EST).

### 7.3 Keterbatasan struktural — hal yang tidak bisa diperbaiki data lebih banyak

1. **TIPS = instrumen dunia nyata, bukan instrumen sempurna.** Real yield & breakeven memuat premium likuiditas dan lag indeksasi CPI ±3 bulan (*konteks umum*). Akibatnya BE bisa "berbohong" saat krisis — jatuh karena TIPS dijual, bukan karena pasar yakin deflasi. Saat Blok F merah, angka BE/RY turunkan bobot bacanya.
2. **z-score 5 tahun buta sejarah lama.** Setelah era berubah (contoh: normalisasi 2022–2023), "z = 0" bisa saja berarti level tertinggi dalam 20 tahun. Solusinya bukan mengubah window asal-asalan, tapi membaca z bersama ingatan konteks era — dan konteks itu persis alasan dokumen ini mencantumkan peta sejarah kasar di §3.1.
3. **Momentum 20d = sinyal swing, bukan tombol intraday.** Terlalu cepat untuk struktur multi-tahun, terlalu lambat untuk scalping. Pas dengan horizon hari–minggu Anda; di luar itu jangan dipaksakan.
4. **Sinyal divergence lambat dan bersyarat.** Korelasi 60d butuh waktu berbalik; data CB terlambat (WGC kuartalan; PBoC bulanan — dan bank sentral lain baru terlihat kuartalan berikutnya). Ambang +0.3 = parameter kalibrasi, bukan kebenaran mutlak. Perlakukan flag ini sebagai **penyesuaian bobot baca**, bukan tombol on/off hubungan emas–RY.
5. **5y5y "murni" tetap berbasis TIPS** — murni dari guncangan jangka pendek, tapi tidak murni dari distorsi likuiditas instrumen itu sendiri.
6. **Blok B hanya sisi AS.** Real yield zona euro/UK tidak ada di spec v1.4 — kaki EUR/GBP crosses hanya dicover lewat kebijakan & inflasi (Blok A/D). Kalau suatu saat XAUEUR bergerak aneh, curigai dulu kaki EUR-nya yang tidak ter-cover penuh, bukan langsung menyalahkan DFII10.

### 7.4 Checklist kewarasan sebelum memakai angka Blok B

Sebelum angka real yield dipakai untuk keputusan posisi, lima pertanyaan ini harus bisa dijawab "ya":

1. **Segar?** — tidak ada tanda basi (freshness stamp) pada DFII10/DGS10/T10YIE hari itu.
2. **Identitas hijau?** — DFII10 ≈ DGS10 − T10YIE dalam ±25bps (gerbang harian §6.3); brief tidak menampilkan flag identitas.
3. **Bebas karantina?** — tidak ada flag cross-val FRED↔EODHD.
4. **Penyebab jelas?** — Anda tahu pergerakan RY datang dari kaki nominal atau kaki breakeven (baca Blok A/C), dan tahu artinya untuk regime.
5. **Cocok horizon?** — sinyal momentum 20d & state Blok B memang untuk swing hari–minggu; jangan dipakai untuk membuktikan tesis setahun, dan jangan untuk entry 15 menit.

Kalau salah satu jawabannya "tidak", angka hari itu turun kelas menjadi "konteks", bukan "dasar keputusan".

---

*Lintas-baca:* driver nominal & dolar di `01-block-a-policy-rates-dollar.md`, inflasi aktual di Blok C, positioning gold di Blok G (`z+1.8 crowded long`), pembeli struktural di Blok H. Rantai angka mana pun di atas bisa ditelusuri: `arkwatch explore series FRED:DFII10 --trace`.
