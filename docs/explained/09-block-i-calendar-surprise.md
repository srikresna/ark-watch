# Blok I — Kalender, Event & Surprise Index

> Dokumen edukasi (1 dari 9 blok) — ditulis untuk pembaca non-finance yang ingin paham sampai bisa menantang keputusan desain.
> Rujukan teknis: `DATA-SPEC.md` §9 (Blok I), §18.1 (kalender CME), §0, §11, §13–14, §15.3 (v1.4, 2026-08-30) dan `BUILD-PLAN.md` §3 Blok I, §2 (tabel `events` + `indicator_stats`).
> Semua angka contoh bertanda **(contoh nilai Agt-2026)** diambil langsung dari spec — tidak ada yang dikarang.

**Versi 30 detik:**
- Blok I = dua alat: (1) **radar event** — KAPAN ada momen berisiko/kejutan, dengan jam presis dalam WIB; (2) **surprise index** — SEBERAPA data ekonomi AS belakangan ini meleset dari ekspektasi pasar, dalam satu angka.
- Prinsip intinya: **harga sudah mengandung ekspektasi**. Yang menggerakkan harga bukan kondisi ekonominya, tapi selisih antara angka aktual dan ekspektasi.
- Blok I **bukan pilar berbobot** regime score — dia radar risiko, bahan surprise untuk Blok D, dan pemicu anomali "surprise flip".

---

## 1. Kenapa blok ini ada — latar ekonomi untuk awam

### 1.1 Pasar tidak bereaksi pada kondisi; pasar bereaksi pada KEJUTAN

Bayangkan harga hari ini sebagai **rata-rata taruhan ribuan orang tentang besok**. Sebelum data rilis, analis sudah membuat prediksi (konsensus), trader sudah mengatur posisi sesuai prediksi itu, dan semua prediksi itu **sudah terbakar ke dalam harga**. Ketika angka resmi keluar, yang menggerakkan harga hanyalah **bagian yang berbeda dari yang diasumsikan**.

Analogi sehari-hari: harga cabai di pasar naik bukan saat panen gagal — naik saat kabar gagal panen ternyata **lebih buruk dari yang sudah dikatakan orang**. Kabar yang sudah beredar sudah masuk harga; kabar yang menyimpang dari rumor itulah yang menggerakkan harga hari itu.

Level (harga 10Y 4,67%, inflasi 2,8%) memberi tahu **keadaan**. Surprise memberi tahu **perubahan narasi**. Untuk pergerakan hari-ke-hari dan mingguan, yang kedua jauh lebih kuat.

### 1.2 Rantai sebab: satu angka CPI bisa menggerakkan emas

Contoh alurnya (rantai yang dipantau blok A–B, dipicu oleh blok I):

```
CPI lebih panas dari konsensus (surprise +)
  → pasar menaikkan perkiraan bunga Fed (FedWatch, Blok A)
  → yield nominal naik (Blok A) → real yield naik (Blok B)
  → dolar menguat (Blok A) → XAUUSD tertekan dari dua sisi
```

Catatan kualifikasi penting: rantai di atas bukan hukum mekanis. CPI panas juga menaikkan breakeven inflasi (Blok B), sehingga arah **real yield** — nominal dikurangi breakeven — bisa naik ATAU turun: tergantung pasar membaca CPI itu lebih sebagai perubahan jalur Fed (nominal naik lebih cepat → RY naik) atau sebagai kenaikan ekspektasi inflasi (breakeven naik lebih cepat → RY turun); di 2021–22 CPI panas justru sering menekan real yield dan menopang gold. Rantai paling mekanis justru kaki dolarnya.

Itulah kenapa satu rilis pukul 08:30 ET bisa menggerakkan XAUUSD lebih jauh daripada sebulan pergerakan pelan — dan kenapa jam rilis harus diketahui **presis**, bukan "pagi".

### 1.3 Dua pekerjaan blok I

| Pekerjaan | Bentuknya di brief | Pertanyaan yang dijawab |
|---|---|---|
| **Radar event** | baris "Minggu ini (EDT→WIB): CPI Kam 19:30 · FOMC Minutes Kam 01:00 …" **(contoh format brief Agt-2026)** | Kapan saya harus mengecilkan posisi / siapkan skenario? |
| **Surprise index (ESI)** | "Surprise US +8.2 → USD supportive" **(contoh nilai Agt-2026)** | Apakah data AS belakangan konsisten mengalahkan ekspektasi (bias dolar)? |

### 1.4 Kenapa trader swing (hari–minggu) khususnya peduli

Timeframe swing = posisi menginap melewati banyak sesi rilis. Kalender adalah **peta medan ranjau waktu**: tahu jam presis = tahu kapan jangan menambah risiko, kapan perlebar stop, atau kapan menyiapkan rencana if-then (lihat §6). Tanpa blok ini, semua blok lain hanya memberi tahu arah angin — blok I memberi tahu kapan badai dijadwalkan.

### 1.5 Pembagian kerja: blok A–H bicara LEVEL, blok I bicara KEJUTAN

Supaya tidak salah menempatkan harapan:

| Pertanyaan | Dijawab oleh | Contoh |
|---|---|---|
| "Berapa inflasi sekarang, sedang memanas atau mendingin?" | Blok C (level + momentum) | "CPI 3m-ann 2,8% COOLING" (contoh output Agt-2026) |
| "Rilis tadi mengejutkan atau tidak?" | **Blok I** (surprise) | "Claims 203K (cons 208K) → surprise +" |
| "Kapan momen berisiko berikutnya?" | **Blok I** (radar) | "CPI Kam 19:30" |
| "Lalu harga harusnya naik atau turun?" | Regime komposit (§11) — bukan blok I sendirian | "EASING + LIQUIDITY EXPANDING (score +1,2)" |

Blok I sengaja tidak menjawab pertanyaan terakhir seorang diri — kejutan adalah *input*, arah trade tetap keputusan regime + manajemen risiko Anda.

---

## 2. Glosarium istilah Blok I

| Istilah | Arti awam | Kenapa penting untuk Anda |
|---|---|---|
| **Event / rilis data** | Pengumuman angka resmi ekonomi (CPI, NFP, ISM, keputusan FOMC) | Sumber lonjakan harga yang bisa dijadwalkan |
| **Konsensus (consensus/forecast)** | Rata-rata prediksi ekonom/analis sebelum rilis | Ini "harapan pasar" — patokan hitung kejutan |
| **Actual** | Angka resmi yang dirilis | Dibandingkan vs konsensus untuk ukur surprise |
| **Previous (+revisi)** | Angka periode lalu, kadang direvisi | Revisi besar sendiri sudah bisa menggerakkan pasar |
| **Beat / miss** | Actual lebih baik / lebih buruk dari konsensus | Bahasa sehari-hari trader untuk arah kejutan |
| **Surprise** | Selisih actual − konsensus | Bahan mentah semua perhitungan blok ini |
| **Surprise index / ESI** | Satu angka rangkuman: rata-rata kejutan semua indikator (terinspirasi Citi Economic Surprise Index — formula versi sendiri, bukan replika Citi) | "Data momentum" — apakah ekonomi belakangan over-/under-deliver |
| **z-score** | Surprise diukur dalam "satuan kejutan normal" indikator itu (lihat §4.2a) | Bikin CPI dan ISM bisa dibandingkan apple-to-apple |
| **σ (sigma) rolling 5y** | Seberapa lebar biasanya actual meleset dari konsensus dalam 5 tahun terakhir, per indikator | Penyebut z: "miss 0,3pp di CPI" itu besar atau kecil, tergantung σ |
| **Winsorize ±4σ** | Kejutan ekstrem dipotong (di-cap) di ±4 supaya tidak merusak statistik | Satu event gila tidak membuat σ terdistorsi selamanya |
| **Decay 90 hari** | Kejutan lama bobotnya memudar secara eksponensial | Pasar berhenti peduli CPI Maret di bulan Agustus |
| **Rata-rata berbobot** | Rata-rata yang memberi bobot beda per item (di sini: makin baru makin berat) | Cara ESI merangkum tanpa membiarkan data basi mengotori |
| **low_conf** | Penanda "kepercayaan rendah" (data historis kurang, <30 observasi) | Jangan taruh keputusan besar pada angka berflag ini |
| **Normalisasi nama + dedup** | Empat sumber menamai event berbeda; sistem menyatukan lalu buang duplikat | 4 baris "CPI" dari 4 sumber jadi 1 baris bersih |
| **Precedence jam** | Urutan kepercayaan jam: kurasi > TV/CME > FMP > EODHD | Jam salah = Anda standby di jam yang salah |
| **00:00 = date-only** | Banyak sumber hanya tahu tanggal, menulis jam 00:00 sebagai penanda | Bukan artinya rilis tengah malam! |
| **Importance/impact tier** | Tingkat kepentingan event (TV pakai skala −1/0/1) | Saring radar: tidak semua rilis setara |
| **Speech** | Pidato pejabat bank sentral (mis. Powell) | Sering menggerakkan pasar tanpa ada angka |
| **Presser** | Konferensi pers FOMC, 14:30 ET (setelah keputusan 14:00 ET) | Sering lebih volatil daripada statement-nya |
| **Minutes** | Notulen rapat FOMC (rilis ~3 minggu setelah rapat) | Event second-order, tetap masuk radar |
| **Jackson Hole (JH)** | Simposium tahunan Fed di Wyoming (Agt), dengan keynote utama | Kasus nyata kenapa "jam presis" itu sulit — lihat §3.3 |
| **Point-in-time (`release_ts`)** | Setiap angka dicatat KAPAN pasar pertama tahu | Mencegah kecurangan analisis: tidak melihat masa depan |
| **EDT/EST vs WIB** | New York selisih 11 jam saat EDT (Mar–Nov), 12 jam saat EST | Jam WIB event bergeser 1 jam tiap pergantian musim |
| **Tier sumber (T1/T3)** | T1 = langganan berbayar (FMP/EODHD); T3 = gray/tridak resmi (TV, backdoor CME) | Menentukan seberapa besar kita percaya & rencana fallback |
| **Append-only** | Data yang sudah masuk tidak pernah ditimpa; koreksi = baris baru | Riwayat kejutan tidak bisa "dibetulkan diam-diam" di kemudian hari |
| **Upsert (khusus konsensus)** | Boleh memperbarui baris — hanya sebelum rilis | Konsensus memang hidup: analis merevisi prediksi menjelang rilis |
| **Radar event** | Tampilan daftar event mendatang di brief | Alat perencanaan risiko Anda, bukan sinyal beli/jual |
| **Variance event** | Event yang memperbesar rentang gerakan harga (volatilitas) | Alasan mengecilkan posisi menjelang CPI/FOMC — bukan prediksi arah |
| **Symposium** | Baris kalender berjenis "acara multi-hari" (bukan rilis berjam) | Selalu tampil jam 00:00 — abaikan; cari baris speech di dalamnya |
| **Sumber gray (T3)** | Sumber tidak resmi/tanpa dukungan (TV, backdoor CME) — selalu bisa mati | Karena itu kalender dibangun sebagai union + fallback |
| **NFP** | Nonfarm Payrolls — perubahan jumlah pekerjaan non-pertanian AS (rilis BLS, Jumat pertama tiap bulan) | Bersama CPI = rilis tenaga kerja paling menggerakkan dolar & indeks |
| **BLS** | Bureau of Labor Statistics — badan statistik ketenagakerjaan & harga AS (CPI, NFP) | Penerbit rilis 08:30 ET yang paling ditonton pasar |
| **BEA** | Bureau of Economic Analysis — badan statistik akun nasional AS (GDP, PCE) | Penerbit PCE (metrik target Fed) |
| **SPF** | Survey of Professional Forecasters — survei prediksi ekonom profesional (Philly Fed) | Alternatif riset tertulis untuk era ESI historis tipis (§18.4) |
| **MPC** | Monetary Policy Committee — komite kebijakan BoE (8 keputusan/tahun) | Kalender kaki GBP dari crosses & GBPUSD |

---

## 3. Peta data — dari mana kalender dan surprise ini datang

### 3.1 Tabel sumber (union-4 + tabel kurasi)

| # | Sumber | Apa sebenarnya | Siapa di belakang & jadwal | Kenapa dipilih (alternatif yang ditolak) | Catatan baca |
|---|---|---|---|---|---|
| 1 | **Kalender primer: FMP** `/stable/economic-calendar` | Agregator kalender ekonomi (langganan, tier T1) | Fetch harian, window **14 hari** | Paling lengkap konsensus + actual terstruktur, sudah langganan | Jam sering hanya presis untuk rilis reguler; jadi acuan nama/event |
| 2 | **Union-2: EODHD** `/economic-events` | Agregator kedua (T1) | Harian | Peran utama: **verifikasi silang** baris FMP | Bukan sumber jam utama (precedence paling bawah) |
| 3 | **Union-3: TradingView** `economic-calendar.tradingview.com/events` | Kalender TV; **terverifikasi live**; gray (T3) — butuh header Origin/Referer; params `from/to` ISO-ms + `countries=US`; importance −1/0/1 | Harian | **Sumber jam presis UTC utama untuk speeches bank sentral** — yang ditolak: mengarang jam dari tanggal | Baris jenis **"Symposium" jam 00:00 = abaikan** (bukan jam nyata) |
| 4 | **Union-4: CME** `/services/economic-release-filters` → `POST …-dates` → `POST …-events` | Kalender ekonomi CME via jalur gray (T3, backdoor — lihat §18.1) | Harian | Bonus unik: **jam presis UTC + tier impact + actual + consensus + previous** — input surprise langsung dari satu tempat | Jebakan teknis: param `impact` **wajib `null`** (string = 403); endpoint lama cchummer **MATI** |
| 5 | **Tabel kurasi** (config internal, update kuartalan) | Daftar buatan tangan dari pengumuman resmi lembaga — **otoritatif untuk jam** | FOMC 14:00 ET + presser 14:30; **JH keynote 10:00 ET**; jadwal rilis resmi BLS/BEA setahun ke depan | Jaminan jam presis untuk event yang paling menggerakkan harga; FOMC di-vendor s/d 2028-01 dan **dicek tiap Januari** vs situs federalreserve.gov | Precedence jam #1 — menimpa semua sumber lain |
| 6 | **Speeches** (FMP events) | Baris pidato pejabat (Powell dkk.) | Harian | Radar "siapa bicara kapan" untuk blok A | Contoh output: "Powell 21:00 WIB (10:00 EDT)" **(contoh format brief Agt-2026)** |
| 7 | **Surprise index (ESI)** — computed | Bukan fetch: dihitung dari actual+consensus yang terkumpul | Dihitung harian saat fetch 06:30 WIB | Terinspirasi Citi Economic Surprise Index, formula diimplementasi sendiri (raw+derived, prinsip §0.4) — bukan replika metodologi Citi | Keluaran: "Surprise US +8.2 → USD supportive" **(contoh nilai Agt-2026)** |

Semua sumber kalender digabung dengan **union + dedup**, bukan dipilih salah satu. Fetch terjadwal **06:30 WIB** (sebelum brief 07:00 — §13).

### 3.2 Kenapa UNION empat sumber + tabel kurasi (bukan satu sumber)

Setiap sumber punya kelemahan yang berbeda:

| Kelemahan | Ditutup oleh |
|---|---|
| FMP/EODHD sering hanya tahu tanggal (jam 00:00) untuk speeches & event non-reguler | TV + CME (jam presis UTC) |
| TV tidak punya konsensus selengkap FMP | FMP + CME |
| CME gray — bisa mati kapan saja | Kurasi + tiga sumber lain |
| Semua sumber agregator bisa salah menyalin jam event besar | **Tabel kurasi** (dari pengumuman resmi lembaga, precedence #1) |

Alternatif yang **ditolak** desain: (a) mengandalkan satu sumber saja — satu jam salah = Anda standby di jam keliru; (b) kalender institusi berbayar — tidak dibeli untuk kebutuhan ini; (c) mengarang jam dari pola umum ("CPI biasanya 8:30") tanpa verifikasi — melanggar prinsip integritas di atas kecepatan.

Mekanikanya: nama event dinormalisasi (`normalized_name`) → dedup pada (nama, waktu) → **jam diambil dari sumber dengan precedence tertinggi yang punya jam nyata**: kurasi > TV/CME > FMP > EODHD; jam 00:00 ditandai date-only. Uji acceptance-nya eksplisit: 4 baris dari 4 sumber harus jadi **1 baris** (BUILD-PLAN §3-I).

### 3.3 Jam presis — kisah Jackson Hole sebagai cerita

**Masalah**: Jackson Hole adalah simposium multi-hari. Banyak kalender menampilkannya sebagai SATU baris bernama "Symposium" dengan jam 00:00 — nyaris tak berguna, padahal yang menggerakkan pasar adalah **keynote Powell di jam spesifik** (10:00 ET saat EDT = 21:00 WIB). Kalender agregator biasa sering tidak mencantumkan jam pidato sama sekali.

**Solusi tiga lapis** (semua live-verified 2026-08-29, §15.3):
1. **TV** terbukti mengembalikan speeches bank sentral dengan **jam presis UTC** — ini penutup kasus Jackson Hole.
2. **CME** juga memberi jam presis UTC.
3. **Tabel kurasi** mem-pin "JH keynote 10:00 ET" — kalau dua sumber gray di atas mati, jam tetap benar.

Aturan sisa: baris jenis "Symposium" jam 00:00 diabaikan (bukan jam rilis nyata); jam 00:00 apa pun = date-only.

**Konversi waktu (wajib hafal ringkas)** — timestamp disimpan UTC, ditampilkan WIB (konversi sadar musim):

| Event | ET | WIB saat EDT (Mar–Nov) | WIB saat EST (Nov–Mar) |
|---|---|---|---|
| Rilis BLS (CPI/NFP) | 08:30 | **19:30** (contoh baris brief "CPI Kam 19:30", Agt-2026) | 20:30 |
| Keputusan FOMC | 14:00 | **01:00 (keesokan harinya)** | 02:00 |
| Presser FOMC | 14:30 | 02:30 besok | 03:30 besok |
| Keynote Jackson Hole | 10:00 | **21:00** ("Powell 21:00 WIB (10:00 EDT)", contoh Agt-2026) | 22:00 |

Jebakan musim: jam WIB event AS **bergeser 1 jam** setiap pergantian EDT↔EST — radar blok I yang menghitung ulang otomatis mencegah Anda datang sejam terlalu cepat/terlambat tiap November dan Maret.

### 3.3b Peta jam penting sepanjang hari & minggu (semua dari spec; WIB saat EDT)

| Kapan (ET) | WIB (EDT) | Apa | Sumber jam |
|---|---|---|---|
| 08:30, hari rilis | 19:30 | Rilis BLS: CPI, NFP/payrolls (jadwal setahun di muka → tabel kurasi) | Kurasi (BLS) |
| 10:00 | 21:00 | Keynote Jackson Hole (Agustus); "Powell 21:00 WIB (10:00 EDT)" (contoh brief Agt-2026) | Kurasi + TV |
| 14:00 | 01:00 besok | Keputusan FOMC (8 rapat/tahun, vendor s/d 2028-01) | Kurasi (Fed) |
| 14:30 | 02:30 besok | Presser FOMC | Kurasi (Fed) |
| ~14:00 (3 pekan pasca-rapat) | 01:00 besok | FOMC Minutes | Kurasi + TV |
| Kamis 08:30 | Kamis 19:30 | Initial claims (mingguan) | Kurasi (DOL/ETA — klaim mingguan diterbitkan Departemen Buruh AS, bukan BLS) |
| Jumat 15:30 | **Sabtu 02:30** | Rilis COT CFTC (radar blok G — dipakai brief positioning akhir pekan) | Kurasi (CFTC) |

Catatan: baris "ISM Services Sel 23:00" pada contoh brief Agt-2026 menunjukkan format tampilan brief — jam per event tetap dibaca dari kolom jam presis union/kurasi, bukan hafalan.

### 3.4 Cara membaca angka: z per event dan ESI

**z per event** (definisi §4.2): bertanda dan tanpa satuan. Panduan baca:

| \|z\| | Bacaan | Catatan |
|---|---|---|
| < 0,3 | Kecil — hampir sesuai ekspektasi | Biasanya cuma noise intraday |
| 0,3–1,0 | Nyata | Mulai layang ke ekspektasi kebijakan |
| 1,0–2,0 | Besar | Sering mengubah bias sesi/hari |
| ≥ 4,0 | Ekstrem — **di-cap di ±4** (winsorize, dari spec) | Kejutan ekstrem dicatat maksimal ±4 agar statistik tidak diracuni |

**ESI (agregat)**: positif = data AS konsisten *beat*; negatif = konsisten *miss*. Nilai 0 = data sesuai ekspektasi. Yang penting bukan hanya levelnya tapi **arahnya berbalik** — itulah anomali "surprise flip" (§11.5) yang memicu alert. Contoh output spec: "Surprise US +8.2 → USD supportive" **(contoh nilai Agt-2026)** — data ketat → bias dolar kuat.

**Arah ke aset TIDAK satu-ke-satu** (jebakan paling umum — detail §5):
- Data kuat (ESI +) → biasanya **headwind** XAUUSD/XAGUSD (dolar & real yield naik) dan EURUSD; **tailwind** DXY.
- Tapi di era *decoupling* (emas naik meski real yield naik — sinyal Blok B/H), rantai itu bisa putus. Selalu baca lewat regime, bukan otomatis.

---

## 4. Logika hulu-hilir: dari angka mentah ke baris brief

### 4.1 Pipeline harian (berjalan 06:30 WIB)

```
[1] FETCH    FMP + EODHD + TV + CME (window 14 hari) + tabel kurasi
[2] NORMALISASI NAMA   "CPI m/m" / "Consumer Price Index" / dsb. → satu normalized_name
[3] DEDUP    (nama, waktu) → 1 baris per event  (uji: 4 sumber → 1 baris)
[4] JAM      precedence: kurasi > TV/CME > FMP > EODHD; 00:00 = date-only
[5] KONSENSUS dicatat BERSAMA SUMBERNYA (consensus_source);
    upsert HANYA pra-rilis (konsensus memang bisa berubah menjelang rilis)
[6] ACTUAL   append-only setelah rilis (revisi = baris baru, bukan timpa;
    setiap angka membawa release_ts = kapan pasar tahu)
[7] z        surprise_z = (actual − consensus) / σ_indikator
             σ rolling 5y, di-update per rilis, winsorize ±4σ, min 30 obs
             (kuartalan dgn n<30 → low_conf permanen di tabel indicator_stats)
[8] ESI      agregat = Σ z·e^(−Δt/90d) / Σ e^(−Δt/90d)
             hari tanpa rilis → ESI membawa nilai terakhir (bukan 0!)
[9] BRIEF    baris "Berubah semalam" (event yang baru rilis)
             + "Minggu ini" (radar) + "Surprise US …"
```

Semua tersimpan di tabel `events` (field: `event_uid, ts_utc, release_ts, country, name, normalized_name, importance, consensus, consensus_source, actual, actual_source, previous, surprise_z, is_curated`) dan `indicator_stats` (`indicator, as_of, sigma, n_obs, window, low_conf`). Rantai bisa ditelusuri: `arkwatch explore series … --trace` dari baris brief sampai raw fetch (BUILD-PLAN §8).

### 4.2 Konsep transform, dijelaskan dari nol

**(a) z-score — "berapa satuan kejutan".**
Masalah: meleset 0,3 poin persen di CPI itu besar atau kecil? Meleset 50 ribu di NFP? Tidak bisa dibandingkan langsung — satuannya beda, "normalnya" juga beda. z-score membagi surprise dengan **lebar miss yang biasa terjadi** di indikator itu (σ, dihitung dari 5 tahun kejutan historis, bergulir, di-update tiap rilis). Hasilnya: "CPI meleset 1,4× normalnya", "NFP meleset 0,6× normalnya" — kini sebanding. Analogi: telat 15 menit untuk kereta antar-kota itu wajar; telat 15 menit untuk take-away yang dijanjikan 5 menit itu skandal. z memberi tahu Anda sedang menghadapi yang mana.

**(b) Winsorize ±4σ — pagar anti-racun.**
Satu event gila (miss 10σ di masa krisis) kalau dibiarkan masuk mentah akan menggembungkan σ selama 5 tahun ke depan, sehingga semua kejutan sesudahnya terlihat kecil. Maka kejutan di-cap di ±4 sebelum dipakai (spec: "satu event 10σ tak meracuni").

**(c) Decay eksponensial 90 hari — memori pasar yang pudar.**
Bobot tiap kejutan = e^(−Δt/90d), Δt = usia kejutan dalam hari. Artinya: kejutan hari ini bobot 1,0; kejutan 90 hari lalu bobot ≈ 0,37; 180 hari lalu ≈ 0,13; setahun lalu praktis nol. Setengah-umur ≈ 62 hari. Ini meniru cara pasar bekerja: kejutan CPI Desember tidak lagi menggerakkan apa pun di bulan Agustus.

**(d) Rata-rata berbobot — merangkum tanpa dikeraskan data basi.**
ESI = Σ(z × bobot) / Σ(bobot). Berbeda dari rata-rata biasa (semua item dihitung sama), rata-rata berbobot memberi suara lebih besar pada kejutan baru. Dan karena pembaginya Σbobot (bukan jumlah hari), **hari tanpa rilis tidak menarik ESI ke 0** — ESI membawa nilai terakhir sampai ada kejutan baru (aturan eksplisit spec).

**Ilustrasi aritmetika lengkap** (angka σ dan usia event di bawah adalah hiasan untuk latihan menghitung — BUKAN nilai terverifikasi; nilai spec asli hanya strukturnya):

```
Langkah 1 — z per event:
  CPI: actual 3,1% vs cons 3,0%; σ historis CPI = 0,15
       z = (3,1 − 3,0)/0,15 = +0,67
  ISM : actual 48,2 vs cons 48,8 (contoh level spec Agt-2026);
       σ = 1,6 → z = (48,2−48,8)/1,6 = −0,38

Langkah 2 — bobot decay (90 hari):
  CPI dirilis 10 hari lalu → bobot = e^(−10/90) = 0,89
  ISM dirilis 40 hari lalu → bobot = e^(−40/90) = 0,64

Langkah 3 — ESI:
  = (0,67×0,89 + (−0,38)×0,64) / (0,89 + 0,64)
  = (0,596 − 0,243) / 1,53
  = +0,23  → data belakangan sedikit di atas ekspektasi
```

Perhatikan dua sifat yang muncul dari contoh: (1) event lama tetap memberi suara tapi makin kecil; (2) satu indikator kuat bisa "dilawan" indikator lain yang miss — ESI adalah neraca kejutan bersama, bukan megafon CPI semata. Hari berikutnya tanpa rilis apa pun, ESI masih +0,23 (carry), bukan 0.

**(e) Kenapa bukan momentum/percentile di sini?**
Momentum (arah perubahan) dan percentile (peringkat historis) adalah alat blok lain. Di blok I padanannya adalah **arah ESI berbalik** ("surprise flip") yang ditangkap sebagai anomali/alert, bukan sebagai state pilar — lihat §4.3.

### 4.3 State & kontribusi ke sinyal komposit

Fakta desain yang perlu Anda pahami (dan boleh tantang): **Blok I tidak punya bobot di regime score**. Bobot resmi (§11): A .20, B .20, C .15, D .15, E .15, F .15 — jumlah 1,00, tanpa "I". Rasionalnya (interpretasi, bukan kutipan spec): surprise adalah **driver perubahan**, bukan **keadaan**; sebagian besar informasinya sudah terpancar di harga dan di blok D — memberi bobot terpisah berisiko menghitung dua kali.

Kontribusi blok I lewat **empat jalur tidak langsung**:

| Jalur | Mekanisme | Tuju ke |
|---|---|---|
| ISM masuk "level+surprise" | PMI dari kalender dipakai blok D dengan level (>50/<50) DAN surprise-nya | Blok D → Dalio quadrant (growth momentum) |
| Anomali "surprise flip" | ESI berbalik arah secara mencolok → alert | Daftar anomali §11.5 |
| Narasi dolar | "Surprise US +8,2 → USD supportive" → bias DXY | Pembacaan metals/majors |
| Radar risiko | Baris "Minggu ini" → keputusan sizing/waktu Anda (bukan angka otomatis) | Manajemen risiko manual |

---

## 5. Membaca baris Blok I di brief + jebakan salah-baca umum

Baris-baris blok I di brief (contoh Agt-2026):

```text
Berubah semalam:
• Claims 203K (cons 208K) → labor ketat, surprise +
Minggu ini (EDT→WIB): ISM Services Sel 23:00 · CPI Kam 19:30 · FOMC Minutes Kam 01:00
(dan di bagian data momentum:)
Surprise US +8.2 → USD supportive
```

| # | Jebaan salah-baca | Yang benar |
|---|---|---|
| 1 | "Surprise + = beli emas" | Surprise + (data kuat) biasanya justru **headwind** emas (dolar/real yield naik). Arah aset dibaca lewat regime, bukan tanda surprise |
| 2 | Claims di bawah konsensus = surprise "negatif" karena 203 < 208 | Ekonomi kuat saat claims **rendah** — tanda ekonominya dibaca terbalik untuk indikator "semakin kecil semakin baik". Brief menulis makna ekonominya ("labor ketat, surprise +") |
| 3 | Baris "Minggu ini" jam 19:30 = tetap 19:30 sepanjang tahun | Jam WIB event AS **bergeser 1 jam** saat EST (Nov–Mar): 19:30 → 20:30 WIB |
| 4 | ISM 48,2 dengan cons 48,8 = buruk | Level 48,2 memang kontraksi (<50), tapi terhadap konsensus hanya miss tipis. **Level ≠ surprise** — dua bacaan berbeda (contoh spec Agt-2026) |
| 5 | ESI naik di hari tertentu = ada data bagus | Hari tanpa rilis, ESI **membawa nilai lalu** — pergerakannya bukan sinyal baru |
| 6 | Jam 00:00 di data mentah = rilis tengah malam | 00:00 = **date-only** (sumber cuma tahu tanggal) — sistem mencari jam dari sumber ber-precedence lebih tinggi |
| 7 | Konsensus = angka pasti yang tetap | Konsensus berubah menjelang rilis (karena itu sistem hanya boleh update-nya **pra-rilis**, dan mencatat `consensus_source`) |
| 8 | Actual di brief = kebenaran final | Actual sering **direvisi** bulan berikutnya; kejutan dihitung pada rilis pertama (point-in-time), revisi dicatat sebagai baris baru |
| 9 | z besar di dua indikator berbeda = kejutannya sama hebat | z sudah menstandarisasi per indikator — itu justru kegunaannya: z 1,5 di CPI ≈ z 1,5 di NFP secara "kejutan relatif" |
| 10 | Event semua sama pentingnya | Ada tier (TV: −1/0/1; CME: impact tier). Rilis tier rendah jarang mengubah bias swing |
| 11 | Indikator kuartalan punya z yang setara kualitasnya | Kuartalan dengan <30 observasi 5 tahun → **low_conf permanen** — kepercayaan rendah, tercatat di `indicator_stats` |

---

## 6. Keterkaitan spesifik dengan instrumen Anda

| Instrumen | Event yang paling menggerakkan | Kanalnya | Catatan swing |
|---|---|---|---|
| **XAUUSD / XAGUSD / XPTUSD** | CPI, NFP, FOMC + presser, PCE, Powell speeches | Real yield (Blok B) + dolar (A) + ekspektasi Fed | Sebelum CPI/FOMC: kecilkan size atau perlebar stop; gunakan vol implisit utk sizing — contoh spec Agt-2026: "vol silver 46 vs gold 24 → sizing XAG ½ XAU" (CVOL, Blok F) |
| **XCUUSD (copper)** | Rilis AS di atas + **China PMI (Caixin/NBS)** via kalender | Dolar + demand China (Blok D non-US) | Contoh spec: "Caixin mfg 49,8 → kontraksi tipis — netral"; ISM mfg AS juga relevan (kanal industri) |
| **BTC / ETH** | FOMC, CPI, NFP | Likuiditas (E) + risk appetite (F) | Crypto kini bereaksi ke makro AS; cek funding/OI (H) sebelum event — leverage tinggi + event = amplitudo besar |
| **US100/500/30** | CPI, NFP, FOMC+presser, ISM, GDP | Ekspektasi rate + growth | Contoh spec: rilis kuat bisa membalik preferensi US500 vs US100 (rasio VXN/VIX, Blok F) |
| **EURUSD / GBPUSD / majors** | Rilis AS (ESI → DXY) + **ECB/BoE** (leg lokal) | Diferensial rate & kebijakan | BoE MPC 8×/tahun (Blok A); EA HICP/PMI masuk kalender untuk leg EUR — contoh: pasar price ECB +45bp s/d Des-26 (ESR, contoh riset Agt-2026) |
| **XAUEUR / XAGGBP / crosses** | **Dua kalender sekaligus**: event AS + event EA/UK | Kedua leg bisa bergerak beda arah | Gerak sering datang dari leg XAU (contoh spec: "XAUEUR: gerak dari leg XAU"); cek jadwal HICP/BoE sebelum menilai cross |
| **DXY** | Semua rilis AS | ESI = bias dolar | "Surprise US +8,2 → USD supportive"; silang dengan positioning ICE DXY futures (G) |

**Playbook radar untuk swing (persiapan sebelum CPI/NFP/FOMC):**
1. **H-1 / pagi H**: buka baris "Minggu ini" — catat jam presis WIB, konsensus, dan previous.
2. **Siapkan dua skenario if-then** sebelum rilis: kalau beat besar, instrumen saya reaksi ke mana menurut regime hari itu (bukan asumsi tetap); kalau miss besar, ke mana. Tulis dulu, jangan improvisasi saat harga lompat.
3. **Ukur posisi menurun** menjelang event tier tertinggi — atau netralkan sebagian; vol implisit (GVZ/CVOL, Blok F) memberi tahu seberapa "mahal" gerakan yang diharapkan pasar.
4. **Jangan pasang entry baru di menit-menit rilis**: spread melebar, likuiditas berkilau palsu. Swing trader menunggu 15–30 menit pasca-rilis (atau setelah presser selesai) untuk melihat arah konvergensi.
5. **FOMC dua babak**: statement 14:00 ET (01:00 WIB saat EDT) lalu presser 14:30 ET — reaksi besar sering terjadi di sesi tanya-jawab, jangan menganggap selesai setelah angka rate keluar.

---

## 7. Yang bisa salah — degradasi, kualitas data, keterbatasan

### 7.1 Mode degradasi (by design — sumber gray selalu bisa mati, §0.3)

| Skenario | Efek | Sistem melakukan |
|---|---|---|
| **TV mati** | Kehilangan jam presis speeches | Kalender tetap FMP ∪ EODHD + kurasi (bunyi persis aturan fallback §11.4; CME masuk union lewat §18.1 — praktiknya union tetap 4 sumber) |
| **CME backdoor mati** | Kehilangan salah satu sumber actual/consensus/jam | Union tinggal 3 sumber + kurasi; jam tetap terjamin utk event terkurasi |
| **FMP/EODHD mati** | Konsensus lebih tipis | Sumber lain + kurasi; baris tanpa konsensus tidak menghasilkan z (tidak dikarang) |
| Kurasi kedaluwarsa | Jam event resmi berubah | Update kuartalan; jadwal FOMC di-vendor s/d 2028-01 dan dicek tiap Januari vs federalreserve.gov |

### 7.2 Kualitas data — jebakan yang sudah diantisipasi

- **Konsensus antar sumber bisa berbeda** — karena itu setiap nilai mencatat `consensus_source`; perubahan konsensus hanya boleh pra-rilis, dan setelahnya ter-log.
- **Actual direvisi** (ICSA, CPI, payrolls suka revisi) — aktual disimpan append-only dengan `release_ts` point-in-time; kejutan selalu dihitung dari rilis pertama yang dilihat pasar, sehingga analisis tidak curang memakai angka revisi masa depan.
- **Quirk teknis CME**: param `impact` wajib dikirim `null` (string = 403); endpoint kalender lama (cchummer) sudah mati — kalender CME harus lewat rantai filters → dates → events.
- **Baris "Symposium" 00:00 di TV** = abaikan (kasus Jackson Hole, §3.3).
- **Libur pasar** (FMP `holidays-by-exchange`) — hari libur AS tidak ada rilis 08:30 ET; juga dipakai sebagai alarm utk harvester CME agar tidak salah menilai "bolong".

### 7.3 Keterbatasan analitik (yang harus Anda sadari, bukan disembunyikan)

1. **ESI historis pra-2018 tipis** — data konsensus terbatas; ESI historis periode itu ber-flag `low_conf` (alternatif riset yang tercatat: median survey SPF, §18.4). Backtest jangka panjang tidak boleh bersandar pada ESI muda.
2. **Indikator kuartalan (n<30 observasi dalam 5 tahun) low_conf permanen** — z-nya ditampilkan dengan peringatan, bukan dipercaya penuh.
3. **Cap ±4σ** berarti kejutan ekstrem sekelas krisis **diremehkan sedikit** oleh desain (kompromi yang disengaja demi stabilitas σ).
4. **ESI tidak tahu "kenapa"** — dia hanya mendeteksi pola beat/miss; interpretasi sebab tetap pekerjaan Anda membaca gabungan blok (mis. beat karena energi ≠ beat karena upah — implikasinya beda untuk inflasi & Fed).
5. **Jam event bisa berubah/dibatalkan** (pidato reschedule, rilis ditunda) — presisi jam adalah presisi "jadwal terverifikasi terbaru", bukan janji.
6. **Speech tanpa angka**: z tidak terdefinisi untuk pidato — radar tetap menampilkannya (impact-nya nyata), tapi ESI tidak memasukkannya.

### 7.4 Pertanyaan untuk menantang desain (latihan berpikir kritis)

Parameter blok ini adalah pilihan, bukan hukum alam — layak Anda tanyakan ulang saat kalibrasi (re-kalibrasi kuartalan memang bagian dari proses, BUILD-PLAN §6.2):

1. **Kenapa decay 90 hari, bukan 60 atau 120?** 90 hari ≈ satu kuartal — asumsinya pasar "membukukan" satu kuartal data lalu reset. Kalau gaya trading Anda lebih pendek, ESI bisa terasa lambat; itulah kenapa z per-event tetap ditampilkan, bukan hanya agregat.
2. **Kenapa σ window 5 tahun?** Kompromi klasik: cukup panjang untuk stabil, cukup pendek untuk mengikuti perubahan rezim survei. Terlalu panjang → σ membawa era yang sudah tidak relevan; terlalu pendek → z melompat-lompat.
3. **Kenapa ESI tidak diberi bobot di regime score?** Lihat §4.3 — risiko double-counting dengan blok D. Kalau suatu saat terbukti ESI memimpin (leading) regime, ini kandidat revisi desain yang sah.
4. **Kenapa winsorize di ±4, bukan ±3 atau ±5?** Semakin ketat cap, semakin "diredam" kejutan krisis; semakin longgar, semakin mudah satu event menggembungkan σ. Ini parameter yang bisa diuji ulang dengan data sendiri begitu historis terkumpul.

---

> **Bacaan terkait**: `01-block-a-policy-rates-dollar.md` (ke mana surprise CPI mengalir: FedWatch & yield) · `02-block-b-real-yield.md` (kanal utama gold) · `04-block-d-growth.md` (konsumen z PMI: level+surprise) · `06-block-f-stress-vol-sentiment.md` (sizing di sekitar event dengan vol implisit).
> Rantai angka bisa ditelusuri sendiri: `arkwatch explore series CAL:ESI --trace` (saat build selesai) — dari baris brief sampai raw fetch log.
