# Blok A — Suku Bunga, Kebijakan Fed & Dolar (dokumen edukasi)

> Bagian dari seri `docs/explained/` (dibaca bersama DATA-SPEC.md §1 dan BUILD-PLAN.md §3-Blok A).
> Ditulis untuk pemilik sistem: trader ritel swing, BUKAN orang finance. Setiap istilah dijelaskan dari nol.
> Angka contoh bertanda **(contoh nilai Agt-2026)** diambil dari spec/riset live; sisanya ilustrasi mekanik dan ditandai.

---

## 1. Kenapa blok ini ada

Bayangkan seluruh pasar keuangan dunia adalah satu kota besar, dan **suku bunga Fed (fed funds rate) adalah suhu AC utamanya**. Kalau AC disetel dingin (rate tinggi), semua orang mahal meminjam uang: kredit macet, bisnis mikir dua kali ekspansi, investor puas parkir uang di deposito/bond yang aman. Kalau AC dihangatkan (rate turun), uang murah, orang berani berisiko, dan uang mengalir ke aset "berani" — emas, saham growth, crypto. Satu tuas di Washington digerakkan 8 kali setahun oleh 12 orang (FOMC), dan getarannya terasa ke SEMUA instrumen yang Anda tradingkan: XAUUSD, XAGUSD, XPTUSD, XCUUSD, BTC, ETH, US100/500/30, EURUSD/GBPUSD, DXY.

Analogi yang lebih tajam: **fed funds adalah "harga sewa uang semalam"**. Bank yang kekurangan uang tunai semalam meminjam dari bank yang kelebihan. Harga sewa itulah yang dikendalikan Fed. Semua harga aset lain, cara paling dasar, adalah "nilai arus kas masa depan didiskon ke hari ini" — dan alat diskonnya adalah suku bunga. Rate naik → nilai masa depan menyusut hari ini; rate turun → membengkak. Karena itu blok ini adalah blok pertama yang dibaca di brief, dan bobotnya terbesar di regime score (0.20, terbagi dengan beberapa blok lain — lihat §4).

Tapi ada tiga lapis informasi di blok ini, dan membedakannya adalah kunci:

1. **Rate saat ini** (sudah diputuskan) — sejarah.
2. **Ekspektasi rate mendatang** (apa yang "diprice" pasar) — inilah yang menggerakkan harga HARI INI. Pasar bergerak bukan karena keputusan, tapi karena selisih keputusan vs ekspektasi.
3. **Dolar** — saluran transmisi. Rate hanyalah angka; dolar adalah harga uang itu sendiri terhadap dunia. Emas dan dolar hampir selalu bergerak berlawanan (emas di-harga dalam dolar).

Blok A juga menengahi tetangga: bank sentral ECB (zona euro) dan BoE (Inggris), karena Anda trading crosses XAUEUR, XAGGBP, EURUSD, GBPUSD — di sana yang penting bukan rate AS sendirian, tapi **selisih rate AS vs Eropa/Inggris** (rate differential).

---

## 2. Glosarium blok A

| Istilah | Arti bahasa awam | Kenapa penting untuk Anda |
|---|---|---|
| **Fed / The Federal Reserve** | Bank sentral AS. Pengatur "harga uang" AS. | Satu-satunya lembaga yang bisa menggeser semua instrumen Anda sekaligus. |
| **FOMC** | Komite 12 orang yang rapat ~8×/tahun memutuskan rate. Keputusan 14:00 ET (01:00 WIB esok hari saat EDT), presser 14:30 ET. | Jam presis penting untuk swing: malam FOMC vol naik, hari sebelumnya pasar "menunggu". |
| **Fed funds rate (target range)** | Range target "harga sewa uang semalam" — Fed menetapkan mis. 4.00–4.25% sebagai pagar, bukan satu angka. | Acuan semua suku bunga dolar; pagar inilah yang dinaikkan/turunkan 25bp per langkah. |
| **Fed funds effective (DFF)** | Rate riil yang terjadi di pasar tiap hari (rata-rata transaksi aktual) — harus jatuh di dalam pagar. | "Kebenaran di lapangan"; kalau mendekati tepi pagar = sinyal stres (dikaitkan blok E). |
| **bp / bps** | Basis point = 0,01%. 25bp = 0,25%. Satuan standar ngobrol suku bunga. | Semua threshold state di blok A pakai bps (mis. ±10bps/20d). |
| **IORB** | Bunga yang Fed bayarkan atas simpanan bank di Fed ("Interest on Reserve Balances") — lantai bawah sistem. | Kaki pertama spread funding `SOFR−IORB` (blok E). Di blok A hanya ditampung. |
| **SOFR** | "Secured Overnight Financing Rate" — rate pinjaman semalam berjaminan (repo). Rate referensi pasar modern, pengganti LIBOR. | Barometer biaya dana harian; spike-nya = alarm likuiditas (lihat blok E). |
| **Treasury / yield** | Obligasi pemerintah AS. **Yield** = imbal hasil: berapa persen setahun Anda dapat. **Harga dan yield bergerak berlawanan** — harga turun = yield naik. | Yield 10Y adalah "suku bunga jangka panjang" yang benar-benar ditentukan pasar, bukan Fed. |
| **Tenor** | Jangka waktu pinjaman: 3 bulan (3M), 2 tahun (2Y), 10Y, 30Y. | Bahan kurva. |
| **Kurva yield (yield curve)** | Kumpulan yield semua tenor, digambar garis dari pendek ke panjang. Normalnya menanjak. | "Denah harga waktu" pasar (lihat analogi parkir di §3). |
| **Slope / 2s10s** | Selisih yield 10Y − 2Y, dalam bps. Positif = menanjak (normal). Negatif = **inversi** (jarak yang dikhawatirkan). | Contoh brief: "2s10s +39bps, STEEPENING" **(contoh nilai Agt-2026)**. |
| **3M10Y (T10Y3M)** | Selisih 10Y − 3M. Proxy resesi klasik: inversi berkepanjangan mendahului resesi. | Input model resesi (blok D/F4). |
| **ZQ (30-Day Fed Funds futures)** | Kontrak berjangka yang harganya = `100 − rata-rata rate sebulan`. Transaksi jual-beli jarak pendek: harga 96.75 "berarti" rate 3.25%. | Bahan baku FedWatch-DIY — jendela #1 ke ekspektasi pasar. |
| **Implied rate** | Rate yang "tersirat" dari harga futures: `100 − harga`. | Rumah semua ekspektasi blok A (Fed dan ECB sama-sama pakai). |
| **FedWatch / implied probability** | Probabilitas hasil meeting berikutnya (cut/hold/hike) yang dihitung dari harga futures — "menurut pasar, bukan menurut ahli". | Baris paling sering dikutip: "pasar price 2 cut s/d Des (68%)" **(contoh nilai Agt-2026)**. |
| **SR1 / SR3** | Futures SOFR 1-bulan / 3-bulan. Sanak saudaranya ZQ, berbasis SOFR. | Pendamping ZQ; SR3 juga kaki formula xccy basis (blok E). |
| **ESR (3M €STR)** | Futures 3-bulan berbasis €STR — "ZQ-nya Eropa". | FedWatch-nya ECB: ekspektasi kebijakan ECB untuk XAUEUR/EURUSD. |
| **MPT (Atlanta Fed)** | File resmi berisi **distribusi probabilitas** rate 3-bulan ke depan (metode implied-opsi, bukan linear). | Cadangan resmi kalau jalur CME mati; historisnya panjang. |
| **DTWEXBGS** | Indeks dolar **berbobot perdagangan riil** terhadap ~26 mitra dagang AS, update harian. | Baris first-class dolar di brief — lebih jujur daripada DXY. |
| **DXY (ICE)** | Indeks dolar klasik terhadap 6 mata uang besar (euro ~57,6% bobotnya). | familiar di chart trading; dipakai sebagai sekunder + positioning (blok G `098662`). |
| **ECB deposit rate (ECBDFR)** | Rate kebijakan kunci ECB (rate simpanan bank di zona euro). | Kaki Eropa dari rate differential US−EU. |
| **BoE Bank Rate** | Rate kebijakan Inggris, diumumkan 8×/tahun oleh MPC. | Kaki Inggris dari differential US−UK → GBPUSD, XAGGBP. |
| **Term premium** | "Asuransi ekstra" yang diminta pemegang obligasi jangka panjang di ATAS gabungan (rata-rata rate masa depan yang diperkirakan). | Kanal fiskal emas: term premium naik = pasar waspadai utang AS — dorongan gold **(contoh nilai Agt-2026: 0.87%)**. |
| **Nominal vs real yield** | Nominal = angka bunga tertulis; Real = nominal − inflasi yang diharapkan. | Teaser: driver #1 XAUUSD adalah real yield, dibahas penuh di Blok B **(contoh nilai Agt-2026: DFII10 2.34%)**. |
| **Dollar smile** | Pola: dolar menguat saat ekonomi AS bagus (kanan) DAN saat dunia ketakutan (kiri), melemah di tengah. | Kerangka membaca baris dolar → bias metals/BTC/majors. |
| **Dovish / hawkish** | Dovish (merpati) = condong melonggarkan kebijakan/rate turun; hawkish (elang) = condong mengetatkan/rate naik. | Bahasa standar narasi bank sentral; skenario latihan §6 dan cara baca settlement memakai istilah ini. |
| **Presser** | Konferensi pers FOMC, 30 menit setelah keputusan rate (14:30 ET). | Sumber vol tambahan malam FOMC — nuansa katanya sering menggerakkan pasar lebih dari keputusan itu sendiri. |

---

## 3. Peta data — series per series

Aturan baca umum: **primer → sekunder** di kolom sumber berarti arah fallback; series gray (backdoor CME) wajib punya cadangan. Semua series harian di-fetch ~06:00 WIB (FRED), brief 07:00 WIB.

### 3.0 Peta ringkas (12 series blok A)

| # | Series | Pertanyaan yang dijawab | Freq | Sumber (primer → sekunder) |
|---|---|---|---|---|
| 1 | `DFF` | Berapa rate riil semalam? | D | FRED → FMP |
| 2 | `IORB` | Di mana lantai sistem? | D | FRED |
| 3 | `SOFR` | Berapa biaya dana harian pasar? | D | FRED → EODHD |
| 4 | ZQ `305` + SR1 `8463` | Ke mana pasar percaya Fed menuju (per-meeting)? | D | backdoor CME (gray) → MPT |
| 5 | MPT Atlanta | Bagaimana DISTRIBUSI penuh rate 3-bulan? | ~Mingguan | Atlanta Fed (resmi, fallback) |
| 6 | `DGS2/10/30` | Berapa harga uang 2/10/30 tahun? | D | FRED → FMP + Treasury XML |
| 7 | `T10Y3M` | Apakah kurva terbalik (proxy resesi)? | D | FRED → FMP |
| 8 | `DTWEXBGS` (+DXY) | Seberapa kuat dolar vs dunia riil? | D | FRED → DXY EOD (gray-eligible) |
| 9 | `ECBDFR` + ESR `10247` | Apa kata ECB — sekarang & mendatang? | D | FRED/ECB/EODHD → backdoor CME → ESTRWatch |
| 10 | BoE Bank Rate | Apa kata BoE? | 8×/thn | EODHD policy-rates (FRED `BOERUKM` MATI) |
| 11 | `THREEFYTP10` | Berapa "premi kekhawatiran" di yield 10Y? | D | FRED |
| 12 | (turunan) differential US−EU / US−UK | Selisih kebijakan dua kaki FX Anda | D | computed dari #1/#9/#10 |

### 3.1 Fed funds effective — `DFF`
- **Apa sebenarnya:** rata-rata tertimbang rate pinjaman semalam antar-bank, diterbitkan NY Fed untuk hari sebelumnya.
- **Siapa & kapan:** NY Fed/FRED, setiap hari kerja (nilai H-1, muncul pagi ET).
- **Kenapa dipilih:** satu-satunya ukuran "rate riil yang hidup" — pager boleh apa saja, inilah suhu aktual. Sekunder: FMP `federalFunds`.
- **Cara baca:** bandingkan terhadap pager (target range). Nempel di atap pagar = dana mahal; nempel lantai = dana longgar. Level 4–5% = "normal ketat" era 2026; angka itu sendiri kurang penting daripada posisinya dalam pagar dan arahnya.

### 3.2 Interest on reserves — `IORB`
- **Apa:** bunga simpanan bank di Fed = lantai administratif sistem.
- **Kenapa dipilih:** bukan untuk dibaca langsung; ini input `SOFR−IORB` (blok E). Kalau SOFR menempel IORB, dana aman; menembus ke atas = scarcity.
- **Cara baca:** sebagai kaki pembagi, bukan headline.

### 3.3 SOFR — `SOFR`
- **Apa:** rate repo semalam berjaminan Treasuries — biaya funding harian pasar modal modern.
- **Kenapa dipilih:** kualitasnya sebagai "denyut nadi dana dolar"; sekunder EODHD `/rates/reference-rates`.
- **Cara baca:** level tenang ≈ tengah pager Fed. Gerak 5–10bp dari IORB wajar; >10bp berkelanjutan = sesuatu sedang terjadi di plumbing (blok E mengambil alih analisisnya). (Panduan umum pembacaan, bukan threshold resmi — ambang resmi state ada di registry.)

### 3.4 Ekspektasi kebijakan per-meeting — ZQ (produk `305`) + SR1 (`8463`) settlements
- **Apa:** harga penutupan (settlement) futures ZQ/SR1 per bulan kontrak, diambil dari jalur backdoor CME (§16–17: endpoint settlements CME, gray tapi terverifikasi; satu-satunya endpoint yang mengembalikan open interest juga).
- **Siapa & kapan:** CME Group; settlement = EOD (akhir hari ET); harvester jalan tiap hari karena **retensi hanya 5 hari kerja** — hari tak ter-fetch = hilang permanen.
- **Kenapa dipilih:** dari sini kita HITUNG SENDIRI probabilitas FedWatch (DIY) — reproducible, tidak bergantung pada parse HTML rapuh. Sekunder/cadangan: MPT (3.5).
- **Cara baca:** `implied = 100 − settlement`. Kontrak Januari setel di 96.00 → pasar rata-rata rate Januari 4.00%. Turunnya harga kontrak = pasar memangkas ekspektasi rate = bias dovish.

### 3.5 Ekspektasi (distribusi 3 bulan) — MPT Atlanta Fed
- **Apa:** `mpt_histdata.xlsx` dari Atlanta Fed: seluruh **distribusi probabilitas** (mean, mode, persentil, probabilitas cut/hike per bucket 25bp) untuk rate 3-bulan ke depan, metode implied-opsi.
- **Kenapa dipilih:** satu-satunya sumber probabilitas RESMI dengan historis panjang (2023-03-29+, ratusan ribu baris) → fallback kalau backdoor mati, dan lapisan validasi DIY.
- **Cara baca & jebakan:** ini **range rata-rata 3 bulan**, bukan per-meeting. 68% "cut di meeting September" (FedWatch) ≠ 68% "rate Des lebih rendah 25bp" (MPT) — semantik beda, brief selalu memberi label "range-3M" saat memakai MPT.

### 3.6 Yield 2/10/30Y — `DGS2` `DGS10` `DGS30`
- **Apa:** yield Treasury par harian, dipublikasi Fed Board (FRED) menjelang tutup sesi AS untuk hari yang sama; sekunder FMP `/stable/treasury-rates` + kurva par resmi Treasury XML (blok 18.3).
- **Analogi kurva:** parkir. Tarif parkir 3 bulan vs tarif parkir 10 tahun. Normalnya parkir lama lebih mahal (Anda menanggung risiko lebih lama) → kurva menanjak. Kalau parkir 10 tahun justru LEBIH MURAH daripada 3 bulan (inversi) = operator parkir percaya suku bunga masa depan akan turun tajam — biasanya karena resesi dikhawatirkan.
- **Cara baca:** 10Y 4.67% **(contoh nilai Agt-2026, golden anchor 2026-08-27)** — level nominal; slope 2s10s +39bps STEEPENING; 30Y menunjukkan term struktur panjang. Angka normal era 2026: 2Y ~4.3%, 10Y ~4.6%; ekstrem bersejarah: 10Y <1% (2020) atau >7% (1990-an).

### 3.7 Kurva 3M10Y — `T10Y3M`
- **Apa:** selisih 10Y − 3M, versi kurva paling disukai riset resesi NBER-era.
- **Cara baca:** negatif (inversi) berbulan-bulan = lampu kuning resesi klasik. Nilai −50bp = inversi dalam; +150bp = sangat menanjak. Setelah periode inversi, re-steepening justru sering menandai fase resesi/pemulihan — jangan baca "balik positif = aman" (lihat jebakan §5).

### 3.8 Dollar index trade-weighted — `DTWEXBGS` (first-class) + DXY
- **Apa DTWEXBGS:** indeks dolar terhadap keranjang ~26 mata uang mitra dagang UTAMA AS, bobot mengikuti porsi perdagangan riil (China, Meksiko, Kanada ikut besar), update HARIAN oleh Fed Board.
- **Apa DXY:** indeks era-1973: hanya 6 mata uang maju, euro 57,6% bobot — tidak mencerminkan perdagangan AS modern, tapi familiar, likuid, ada futurnya (positioning blok G `098662`) dan historisnya panjang (Yahoo 1971+).
- **Kenapa DUA-DUANYA dipakai:** DTWEXBGS = kejujuran ekonomi (driver silang seluruh book); DXY = bahasa pasar & data positioning. Selisih keduanya sendiri informatif: DXY naik tapi DTWEXBGS datar = gerakan "euro story", bukan cerita dolar-broad.
- **Cara baca:** DTWEXBGS momo-20d; contoh brief: "dolar melemah 0.4% (20d) → tailwind metals+BTC" **(contoh nilai Agt-2026)**. Threshold state: >+0.4% STRONG, <−0.4% WEAK.

### 3.9 ECB deposit rate — `ECBDFR` + ekspektasi ECB (ESR `10247`)
- **Apa:** rate kebijakan ECB; dan ESR = futures 3M €STR → jalur ekspektasi ECB. `implied = 100 − price` seperti ZQ. Dua output: **path** level (`ECB path:`) dan — sejak D-006 (2026-09-10) — **probabilitas per-rapat** (`Policy: ECBWatch …`): karena satu kontrak kuartalan memuat 1–2 rapat, probabilitas diselesaikan serentak untuk seluruh kurva; rapat yang berbagi kuartal ditandai `≈` (split = konvensi min-norm, bukan observasi). Metodologi penuh: `docs/methodology/estrwatch.md`.
- **Cross-check:** konsistensi internal vs path (fitted ≤3bp RMS); view ESTRWatch QuikStrike (referrer-trick §19) = tool skenario, bukan oracle.
- **Contoh angka riset:** strip ESR 2.19% → 2.77% ke Des-26, dibaca brief "pasar price ECB +45bp s/d Des-26" **(contoh nilai riset Agt-2026)**; ECBWatch live 09-10: "hike ≈85% (Sep-10, +21bp → DFR 2.46%)".
- **Cara baca:** selisih US−EU inilah yang menggerakkan EURUSD: differential melebar (AS relativamente lebih ketat) → EURUSD tertekan; menyempit → EURUSD naik dan XAUEUR tertekan sisi EUR.

### 3.10 BoE Bank Rate
- **Apa:** rate kebijakan Inggris, 8 keputusan/tahun (MPC).
- **Sumber:** EODHD `/rates/policy-rates`. **JEBAKAN TERSEBAR LUAS:** mirror FRED `BOERUKM` MATI sejak 2017 — angka apapun yang tampak "baru" dari situ adalah mayat data.
- **Cara baca:** sama seperti ECB: differential US−UK untuk GBPUSD, XAGGBP, XAUGBP.

### 3.11 Term premium 10Y — `THREEFYTP10`
- **Apa untuk awam:** yield 10Y bisa dibongkar jadi dua bagian: (a) rata-rata rate pendek yang DIPERKIRAAN pasar sampai 10 tahun ke depan, dan (b) **premi kompensasi ekstra** karena bersedia mengunci lama — premi itulah term premium. Analogi: tarif bensin vs premi asurensi perjalanan jauh; premi naik bukan karena bensin mahal, tapi karena jalanan dianggap makin berisiko (defisit,Supply bond, kepercayaan pada utang AS).
- **Cara baca:** 0.87% dan NAIK = dorongan gold **(contoh nilai Agt-2026)** — pasar menagih kompensasi atas fiskal AS, teman satu kanal dengan defisit (blok E) dan CDS berdaulat (blok F). Term premium turun sambil yield turun = disinflate bersih.

---

## 4. Logika hilir-ke-hulu: dari harga mentah sampai regime score

Konsep transform yang dipakai blok ini (dan seluruh sistem) — kenali sekali, terpakai selamanya:

- **Momentum-N hari** = `nilai_hari_ini − nilai_N_hari_lalu` (atau persentase). Bukan "naik atau tidak", tapi "seberapa cepat dan seberapa jauh bergerak dalam jendela tetap". Dipakai: slope ±10bps/20d, DTWEXBGS ±0.4%/20d.
- **Z-score** = `(x − rata2_5tahun) / simpangan_baku_5tahun` — "berapa simpangan dari normal". z=0 biasa; z=+2 sangat tinggi secara historis. Standar sistem: window 5y sesuai frekuensi, min-obs 80%, σ populasi.
- **Percentile** = peringkat: "nilai ini masuk 5% teratas 5 tahun terakhir?".
- **Probabilitas implied** — dijelaskan pelan-pelan di 4.1, ini jantung blok A.

### 4.1 FedWatch-DIY: dari harga ZQ ke "68% cut" (dipelankan)

1. **Harga → rate tersirat.** Kontrak ZQ berperilaku `100 − rate`. Kontrak Des setel di 95.50 → pasar bilang "rata-rata rate Desember 4.50%". Hitungan ini gratis, deterministik, dan bisa diulang siapa pun — itulah kenapa DIY dipilih sebagai primer, bukan parse halaman.
2. **Pisahkan hari sebelum vs sesudah meeting.** Meeting (mis. 18 Des) membelah bulan: sebelum → rate lama, sesudah → rate baru. Formula `post = (implied·D − pre·(d−1)) / (D−d+1)` membalik campuran itu (D = hari dalam bulan, d = tanggal meeting). Ilustrasi mekanik (angka rekaan): pre = 4.00, implied Des = 3.83, D=31, d=18 → post = (3.83·31 − 4.00·17)/14 ≈ 3.62… perhitungan tepat menyesuaikan hari; intinya implied bulanan adalah CAMPURAN dua rezim dan harus dibedah dulu.
3. **Rate sesudah meeting → probabilitas.** Fed bergerak 25bp. Kalau hasil belah tadi (post) jatuh DI ANTARA dua outcome yang bertetangga (mis. 3.75 dan 4.00), interpolasi linear memberi probabilitas: `p_cut = (pre − post)/0.25`. Catatan konvensi tanda: BUILD-PLAN §3-Blok A menulis magnitudo `(post−pre)/0.25` — jumlahnya sama, tandanya diinterpretasi per arah (post di bawah pre = cut); rumus di sini memakai bentuk bertanda supaya p_cut langsung positif untuk cut. Contoh angka rekaan yang konsisten dengan spec — cabang ilustrasi TERPISAH yang memakai implied mentah (3.83) langsung sebagai post, bukan hasil belah 3.62 di langkah 2: implied 3.83 dengan pre 4.00 → p_cut = (4.00−3.83)/0.25 = 0.68 → **"68% cut 25bp"** — persis format brief **(contoh nilai Agt-2026: pasar price 2 cut s/d Des, 68%)**. Probabilitas dinormalisasi Σ=1, di-anchor ke `floor(pre/0.25)`.
4. **Aturan pemetaan meeting→kontrak:** meeting bulan-M pakai kontrak bulan-M, KECUALI meeting hari-1 bulan (sisa hari bulan sebelumnya lebih relevan → pakai M−1); meeting di 3 hari terakhir bulan → pakai kontrak bulan berikutnya. Aturan ini di-vendor dari `cme-fedwatch/calc.py` + diuji dengan fixture.
5. **Kumulatif year-end** → state: CUTTING / HOLD / HIKING (total perubahan Des vs target kini; "2 cut s/d Des" artinya kumulatif −50bp per Desember, BUKAN janji meeting September).

Tabel kerja ilustrasi mekanik (angka rekaan, bukan nilai spec) — satu meeting Desember:

| Langkah | Input/Hasil | Penjelasan |
|---|---|---|
| Settlement ZQ Des | 96.17 | harga penutupan kontrak dari endpoint settlements CME |
| Implied Des | 100 − 96.17 = **3.83%** | rata-rata rate Desember versi pasar |
| `pre` (rate sebelum meeting) | 4.00% | implied kontrak sebelumnya (fallback: EFFR/DFF) |
| Belah `post` | ≈ 3.62% | memisahkan hari sebelum vs sesudah meeting (formula D, d) |
| Anchor 25bp | `floor(4.00/0.25)` = 16 → outcome 3.75% vs 4.00% | dua titik tetangga yang mungkin |
| Probabilitas | p(3.75) = (4.00−3.62)/0.25 ≈ ... , dinormalisasi Σ=1 | interpolasi linear antar 2 outcome |
| Dibaca | "cut 25bp mendekati pasti" | kalau post malah 3.83 → 68% cut — format persis brief |

Catatan penting membaca tabel: probabilitas TIDAK dibatasi 0–100% sebelum normalisasi (post bisa menjorok melewati outcome tetangga — itulah kasus "price lebih dari 1 cut"); normalisasi Σ=1 adalah gerbang harian (§6.3 BUILD-PLAN).

**Kenapa 68% bukan 100% walau "semua orang tahu"?** Karena 68% adalah taruhan berpasang uang riil para trader — kalau Anda yakin 100% dan pasar 68%, ANDA yang berbeda pendapat dengan miliaran dolar. Probabilitas ini juga mengangkut premi risiko dan likuiditas kontrak, jadi ia "ekspektasi + gesekan pasar", bukan ramalan murni. Kolom Δ1D/1W/1M (dari view FedWatch resmi) menunjukkan seberapa cepat keyakinan itu bergerak — perubahan probabilitas sering lebih penting daripada levelnya.

### 4.2 Jalur data CME & QuikStrike (§16–19) — kenapa "gray" dan bagaimana ia dijaga

- **Backdoor settlements** (ZQ 305, SR1 8463, SR3 8462, ESR 10247): endpoint publik CME yang diakses dengan sidik browser (`curl_cffi` impersonate chrome, di-pin; harus dijalankan dari Windows lokal — IP cloud dan PowerShell mentah ditolak 403). Status **gray**: tidak kontraktual, bisa berubah tanpa pengumuman — maka wajib degradable + snapshot raw JSON disimpan bersama hasil hitung (raw = bisa hitung ulang kapan pun).
- **Retensi 5 hari kerja** → harvester harian tidak boleh bolong >3 hari trading; kalender libur (FMP `holidays-by-exchange`) dipakai supaya "kosong karena libur" tidak dianggap gagal.
- **View resmi FedWatch (QuikStrike)** ternyata hanya ber-Referer (§19.1): bawa header `Referer` dari cmegroup.com → render penuh anonim sebagai trial "Pro - Limited"; tanpa itu ErrorPage. Matriks probabilitasnya HTML WebForms (tidak ada JSON). **Keputusan desain:** DIY tetap PRIMER (reproducible); HTML resmi = cross-check harian + sumber kolom **Now/1Day/1Week/1Month** gratis. Gerbang kalibrasi F2: DIY vs resmi Δprob ≤ 3pp; ESR-implied vs ESTRWatch ±0.5bp.
- **Dua jebakan yang sudah ditemukan & dikunci:** (a) endpoint delayed-quotes legacy REFUTED — pakai settlements saja; (b) fungsi `get_history()` paket cme-fedwatch berbuga (menerapkan EFFR hari ini ke tanggal lampau) → snapshot wajib `fetch_settlements(tanggal_eksplisit)`.
- **Beda anchor yang bisa muncul:** DIY kita meng-anchor probabilitas ke implied bulan SEBELUMNYA, QuikStrike ke target saat ini — dua tampilan sah yang bisa beda beberapa pp; didokumentasikan di brief, bukan disamarkan.

### 4.3 Rantai lengkap blok A

```
settlement ZQ/SR1 (CME)  →  implied = 100−settle  →  belah pre/post  →  probabilitas per-meeting (Σ=1)
                                                                    ↘ kumulatif year-end → STATE-1 CUTTING/HOLD/HIKING
DGS2,DGS10,DGS30 (FRED)  →  2s10s = 10Y−2Y  →  momo  ±10bps/20d    → STATE-2 FALLING/FLAT/RISING (+ label STEEPENING/FLATTENING)
T10Y3M (FRED)            →  level + arah                                → input model resesi (blok D)
DTWEXBGS (FRED)          →  momo-20d  ±0.4%                            → STATE-3 WEAK/FLAT/STRONG + input dollar smile
ECBDFR + ESR strip       →  differential US−EU + path ECB               → smile (syarat KANAN), crosses EUR
BoE policy-rates         →  differential US−UK                          → leg GBP
THREEFYTP10 (FRED)       →  level + arah                                → kanal fiskal gold (teaser blok E/F)
DFF/SOFR/IORB (FRED)     →  posisi dalam pagar + kaki SOFR−IORB        → header brief + serah ke blok E
```

Pilar A = rata-rata z-score anggota → state; flip di ±0.5. **Regime score** (−2…+2) menjumlahkan pilar dengan bobot **A .20** (B .20, C/D/E/F .15). Contoh: state Policy=CUTTING + slope FALLING + dolar WEAK → pilar A condong positif → mendukung label regime "EASING"-family, yang oleh lookup §11.4 memberi bias tailwind metals/BTC. Label contoh brief: `Policy=CUTTING (pasar: 2 cut s/d Des, 68%)`.

---

## 5. Cara membaca baris blok A di brief + jebakan salah-baca

Baris khas blok A di brief (contoh nilai Agt-2026):

```text
Pilar  : Policy=CUTTING (pasar: 2 cut s/d Des, 68%)
• 10Y 4.67%, 2s10s +39bps, STEEPENING
• Term premium 0.87% naik → dorongan gold
• Dolar (DTWEXBGS) −0.4%/20d → tailwind metals+BTC
• Pasar price ECB +45bp s/d Des-26 (implied dari futures ESR)
```

**JEBAKAN umum — hafalkan ini:**

1. **"68%" bukan kepastian dan bukan ramalan Fed.** Itu konsensus taruhan pasar hari INI; bisa 40% besok bila satu data payroll menyimpang (cek kolom Δ1D/1W/1M). Salah-baca klasik: buka posisi "karena pasti cut".
2. **"2 cut s/d Des" = kumulatif ke akhir tahun**, bukan "meeting berikutnya pasti cut 2×25bp". Bisa jadi komposisinya 1 cut besar (50bp) — probabilitas per-bucket ada di MPT.
3. **2s10s positif ≠ sehat, negatif ≠ langsung resesi.** Inversi adalah indikator LEADING bermonth-month (bahkan >1 tahun); dan re-steepening pasca-inversi justru sering fase resesi. Yang dipakai model resesi adalah 3M10Y, bukan 2s10s.
4. **Jangan bandingkan %DXY dengan %DTWEXBGS satu-ke-satu.** Bobot keranjangnya beda; yang sah adalah arah + masing-masing momentum terhadap threshold sendiri.
5. **Dua baris ECB = dua keluarga angka.** `ECB path:` = PATH level ("+45bp s/d Des-26"), dan sejak 2026-09-10 ada juga `Policy: ECBWatch hike ≈85% …` = PROBABILITAS per-rapat (D-006, solve serentak; `≈` menandai rapat yang berbagi kuartal — split-nya konvensi, bukan observasi). Jangan dicampur dalam satu kalimat; probabilitas bukan derivat sederhana dari path.
6. **Baris MPT (mode fallback) berlabel "range-3M"** — semantik beda dari FedWatch per-meeting; jangan dicampur dalam satu kalimat perbandingan.
7. **Yield turun ≠ otomatis gold naik.** Yang relevan untuk gold adalah REAL yield (yield − inflasi): nominal 4.67% dengan inflasi 2.31% → real ~2.34% **(contoh nilai Agt-2026, DFII10)** — dibahas penuh di Blok B. Blok A memberi nominal + ekspektasi; Blok B memberi "setelah dipotong inflasi".
8. **Harga settlement ≠ harga live.** Settlement = EOD; angka FedWatch brief pagi WIB adalah potret penutupan kemarin (cukup untuk keputusan swing harian).
9. **BoE jarang update (8×/tahun)** — kolomnya "sepi" itu normal, bukan data mati; kebalikannya, kalau FRED `BOERUKM` tampak hidup, itu justru data mati-2017.

---

## 6. Keterkaitan spesifik per instrumen Anda

| Instrumen | Jalur utama pengaruh blok A | Catatan baca |
|---|---|---|
| **XAUUSD / XAGUSD / XPTUSD** | rate↓ → yield nominal↓ → real yield↓ (blok B) + dolar WEAK → tailwind. Term premium naik = kanal fiskal terpisah yang MENDUKUNG gold walau rate tinggi. | Kalau gold naik saat rate naik, curigai kanal fiskal/CB-buying (bukan logika yield biasa) — cek anomali divergence blok B. |
| **XCUUSD (copper)** | Kanal utamanya growth/China (blok D), tapi rate AS menentukan dolar → harga komoditas ber-denominasi USD. | Dolar WEAK = angkat semua metal seragam; copper paling peka growth, bukan rate. |
| **BTC / ETH** | Ekspektasi easing + likuiditas (teaser blok E: net liquidity) → risk appetite. "Biaya uang murah" = bahan bakar aset berisiko. | FedWatch probabilitas berbalik cepat sering mendahului koreksi crypto. |
| **US100 / US500 / US30** | Discount factor: ekspektasi rate turun → valuasi saham panjang durasi (growth/tech) paling terbantu → US100. | Steepening sehat menopang bank/US30 relatif. |
| **EURUSD / GBPUSD / majors** | Rate differential US−EU / US−UK + kerangka dollar smile (KANAN: DTWEXBGS momo-20d >+0.4% DAN differential melebar; KIRI: dolar naik DAN PMI ex-US jatuh; TENGAH: selain itu). | Smile KIRI (flight-to-safety) menjungkirbalik bacaan "dolar kuat = Fed hawkish". |
| **XAUEUR / XAGEUR / XAUGBP / XAGGBP** | Emas dalam EUR = XAUUSD ÷ EURUSD → leg kedua dikendalikan ECB/BoE. ECB +45bp priced (contoh Agt-2026) → EUR kaku → XAUEUR tertinggal XAUUSD. | Cross bergerak dua-kaki: selalu tanya malam ini kaki mana yang gerak. |
| **DXY (sebagai instrumen)** | Blok A memberi DTWEXBGS (driver silang) + differential; positioning DXY futures ada di blok G. | Trade DXY = trade differential + smile, bukan trade angka index kosong. |

---

### 6.1 Dua skenario latihan baca (mekanisme, bukan saran posisi)

**Skenario 1 — "dovish surprise":** CPI rilis lebih dingin dari konsensus → settlement ZQ Des turun (harga naik) → FedWatch-DIY besok pagi: probabilitas cut naik dari 68% ke misal 90% → 2s10s STEEPENING (pasar yakin rate pendek turun) → DTWEXBGS melemah >0.4%/20d → brief: tailwind metals+BTC. Perhatikan URUTAN: ekspektasi bergerak LEBIH DULU daripada keputusan Fed sungguhan — di sinilah swing trader hidup.

**Skenario 2 — "hawkish tapi dolar tak kuat":** Fed menahan rate + pernyataan tegas, tapi DTWEXBGS hanya datar. Dua kemungkinan baca: (a) pasar sudah memprice-nya (kolom Δ1M FedWatch hampir nol), atau (b) dolar dinilai mahal (smile di tengah). Pelajarannya: jangan trade narasi; trade kombinasi probabilitas + momentum dolar yang tertulis di brief.

## 7. Yang bisa salah: degradasi, kualitas data, keterbatasan

**Mode degradasi (otomatis, per §11.4):**
- **Backdoor CME mati** → baris ekspektasi Fed diganti MPT Atlanta dengan label **"probabilitas range-3M…"** — semantik berbeda diumumkan eksplisit, bukan diselipkan.
- **ESR mati** → ekspektasi ECB dari view **ESTRWatch** (QuikStrike referrer-trick; retry bila mendarat di ErrorPage; sesi `insid/qsid` kedaluwarsa ~7 hari → selalu mulai GET baru).
- **Sumber gray down total** → brief tetap terbit dengan pilar A dari jalur FRED resmi (kurva, dolar, term premium, DFF) — hanya baris ekspektasi yang berubah bentuk. FRED/lembaga resmi boleh single-source karena freshness-check aktif (`series/updates`, §0.2).

**Kualitas data & operasional:**
- Retensi 5 hari → bolong >3 hari trading = data CME hilang permanen; ada status kolom per `trade_date` (empty → retry H-1 → log) + kalender libur.
- Settlement EOD + snapshot raw JSON disimpan bersama hasil hitung (prinsip raw+derived §0.4) → angka brief selalu bisa direkonstruksi.
- Kalibrasi berjalan: DIY vs FedWatch resmi ≤3pp; implied ESR vs ESTRWatch ±0.5bp; identitas slope dua-jalur (FRED selisih vs Treasury XML recompute) ≤2bps; Σprobabilitas = 1 dicek harian sebagai gerbang brief.
- Jadwal FOMC di-vendor s/d 2028-01 — wajib dicek tiap Januari vs federalreserve.gov.

**Keterbatasan konseptual (bukan bug — sifat datanya):**
- Probabilitas implied mengangkut premi risiko & likuiditas — bukan pendapat "murni"; bisa salah sistematis saat pasar diguncang.
- Historis probabilitas per-meeting DIY terbatas: snapshot mulai build; backfill = MPT (2023+) + recompute Yahoo `ZQ=F` 2000+ (divalidasi dulu di overlap 2023–26).
- Path ECB (ESR) adalah kontrak muda → pengecualian backtest terdokumentasi.
- BoE frekuensi rendah & MPT ~mingguan → resolusi blok ini untuk "detik-menit" memang tidak ada; ini sistem swing harian-mingguan, dan itu cukup.
- FedWatch resmi = HTML WebForms anonim — jalur paling rapuh di seluruh blok; DIY justru dipilih karena itulah letak ketahanan sistem ini.

## 8. FAQ — untuk menantang keputusan desain blok ini

Pemilik sistem boleh (dan dianjurkan) menantang desain. Jawaban resmi untuk pertanyaan yang paling mungkin muncul:

- **"Kenapa FedWatch hitung sendiri, bukan ambil angka resmi CME saja?"** — Karena jalur resminya HTML WebForms anonim yang rapuh (referrer-trick, tanpa JSON API); tiap perubahan layout bisa memutus baris headline. DIY dari settlement mentah = reproducible kapan pun, dan angka resmi tetap dipakai sebagai cross-check harian (gerbang selisih ≤3pp). Rapuh dipindah ke posisi pendamping, kokoh diposisikan primer.
- **"Kenapa dolar pakai DTWEXBGS, bukan DXY yang ada di semua chart?"** — DXY adalah keranjang 1973 (euro 57,6%); ia cerita euro-yen, bukan perdagangan AS. DTWEXBGS berbobot mitra dagang riil (China, Meksiko) dan harian. DXY tetap dipakai — sebagai bahasa pasar, data backtest 1971+, dan kontrak positioning (blok G). Selisih gerak keduanya sendiri informatif (§3.8).
- **"Kenapa MPT hanya jadi fallback, padahal resmi?"** — MPT memberi distribusi 3-bulan rata-rata, bukan per-meeting; semantiknya lebih kasar untuk kebutuhan "pasar price X cut s/d Des". Ia menang di resmi+historis panjang, kalah di resolusi — maka posisinya cadangan + validasi.
- **"Kenapa tidak pakai OIS swap saja seperti institusi?"** — OIS harian tidak tersedia di FRED (§18.5); proksinya sofrai30−SOFR dipakai di blok E untuk kebutuhan lain. ZQ/SR sudah memadai untuk horizon swing.
- **"Kenapa ekspektasi ECB hanya path, tanpa probabilitas?"** — ~~Struktur kontrak ESR (3M €STR) dan kalender meeting ECB tidak sejajar per-bulan seperti AS; memaksakan probabilitas per-meeting akan mengarang presisi palsu.~~ **SIKAP DIBALIK 2026-09-10 (D-006 ESTRWatch):** kini ADA probabilitas per-rapat ECB (`Policy: ECBWatch …`), dan alasan lama itu sendiri yang menuntun desainnya: karena satu kontrak kuartalan memuat 1–2 rapat, probabilitasnya dihitung SERENTAK untuk seluruh kurva (least-squares berbobot hari), bukan dipaksakan per-bulan. Ketidaksejajaran yang dulu bikin "mengarang presisi" kini dibaca jujur: rapat yang berbagi kuartal ditandai `≈` di brief (split-nya konvensi min-norm, bukan observasi), rapat yang sendirian di kuartalnya exact. Detail: `docs/methodology/estrwatch.md`.
- **"Sistem bisa salah?"** — Bisa, tiga tempat: (1) jalur gray mati (ada fallback berlabel), (2) probabilitas pasar sendiri salah (itu risiko membaca, bukan bug — pasar bisa 100% yakin dan tetap keliru), (3) revisi data (ditangani append-only + vintage, §0.5). Yang tidak boleh salah diam-diam: pelanggaran kalibrasi selalu jadi flag di brief, bukan angka yang dipakai senyap.

---

> Ringkasnya: Blok A menjawab tiga pertanyaan tiap pagi — (1) berapa biaya uang sekarang, (2) ke mana pasar percaya biaya uang itu menuju, (3) dan berapa mahal dolar hari ini. Semua instrumen Anda adalah konsekuensi dari tiga jawaban itu.
