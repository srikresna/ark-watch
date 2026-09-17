# Blok C — Inflasi (+ Kanal Energi)

> Dokumen edukasi (Bahasa Indonesia, untuk non-finance). Pendamping resmi: [DATA-SPEC.md](../DATA-SPEC.md) §3 (tabel blok C) + §18.3 (Dallas trimmed PCE), dan [BUILD-PLAN.md](../BUILD-PLAN.md) §3 (transform-spec blok C).
> Rantai data bisa ditelusuri langsung: `arkwatch explore block C` → `arkwatch explore series FRED:CPIAUCSL` → `arkwatch explore signal INFL_STATE --trace`.

---

## 1. Kenapa blok ini ada

Inflasi, untuk trader, bukan soal "harga beras naik". Inflasi adalah **setengah dari kompas regime**. Seluruh sistem ark-watch bermuara pada satu peta 2 sumbu (Dalio quadrant, §11.2 DATA-SPEC): **growth momentum × inflasi momentum**. Blok C adalah pemilik sumbu "inflasi momentum" itu. Blok D (growth) memegang sumbu satunya.

Kenapa inflasi sebegitu penting sampai jadi sumbu tersendiri? Karena **inflasi adalah input #1 kebijakan Fed**. Fed punya dua mandat (harga stabil + tenaga kerja). Ketika inflasi naik, Fed terpaksa menaikkan rate / memotong lebih lambat → itu menggerakkan blok A (rate), blok B (real yield — driver #1 XAUUSD), dan dolar (DXY). Jadi rantai kausalnya:

```
Inflasi (C) → reaksi & ekspektasi Fed (A) → nominal yield + real yield (B) → dolar → harga aset Anda
```

Analogi sehari-hari untuk seluruh blok ini: **CPI itu seperti hasil lab darah bulanan** — resmi, akurat, tapi telat (baru keluar ~2 minggu setelah bulan berakhir). **Nowcast Cleveland adalah alat cek kesehatan instan harian** — estimasi lab bulan yang belum selesai dihitung, dari data yang SUDAH keluar hari ini (harga energi, data klaim, dsb.). **WTI adalah makanan yang baru saja Anda telan** — penyebab paling cepat merambat ke hasil lab berikutnya. **MICH dan breakeven adalah "persepsi orang soal lab bulan depan"** — dari survei dan dari taruhan uang sungguhan. Semua lima ini saling melengkapi; tidak ada satu pun yang cukup sendirian.

Pertanyaan desain yang wajar Anda ajukan: *"kan blok B sudah punya breakeven (inflasi versi pasar)? kenapa perlu blok C juga?"* Jawabannya: **breakeven = pendapat pasar, CPI/PCE = fakta yang sudah terjadi**. Breakeven harian dan cepat, tapi bercampur risk premium (orang bayar mahal bukan cuma karena takut inflasi, tapi juga karena panik). CPI/PCE lambat tapi bersih — dan inilah yang sebenarnya direspon Fed dalam rapat FOMC. Fed tidak menaikkan rate karena breakeven naik; Fed menaikkan rate karena PCE core dan proyeksinya naik. Blok C memberi Anda "faktanya"; blok B memberi "pendapat pasar tentang masa depannya". Kalau keduanya berlawanan arah — itu sendiri sinyal berharga.

Bobot blok C dalam regime score hanya **0.15** (lihat §4.4) — lebih kecil dari A dan B (0.20). Ini sadar: efek inflasi ke book Anda kebanyakan *bekerja lewat* blok A/B (Fed dan real yield). Kalau inflasi naik tapi Fed jelas tidak akan bereaksi dan real yield datar, efeknya kecil. Blok C adalah *bahan bakar* untuk dua mesin itu, bukan mesin itu sendiri.

---

## 2. Glosarium istilah blok

| Istilah | Arti untuk awam | Kenapa penting untuk Anda |
|---|---|---|
| **Inflasi** | Harga keranjang belanja umum naik dari waktu ke waktu | Mengekang/memacu Fed → menggerakkan rate → aset Anda |
| **Disinflasi (COOLING)** | Harga masih naik, tapi laju kenaikannya melambat | Quadrant "disinflationary growth" = kombinasi ramah bagi banyak aset |
| **Deflasi** | Harga benar-benar turun | Biasanya tanda permintaan hancur (resesi) — buruk, meski "harga turun" kedengaran enak |
| **CPI** | Indeks harga keranjang belanja konsumen AS, dihitung BLS (Bureau of Labor Statistics) | Angka inflasi yang paling ditonton pasar tiap bulan; dipakai indexasi gaji/TIPS |
| **PCE** | Indeks harga dari data pengeluaran aktual di akun nasional, dihitung BEA (Bureau of Economic Analysis) | **Metrik resmi target Fed** — Fed menyebut target 2% dalam istilah PCE |
| **Core** | Versi indeks yang *membuang makanan & energi* | Menampilkan tren yang lebih mulus; tapi bisa menutupi lonjakan energi yang menetap |
| **Trimmed mean PCE** | Rata-rata PCE setelah komponen termahal & termurah tiap bulan DIBUANG — seperti lomba menyelam membuang skor tertinggi/terendah hakim | Ukuran inti paling bersih & adaptif (Dallas Fed); "ukuran inti paling bersih saat energi menyabet headline" (§18.3) |
| **SA (seasonally adjusted)** | Sudah dibersihkan dari pola musiman (liburan, musim panas, dll.) | Wajib untuk MoM; tanpa SA, MoM cuma mencerminkan kalender |
| **MoM (month-over-month)** | Perubahan indeks vs bulan lalu | Kecepatan *sesaat* — bising tapi paling baru |
| **YoY (year-over-year)** | Perubahan vs bulan yang sama tahun lalu | Yang dikutip media; otomatis bebas pola musiman; tapi lambat berbalik |
| **3m-annualized** | Kecepatan rata-rata 3 bulan terakhir, "dipampat" menjadi setahun | Kompromi terbaik: cepat tapi tidak sekasar MoM — **headline utama blok C** |
| **Base effect** | YoY jadi aneh karena bulan pembanding tahun lalu harganya tak wajar | Sumber #1 salah-baca berita inflasi |
| **Nowcast** | Estimasi angka yang belum resmi dirilis, dihitung dari data harian yang sudah ada | "Radar cuaca jam depan" — kunci posisi menjelang CPI-week |
| **Ekspektasi inflasi** | Berapa orang *pikir* inflasi bakal jadi | Kalau terlepas dari 2%, inflasi jadi mandiri (upah mengejar harga) |
| **Anchor** | Titik berat ekspektasi menempel | Anchor rusak = regime berubah — alasan MICH dipantau |
| **MICH** | Survei University of Michigan: median ekspektasi inflasi konsumen 12 bulan ke depan | Suara konsumen (pendapat), vs breakeven (taruhan uang) |
| **Breakeven** | Selisih yield Treasury biasa vs TIPS anti-inflasi | Inflasi terimplikasi PASAR — hidup di blok B, dibanding silang dengan MICH |
| **WTI** | Harga minyak mentah acuan AS (West Texas Intermediate) | Kanal transmisi tercepat ke CPI headline; angka harian |
| **OVX** | Indeks volatilitas opsi minyak (blok F) | "Seberapa takutnya pasar akan kejutan harga minyak" — pemicu anomali blok C |
| **Konsensus** | Perkiraan rata-rata ekonom sebelum rilis | Pasar bergerak pada *selisih* aktual vs konsensus (surprise), bukan levelnya saja |
| **Surprise (z)** | (aktual − konsensus) / deviasi historis | Dihitung blok I; inilah yang menggoyang harga di menit-menit rilis |
| **z-score** | Jauhnya nilai dari rata-rata 5 tahun, dalam satuan deviasi standar | Bahasa umum semua pilar — angka mentah jadi comparable |
| **Momentum** | Arah/kecepatan perubahan beberapa periode terakhir | State blok C dibangun dari arah, bukan level semata |
| **Vintage / revisi** | Data resmi bisa direvisi; tiap versi disimpan terpisah | Mencegah *look-ahead*: pakai angka sebagaimana diketahui saat itu |
| **Contango / backwardation** | Bentuk kurva futures: contango = kontrak berikutnya LEBIH MAHAL dari spot (normal); backwardation = lebih MURAH (stok ketat diperebutkan sekarang) | Menjelaskan basis kecil futures CL vs spot WTI (§3.5) → toleransi cross-val longgar |
| **Stagflasi** | Ekonomi stagnan + inflasi tinggi sekaligus | Kuadran falling×reaccel (§4.4) — paling beracun bagi mayoritas aset |
| **HICP** | Indeks harga konsumen zona euro (Harmonised Index of Consumer Prices) — "CPI-nya Eropa" | Didefinisikan penuh di dokumen blok D (04); kaki EUR dari crosses di §6 |

---

## 3. Peta data blok C

Ringkasan (sumber kebenaran: DATA-SPEC §3 + §18.3):

| Series | ID | Sumber (primer → sekunder) | Frek | Peran |
|---|---|---|---|---|
| CPI (indeks, SA) | `CPIAUCSL` | FRED → FMP `CPI`,`inflationRate` | M | Arah inflasi rilis; MoM/YoY/3m-ann dihitung sendiri |
| Core PCE | `PCEPILFE` | FRED **satu-satunya** (fallback FMP putus — temuan audit) | M | Metrik favorit Fed → state |
| Trimmed PCE (Dallas) | `PCETRIM1M158SFRBDAL` + `PCETRIM12M159SFRBDAL` | FRED | M | Momentum + trend inti paling bersih |
| Ekspektasi konsumen | `MICH` | FRED → FMP `consumerSentiment` | M | Anchor |
| WTI minyak | `DCOILWTICO` | FRED → backdoor CME CL | D | Kanal energi → CPI headline; pelengkap OVX |
| Nowcast inflasi | Cleveland Fed `nowcast_month.json` (juga `_quarter`,`_year`) | Cleveland Fed (JSON FusionCharts) | D | CPI-week positioning |
| *(konteks, blok B)* | `T5YIE` `T10YIE` `T5YIFR` | FRED | D | Ekspektasi inflasi versi pasar — pembanding MICH |

### 3.0 Tabel bantu — empat "versi" inflasi dalam satu halaman

Sebelum masuk per-series, ini peta besar konsepnya (tanda ✓ = ada series-nya di blok ini; konsep = hanya untuk pemahaman):

| Versi | Cara buang noise | Kekuatan | Kelemahan | Status di blok |
|---|---|---|---|---|
| **Headline (CPI all items)** | Tidak dibuang — semua komponen masuk | Inilah biaya hidup yang dirasakan; yang ditonton pasar di menit rilis | Paling volatil (energi & makanan menyabet) | ✓ `CPIAUCSL` |
| **PCE headline** *(konsep)* | Tidak dibuang | Cakupan paling luas | Tetap volatile | tidak diambil (redundan dgn CPI utk kebutuhan brief) |
| **Core (PCE ex food & energy)** | Buang kategori TETAP: makanan + energi | Favorit Fed; menampilkan tren | Bisa menutup lonjakan energi yang menetap | ✓ `PCEPILFE` |
| **Trimmed mean (Dallas)** | Buang EKOR distribusi tiap bulan, siapa pun komponennya | Adaptif: noise dibuang, sinyal yang menetap lolos | Butuh data komponen → paling telat terbit | ✓ 2 series (1M + 12M) |

Cara mengingat cepat: **headline = apa yang dirasakan; core = apa yang ditargetkan; trimmed = core versi adaptif.** Ketiga "core" bisa berbeda kesimpulan di bulan yang sama — contohnya saat minyak anjlok lalu mantul dalam bulan yang sama: headline tampak liar, core biasa diam, trimmed memberi gambaran tengah yang jujur.

### 3.1 CPI — `CPIAUCSL` (FRED → FMP)

- **Apa itu sebenarnya:** indeks level (bukan persen!) dari harga keranjang ribuan barang/jasa konsumen kota AS, versi *all items, seasonally adjusted*. Yang kita simpan raw adalah indeksnya; MoM/YoY/3m-annualized dihitung sendiri dari level (prinsip raw+derived §0.4 — FMP `CPI`/`inflationRate` yang berbentuk persen jadi sekunder/cross-check saja, dan **unit-nya beda** — value_format wajib dibedakan di registry).
- **Siapa menerbitkan & kapan:** BLS (Bureau of Labor Statistics), rilis ~pertengahan bulan berikutnya jam 08:30 ET. Contoh kalender brief Agt-2026: **"CPI Kam 19:30"** WIB (saat EDT; 20:30 WIB saat EST). Jam presis diambil dari kalender union-4 + tabel kurasi (blok I).
- **Kenapa ini yang dipilih:** CPI adalah angka inflasi yang *ditonton pasar* (menggerakkan harga di menit rilis) dan basis indexasi resmi. Alternatif: `CPILFESL` (core CPI) sengaja tidak jadi baris utama karena peran "inti" sudah diwakili PCE core & trimmed PCE — dua versi core yang berbeda-beda hanya menambah noise.
- **Cara baca angka:** yang muncul di brief adalah turunannya: contoh nilai Agt-2026 — **"CPI 3m-ann 2.8% COOLING"**. Angka 2.8% = kecepatan setahun-an dari 3 bulan terakhir (lihat §4.1 cara hitung). Konteks: target Fed (dalam PCE) 2%, jadi ~2.8% masih *di atas* target namun arah melandai → "COOLING" merujuk **arah momentum**, bukan level yang sudah aman.
- **Catatan revisi:** CPI masuk daftar tracking vintage ALFRED (§18.2). Revisinya kecil, tapi **faktor musiman diperbarui tahunan** — seluruh riwayat SA bisa bergeser sedikit, yang otomatis menggeser MoM/3m-ann historis. Karena itu raw disimpan append-only per vintage.

### 3.2 Core PCE — `PCEPILFE` (FRED, SATU-SATUNYA)

- **Apa itu sebenarnya:** indeks harga pengeluaran konsumsi dari akun nasional, *minus makanan & energi*.
- **Siapa & kapan:** BEA, rilis bersama laporan "Personal Income & Outlays" di akhir bulan berikutnya (~4 minggu setelah akhir bulan referensi), 08:30 ET. Jadi urutannya tiap bulan: **CPI dulu (rilis ~2 minggu setelah akhir bulan referensi) → PCE ~2 minggu kemudian**.
- **Kenapa Fed lebih suka PCE core daripada CPI:** (1) cakupan lebih luas — PCE menangkap pengeluaran yang *dibayarkan pihak lain atas nama Anda* (premi asuransi kesehatan oleh majikan, program pemerintah); (2) bobot mengikuti perilaku belanja aktual — saat daging mahal orang pindah ke ayam, PCE "mengikuti" perpindahan itu, CPI memakai keranjang bobot tetap yang lebih lama; (3) historisnya lebih stabil/mulus sehingga lebih gampang dibaca trennya. Konsekuensinya bagi Anda: **CPI menggerakkan harga di hari rilis; PCE core menentukan keputusan multi-bulan Fed.** Dua-duanya wajib.
- **Peringatan penting (temuan audit spec):** fallback FMP economic-indicators untuk PCE **ternyata putus** — jadi series ini *single-source FRED*. Ini diizinkan §0.1 (lembaga resmi + freshness check aktif), tapi artinya ketahanannya lebih rendah dari CPI (lihat §7).
- **Cara baca:** angka YoY-nya dibandingkan langsung dengan target 2% Fed. Selisih CPI vs PCE core yang melebar biasanya soal cakupan/bobot — bukan sinyal pertengkaran data.

### 3.3 Dallas trimmed-mean PCE — `PCETRIM1M158SFRBDAL` (momentum) + `PCETRIM12M159SFRBDAL` (trend)

- **Apa itu sebenarnya:** versi "inti" PCE versi Dallas Fed. Alih-alih membuang kategori tetap (makanan+energi), **tiap bulan mereka membuang komponen yang naik paling ekstrem dan turun paling ekstrem** (ekor kiri & kanan distribusi), lalu merata-rata sisanya.
- **Analogi:** lomba selancar menyelam membuang skor tertinggi & terendah para juri supaya satu juri yang emosional tak merusak nilai akhir. "Core biasa" = selalu membuang nama juri tertentu; "trimmed" = membuang juri yang hari itu menyimpang paling jauh, siapa pun dia.
- **Kenapa lebih bersih dari core biasa:** core menetapkan *energi selalu dibuang*. Padahal ada dua jenis lonjakan energi — yang cepat pulih (noise, sebaiknya dibuang) dan yang menetap lalu menular ke barang lain (sinyal, sebaiknya dihitung). Trimmed menangani keduanya otomatis: energi yang menetap tidak akan selalu berada di ekor. Spec menyebutnya "ukuran inti paling bersih saat energi menyabet headline" (§18.3).
- **Kenapa dua series:** `...1M158S...` = versi 1 bulan (bahan **momentum** — cepat), `...12M159S...` = versi 12 bulan (bahan **trend** — lambat tapi tak terkecoh). Ketika momentum di bawah trend dan keduanya turun → disinflasi meyakinkan; ketika momentum memotong naik di atas trend → peringatan dini reakselerasi.
- **Siapa & kapan:** Dallas Fed, bulanan, menyusul beberapa hari setelah rilis PCE BEA (dia butuh data komponen PCE dulu sebagai bahan). Jadi jangan berharap angka ini update saat CPI-week — dia selalu telat dari PCE.
- **Cara baca:** perlakukan seperti membaca PCE core: dibandingkan ke 2%, dan yang lebih penting arah 3 bulan terakhir.

### 3.4 Ekspektasi konsumen — `MICH` (FRED → FMP `consumerSentiment`)

- **Apa itu sebenarnya:** median jawaban rumah tangga AS yang disurvei University of Michigan: "berapa persen Anda perkirakan harga naik 12 bulan ke depan?" Keluar sebagai persen.
- **Kenapa ada di blok inflasi:** teori yang dianut bank sentral modern — inflasi sebagian **self-fulfilling**. Kalau semua yakin besok harga naik 5%, orang menuntut kenaikan gaji 5% sekarang, toko menaikkan harga sekarang → inflasi 5% terwujud sendiri. Karena itu "anchor" ekspektasi dipantau sebagai penjaga terakhir target 2%.
- **Penting memahami biasnya:** konsumen (a) cenderung menyebut angka LEBIH TINGGI dari inflasi aktual kronis, (b) sangat terpengaruh harga pom bensin yang paling sering mereka lihat. Maka **level MICH yang selalu >2% bukan alarm; yang bermakna adalah perubahan arah dan lonjakan tajamnya**.
- **MICH vs breakeven — konsumen vs pasar:** MICH = *pendapat* (survei ~ratusan rumah tangga, tanpa risiko uang); breakeven (`T5YIE`/`T10YIE`, blok B) = *taruhan uang sungguhan* investor yang membeli proteksi TIPS. Breakeven lebih kredibel sebagai prediksi, tapi bercampur premium risiko & likuiditas (saat panik, breakeven naik bukan murni karena ekspektasi inflasi). **Praktik baca: lonjakan KEDUANYA bersamaan = sinyal anchor menganga; keduanya tenang = Fed punya ruang kerja.** Versi paling murni untuk anchor jangka panjang adalah 5y5y forward `T5YIFR` (blok B) — yang benar-benar dibandingkan langsung dengan 2%.
- **Catatan verifikasi (untuk F0):** sekunder FMP `consumerSentiment` berpotensi beda makna — kemungkinan berupa indeks kepercayaan konsumen (skala ~0–100), bukan median ekspektasi inflasi (%). Kalau memang begitu, ia bukan pengganti apples-to-apples; cross-val harus diuji dulu di gerbang kebenaran, jangan dipakai diam-diam.

### 3.5 WTI — `DCOILWTICO` (FRED → backdoor CME CL)

- **Kenapa MINYAK masuk blok inflasi, bukan blok komoditas:** karena di sini minyak dipakai sebagai **kanal transmisi tercepat ke CPI headline**. Energi adalah komponen volatil terbesar keranjang CPI; perubahan WTI terlihat di pom bensin dalam hitungan hari, lalu merambat ke biaya angkut semua barang. Dengan frekuensi D (harian), WTI adalah satu-satunya anggota blok C yang bisa memberi "denyut" setiap hari di antara rilis bulanan yang jarang.
- **Analogi:** CPI adalah hasil lab; WTI adalah makanan yang baru Anda telan — tidak langsung mengubah hasil lab, tapi paling cepat memberi tahu arah lab berikutnya.
- **Siapa & kapan:** spot WTI harian hari kerja (EIA, via FRED). Sekunder: futures CL lewat backdoor CME (settlement EOD; gray-zone, degradable) — catat futures vs spot punya basis kecil (kontrak bulan tertentu + pola contango/backwardation), jadi toleransi cross-val harus longgar.
- **Cara baca + pasangan OVX:** contoh nilai Agt-2026 dari brief: **"Inflasi=COOLING (WTI 83.9 tenang, OVX 46 tinggi → waspadai)"**. WTI 83.9 levelnya tenang, TAPI OVX (vol implied minyak, blok F) di 46 = pasar mempersiapkan kejutan besar. Kombinasi "harga tenang + vol tinggi" = risiko CPI headline menyabet SATU bulan ke depan. Itulah kenapa brief Agt-2026 juga memunculkan baris anomali: **"OVX 46 persentil ekstrem — pantau energi"**.
- **Batasan logika:** WTI naik ≠ CPI bulan itu otomatis naik — ada delay pass-through dan bobot. WTI adalah *early warning*, bukan komponen mekanik. EIA versi-2 (stok crude) tidak diambil: untuk harga, DCOILWTICO sudah cukup (redundan, §18.4).

### 3.6 Nowcast Cleveland Fed (harian, tanpa key)

- **Apa itu sebenarnya:** model Cleveland Fed yang **setiap hari kerja memperbarui estimasi** CPI/PCE untuk bulan yang *belum resmi dirilis*, dari data harian yang sudah terbit (harga komoditas & energi, klaim pengangguran, dsb.). Bukan ramalan dukun — model statistik resmi bank sentral.
- **Kenapa update harian penting untuk CPI-week:** masalah struktural CPI adalah telat ~2 minggu dari akhir bulan. Tanpa nowcast, Anda buta total menjelang rilis. Dengan nowcast: pagi hari Anda bisa membandingkan *"model Cleveland: nowcast CPI 2.6%"* (contoh nilai Agt-2026) vs *konsensus ekonom*. **Kalau keduanya berdekatan → pasar kemungkinan sudah mem-price → ruang gerak kecil. Kalau berjauhan → ada ruang surprise** — itulah momen CPI-week yang menentukan sizing. Nowcast juga bergerak HARI demi HARI menjelang rilis (makin banyak data masuk, estimasi makin sempit) — arah pergerakannya sendiri informasi.
- **Detail teknis implementasi (dari spec):** endpoint `/-/media/files/webcharts/inflationnowcasting/nowcast_month.json` — JSON FusionCharts, tanpa API key, wajib UA browser; tersedia juga `_quarter` dan `_year`. Parser: **ambil elemen terakhir per bulan**; label tanggal format MM/DD, dan **tahunnya diambil dari subcaption** (jebakan klasik parser). Ini sumber tunggal tanpa sekunder — mutunya dijaga lewat uji "parser vs nilai yang tampil di halaman web" (gerbang F1) dan alarm schema-fingerprint bila struktur JSON berubah diam-diam.

---

## 4. Logika hilir-ke-hulu: dari angka mentah ke regime score

### 4.1 Tahap 1 — dari indeks mentah ke MoM / YoY / 3m-annualized

Raw `CPIAUCSL` adalah *indeks level* (angka ratusan, bukan persen). Semua turunan dihitung sendiri dari level ini:

- **MoM** = `I_t / I_(t−1) − 1`, dihitung pada versi SA. Kelebihan: paling segar. Kekurangan: bising (satu diskon besar di satu kategori bisa menipu).
- **YoY** = `I_t / I_(t−12) − 1`. Otomatis bebas musiman (membandingkan bulan sama). Kekurangan: **11 dari 12 bulannya adalah "bekas"** — angka berbalik arah sangat lambat, dan terkena *base effect*: kalau Juni tahun lalu energi anjlok, YoY Juni ini terlihat "meloncat" padahal bulan ini biasa saja. Analogi: nilai rapor naik 30% terlihat hebat kalau dibanding semester lalu yang remuk.
- **3m-annualized** = kecepatan gabungan 3 bulan terakhir dipampat menjadi laju setahun. Konsep: MoM terlalu bising, YoY terlalu tua; 3m-ann adalah jalan tengah yang **paling dulu berbalik** saat inflasi berubah arah — dan itulah kenapa jadi headline blok C di brief.

Contoh base effect dengan angka ilustratif (indeks fiktif, hanya untuk merasakan mekanismenya): bayangkan Juni tahun lalu indeks sempat anjlok karena subsidi bensin satu kali (120.0), lalu normal kembali. Bulan ini indeks 126.0 dan bulan lalu 125.7.
- MoM = 126.0/125.7 − 1 = **+0.24%** → kecepatan sesaat biasa-biasa saja.
- YoY = 126.0/120.0 − 1 = **+5.0%** → terlihat mengerikan, padahal 4 poin dari 5 itu datang dari pembanding yang tahun lalu "remuk".
Sekarang jelas kenapa berita yang hanya mengutip YoY bisa menyesatkan, dan kenapa brief memakai 3m-ann sebagai headline: 3m-ann hanya melihat 3 bulan terakhir — pembanding "remuk" setahun lalu tidak ikut masuk.

Rumus 3m-annualized **persis ter-PIN di BUILD-PLAN §3 (v1.1)**:

```
3m-ann = ((1+m1)(1+m2)(1+m3))^(4/3) − 1        m = MoM desimal, pada CPIAUCSL (SA)
```

Kenapa dikali-masak pakai `(1+m)` (bukan dijumlah lalu dibagi 3): inflasi adalah *bunga berbunga* — harga bulan ini menumpuk di atas harga bulan lalu; mengalikan faktor `(1+m)` menjaga matematika majemuk itu benar.

Contoh hitung tangan (angka ilustratif, bukan data rilis): MoM tiga bulan berturut = 0.2%, 0.3%, 0.4% →
`(1.002)(1.003)(1.004) = 1.009026` → `1.009026^(4/3) − 1 ≈ 1.21%`.

**Catatan verifikasi yang perlu Anda ketahui (bukan untuk diubah diam-diam):** konvensi umum "3-month annualized" memampatkan 3 bulan (= 1/4 tahun) menjadi setahun dengan pangkat **4**: `P^4 − 1`; dengan pangkat 4, contoh di atas ≈ 3.66%, dan MoM stabil ~0.23%/bln menghasilkan 3m-ann ≈ 2.8% — konsisten dengan contoh output brief Agt-2026 ("3m-ann 2.8% COOLING"). Dengan pangkat 4/3 persis seperti tertulis, angka 2.8% baru muncul dari MoM ~0.69%/bln (setara laju YoY ~8.6% — janggal disebut COOLING). BUILD-PLAN sendiri mewajibkan fixture **"nilai 3m-ann dihitung tangan untuk 1 bulan historis = pipeline"** — poin verifikasi inilah yang akan merekonsiliasi maksud rumus vs teksnya. Kalau Anda (pemilik) ingin menantang, ini tempatnya: pastikan fixture itu menegaskan pangkat mana yang dimaksud *sebelum* sinyal hidup.

### 4.2 Tahap 2 — konsep transform umum (dipakai semua blok)

- **z-score** = `(x − rata-rata_5y) / σ_5y`, σ populasi, window sesuai frekuensi (bulanan = 60 observasi). Bahasa awam: "berapa 'lintasan aneh' nilai ini dibanding 5 tahun terakhir". z +2.0 = dua deviasi di atas normal.
- **Percentile** = ranking historis pada window sama: "nilai ini lebih tinggi dari X% kejadian 5 tahun terakhir".
- **Momentum** series bulanan dihitung dalam N *bulan*.
- **Syarat minimal data** 80% window (48 dari 60 observasi); kalau kurang → `state = INSUFFICIENT` — sistem memilih *tidak punya pendapat* daripada mengarang angka.
- **As-of join anti look-ahead:** anggota pilar yang beda frekuensi digabung hanya dengan nilai yang *sudah dirilis* per tanggal sinyal (pakai `release_ts`) — bukan forward-fill buta. Konkritnya: tanggal 12 bulan, CPI terakhir yang sah = bulan referensi yang SUDAH dirilis BLS, sekalipun nowcast sudah punya estimasi bulan lebih baru (nowcast masuk baris terpisah, bukan menyusup jadi "CPI resmi").

### 4.3 Tahap 3 — state blok C

State resmi (BUILD-PLAN §3): **COOLING / STABLE / REACCEL**, ditentukan dari **arah Δ3-bulan** dari 3m-annualized CPI (bukan dari level absolut). Logikanya: level 2.8% yang turun tiga bulan berturut dan level 2.8% yang naik tiga bulan berturut adalah dua dunia berbeda bagi Fed — yang pertama menuju target, yang kedua menjauh.

Contoh nyata di brief Agt-2026: `Inflasi=COOLING` — dengan konteks "WTI 83.9 tenang, OVX 46 tinggi → waspadai" (state bisa COOLING sambil membawa catatan risiko).

### 4.4 Tahap 4 — kontribusi ke sinyal komposit

1. **Regime score (−2…+2):** tiap pilar = rata-rata z-score anggotanya (window 5y); flip state di ±0.5. **Bobot pilar C = 0.15** (bandingkan A 0.20, B 0.20, D/E/F masing-masing 0.15). Label regime diambil dari kombinasi state pilar — contoh brief Agt-2026: `EASING + LIQUIDITY EXPANDING (score +1.2)`.
2. **Dalio quadrant:** sumbu inflasi momentum diambil dari blok C, disilangkan dengan growth momentum (blok D). Empat kuadran: growing×reaccel (overheat), **steady×cooling = "disinflationary growth"** (contoh Agt-2026: `growth STEADY × inflasi COOLING`), falling×cooling (risiko resesi/deflasi), falling×reaccel (stagflasi — paling beracun untuk mayoritas aset). Kuadran di-map ke return historis instrumen di fase backtest (F4).
3. **Anomali & alert:** blok C memicu baris anomali lewat kanal energi — contoh nyata Agt-2026: OVX 46 di persentil ekstrem → "pantau energi".

### 4.5 Alur hidup satu bulan data (CPI-week dalam praktik)

```
Bulan berjalan:  nowcast harian bergeser tiap hari kerja (± ruang surprise vs konsensus)
H-1..H-0:        brief pagi memakai nowcast + konsensus; sizing event ditentukan
Rilis (19:30 WIB saat EDT): aktual masuk → blok I menghitung surprise-z → harga bergerak
H+1 pagi:        brief mencetak angka rilis; MoM/YoY/3m-ann dihitung ulang
~2 minggu kemudian: PCE + trimmed Dallas menyusul → state dikonfirmasi/dikoreksi
```

Perhatikan: brief dikirim 07:00 WIB, rilis CPI jam 19:30 WIB (EDT) — jadi **pada hari rilis, angka aktual TIDAK mungkin ada di brief pagi**; fungsi brief pagi adalah menyiapkan skenario (nowcast vs konsensus), bukan melaporkan hasil.

Playbook tiga skenario CPI-week (cara menyiapkan diri sebelum rilis — edukasi, bukan sinyal):

| Skenario pra-rilis | Ciri | Orientasi umum pasar | Yang Anda lakukan dengan brief |
|---|---|---|---|
| **In-line** (nowcast ≈ konsensus) | Gap dua angka sempit | Market sudah mem-price → gerak pasca-rilis cenderung kecil | Risiko event rendah; posisi swing boleh dipertahankan; jangan bereaksi berlebihan pada selisih kecil |
| **Hot risk** (nowcast > konsensus, atau OVX ekstrem spt contoh Agt-2026) | Model melihat tekanan yang belum masuk konsensus | Ekspektasi Fed lebih ketat → yield & DXY naik, gold/equities tertekan | Kecilkan sizing / perketat stop sebelum 19:30 WIB; siapkan skenario reaksi blok B (RY naik = headwind XAU) |
| **Cold risk** (nowcast < konsensus) | Model melihat disinflasi lebih cepat | Ekspektasi cut menguat → risk-on, dolar melemah | Favorable XAU/XAG/BTC — tapi ingat jebakan #7: nowcast bisa salah; jangan full-position murni atas dasar satu model |

Intinya: nilai terbesar nowcast harian bukan ramalan jitu, melainkan **mengubah malam rilis dari tebak-tebakan menjadi tiga skenario berbayang** — itulah kenapa series ini masuk blok meski CPI resminya hanya bulanan.

---

## 5. Membaca baris blok C di brief + jebakan salah-baca

Baris-baris blok C di brief (contoh dari spec, nilai Agt-2026):

```text
• CPI 3m-ann 2.8% COOLING                     ← headline utama (kecepatan, bukan YoY)
• nowcast CPI 2.6%                            ← estimasi Cleveland utk bulan berjalan
• Inflasi=COOLING (WTI 83.9 tenang, OVX 46 tinggi → waspadai)
• QUADRANT: growth STEADY × inflasi COOLING → "disinflationary growth"
• Minggu ini: ... CPI Kam 19:30 ...           ← radar jadwal (blok I)
• Anomali: OVX 46 persentil ekstrem — pantau energi
```

Jebakan salah-baca yang paling sering:

1. **"3m-ann 2.8%" dibaca sebagai YoY.** Bukan. 3m-ann = kecepatan 3 bulan terakhir dipampat setahun; YoY = rata-rata 12 bulan terakhir. Keduanya boleh berbeda arah — dan saat berbeda, **3m-ann yang lebih dulu benar**.
2. **YoY melambat = "disinflasi pasti".** Bisa cuma base effect (bulan pembanding tahun lalu tinggi). Cek dulu 3m-ann & trimmed PCE sebelum menyimpulkan.
3. **"Core turun = bagus, selalu."** Salah konteks: core yang anjlok SAAT growth lemah = permintaan runtuh (kuadran falling×cooling), bukan kabar baik.
4. **MICH naik dibaca "inflasi pasti naik".** MICH itu opini konsumen dengan bias bensin — yang bermakna perubahan arahnya, bukan satu bulan naik; dan yang lebih kuat lagi MICH *bersamaan* dengan breakeven naik.
5. **Breakeven naik dibaca "ekspektasi naik" mentah-mentah.** Breakeven bercampur premium risiko/panik. Selalu baca berdampingan MICH dan 5y5y (`T5YIFR`).
6. **WTI naik → "CPI pasti naik bulan ini".** WTI early-warning, bukan komponen mekanik: ada delay pass-through dan bobot. Fungsi WTI + OVX di brief adalah mengatur kewaspadaan, bukan menjanjikan angka.
7. **Nowcast dibaca sebagai konsensus (atau sebaliknya).** Dua hal berbeda: model statistik vs rata-rata prediksi ekonom. Justru *gap* keduanya yang menentukan ruang kejutan di CPI-week.
8. **"COOLING" dibaca "harga turun".** COOLING = laju kenaikan melambat (disinflasi), bukan deflasi. Harga masih mahal — hanya naiknya lebih pelan.
9. **Menunggu brief pagi hari-H untuk angka rilis hari itu.** Rilis jam 19:30/20:30 WIB; brief pagi memuat skenario pra-rilis. Angka aktual muncul di brief H+1 (dan surprise-nya di blok I).
10. **Lupa bahwa state = arah, bukan level.** Level di atas target + arah turun tetap "COOLING" — dua informasi (level vs target, arah momentum) harus dibaca terpisah sebelum menyimpulkan sikap Fed.
11. **Percaya angka bulanan mentah tanpa cek vintage.** Faktor musiman direvisi tahunan; MoM yang kemarin Anda catat bisa bergeser di riwayat (raw append-only + vintage menangani ini — selalu lihat kapan angka diambil).

---

## 6. Keterkaitan spesifik per instrumen Anda

Mekanisme umum dulu, baru per instrumen. Kunci: **inflasi menggerakkan instrumen Anda hampir seluruhnya lewat dua relai — ekspektasi Fed (→ nominal rate, → real yield blok B) dan dolar.** Hubungan emas-inflasi yang populer ("inflasi naik = beli emas") itu setengah benar dan sering terbalik jangka pendek: inflasi *yang memaksa Fed mengetat* menaikkan real yield → justru headwind emas. Kombinasi emas: **inflasi menurun TANPA resesi** (disinflationary growth) — real yield turun, dolar melemah, growth masih ada.

| Instrumen | Kanal utama dari blok C | Yang perlu diperhatikan |
|---|---|---|
| **XAUUSD** | Inflasi → ekspektasi Fed → real yield (blok B, driver #1) | Kuadran steady×cooling = ramah; reakselerasi yang memicu ekspektasi hike = tekanan lewat RY. CPI-week = jendela vol tertinggi bulanan — pakai nowcast utk skenario |
| **XAGUSD** | Beta lebih tinggi ke faktor yang sama dgn XAU + sisi industri | Kejutan CPI yang menggerakkan XAU biasanya menggerakkan XAG lebih besar dua arah — sizing CPI-week mesti lebih kecil |
| **XPTUSD** | Kombinasi logam moneter + industri (autokatalis) | Sensitif ke kuadran risk-on/off secara keseluruhan; blok C memberi sumbu kuadran, bukan trigger langsung |
| **XCUUSD** | Copper = logam growth (driver utamanya China/US PMI, blok D & §8) | Relevansi blok C via kuadran: disinflationary growth mendukung demand; stagflasi (falling×reaccel) paling buruk |
| **BTC / ETH** | Risk asset + narasi "inflasi hedge" jangka panjang | Praktisnya: CPI panas → ekspektasi ketat → risk-off bersama equities; disinflationary growth = lingkungan ramah. Driver harian lebih dominan di blok E/H (net liq, flow, funding) |
| **US100 / US500 / US30** | Valuasi via rate; US100 paling rate-sensitif | Steady×cooling = sweet spot (multiple melebar tanpa resesi); reaccel = tekanan yield & DXY → US100 paling terpukul |
| **EURUSD & majors** | US CPI relatif vs inflasi EA (HICP, blok D non-US) → differensial rate (blok A) | CPI AS panas → DXY bid → EURUSD turun; perhatikan rilis HICP di kaki sebelah |
| **DXY / crosses (XAUEUR, XAGGBP, XAUGBP)** | Dua kaki: kaki USD dari CPI AS; kaki EUR/GBP dari HICP/CPI UK | XAUEUR bergerak saat salah satu kaki punya rilis inflasi sendiri — cek kalender kedua zona; XAGGBP/XAUGBP dihitung sintetis (§10) dari komponen yang masing-masing kena rilis AS & UK |

Pola praktis untuk swing Anda: blok C jarang memberi *trigger entry* harian; ia menentukan **arah angin** (regime + kuadran) dan **kalender risiko** (CPI/PCE week). Trigger teknis/positioning biasanya datang dari blok B, F, G, H.

---

## 7. Yang bisa salah: degradasi, kualitas data, keterbatasan

### 7.1 Mode degradasi per sumber (apa yang terjadi kalau sumber mati)

| Sumber mati | Konsekuensi | Perilaku sistem |
|---|---|---|
| FRED (CPI, MICH, WTI, trimmed) | Primer semua series inti | CPI → sekunder FMP (`CPI`/`inflationRate` — beda unit, cross-val ketat); MICH → FMP `consumerSentiment` (cek makna dulu, §3.4); WTI → backdoor CME CL (gray, basis futures-vs-spot); trimmed → tanpa sekunder |
| FRED (PCEPILFE) | **Tidak ada fallback — dipastikan audit** | Baris basi + flag di brief; pilar dihitung dari anggota hidup; tidak pernah dipakai diam-diam (§0.2 freshness) |
| Cleveland nowcast | Satu-satunya sumber estimasi harian | Baris nowcast hilang dari brief → CPI-week tinggal konsensus (ruang surprise tak terukur) — turunkan sizing event |
| Backdoor CME CL | Sekunder WTI hilang | WTI tetap dari FRED; tak ada aksi lain |

Aturan umum berlaku: series resmi single-source diizinkan **asal** freshness check aktif — data lewat jadwal rilis tanpa update ditandai basi, bukan dipakai lama diam-diam.

### 7.2 Kualitas data & jebakan teknis

- **Bedakan unit sejak registry:** `CPIAUCSL` = indeks level; `MICH` = persen; FMP sekunder = persen jadi. `value_format` ada untuk mencegah mixup (kasus klasik: membandingkan indeks 320 dengan 3.2%).
- **Nowcast parser rapuh:** FusionCharts JSON bukan API resmi berkontrak — tanggal MM/DD + tahun dari subcaption, elemen terakhir per bulan. Dilindungi uji parser-vs-halaman-web (F1) + alarm schema-fingerprint saat struktur berubah. Nowcast yang berubah antar hari itu **fitur** (estimasi menyempit), bukan bug — jangan treat sebagai "revisi kotor".
- **Revisi vintage:** CPIAUCSL masuk mekanisme ALFRED (§18.2) — pembaruan faktor musiman tahunan menggeser riwayat SA → 3m-ann historis ikut bergeser. Sistem menyimpan vintage; Anda harus sadar backtest pakai angka "sebagaimana diketahui saat itu" (`release_ts`).
- **Rumus 3m-ann:** lihat catatan pangkat 4 vs 4/3 di §4.1 — wajib direkonsiliasi lewat fixture hitung-tangan SEBELUM sinyal dianggap hidup.

### 7.3 Keterbatasan konseptual (yang tidak bisa diperbaiki dengan data lebih)

1. **Blok C = AS saja.** Inflasi EA (HICP) dan UK hidup di blok D sub-blok non-US — untuk crosses, dua blok harus dibaca bersama.
2. **Frekuensi bulanan + lag.** CPI ~2 minggu, PCE ~4 minggu, trimmed lebih telat lagi. Segala sesuatu harian di blok ini (WTI, nowcast, breakeven di blok B) ada justru untuk menutup lubang itu — tapi tetap bukan pengganti angka resmi.
3. **Nowcast tetap model.** Di titik balik tak terduga (kejutan akhir bulan) ia bisa meleset — itu sebabnya ia dipasangkan dengan konsensus, bukan menggantikannya.
4. **Trimmed membersihkan noise — juga bisa menelan sinyal.** Lonjakan energi yang benar-benar menetap butuh beberapa bulan sebelum lolos ke trimmed (setelah menular ke komponen lain). Headline + WTI tetap perlu dipantau berdampingan.
5. **Ekspektasi terukur ≠ ekspektasi sebenarnya.** MICH (survei kecil, bias bensin) dan breakeven (tercampur premium) dua-duanya proksi. Anchor sesungguhnya tidak pernah terobservasi langsung.
6. **Hubungan inflasi→aset tidak mekanis.** Efeknya selalu lewat relai Fed/real-yield/dolar, dan relai itu bisa diputus (mis. Fed yang memilih mengabaikan lonjakan sementara). Karena itu bobot C (0.15) sengaja di bawah A dan B — baca blok ini sebagai *bahan bakar*, bukan *kemudi*.

---

## 8. Tantangan desain yang sah untuk Anda ajukan (dan di mana jawabannya hidup)

Anda berhak menantang setiap keputusan blok ini. Daftar pertanyaan yang paling layak diajukan, plus di mana kebenarannya diuji:

1. **"Kenapa bobot pilar C cuma 0.15, lebih kecil dari A dan B?"** — Keputasan formula §11.1 (kalibrasi bisa berubah, dihitung ulang dari raw). Argumennya di §1 dokumen ini. Tantang dengan data saat F4: uji apakah z-pilar C menambah daya beda regime di luar apa yang sudah ditangkap A+B.
2. **"Rumus 3m-ann pangkat 4/3 vs 4 — mana yang benar?"** — Ini item verifikasi terbuka yang PENTING (§4.1). Fixture hitung-tangan wajib di gerbang F1; jangan biarkan sinyal hidup sebelum pangkatnya merekonsiliasi dengan contoh output brief.
3. **"Kenapa PCE core single-source tanpa fallback?"** — Bukan pilihan malas: fallback FMP terbukti putus saat audit (§16/DATA-SPEC). Tantangan yang konstruktif: cari sumber sekunder resmi lain (mis. BEA langsung) dan usulkan masuk registry lewat proses biasa.
4. **"Kenapa MICH, padahal konsumen bias?"** — Karena dia satu-satunya suara *rumah tangga* di koor ekspektasi (breakeven = suara pasar; keduanya saling mengoreksi bias). Kalau dirasa kurang, kandidat yang sudah teridentifikasi di spec adalah model Cleveland `EXPINF1YR/10YR` (§18.4 nice-later) — usulkan naik prioritas.
5. **"Kenapa EA/UK inflasi tidak di blok C?"** — Keputusan struktur: blok C = inflasi AS; non-US (HICP EA, CPI UK, PMI) dikelola blok D. Konsekuensinya untuk crosses: dua blok harus dibaca bersama (§6).
6. **"Kenapa tidak ada PPI / indeks input produksi?"** — Sederhana: tidak ada di spec v1.4. Bukan berarti tidak berguna (PPI = kanal hulu CPI), tapi jangan harap barisnya muncul sebelum ada keputusan desain baru + verifikasi sumber.
7. **"Sekunder FMP `consumerSentiment` benar-benar menggantikan MICH?"** — Belum terbukti sama makna (kemungkinan indeks kepercayaan, bukan ekspektasi inflasi). Ini harus lolos gerbang cross-val F0 dulu (§3.4).

Pola umumnya: semua jawaban berujung ke registry + gerbang verifikasi (F0) + fixture (F1), bukan ke opini. Itulah desain sistemnya — keputusan boleh ditantang kapan pun selama tantangannya diuji lewat jalur yang sama.

---

*Tautan untuk menelusuri sendiri: `arkwatch explore block C` (nilai + state + freshness semua series), `arkwatch explore series FRED:CPIAUCSL --trace` (vintage & cross-val), `arkwatch explore signal INFL_STATE --trace` (dari indeks mentah → MoM/3m-ann → state → skor).*
