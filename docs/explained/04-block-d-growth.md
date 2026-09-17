# Blok D — Pertumbuhan Ekonomi (Growth)

> Seri edukasi ark-watch — ditulis untuk pembaca non-finance: setiap istilah dijelaskan dari nol dengan analogi sehari-hari, tanpa meremehkan.
> Rujukan teknis: [DATA-SPEC.md](../DATA-SPEC.md) §4 (peta series), §18.3 (pengayaan ADS/CFNAI/H.8/WGT), §11 (sinyal komposit), §0 (prinsip primer-sekunder); [BUILD-PLAN.md](../BUILD-PLAN.md) §3 "BLOK D — Growth" (transform terkunci) dan §4 (kedalaman backtest).
> Angka bertanda **(contoh nilai Agt-2026)** diambil dari brief-contoh spec 2026-08-29 dan tabel golden-anchor F0 — bukan karangan. Panduan baca yang hanya konteks pasar umum (bukan angka spec) ditandai eksplisit.

---

## 1. Kenapa blok ini ada — pertumbuhan ekonomi itu "pasang laut"-nya

### 1.1 Latar untuk awam

Kalau inflasi (Blok C) adalah *harga sembako*, pertumbuhan ekonomi adalah *apakah tetangga sekompleks masih punya kerja dan gaji*. "Pertumbuhan" (growth) = seberapa cepat ekonomi memproduksi barang+jasa dari kuartal ke kuartal. Harga semua instrumen yang Anda pegang — gold, silver, copper, BTC, indeks, FX — pada dasarnya adalah *taruhan tentang masa depan pertumbuhan ini*:

- Pertumbuhan **panas** → perusahaan untung besar (indeks naik), bahan baku laris (copper naik), tapi pasar mulai takut The Fed menahan suku bunga tinggi lebih lama (real yield naik → **headwind gold**, lewat Blok B).
- Pertumbuhan **mendingin tajam (resesi)** → indeks dan copper tertekan, tapi ekspektasi pemangkasan suku bunga (rate cut) muncul → real yield turun → **tailwind gold** (gold juga "safe haven": dibeli saat takut).
- Pertumbuhan **moderat + inflasi menurun** → kombinasi paling ramah untuk mayoritas book (di brief disebut kuadran *"disinflationary growth"* — **contoh nilai Agt-2026**: `growth STEADY × inflasi COOLING`).

Analogi utama: **ekonomi adalah pasang laut, harga aset adalah perahu di atasnya**. Perahu bisa olah gerak (positioning, sentimen — Blok F/G), tapi arah pasang (growth) menentukan apakah olah gerak itu mudah atau melawan arus.

### 1.2 Leading, coincident, lagging — rem, speedometer, spion

Blok D sengaja mencampur data dengan *waktu reaksi* berbeda. Bayangkan Anda berkendara di jalan tol:

| Tipe | Analogi mobil | Artinya | Anggota di Blok D |
|---|---|---|---|
| **Leading** (memimpin) | **Lampu rem mobil di depan** menyala *sebelum* kecepatan Anda berubah — kalau Anda menunggu mobil depan benar-benar melambat, terlambat | Berubah duluan sebelum ekonomi berubah; bahan *persiapan* | SLOOS (standar kredit bank), initial claims (leading labor), H.8 impulse kredit, PMI (order baru), sub-blok China |
| **Coincident** (bersamaan) | **Speedometer** — bilang kecepatan *sekarang*, akurat tapi baru tahu saat kejadian | Merekam kondisi bulan berjalan; bahan *konfirmasi* | ADS (harian!), CFNAI, payrolls, industrial production, retail sales, level ISM |
| **Lagging** (terlambat) | **Kaca spion** — memperlihatkan yang *sudah lewat*; berguna untuk memastikan, bukan mengantisipasi | Baru berubah setelah ekonomi berubah; bahan *pemakluman* | Tingkat pengangguran (puncaknya biasanya setelah resesi berakhir), Wage Growth Tracker, Sahm (alarm yang bunyi saat resesi *sudah dimulai*, bukan prediksi) |

Kenapa dicampur? Karena satu angka tidak cukup: leading bisa *false alarm* (lampu rem menyala tapi mobil depan hanya mengerem pelan), coincident terlambat untuk positioning swing 3–10 hari. Brief membacanya sebagai satu cerita: "apakah lampu rem, speedometer, dan spion mulai menunjuk arah yang sama?"

Satu catatan soal PMI yang muncul di dua baris: **sub-komponen ISM *new orders* (order baru) bersifat leading** — pesanan mendahului produksi — sedangkan **level ISM headline mencerminkan bulan berjalan (coincident-ish)**. Itu sebabnya PMI tercantum di dua kolom dengan peran berbeda, bukan tumpang tindih kelalaian.

### 1.3 Peran di mesin komposit

Blok D memberi makan dua mesin (spec §11):

1. **Regime score** (−2…+2): pilar Growth = rata-rata z-score anggotanya; **bobot D = 0,15** dari total skor.
2. **Kuadran Dalio**: sumbu growth = momentum pertumbuhan (lihat formula mayoritas-suara di §4.3) dikali sumbu inflasi (Blok C) → 4 kuadran → dipetakan ke return historis tiap instrumen Anda.
3. Bonus: **dollar smile kiri** memakai PMI non-AS ("dolar naik **dan** PMI ex-US jatuh") — sub-blok non-US di bawah adalah pemasoknya.

---

## 2. Glosarium

| Istilah | Arti untuk awam | Kenapa penting untuk book Anda |
|---|---|---|
| **Resesi** | Ekonomi menyusut nyata berbulan-bulan; definisi resmi ditetapkan NBER (komite penanggalan siklus AS), bukan "dua kuartal negatif" | Menentukan regime: gold vs indeks vs copper bergerak berlawanan arah |
| **Initial claims** | Jumlah orang yang *baru* mendaftar tunjangan pengangguran minggu ini | Data tenaga kerja tercepat (mingguan) — radar dini pemecatan massal |
| **4-week MA** | Rata-rata 4 minggu terakhir dari claims | Satu minggu bisa berisik (libur); MA = "denyut nadi", bukan "kedipan" |
| **Unemployment rate** | Persen angkatan kerja yang menganggur | Coincident/lagging; bahan Sahm |
| **Payrolls / NFP** | Bersih jumlah pekerjaan non-pertanian bulanan (jutaan bisnis disurvei) | Momentum pasar kerja; penggerak indeks & DXY di hari rilis |
| **Sahm rule** | Aturan: kalau rata-rata 3-bulan pengangguran naik ≥ 0,50 poin dari terendah 12 bulan → resesi (hampir) selalu sudah dimulai | Sinyal "resesi berjalan" yang sederhana dan sulit gagal-palsu; nilai kini **(contoh Agt-2026): −0,03 → "tidak terpicu"** |
| **GDP** | Nilai total produksi ekonomi per kuartal | Ukuran pertumbuhan resmi — tapi terbit telat (±1 bulan setelah kuartal berakhir) |
| **Nowcast / GDPNow** | Model Atlanta Fed yang *memperkirakan GDP kuartal berjalan dari data parsial* (claims, retail sales, PMI, dsb.) | "Foto kilat" sebelum foto resmi dicuci; sumbu growth kuadran |
| **PMI** | Survei manajer pembelian: pertanyaan sederhana "bulan ini lebih baik/lebih buruk/sama?" dirangkum jadi satu angka | Cepat (awal bulan) dan luas; garis 50 memisahkan ekspansi vs kontraksi |
| **Garis 50** | PMI > 50 = mayoritas menjawab "lebih baik" (ekspansi); < 50 = kontraksi | **(contoh Agt-2026): ISM 48,2 = kontraksi; Caixin mfg 49,8 = kontraksi tipis** |
| **ISM** | Institute for Supply Management — lembaga survei PMI versi AS (mfg + services) | PMI AS kanonik; masuk brief lewat level + surprise |
| **Caixin vs NBS** | Dua PMI China: Caixin (swasta, berat perusahaan kecil-ekspor) vs NBS (resmi, berat BUMN besar) | Demand sisi copper; dua-duanya dipakai saling cek |
| **SLOOS** | Survei Fed ke pejabat kredit bank: "kalian memperketat/melonggarkan standar pinjaman?" | Keran kredit = bahan bakar ekonomi; survei keran memimpin ekonomi 2–4 kuartal |
| **H.8** | Laporan Fed tentang aset & pinjaman bank (mingguan) | Bukti *perbuatan* bank, bukan cuma kata-kata — jembatan antar kuartal SLOOS |
| **ADS index** | Indeks Philly Fed harian: kondisi bisnis hari ini vs tren normal | Coincident tercepat di seluruh mesin; bahannya backtest sejak 1960 |
| **CFNAI** | Indeks Chicago Fed bulanan: 85+ data dirangkum jadi satu angka aktivitas | Coincident bulanan paling komprehensif; MA3-nya punya trigger resesi |
| **Wage Growth Tracker (WGT)** | Tracker Atlanta Fed: median kenaikan gaji orang yang *gaji barunya berubah* | Upah = biaya perusahaan + daya beli; jembatan ke inflasi (Blok C) |
| **USDCNY** | Harga yuan China per dolar AS | Termometer siklus China (dikelola PBoC) → copper |
| **HICP** | "CPI-nya Eropa" (harmonized, metodologi seragam antarnegara EA) | Menentukan jalur ECB → kaki EUR dari XAUEUR |
| **Probit / probabilitas resesi** | Model statistik yang mengubah indikator (mis. kemiringan kurva yield) jadi peluang resesi 0–100% | Cross-check; angka tunggal yang gampang salah-baca (lihat §5) |
| **Z-score** | "Berapa jauh dari rata-rata, diukur pakai satuan kebiasaan naik-turunnya" — nilai ujian 80 beda makna di kelas rata-rata 78 vs 60 | Bahasa bersama seluruh pilar agar bisa dirata-rata (lihat §4.1) |
| **Momentum** | Arah perubahan N periode (turun-naiknya, bukan levelnya) | "Claims 203K" (level) berbeda dari "MA turun 3 minggu" (momentum) |
| **Percentile** | Posisi angka di liga historisnya: "dari 100 pengamatan, ia di peringkat ke-8" | Untuk membandingkan apalagi yang tidak punya ambang alami |
| **As-of join** | Saat mencampur data mingguan+bulanan+kuartalan, hanya pakai angka yang *sudah dirilis* pada tanggal itu | Anti "mencla-mencala masa depan" (look-ahead) — kata kunci: `release_ts` |
| **Vintage / revisi** | Angka yang sama bisa diubah penerbitnya beberapa pekan kemudian; "vintage" = versi angka saat itu | Angka brief lama ≠ angka final; klaim ICSA/PAYEMS/GDPNOW masuk daftar revisi mingguan ALFRED |
| **Indeks difusi** | Indeks yang merangkum jawaban "naik/turun/sama" banyak responden jadi satu angka (50 = netral) | Format PMI/ISM: membaca *arah* mayoritas, bukan besarannya dalam rupiah |
| **Control group (retail sales)** | Subset retail sales yang paling masuk perhitungan PCE (buang mobil, bensin, bahan bangunan) — versi "inti"-nya | Bahan input GDPNow; less noisy daripada headline |

---

## 3. Peta data — per series, siapa menerbitkan, kenapa dipilih, cara bacanya

> Aturan umum (spec §0.1): sumber resmi (FRED/lembaga) boleh satu-sumber asal freshness-check aktif; yang lain wajib primer+sekunder. Tier: T0 institusi, T1 langganan (FMP/EODHD).

### 3.1 Tenaga kerja (labor)

| Seri (ID) | Apa sebenarnya | Siapa & kapan | Kenapa dipilih / alternatif ditolak | Cara baca angka |
|---|---|---|---|---|
| Initial claims `ICSA` | Orang yang minggu ini *baru* mendaftar tunjangan pengangguran AS (minggu berakhir Sabtu) | DOL/ETA, **tiap Kamis 08:30 ET** = **Kamis 19:30 WIB saat EDT / 20:30 WIB saat EST** (konversi sadar-musim, spec header) | Frekuensi tertinggi dari semua indikator tenaga kerja; alternatif bulanan terlalu lambat untuk swing | Rendah & turun = pemecatan minim → labor ketat **(contoh Agt-2026: 203K, cons 208K → "labor ketat")**; lonjakan beruntun = radar resesi. Panduan umum (bukan angka spec): <220K = ketat, >300K = deteriorasi serius |
| Unemployment `UNRATE` | % angkatan kerja tanpa kerja (survei rumah tangga) | BLS, Jumat pertama tiap bulan 08:30 ET | Input Sahm; coincident-lagging | Level + arah; kenaikan cepat lebih penting daripada levelnya |
| Payrolls `PAYEMS` | Perubahan bersih jumlah pekerjaan (survei bisnis) | BLS, bersama UNRATE | Momentum bulanan; penggerak pasar di hari rilis | Dibaca Δ3m (bukan satu bulan); panduan umum: +150K/bulan ≈ titik jaga agar pengangguran tak naik |
| Sahm `SAHMREALTIME` | Versi *realtime* (tanpa revisi masa depan) dari indikator Sahm | FRED, bulanan, dari UNRATE | Realtime = jujur untuk backtest; toleransi vs hitungan-manual ±0,05 karena revisi vintage (BUILD-PLAN FIX v1.1) | **>0,50 = resesi (hampir selalu sudah berjalan)**; (contoh Agt-2026: −0,03 → tidak terpicu) |

**Kenapa claims keluar "Kamis malam WIB" dan itu penting**: pekan data berakhir Sabtu; DOL merilis Kamis 08:30 ET — di WIB itu Kamis malam (19:30 EDT / 20:30 EST). Mesin menariknya di fetch FRED 06:00 WIB berikutnya → masuk **brief Jumat pagi**, sehari setelah rilis, jauh sebelum data bulanan manapun. Golden anchor F0: `ICSA = 203.000 @ 2026-08-22` (nilai pekan itu dikunci sebagai kunci kebenaran pipeline).

### 3.2 Aktivitas riil & indeks komposit cepat

| Seri (ID) | Apa sebenarnya | Siapa & kapan | Kenapa dipilih / alternatif ditolak | Cara baca |
|---|---|---|---|---|
| Industrial production `INDPRO` | Output pabrik-tambang-utilitas (indeks, bukan %) | Fed Board (G.17), pertengahan bulan, data bulan lalu | Puls industri riil → logam industri | Baca momentum; IP turun beruntun = sinyal awal resesi manufaktur |
| Retail sales `RSAFS` | Penjualan ritel (nilai, disesuaikan musim) | Census, pertengahan bulan | Konsumsi = mesin terbesar ekonomi AS (± dua pertiga — konteks umum) | Momentum; angka control-group dipantau sebagai bahan GDPNow |
| **ADS** (`ADS_Index_Most_Current_Vintage.xlsx`) | Indeks harian kondisi bisnis, dirancang 0 = pertumbuhan tren normal | Philly Fed, **harian, seri 1960→kini, 24.282 baris** (pengayaan §18.3; fetch wajib `curl_cffi`-chrome) | Satu-satunya indikator growth *harian*; kedalaman 60+ tahun → bahan backtest surrogate | **0 = normal (bukan "nol persen")**; positif = di atas tren, negatif = di bawah tren; negatif dalam-dalam = resesi |
| **CFNAI / CFNAIMA3** | Komposit 85+ indikator aktivitas, skala mirip ADS | Chicago Fed, bulanan (rilis ±3–4 pekan setelah bulan berakhir) | Coincident bulanan paling lengkap; **MA3 < −0,70 = trigger resesi historis** (spec §18.3); seri 1967→ (bahan backtest) | Sama seperti ADS: 0 = tren; yang dibaca flag MA3 dan Δ-nya |

Alternatif yang **ditolak** (spec §18.5): OECD Composite Leading Indicator — data China telat 9–10 bulan dan API-nya membalas blob 4,9MB apa pun filternya. Untuk label resesi backtest dipakai **NBER resmi** (HTML bersih, 42 baris peak/trough) menggantikan inferensi `USREC`.

### 3.3 PMI — survei manajer pembelian

| Seri | Apa sebenarnya | Siapa & kapan | Kenapa dipilih | Cara baca |
|---|---|---|---|---|
| ISM Manufacturing & Services | Survei >400 manajer pembelian AS: "produksi/order/tenaga kerja lebih baik?" → indeks difusi | ISM: mfg hari-kerja-1, services hari-kerja-3 tiap bulan (10:00 ET) | Masuk via **kalender** (Blok I) dengan konsensus → dipakai level + surprise | **Garis 50**; (contoh Agt-2026: "ISM 48,2 (cons 48,8) kontraksi" — level di bawah 50 *dan* di bawah ekspektasi = dua pukulan sekaligus). Services > mfg dalam porsi ekonomi AS — jangan menilai AS cuma dari manufaktur |

### 3.4 Nowcast & probabilitas resesi

| Seri (ID) | Apa sebenarnya | Siapa & kapan | Kenapa dipilih | Cara baca |
|---|---|---|---|---|
| GDP nowcast `GDPNOW` | Estimasi Atlanta Fed atas GDP kuartal *berjalan*, di-update tiap ada rilis data input | FRED (terverifikasi ada) → sekunder XLSX Atlanta Fed; **refetch event-driven** (spec §13) | Sumbu growth kuadran; mengisi kekosongan antara rilis GDP resmi yang telat | Yang dibaca **Δ antar update**, bukan cuma level **(contoh Agt-2026: "GDPNow Q3 2,8% (dari 2,6%)" = direvisi naik 0,2pp → momentum growth positif)**; awal kuartal noisnya besar |
| Probabilitas resesi `smoothedUSRecessionProbabilities` | Output model statistik → peluang resesi (%) | FMP → fallback **probit kurva internal** (kemiringan 3M10Y dari Blok A) | Cross-check terhadap Sahm/CFNAI | % + arah; jangan dibaca sebagai ramalan tunggal — ini peluang model, bukan takdir |

### 3.5 Kanal kredit (kenapa survei bank *memimpin*)

Logika ekonominya: bank = **keran air**, ekonomi = **sawah**. Kalau petugas keran mengecilkan kran (standar kredit diperketat), air (pinjaman) baru sampai ke sawah berbulan-bulan kemudian — tapi *arahnya* sudah pasti. Karena itu survei keran memimpin ekonomi nyata 2–4 kuartal, dan Dalio-quadrant secara eksplisit memakainya.

| Seri (ID) | Apa sebenarnya | Siapa & kapan | Kenapa dipilih | Cara baca |
|---|---|---|---|---|
| SLOOS `DRTSCILM` | Net % bank yang *memperketat* standar kredit usaha (C&I) bagi perusahaan besar-menengah | Fed Board (SLOOS), **kuartalan** | Leading sejati (kanal kredit); anggota kuadran | Negatif = melonggar **(output brief: "standar kredit melonggar")** = bahan bakar growth; positif dalam = menjepit. Frekuensi kuartalan = lambat — makanya ada pendamping: |
| H.8 `TOTBKCR` + `TOTLL` | Total kredit & pinjaman bank seluruh sistem | Fed Board (H.8), **mingguan** (§18.3) | Bukti *perbuatan* bank tiap pekan — jembatan antar kuartal SLOOS | Baca **impulse YoY** (akselerasi/deselerasi pertumbuhan kredit); kontraksi kredit berjalan = drain klasik pra-resesi |

### 3.6 Upah

| Seri | Apa sebenarnya | Siapa & kapan | Kenapa dipilih | Cara baca |
|---|---|---|---|---|
| Wage Growth Tracker (WGT) | Median kenaikan gaji orang yang gajinya barusan berubah, + potongan job-switcher & kuartil upah | Atlanta Fed, XLSX bulanan, **seri 1997→, 19 sheet** (§18.3) | Menghubungkan pasar kerja (D) dengan inflasi jasa (C); lagging | Median (bukan rata-rata) → tahan terhadap outlier; bandingkan dengan inflasi: upah > inflasi = daya beli riil naik |

### 3.7 Sub-blok non-US — kenapa ekonomi asing menggerakkan instrumen Anda

Prinsip: instrumen non-dolar Anda punya **dua kaki**. XAUEUR = emas × nilai EUR; kalau Eropa memanas datanya, EUR menguat → XAUEUR *turun* meski emas datar. Copper bahkan lebih China daripada AS: China menyerap porsi terbesar tembaga dunia (sering dikutip sekitar separuh — konteks sektor, bukan angka spec), sehingga PMI China lebih relevan untuk XCUUSD daripada IP AS.

| Seri (ID) | Apa sebenarnya | Siapa & kapan | Kenapa dipilih | Cara baca |
|---|---|---|---|---|
| USDCNY `DEXCHUS` | Harga yuan per dolar | FRED (H.10), harian | Termometer siklus China + PBoC → copper | **Naik = yuan melemah** = permintaan dalam negeri lemah/ekspor dijaga; **(contoh Agt-2026: "USDCNY stabil → tidak ada shock China")**. Ingat: kurs dikelola — "stabil" bisa berarti intervensi |
| China PMI (Caixin & NBS) | Dua survei PMI China | Caixin awal bulan berikutnya; NBS resmi akhir bulan berjalan | Demand sisi copper; dua sumber saling cek | (contoh Agt-2026: "Caixin mfg 49,8 → kontraksi tipis" → netral-tilt-negatif untuk XCUUSD) |
| EA HICP + PMI (`CP0000EZ19M086NEST` / ECB `ICP/M.U2.N.000000.4.ANR`) | Inflasi zona euro + pertumbuhannya | Eurostat (flash akhir bulan), PMI via kalender | Menentukan jalur ECB → kaki EUR dari XAUEUR/XAGEUR & EURUSD | (contoh Agt-2026: "EA HICP 2,1% stabil" → kaki EUR diam, gerak XAUEUR datang dari kaki XAU). HICP ≠ inflasi satu negara |
| UK PMI + CPI | Pertumbuhan & inflasi Inggris | via kalender, FMP/EODHD `country=GB` | Kaki GBP dari XAGGBP/XAUGBP & GBPUSD | Relatif terhadap target 2% BoE → jalur BoE (Blok A) |

Sumber kalender non-US: FMP actuals → EODHD `country=CN/EA/GB` (union), lewat mesin kalender Blok I.

---

## 4. Logika hulu-ke-hilir — dari angka mentah ke regime

### 4.1 Konsep transform, dijelaskan dulu

1. **Rata-rata bergerak (4wk MA)** — klaim mingguan seperti denyut jantung: berdebar satu ketukan belum artinya apa-apa. MA-4 meratakan kedip agar pola terlihat. Spec membaca *level + slope MA*.
2. **Z-score** = `(x − rata-rata) / simpangan-baku`, window **5 tahun sesuai frekuensi** (D: 1260 obs; W: 260; M: 60), σ populasi. Bahasa awam: "angka ini berapa 'londehan' dari normal, diukur pakai satuannya sendiri". z +2 = sangat tinggi menurut sejarahnya sendiri. Kalau data < 80% window → state `INSUFFICIENT` (mesin menolak mengarang).
3. **Momentum** = perubahan N periode. Untuk series bulanan momentum-nya bulanan; untuk harian dalam hari-trading. Level menjawab "di mana kita", momentum menjawab "ke mana kita bergerak".
4. **Percentile** = peringkat di liga historis (window sama). Dipakai kalau tidak ada ambang alami.
5. **Majority vote** = 4 hakim (lihat §4.3) masing-masing memberi suara memanas/mendingin; suara terbanyak menang; seri = FLAT. Sistem ini tahan terhadap satu indikator ngaco.
6. **As-of join (`release_ts`)** = saat menggabung claims (mingguan) + SLOOS (kuartalan) + ADS (harian), mesin hanya memakai angka yang *sudah publik* pada tanggal itu — sama seperti Anda tidak boleh memakai koran besok untuk keputusan hari ini. Ini prinsip anti look-ahead yang di-test ulang di F4.

### 4.2 Pipeline per series (BUILD-PLAN §3 "BLOK D", terkunci)

| Seri | Transform | Output/state di brief |
|---|---|---|
| ICSA | 4wk-MA + slope | "claims 203K, MA turun 3 minggu" |
| ADS | dipakai langsung (harian) | puls growth harian |
| CFNAI | MA3; flag bila **MA3 < −0,70** | flag resesi historis |
| GDPNOW | **Δ antar update** | "GDPNow Q3 2,8% (dari 2,6%)" |
| Sahm | langsung; tol. hitungan-manual ±0,05 (vintage) | "tidak terpicu (−0,03)" |
| UNRATE/PAYEMS/INDPRO/RSAFS | z (level) + momentum → state | "Growth=STEADY" dst. |
| SLOOS | level → suara kuadran | "standar kredit melonggar" |
| H.8 | impulse YoY | pendamping SLOOS |
| Claims & ISM **surprise** | `z=(actual−consensus)/σ` → mesin surprise Blok I (decay 90 hari) | "Claims 203K (cons 208K) → surprise +" |
| Non-US | level/state per negara | baris EA/UK/China di implikasi book |

### 4.3 Sumbu growth kuadran Dalio

`growth_mom = majority-vote { ΔGDPNow, trend-ICSA, SLOOS, ΔCFNAI }` — mayoritas menang, seri = FLAT.

Catatan transparansi (bahan menantang desain): spec §11.2 versi lama menyebut anggota {GDPNowΔ, ICSA, SLOOS, **PMI**}; BUILD-Plan v1.1 (implementasi, pasca-pengayaan v1.3) memakai **CFNAIΔ** sebagai pemilih ke-4 — CFNAI dinilai lebih komposit dan historinya panjang, sedangkan PMI tetap hadir lewat jalur surprise + level di baris brief. Kalau suatu hari kalibrasi mengganti lagi, itu wilayah parameter, bukan perubahan konsep.

### 4.4 Kontribusi ke regime score

Pilar D = **rata-rata z anggotanya** (mixed-frequency via as-of join) → state flip di ±0,5 → masuk skor total dengan **bobot 0,15** (A .20, B .20, C/D/E/F .15). Contoh rantai **(nilai Agt-2026)**: claims 203K + MA turun, GDPNow naik 2,6→2,8%, SLOOS melonggar → growth_mom positif-tapi-tidak-ekstrem → "Growth=STEADY"; dikali inflasi COOLING → kuadran "disinflationary growth"; skor regime +1,2 → risk-on.

### 4.5 Jejak lengkap satu angka (contoh claims)

```
pekan berakhir Sab 22-Agt-2026: ICSA raw = 203.000 (golden anchor F0)
→ rilis Kamis 27-Agt 19:30 WIB (EDT), tersimpan dgn release_ts (append-only; revisi via job ALFRED mingguan)
→ 4wk-MA + slope: "MA turun 3 minggu"
→ z-5y (window 260 obs mingguan) → suara pilar D "memanas-tipis"
→ surprise: (203−208)/σ → z negatif-arti-baik → "surprise +" di ESI Blok I
→ pilar D → regime score (bobot 0,15); suara ICSA-trend → kuadran
```

---

## 5. Membaca baris Blok D di brief + jebakan salah-baca

Baris-baris Blok D di brief contoh **(Agt-2026)**:

```text
QUADRANT: growth STEADY × inflasi COOLING → "disinflationary growth"
• Claims 203K (cons 208K) → labor ketat, surprise +
• GDPNow Q3 2.8% (dari 2.6%)
Pilar  : Growth=STEADY
• XCUUSD : China PMI 49.8 tipis — netral
• XAUEUR : gerak dari leg XAU (EA HICP 2.1% stabil)
```

Jebakan yang paling sering menjatuhkan orang:

1. **Reaktif ke satu minggu claims.** Libur nasional (Thanksgiving, 4 Juli) merusak penyesuaian-musim → angka satu minggu melompat tanpa makna. Selalu baca MA+slope dulu.
2. **Menyangka Sahm = prediksi.** Sahm bunyi saat resesi *sudah berjalan* — ia alarm kebakaran, bukan detektor asap. Untuk asap, lihat SLOOS/PMI/ADS. Nilai −0,03 jauh dari 0,50; yang relevan justru *arahnya beberapa bulan*.
3. **Membaca GDPNow sebagai ramalan Atlanta Fed soal suku bunga.** Ia model statistik GDP *rilis*, bukan opini kebijakan; awal kuartal sangat nois. Yang bernilai adalah **Δ antar-update** dan konvergensinya menjelang rilis resmi.
4. **Menganggap "PMI 48,2" buruk tapi selesai.** Ada dua lapis: level (48,2 = kontraksi) *dan* surprise (48,2 vs cons 48,8 = di bawah ekspektasi → kecewa tambahan). Dua-duanya masuk brief lewat jalur berbeda (level → kuadran; surprise → ESI).
5. **Menyamakan ADS/CFNAI = 0 dengan "nol pertumbuhan".** 0 berarti *tren normal* (≈ +2% TAHUNAN, annualized, historis). ADS −1 = ekonomi di bawah tren, belum tentu resesi.
6. **Menunggu MA3 CFNAI −0,70 sebagai sinyal entry.** Trigger itu historis-late by design (MA3 = rata-rata 3 bulan). Perannya mengonfirmasi, bukan memicu posisi.
7. **Lupa SLOOS kuartalan.** Standar kredit Q2 yang melonggar baru terasa di GDP Q3–Q4. Jangan harap reaksi harga instan — dan jangan bingung "standar" dengan "permintaan" (dua pertanyaan berbeda di survei yang sama; kita pakai `DRTSCILM` = standar, perusahaan besar-menengah).
8. **USDCNY "stabil" dibaca bebas-peristiwa.** Kurs ini dikelola PBoC; stabilitas bisa hasil intervensi. Sinyal justru saat ia *bergerak* tajam atau fixing-nya bergeser — itu pernyataan kebijakan.
9. **HICP EA disamakan dengan inflasi Jerman.** XAUEUR peduli zona-euro agregat + jalur ECB, bukan satu negara.
10. **Membandingkan angka brief lama vs baru langsung.** ICSA/PAYEMS/GDPNOW rutin direvisi (job vintage ALFRED mingguan, spec §18.2). Angka yang sah untuk backtest adalah versi *saat itu* (`release_ts`), bukan final.
11. **Dua probabilitas resesi yang beda = mesin rusak?** Bukan — `smoothedUSRecessionProbabilities` (FMP) dan probit-kurva internal memang dua model berbeda; keduanya cross-check, selisih wajar.
12. **Kebalikan arah dolar.** Dolar naik karena PMI ex-US jatuh (smile kiri) maknanya berbeda bagi metals dibanding dolar naik karena data AS panas (smile kanan) — keduanya "dolar kuat", implikasi book tidak sama.

---

## 6. Keterkaitan spesifik per instrumen Anda

| Instrumen | Kanal dari Blok D | Growth memanas | Growth mendingin | Catatan |
|---|---|---|---|---|
| **XAUUSD** | tidak langsung: growth → ekspektasi suku bunga → real yield (Blok B) + safe-haven | headwind tipis (cut menjauh, RY ↑) | tailwind (cut dekat, RY ↓ + haven) | swing: baca *kombinasi* D+B; gold sering justru kuat saat growth STEADY + inflasi COOLING (contoh Agt-2026) |
| **XAGUSD** | dua kepribadian: moneter (ikut gold) + industrial (ikut copper) | demand industri supportive, tapi rate-headwind menahan | terjepit dua sisi bila resesi dalam | baca bareng Blok D-China dan Blok B |
| **XPTUSD** | paling industrial di antara logam mulia (katalis, otomotif) | menguat lebih dulu dari gold saat siklus naik | jatuh lebih dalam saat resesi manufaktur | IP + PMI mfg AS/Eropa relevan |
| **XCUUSD** | paling sensitif growth: China (Caixin/NBS, USDCNY) + IP global | tailwind jelas bila China ekspansi | cedera bila China kontraksi | (contoh Agt-2026: Caixin 49,8 → "netral") |
| **BTC / ETH** | risk-appetite + (lewat D→A) ekspektasi likuiditas | risk-on supportive | sempat risk-off, lalu cut-expectation supportive | jangan baca growth sendirian — selalu dengan Blok E/F |
| **US100/500/30** | paling langsung: laba = fungsi growth | tailwind, apalagi kuadran disinflationary-growth | pressure; US100 paling peka rate jadi paling sensitif saat "panas" | kuadran return-mapping ada di F4 |
| **EURUSD** | growth relatif US-vs-EA + HICP→jalur ECB | AS lebih panas dari EA = USD naik = pair turun | AS lebih cepat lemah = pair naik | sub-blok EA adalah kaki keduanya |
| **GBPUSD / majors** | UK PMI+CPI → BoE; PMI ex-US juga masuk smile dolar | relatif — yang dibaca *selisih* momentum | idem | AUD = proxy risk Asia (Blok G menyimpan positioning-nya) |
| **DXY** | smile: kanan (US panas + rate-diff melebar), kiri (PMI ex-US jatuh), tengah | tergantung kaki mana yang menggerakkan | idem | Blok A `DTWEXBGS` = series-nya; Blok D = penjelas penyebab |
| **XAUEUR / XAGEUR** | kaki EUR = HICP+PMI EA → ECB | EA memanas → EUR kaku → cross tertekan | EA lemah → cross didongkrak kaki EUR | (contoh Agt-2026: HICP 2,1% stabil → gerak dari kaki XAU) |
| **XAGGBP / XAUGBP** | kaki GBP sintetis (`XAGUSD ÷ GBPUSD` — spec §10 sudah dikoreksi ke operator ÷ pada 2026-08-30) | UK CPI/PMI panas → GBP kaku → cross tertekan | idem terbalik | data UK masuk lewat kalender `country=GB` |

---

## 7. Yang bisa salah — degradasi, kualitas, keterbatasan

### 7.1 Mode degradasi per sumber (aturan spec §0 & §11.4)

| Kalau ini mati | Mesin turun ke | Efek di brief |
|---|---|---|
| FRED (claims/UNRATE/PAYEMS/INDPRO/RSAFS/…) | FMP `initialClaims` dst. (sekunder T1) | baris tetap; cross-val |primer−sekunder| > tol → **keduanya dikarantina** + flag (no silent fallback) |
| FRED `GDPNOW` | XLSX Atlanta Fed langsung | tetap jalan; refetch event-driven |
| Kalender FMP (ISM/PMI non-US) | EODHD union (`country=US/CN/EA/GB`) | level tanpa surprise sampai konsensus kembali |
| FMP `smoothedUSRecessionProbabilities` | probit kurva internal (T10Y3M) | label ganti "probit internal" |
| FRED `CP0000EZ19M086NEST` | ECB API `ICP/M.U2.N.000000.4.ANR` | tanpa perubahan semantik |
| ADS XLSX (Philly) | tidak ada sekunder — fetch wajib `curl_cffi`-chrome | ADS basi → flag STALE; kuadran jalan dengan 3 suara sisanya |
| Semua di atas lewat jadwal | freshness-check §0.2 (`series/updates`) | data lewat jadwal tanpa update **ditandai basi**, tidak dipakai diam-diam |

### 7.2 Kualitas data

- **Revisi**: ICSA, PAYEMS, GDPNOW di daftar job vintage ALFRED mingguan — angka berubah setelah rilis; backtest wajib pakai `release_ts`.
- **Libur & musim**: claims dan retail sales rawan distorsi penyesuaian-musim di pekan berlibur; MA-4 adalah pertahanan pertama.
- **PMI = opini, bukan transaksi**: indeks difusi menjawab "lebih baik/kah?", bukan "berapa rupiah?". Level 50-tipis bisa berarti ekonomi datar-datar-abu.
- **H.8 mingguan = estimasi** yang direvisi; impulse YoY-nya jangan dibaca hingga presisi.
- **WGT** median dari sampel *berganti gaji* — bukan rata-rata upah ekonomi; komposisi bisa bergeser.
- **GDPNow satu model saja** — selisih vs konsensus pasar itu sendiri informasi, bukan error.
- **Kunci kebenaran F0**: golden anchor (mis. `ICSA=203000@2026-08-22`) + sanity-range + depth (`min_ts ≥ expected_start`) — angka "ada" tapi salah tetap tertangkap sebelum masuk brief.

### 7.3 Keterbatasan konseptual

- **Kuartalan vs mingguan**: SLOOS hanya 4 titik setahun; antar-titik, H.8/ADS yang menjaga. Jangan menuntut presisi kuartalan dari data mingguan (dan sebaliknya).
- **Backtest**: pilar growth di-backtest memakai surrogate panjang **ADS (1960→), CFNAI (1967→), SLOOS** (BUILD-PLAN §4); GDPNow muda → hanya untuk live-path, dicatat sebagai pengecualian depth.
- **Non-US tidak setara AS**: PMI Caixin/NBS dan HICP tidak punya kedalaman mesin surprise yang sama dengan AS; perlakukan sebagai state, bukan sinyal presisi.
- **Leading bukan ramalan**: SLOOS/PMI bisa false-positive (pengetatan yang berhenti sendiri). Sistem sengaja memakai mayoritas-suara + rata-rata-z agar satu suara salah tidak membalikkan regime; state flip baru di ±0,5.
- **Yang tidak blok ini ukur**: *kualitas* pertumbuhan (utang vs produktivitas) ada di Blok E (fiskal/likuiditas); suhu pasar uang di Blok F. Growth STEADY + stress tinggi adalah kombinasi sah yang harus dibaca bersama.

---

*Akhir dokumen Blok D. Rantai angka apa pun di brief bisa ditelusulkan dengan `arkwatch explore block D`, `arkwatch explore series FRED:ICSA`, atau `arkwatch explore signal REGIME_SCORE --trace` (BUILD-PLAN §8).*
