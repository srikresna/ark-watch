# 00 — Gambaran Besar Sistem ark-watch

> Dokumen edukasi untuk pemilik sistem (trader ritel, bukan latar finance). Bahasa Indonesia, istilah dijelaskan dari nol.
> Posisi: pengantar seluruh `docs/explained/`. Dokumen blok (01, 02, …) mengambil alih untuk detail per blok — di sini hanya peta dan konsep.
> Referensi spec: DATA-SPEC.md v1.4 (2026-08-30) dan BUILD-PLAN.md v1.1 (2026-08-30). Semua angka contoh diambil dari spec, ditandai "contoh nilai Agt-2026".

---

## 1. Kenapa dokumen ini ada

Sistem ark-watch adalah mesin pemantau makro AS yang setiap pagi menyusun satu lembar ringkasan ("US Session Brief") berisi: kondisi besar pasar sekarang, apa yang berubah semalam, dan apa artinya untuk instrumen yang Anda tradingkan (XAUUSD, XAGUSD, XPTUSD, XCUUSD, crosses, BTC/ETH, US100/500/30, EURUSD/GBPUSD/majors, DXY) pada timeframe swing hari-minggu.

Masalahnya: sistem ini punya ratusan series dari puluhan sumber. Kalau Anda hanya membaca hasil akhirnya, sistem itu jadi kotak hitam — Anda harus percaya angka yang tidak Anda pahami asalnya. Dokumen-dokumen `explained/` ada untuk memecah kotak hitam itu: setiap angka di brief bisa Anda telusuri balik sampai ke sumber mentahnya, dan Anda paham **kenapa** angka itu dihitung begitu, bukan cuma **berapa**.

Analogi posisi dokumen ini: kalau sistem = rumah, maka DATA-SPEC adalah daftar bahan bangunan, BUILD-PLAN adalah cetak biru tukang, dan `docs/explained/` adalah tur berpandu untuk pemilik rumah. Dokumen 00 ini adalah tur pertama: denah lantai, di mana saklar lampunya, mana dinding struktural yang boleh dan tidak boleh dibongkar.

---

## 2. Konsep inti: REGIME — membaca musim, bukan meramal cuaca per jam

### 2.1 Analogi dasar

Ada dua cara menatap pasar:

- **Meramal cuaca per jam**: "besok jam 10 XAUUSD naik 0.4%". Ini ramalan titik — hampir mustahil dilakukan konsisten, dan sistem ini TIDAK mencobanya.
- **Membaca musim**: "kita sedang masuk musim di mana Fed condong memangkas rate, likuiditas mengembang, dan inflasi mendingin". Musim tidak memberi tahu hujan jam berapa, tapi memberi tahu bahwa membawa payung lebih sering benar daripada salah selama beberapa minggu ke depan.

Trading swing hari-minggu hidup di skala musim. Karena itu satu-satunya "produk" utama sistem adalah pembacaan **regime** — label kondisi besar seperti:

```text
REGIME : EASING + LIQUIDITY EXPANDING   (score +1.2 → risk-on)
QUADRANT: growth STEADY × inflasi COOLING → "disinflationary growth"
```

(contoh nilai Agt-2026, dari contoh brief DATA-SPEC §14)

Dua baris itu adalah kesimpulan; sisanya di brief adalah bukti-bukti pendukungnya.

### 2.2 Bagaimana regime dihitung (gambar besar; detail transform di §6)

1. Setiap series mentah (mis. yield riil 10Y) diubah jadi angka standar yang bisa dibandingkan antar-istilah: **z-score** dan **percentile** (dijelaskan awam di §6.3).
2. Series-series sekelompok dirata-rata jadi **pilar** (mis. pilar Real Yield = rata-rata z anggota blok B).
3. Enam pilar (A–F) dijumlah dengan bobot tetap → **regime score** antara −2 dan +2.
4. Label diambil dari kombinasi **state** tiap pilar (mis. Policy=CUTTING + Likuiditas=EXPANDING).
5. Score melewati ±0.5 = pergantian state (ambang ini sengaja: agar fluktuasi kecil harian tidak membuat label "kedip-kedip").

Bobot resmi v1 (DATA-SPEC §11.1):

| Pilar (blok) | Bobot | Pertanyaan yang dijawab pilar |
|---|---|---|
| A — Policy, Rates & Dollar | 0.20 | Bank sentral condong ke mana? Dolar menguat atau melemah? |
| B — Real Yield | 0.20 | Berapa "biaya kesempatan" memegang emas/uang tunai? |
| C — Inflasi | 0.15 | Inflasi memanas, stabil, atau mendingin? |
| D — Growth | 0.15 | Ekonomi ekspansi atau melambat? |
| E — Likuiditas & Fiskal | 0.15 | Uang beredar di sistem bertambah atau menyusut? |
| F — Stress, Vol & Sentimen | 0.15 | Pasar tenang atau panik? |

Perhatikan: G (positioning), H (flows), I (kalender) **tidak masuk bobot score**. Mereka lapisan timing dan konfirmasi — lihat §5.2. Ini keputusan desain yang bisa Anda tantang, dan alasan resminya: G/H menjawab "siapa yang sudah ikut serta" (bisa jadi kontraindikasi entry, mis. "tailwind TAPI crowded → tunggu pullback"), bukan "musim apa sekarang".

Selain regime score ada dua komposit pendamping (sama-sama dari DATA-SPEC §11):

- **Dalio quadrant**: sumbu growth momentum (dari blok D) × sumbu inflasi momentum (dari blok C) → 4 kuadran, masing-masing di-map ke kecenderungan return historis instrumen. Contoh: "growth STEADY × inflasi COOLING" = musim klasik yang ramah logam dan obligasi.
- **Dollar smile**: posisi dolar di kurva "senyum" — kanan (dolar kuat karena ekonomi AS unggul), tengah, atau kiri (dolar kuat karena dunia panik). Pakai DTWEXBGS momentum-20 hari + differential rate US−EU + PMI ex-US. Menentukan apakah dolar jadi tailwind atau headwind untuk seluruh book Anda.

### 2.3 Kenapa pendekatan "musim" cocok untuk timeframe swing Anda

Alasan ekonominya sederhana kalau diurai:

- **Data makro berdetak lambat.** Sebagian besar bahan sistem ini rilis mingguan atau bulanan (claims tiap Kamis, CPI tiap bulan, COT tiap Sabtu, SLOOS tiap kuartal). Detak seperti itu tidak bisa dimanfaatkan oleh trading 5-menit, tapi sangat relevan untuk posisi yang dipegang hari-minggu — persis detak Anda.
- **Biaya transaksi & noise.** Makin pendek horizon, makin besar porsi pergerakan yang benar-benar acak (noise) relatif terhadap sinyal. Di horizon swing, sinyal musim punya ruang untuk "kembali ke rata-rata" — kelebihan ramalan jangka pendek tidak pernah sempat terbayar.
- **Musim bisa salah, tapi bisa diverifikasi.** Karena setiap komponen musim adalah data publik ber-jadwal, Anda bisa mengaudit kapan pembacaan keliru, dan backtest (Fase F4) mengukur hit-rate historis per regime — sesuatu yang mustahil dilakukan pada "feeling" intraday.

### 2.4 Yang regime BUKAN

Regime bukan prediksi arah harga besok, bukan sinyal entry/exit otomatis, dan bukan kebenaran mutlak. Ia adalah **kompas kondisi**: memberi tahu arah angin dominan supaya keputusan posisi Anda (long/flat/size) punya konteks. Sistem juga sengaja menampilkan skor + label + bukti, bukan sekadar rekomendasi — keputusan tetap milik Anda. Satu penanda arah praktis dari contoh brief: label kombinasi yang menopang aset berisiko ditulis eksplisit ("score +1.2 → risk-on"); kombinasi sebaliknya (mis. HIKING + LIQUIDITY CONTRACTING + STRESS tinggi) akan terbaca sebagai musim defensif — dan pemetaan lengkap regime→bias per instrumen adalah bagian Fase F4 (BUILD-PLAN §1), bukan tebakan dibaca-baca dari skor mentah.

---

## 3. Glosarium istilah sistem

| Istilah | Arti untuk awam | Kenapa penting |
|---|---|---|
| Series | Satu deret data berurutan waktu (mis. "yield 10Y harian"). Satuan terkecil data sistem. | Semua analisis dibangun dari series; registry mencatat ±ratusan series. |
| Blok (A–I) | Kelompok series yang menjawab satu pertanyaan besar (mis. blok C = semua tentang inflasi). | Struktur mental utama sistem; brief dan CLI disusun per blok. |
| Pilar | Rata-rata z-score anggota satu blok yang masuk regime score (A–F saja). | Jembatan antara "banyak angka" dan "satu skor". |
| State | Label kata dari sebuah series/pilar: FALLING/FLAT/RISING, COOLING/STABLE/REACCEL, dsb. | Manusia membaca kata lebih baik daripada desimal; state adalah terjemahan resmi angka. |
| z-score | "Berapa langkah dari normal" — selisih nilai hari ini vs rata-rata 5 tahun, dibagi ukuran gejolak normalnya. Analogi: nilai ujian 80 baru bermakna kalau tahu rata-rata kelas 70 dan simpangan baku 5 (z = +2 = sangat di atas normal). | Bahasa umum untuk membandingkan hal yang beda satuan (bps, %, ribu orang). |
| Percentile | Posisi ranking hari ini dalam sejarahnya. "Persentil 8" = hanya 8% waktu historis yang lebih rendah. Analogi: peringkat 8 dari 100 ulangan. | Menjawab "ini ekstrem atau biasa?" tanpa asumsi bentuk distribusi. |
| Momentum-N | Perubahan selama N hari trading. Analogi: bukan posisi mobil, tapi kecepatannya. | Arah perubahan sering lebih penting dari level untuk swing trading. |
| Rata-rata berbobot | Rata-rata yang anggota tertentu dihitung lebih besar pengaruhnya. Analogi: nilai akhir kuliah = 40% UAS + 60% tugas. | Dipakai di bobot pilar, dan di surprise index (berita baru lebih berat, memudar 90 hari). |
| Surprise / deviation | Selisih angka rilis vs konsensus (dugaan ekonom), dinormalisasi jadi z. | Pasar bergerak pada kejutan, bukan pada angkanya; "Surprise US +8.2 → USD supportive" (contoh Agt-2026). |
| Primer / sekunder | Sumber utama sebuah series + cadangan resminya. | Kalau primer mati/aneh, sekunder menggantikan — dan selisih keduanya jadi alarm kualitas. |
| Tier 0–4 | Peringkat kepercayaan sumber (lihat §7). | Menentukan siapa yang dipercaya duluan saat dua sumber bertentangan. |
| Sumber gray / backdoor | Sumber yang diakses lewat jalur tidak-resmi (API tanpa dokumen, trik header). | Datanya sering unik dan berharga, tapi bisa berubah/mati sewaktu-waktu — wajib punya rencana cadangan. |
| Raw / derived | Raw = angka apa adanya dari sumber. Derived = hasil hitungan kita (z, state, skor). | Aturan emas: derived selalu bisa dihitung ulang dari raw. Tidak ada angka "hilang sumbernya". |
| Append-only | Tabel raw tidak pernah diedit; koreksi = baris baru. | Revisi data resmi (sering terjadi!) tercatat, bukan menimpa sejarah. |
| Vintage | "Edisi" sebuah nilai — angka yang diketahui pada tanggal tertentu, termasuk sebelum direvisi. | Mencegah kecurangan backtest: sistem 2026 tidak boleh "tahu" angka revisi tahun 2023 lebih awal dari waktunya. |
| Look-ahead bias | Kesalahan analisis historis yang memakai informasi yang belum tersedia saat itu. | Musuh nomor satu backtest; kolom `release_ts` ada khusus untuk ini. |
| Freshness stamp | Tanda usia data: tiap series punya jadwal rilis resmi; lewat jadwal tanpa update = ditandai basi. | Data basi yang dipakai diam-diam lebih berbahaya daripada data kosong. |
| Degradasi | Mode turun nilai: sumber mati → sistem turun ke cadangan dan MENULIS itu di brief. | Supaya Anda selalu tahu kualitas pagi ini lebih rendah dari biasanya. |
| Brief | Lembar ringkasan harian (contoh penuh di DATA-SPEC §14). | Produk akhir yang Anda baca tiap pagi sebelum sesi AS. |
| UTC / WIB / ET | UTC = jam standar dunia (penyimpanan). WIB = jam tampilan Anda. ET = waktu bursa AS (jadwal rilis). | Selisih WIB–ET 11 jam saat EDT (Mar–Nov), 12 jam saat EST. Salah konversi = salah baca jadwal CPI/FOMC. |
| Regime score | Angka −2…+2 hasil bobot enam pilar; label musim diambil dari kombinasi state. | Kesimpulan paling atas dari seluruh pipeline. |
| Risk-on / risk-off | Suasana pasar yang berani (dana masuk aset berisiko) vs defensif (dana lari ke safe-haven). | Cara tercepat menerjemahkan musim ke sikap portofolio. |
| Tailwind / headwind | Angin punggung (mendorong posisi Anda) vs angin sakit (melawan). | Brief memakai kata ini per instrumen, hasil gabungan beberapa blok. |
| Crowded | Terlalu banyak orang di posisi yang sama (diukur z-score positioning). | Kontraindikasi entry: kerumunan yang panik keluar bersamaan = gerakan melawan Anda. |
| Squeeze | Gerakan harga cepat karena terjepitnya posisi ramai (bukan karena berita baru). | Kenapa sistem memantau konsentrasi positioning + stok fisik (silver/copper). |
| Karantina | Primer & sekunder bertentangan melebihi toleransi → keduanya tidak dipakai + flag. | Sistem memilih jujur kosong daripada diam-diam salah. |
| Golden anchor | Nilai harapan terkunci per series dari riset (mis. DGS10=4.67 @2026-08-27) untuk gerbang kebenaran F0. | Ujian berulang bahwa fetcher mengambil data yang BENAR, bukan sekadar data yang ADA. |
| As-of join | Cara menggabung series berfrekuensi beda: pakai nilai terakhir yang SUDAH dirilis pada tanggal itu. | Varian look-ahead: menggabung dengan angka yang belum terbit = backtest curang. |
| `INSUFFICIENT` | State resmi saat data terlalu sedikit untuk dihitung z-nya. | Sistem bilang "belum tahu", bukan mengarang angka. |
| Identitas harian | Pemeriksaan matematika tiap pagi (mis. yield riil ≈ nominal − breakeven). | Jaring pengaman terakhir sebelum brief terbit. |

---

## 4. Peta dokumen proyek

| Dokumen | Peran (satu kata) | Isinya | Kapan Anda buka |
|---|---|---|---|
| `docs/DATA-SPEC.md` | **APA** | Kamus data resmi: 9 blok, semua series, sumber primer/sekunder, jadwal, jebakan per sumber, hasil verifikasi live | Mau tahu "data ini asalnya darimana dan bisadipercaya?" |
| `docs/BUILD-PLAN.md` | **BAGAIMANA** | Cetak biru teknis: fase F0–F5 + gerbang mutu, skema database, rumus transform terkunci, struktur CLI | Mau tahu "gimana dihitungnya dan gimana dijaga kebenarannya?" |
| `docs/explained/` | **KENAPA** | Edukasi berbahasa awam, satu dokumen per blok + dokumen 00 ini | Belajar & menantang keputusan desain |
| `docs/methodology/` | **RISET** | Kajian riset (contoh yang ada: `inflation-regimes.md`) | Mau paham dasar riset di balik sebuah keputusan |
| `CLAUDE.md`, `API.md` | KONTEKS | Daftar langganan & API key aktif | Operasional, bukan konsep |

Urutan baca yang disarankan: dokumen 00 ini → brief contoh (DATA-SPEC §14) → dokumen blok sesuai instrumen favorit Anda (mulai blok B untuk gold) → methodology bila ingin dalam.

---

## 5. Peta 9 blok + bagaimana saling terhubung

### 5.1 Sembilan blok

| Blok | Nama | Pertanyaan inti | Contoh output brief (nilai Agt-2026) |
|---|---|---|---|
| A | Policy, Rates & Dollar | Fed/ECB/BoE condong apa? Dolar ke mana? | "pasar price 2 cut s/d Des (68%)"; "10Y 4.67%, 2s10s +39bps, STEEPENING"; "dolar melemah 0.4%/20d → tailwind metals+BTC" |
| B | Real Yield | Yield setelah dipotong inflasi naik atau turun? | "DFII10 2.34% FALLING (−15bps/20d) → tailwind gold" |
| C | Inflasi (+ kanal energi) | Inflasi arahnya bagaimana? | "CPI 3m-ann 2.8% COOLING"; "WTI 83.9, OVX 46 → pantau energi" |
| D | Growth (+ non-US) | Ekonomi & tenaga kerja? (termasuk China/EA/UK) | "GDPNow Q3 2.8% (dari 2.6%)"; "claims 203K, MA turun 3 minggu" |
| E | Likuiditas & Fiskal | Uang sistem bertambah/berkurang? Tekanan fiskal? | "Net liq $5.8T, +$45B/w → EXPANDING"; "xccy Dec26 −4.0bp → funding normal" |
| F | Stress, Vol & Sentimen | Pasar ketat-uang atau longgar? Vol tinggi? | "HY 263bps = persentil 8"; "vol silver 46 vs gold 24 → sizing XAG ½ XAU" |
| G | Positioning (COT) | Siapa sudah numpuk di posisi mana? | "Gold MM z+1.8 crowded long — jangan chase" |
| H | Flows & Crypto-Native | Uang sungguhan masuk/keluar instrumen? | "GLD +2.1t (konfirmasi)"; "BTC ETF +$240M"; "PBoC beli 7 bulan berturut" |
| I | Kalender & Data Momentum | Event apa yang datang? Data akhir-akhir ini mengejutkan tidak? | "CPI Kam 19:30 WIB"; "Surprise US +8.2 → USD supportive" |

### 5.2 Cara blok-blok terhubung

```text
                    ┌──────────────────────────────┐
                    │  REGIME SCORE  (−2 … +2)     │
                    │  = 0.20·A + 0.20·B + 0.15·C  │
                    │    + 0.15·D + 0.15·E + 0.15·F│
                    └──────────────┬───────────────┘
      A ── Policy/Rates/Dolar ─┐   │
      B ── Real Yield ─────────┤   │         G ── Positioning ──┐
      C ── Inflasi ────────────┼───┤                            ├──► IMPLIKASI PER
      D ── Growth ─────────────┤   │         H ── Flows ────────┘    INSTRUMEN (book)
      E ── Likuiditas ─────────┤   │              (lapis konfirmasi
      F ── Stress/Vol ─────────┘   │               & timing, di luar skor)
                                   ▼
              QUADRANT (D × C)  +  DOLLAR SMILE (A)
                                   │
      I ── Kalender/Surprise ── radar & bobot kejutan (mengubah "seberapa
                                 percaya diri" membaca hari itu, bukan musimnya)
```

Tiga jenis peran:

1. **Blok pembentuk musim (A–F)**: masuk regime score dengan bobot §2.2. C dan D juga jadi sumbu quadrant; A jadi input dollar smile.
2. **Blok konfirmasi & timing (G, H)**: tidak mengubah skor, tapi mengubah implikasi. Contoh nyata dari brief: XAUUSD tailwind (dari B dan A) TAPI COT gold z+1.8 crowded → kesimpulan "tunggu pullback", bukan "kejar". Flows GLD +2.1t berfungsi memvalidasi bahwa kenaikan harga gold memang dibeli demand barat, bukan sekadar short-squeeze.
3. **Blok radar (I)**: kalender memberi tahu kembali risiko event (hari CPI, FOMC), surprise index memberi tahu apakah arus data akhir-akhir ini mendukung atau melawan pembacaan musim.

Ketergantungan lintas blok juga eksplisit di spec: net liquidity (E) di-cross-check dengan stablecoin supply (H); divergence gold↔real yield (B) hanya dianggap serius bila central-bank buying (H) aktif; funding stress (E) dibaca bersama stress pasar (F); positioning dolar (G, ICE DXY futures) melengkapi pembacaan dolar (A).

### 5.3 Urutan belajar yang disarankan

| Prioritas | Blok | Alasan untuk profil Anda |
|---|---|---|
| 1 | B — Real Yield | Driver #1 XAUUSD; konsepnya paling perlu dikuasai sampai bisa menantang |
| 2 | A — Policy & Dollar | Fed = penggerak lintas-semua-instrumen; dolar = driver silang book |
| 3 | E — Likuiditas | Driver utama BTC; menjelaskan "kenapa semua naik bersamaan" |
| 4 | F — Stress & Vol | Bahasa sizing: kapan vol menentukan setengah posisi |
| 5 | G + H | Lapis konfirmasi/timing entry swing |
| 6 | C, D, I | Radar & konteks; penting tapi paling banyak rilis resmi (lebih stabil) |

---

## 6. Prinsip HULU-KE-HILIR dan CLI `arkwatch explore`

### 6.1 Rantainya

Setiap angka di brief punya rantai yang sama arah (dari hulu/sumber ke hilir/kesimpulan):

```text
sumber asli (FRED/CME/...) → fetcher → raw_observations (append-only, raw murni)
  → transform (z / percentile / momentum / rumus blok) → computed_signals (state + inputs_json)
  → komposit (pilar → skor / quadrant / smile) → baris brief
```

Dua aturan yang membuat rantai ini bisa diikuti sampai tuntas (BUILD-PLAN §0 dan §8):

- **Raw append-only**: angka mentah tidak pernah ditimpa. Derived selalu bisa dihitung ulang dari raw.
- **`inputs_json` merujuk series_id, bukan nilai tempelan**: setiap sinyal mencantumkan dari series mana ia dihitung — jadi jejaknya tidak pernah putus.

### 6.2 Perintah eksplorasi (dari BUILD-PLAN §8)

```text
arkwatch explore blocks                      # daftar 9 blok + deskripsi
arkwatch explore block E                     # semua series blok E: nilai kini, state, freshness, sumber
arkwatch explore series FRED:WALCL           # profil: definisi, satuan, jadwal rilis, primer/sekunder,
                                             #   + riwayat + vintage revisi + status cross-val
arkwatch explore series SYN:NETLIQ --trace   # RANTAI HILIR-KE-HULU: tunjukkan input (WALCL, RRP, TGA),
                                             #   transform, inputs_json, hingga raw fetch_log
arkwatch explore signal REGIME_SCORE --trace # dari raw semua pilar → z → state → bobot → skor
arkwatch export block F --csv                # data mentah per kategori untuk analisis sendiri
```

Artinya: Anda tidak perlu percaya skor +1.2. Anda bisa menjalankan `--trace` dan melihat enam pilar, z masing-masing, dan series mentahnya. Brief juga mencantumkan id series di tiap angka — klik/teleport langsung ke hulunya.

### 6.3 Konsep transform, dijelaskan untuk awam

Ini kosakata "dapur" tempat angka mentah dimasak. Spesifikasi teknis lengkap ada di BUILD-PLAN §3; di sini konsepnya saja:

- **z-score = "berapa aneh hari ini?"** Ambil rata-rata 5 tahun sebagai "normal", dan simpangan baku (ukuran gejolak normal) sebagai "satuan langkah". z = +2 artinya hari ini dua langkah lebih tinggi dari biasanya — kejadian yang jarang. Window 5 tahun menyesuaikan frekuensi (harian ≈ 1.260 hari trading; mingguan 260; bulanan 60). Kalau data terlalu sedikit (< 80% window), state = `INSUFFICIENT` — sistem lebih memilih bilang "belum tahu" daripada mengarang angka.
- **Percentile = "peringkat di kelas".** "HY 263bps = persentil 8" berarti spread kredit junk hari ini lebih rendah dari 92% sejarahnya — pasar sangat tenang/komplean (yang justru bisa berarti rawan kejutan). Percentile dan z saling melengkapi: percentile tidak mengasumsikan data berbentuk lonceng.
- **Momentum = kecepatan, bukan posisi.** Yield 10Y di 4.67% adalah posisi; "−15bps dalam 20 hari" (contoh Agt-2026) adalah kecepatan turun. Untuk swing, kecepatan sering mendahului perubahan cerita.
- **Rata-rata berbobot = nilai akhir kuliah.** Bobot pilar (A lebih berat dari C) satu jenis; surprise index jenis lain: kejutan lama bobotnya memudar eksponensial selama 90 hari, seperti berita kemarin yang makin lama makin tak terasa.
- **State = terjemahan kata.** Contoh aturan blok A: FALLING/FLAT/RISING dengan ambang ±10bps/20 hari; blok G: |z|>1.5 = crowded. Ambang ini parameter tercatat, bukan selera — Anda boleh menantangnya dengan membuka registry.

### 6.4 Dua contoh jalan rantai (nilai Agt-2026)

- **SYN:NETLIQ (net liquidity)**: hulu = `WALCL` (balance sheet Fed, $6.73T), `RRPONTSYD` (reverse repo), TGA (rekening pemerintah, contoh 950.804 juta USD = $950,8 miliar pada 2026-08-27). Rumus = WALCL − RRP − TGA → $5.8T, +$45B/minggu → state EXPANDING. Satu baris brief, tiga sumber resmi, satu pengurangan — semuanya bisa di-trace.
- **REGIME_SCORE**: hulu = ratusan series A–F → z per series → rata-rata per pilar → bobot → +1.2 → label "EASING + LIQUIDITY EXPANDING". Trace penuh memperlihatkan pilar mana yang menarik naik dan mana yang menahan.

---

## 7. Hirarki tier sumber 0–4 — dan kenapa ada aturan primer/sekunder

### 7.1 Lima tier (taksonomi resmi BUILD-PLAN §0)

| Tier | Kelas | Contoh anggota | Sifat |
|---|---|---|---|
| 0 | Institusi resmi | FRED, CFTC, Treasury, NY Fed, Cleveland Fed, Atlanta Fed, ECB, CBOE, SAFE, LBMA-CDN, Philly Fed, NBER | Penyusun angka resmi; gratis; paling lambat berubah |
| 1 | Langganan berbayar | EODHD, FMP | Andal, punya data unik (mis. CMDI, HGUSD copper), tapi terikat kuota/plan |
| 2 | Market-data gratis | Yahoo, TwelveData | Praktis untuk harga historis panjang; tanpa jaminan resmi |
| 3 | Gray / backdoor | Backdoor CME settlements, view QuikStrike, kalender TradingView, Farside, stealth CNN | Data sering unik (mis. vol silver/copper/platinum dari CVOL); tapi jalurnya tidak resmi — bisa mati/berubah kapan saja |
| 4 | Sintetis / computed | XAGGBP = XAGUSD ÷ GBPUSD; xccy basis dari 3 settlement; net liquidity; MOVE proxy | Bukan "diambil" tapi "dihitung"; benar selama rumus + input benar |

### 7.2 Kenapa hirarki dan aturan primer/sekunder ada

Tiga alasan ekonomi:

1. **Kepercayaan berjenjang.** Saat dua sumber bertentangan, sistem tidak melempar koin: `v_latest` memakai nilai dari tier terendah (paling resmi) yang sehat.
2. **Kerapuhan berbeda-beda.** Sumber gray wajib punya cadangan karena bisa mati mendadak. Aturan DATA-SPEC §0.1: primer+sekunder wajib untuk (a) semua sumber gray, (b) setiap series yang jadi baris headline brief. Lembaga resmi boleh single-source asal freshness check aktif (§0.2) — data lewat jadwal rilisnya tanpa update ditandai basi, bukan dipakai diam-diam.
3. **Tanpa fallback diam-diam (no silent fallback).** Kalau primer dan sekunder saling bertentangan melebihi toleransi, KEDUANYA dikarantina + baris peringatan muncul di brief. Ini desain yang mahal (Anda kehilangan angka hari itu) tapi jujur — angka salah-tapi-tampil lebih berbahaya daripada angka kosong-ditandai.

Contoh nyata pentingnya tier: vol implied metal non-gold (silver 45.9, copper 26.8, platinum 38.9 — contoh Agt-2026) hanya ada di sumber tier-3 (CVOL, tanpa historis). Konsekuensinya dijaga dengan harvester append-only dan peringatan eksplisit — bukan disembunyikan. Contoh kebalikan: yield Treasury diambil dari FRED (tier 0) dengan kurva par Treasury resmi sebagai pembanding identitas harian.

---

## 8. Siklus harian sistem (jadwal fetch, DATA-SPEC §13)

| Waktu (WIB) | Aktivitas | Kenapa jam itu |
|---|---|---|
| 06:00 | FRED harian + cross-check FMP/EODHD | Data bursa AS (yang ditutup pagi WIB) sudah final; cross-val dilakukan sebelum brief terbit |
| 06:30 | Kalender union-4 (FMP ∪ EODHD ∪ TV ∪ CME) + merge tabel kurasi + surprise + flows crypto-native | Kalender & flows crypto tersedia 24 jam; cukup sekali sebelum sesi |
| 07:00 | Generate & kirim **US Session Brief** | Sampai sebelum pembukaan sesi Eropa/AS yang relevan bagi swing Anda |
| Harian (gray) | FedWatch-DIY snapshot, GLD/funding/OI/stablecoin, backdoor CME (settlements, CVOL, VOI) | Sumber gray ber-retensi pendek (settlements CME hanya 5 hari kerja) → HARUS diambil tiap hari, gap >3 hari = hilang permanen; CVOL diambil pagi WIB karena fixing terbit ≤21:00 ET hari sebelumnya |
| Sabtu 03:00 | COT pull + brief positioning akhir pekan | CFTC merilis Jumat 15:30 ET = Sabtu 02:30 WIB saat EDT (03:30 saat EST) |
| Event-driven | H.4.1 dirilis → refetch WALCL/WRESBAL; event GDPNow → refetch GDPNOW | Angka komponen likuiditas & nowcast baru masalah setelah dokumen sumbernya terbit |

Dua konsekuensi yang perlu Anda ingat:

- **Ritme Sabtu berbeda**: positioning selalu basi data Selasa (itulah tanggal lapor COT), dirilis Sabtu. Ini sifat datanya, bukan bug sistem — dan alasan kolom `release_ts` ada (anti look-ahead 3 hari).
- **Zona waktu**: simpan UTC, tampil WIB, jadwal bursa ET. Bulan Maret–November (EDT) selisih WIB–ET 11 jam; November–Maret (EST) 12 jam. Contoh: "CPI Kam 19:30 WIB" pada bulan Agustus karena 08:30 EDT + 11 jam = 19:30 WIB.

### 8.1 Ritme yang lebih panjang dari sehari

| Periode | Aktivitas | Asal keputusan |
|---|---|---|
| Sabtu pagi | Brief positioning akhir pekan (khusus COT) | Jadwal rilis CFTC |
| Mingguan | Job ALFRED vintage: refetch series yang suka direvisi (ICSA, CPIAUCSL, PAYEMS, GDPNOW, M2SL, WALCL) → revisi di-append sebagai baris vintage | Mekanisme §18.2 DATA-SPEC |
| Bulanan | Data PBoC emas (SAFE XLSX); LBMA silver vault bulanan | Jadwal penerbit masing-masing |
| Kuartalan | WGC central-bank gold (insert manual via CLI dengan review); re-kalibrasi: re-run verify-sources + golden anchor segar | WGC bot-gated; tangga kalibrasi BUILD-PLAN §6.2 |
| Tiap Januari | Cek jadwal FOMC vendored vs situs federalreserve.gov (tervendoring s/d 2028-01) | Aturan operasional §17 DATA-SPEC |

---

## 9. Cara membaca brief + jebakan salah-baca umum

### 9.1 Anatomi brief (dari contoh DATA-SPEC §14)

1. **REGIME + QUADRANT** — dua baris kesimpulan musim (dan skor).
2. **Berubah semalam** — hanya delta; supaya mata Anda langsung ke yang bergerak.
3. **Pilar** — state enam pilar pembentuk skor.
4. **Positioning (COT)** — lapis konfirmasi/kontraindikasi.
5. **Flows** — uang sungguhan masuk/keluar.
6. **Implikasi book** — per instrumen Anda, selalu dengan kata "TAPI" bila ada konflik.
7. **Minggu ini + Anomali** — radar event dan alarm.

### 9.2 Jebakan umum (paling sering menipu)

- **Membaca skor sebagai sinyal entry.** Skor +1.2 mendukung bias long risk; timing entry, stop, dan sizing tetap analisis Anda. Brief bahkan sering menulis kebalikan timing: "tailwind TAPI crowded → tunggu pullback".
- **Lupa COT mingguan-lag.** "Gold MM z+1.8" menggambarkan posisi per Selasa yang lalu, dirilis Sabtu. Dalam pasar yang bergerak cepat, positioning bisa sudah berubah.
- **Bingung z vs percentile vs level.** Level 4.67% pada 10Y tidak bilang apa-apa tanpa konteks; z bilang "2 langkah dari normal"; percentile bilang "peringkat 95 dari 100". Ketiganya beda pertanyaan.
- **Menyamakan VXN level dengan rasio.** Vol NASDAQ secara struktural memang lebih tinggi dari VIX S&P — karena itu yang dipakai adalah RASIO VXN/VIX terhadap historisnya sendiri ("persentil 80 → US500 > US100"), bukan angka mentahnya.
- **Menganggap divergence gold↔real yield pasti kekal.** Gold naik meski yield riil naik itu flag yang hanya dianggap serius bila ada konfirmasi struktural (central bank aktif beli di blok H) — bukan undang-undang alam.
- **Menyalahartikan "tenang".** HY persentil 8 atau xccy ≤4bp itu kabar BAIK untuk stability tapi berarti pasar tidak mencemaskan — kondisi yang justru rawan kejutan. Baca "tenang" sebagai "tidak ada asuransi yang dibeli", bukan "tidak akan ada masalah".
- **Mengabaikan flag kualitas.** Mode degradasi, data basi, dan karantina cross-val ditampilkan di brief dengan sengaja. Hari ketika brief penuh flag = hari untuk memperkecil keyakinan (dan sering: memperkecil size).
- **Membaca satu hari terlalu besar.** State di-flip hanya di ±0.5; perubahan harian kecil memang seharusnya tidak mengubah label. Kalau label berubah, itu baru berita.

### 9.3 Satu pagi membaca brief, langkah demi langkah (contoh nilai Agt-2026)

1. Baris REGIME dulu: "EASING + LIQUIDITY EXPANDING (+1.2 → risk-on)" — sikap umum hari ini: kondusif aset berisiko.
2. Baris QUADRANT: "growth STEADY × inflasi COOLING" — musim "pertumbuhan dis-inflasi", ramah logam & indeks.
3. "Berubah semalam": apakah ada yang GERAK? Contoh: DFII10 −3bps, GDPNow naik 2.6→2.8%, dolar −0.4%/20d. Tiga dari ini konsisten arahnya dengan musim → keyakinan naik.
4. Pilar: cari pilar yang MENYIMPANG dari musim (contoh: OVX 46 tinggi di tengah inflasi cooling) — itulah kandidat anomali yang diulang di baris paling bawah.
5. Positioning & flows: periksa apakah konfirmasi (GLD +2.1t) atau kontraindikasi (gold z+1.8 crowded). Impilikasi book sudah menggabungkan ini untuk Anda, lengkap dengan "TAPI".
6. Minggu ini: rencanakan ukuran risiko menjelang event besar (CPI Kam 19:30 WIB) — bahkan musim yang benar bisa terguncang sekejap oleh rilis.

---

## 10. Keterkaitan spesifik per instrumen Anda

Peta cepat "blok mana yang paling menggerakkan apa" — detail penuh di dokumen blok masing-masing:

| Instrumen | Blok paling relevan | Catatan kunci |
|---|---|---|
| XAUUSD (gold) | **B** (driver #1 real yield), A (dolar), E (term premium/fiskal), G+H (crowding & CB/GLD) | Contoh: "DFII10 2.34% FALLING → tailwind"; divergence flag bila CB buying aktif |
| XAGUSD (silver) | B, A, + **F** (CVOL SIVL 45.9 vs GCVL ~24 → sizing ½ XAU), H (LBMA vault) | Squeeze watch = positioning + stok vault |
| XPTUSD (platinum) | B, A, F (POVL 38.9), G | Data lebih tipis; vol sendiri baru diakumulasi |
| XCUUSD (copper) | **D non-US** (China PMI/USDCNY), H (stok COMEX + curve), G (konsentrasi top-4) | "Caixin 49.8 → netral"; spot EODHD basi → pakai futures HG |
| BTC / ETH | **E** (net liquidity), H (ETF flows, funding, OI, stablecoin), F | "likuiditas ↑ + flow ↑, funding sehat" = kombinasi favorit; funding ekstrem = alarm leverage |
| US100/500/30 | D (growth), F (VIX/VXN curve, HY, NFCI), A | Rasio VXN/VIX persentil 80 → rotasi US500 > US100 |
| EURUSD / GBPUSD / majors | **A** (differential rate US−EU/UK; path ECB via ESR; BoE), D non-US (EA/UK), G (TFF per mata uang) | ESR implied "ECB +45bp s/d Des-26" (contoh Agt-2026) = bahan XAUEUR juga |
| DXY | A first-class (DTWEXBGS + dollar smile), G (ICE DXY futures positioning) | DXY = driver silang seluruh book, bukan sekadar satu lagi simbol |
| XAUEUR / XAGGBP dll | Kombinasi: leg metal (B/A) + leg fiat (A/EU, D-EA); XAGGBP sintetis | Jejak per leg bisa di-trace terpisah |

---

## 11. Yang bisa salah: degradasi, kualitas data, keterbatasan

### 11.1 Mode degradasi per sumber (DATA-SPEC §11.4)

| Kalau sumber ini mati | Sistem melakukan | Efek ke brief |
|---|---|---|
| Backdoor CME (FedWatch) | Turun ke Atlanta Fed MPT | Baris ekspektasi diganti "probabilitas range 3M" (semantik beda — dilabeli) |
| Fear & Greed (stealth) | Baris sentiment dihilangkan | CBOE put/call tetap tampil |
| Farside (ETF flows) | Mirror BitMEX/CoinGlass, atau "flow: N/A" | Baris flow hilang/berganti sumber |
| TradingView | Kalender tetap FMP ∪ EODHD + kurasi | Jam presis speeches bisa berkurang sumbernya |

Prinsip umum: degradasi SELALU tertulis di brief. Tidak ada "diam-diam pakai data lama".

### 11.2 Kualitas data & keterbatasan struktural

- **Sumber gray bisa mati sewaktu-waktu** (backdoor, view, stealth). Retensi settlements CME hanya 5 hari kerja — harvester bolong >3 hari = data hilang permanen; itu risiko operasional yang diterima dengan sadar.
- **CVOL tanpa historis**: z-score/percentile vol metal non-gold baru valid setelah ±1 tahun akumulasi sendiri; setahun pertama hanya level + perbandingan antar-simbol. Break struktural (perubahan tenor Mar-2026) dicatat di registry sebagai reset window.
- **Beberapa series muda utk backtest panjang**: xccy basis & ESR mulai akumulasi saat build; backtest jangka menengahnya terbatas (dicatat sebagai pengecualian resmi di BUILD-PLAN §4). Backtest 10 tahun otherwise memakai surrogate panjang (ADS 1960→, CFNAI 1967→, NBER).
- **Surprise historis tipis pre-2018** → ESI historis ditandai `low_conf`.
- **Rumus v1 bisa berubah**: bobot, ambang state, dan rumus komposit adalah parameter terkalibrasi — dihitung ulang dari raw bila berubah (prinsip derived-recomputable), dan re-kalibrasi dijadwalkan kuartalan.
- **Ekspektasi pasar ≠ ramalan masa depan.** Angka seperti "pasar price 2 cut s/d Des (68%)" adalah KONSENSUS yang sudah terkandung di harga (implied dari futures), bukan prediksi tentang apa yang akan Fed putuskan. Kegunaannya: mengukur kejutan — bila Fed berbeda dari 68% itu, pasar terguncang. Jangan membaca angka implied sebagai " forecasts yang pasti".
- **Revisi data mengubah sejarah.** Banyak series resmi direvisi (itulah mekanisme vintage ada). Pembacaan "live" di masa lalu bisa berbeda dari pembacaan "final" hari ini — backtest yang jujur memakai versi yang diketahui saat itu (kolom `release_ts`), dan karena itu hasil backtest tidak akan pernah identik dengan ingatan membaca brief.
- **Sistem membaca, bukan meramal**: regime score adalah deskripsi musim berjalan dengan semua keterbatasan datanya. Ia tidak melihat black swan, tidak tahu geopolitik yang belum masuk data, dan tidak menggantikan manajemen risiko.

### 11.3 Jaminan yang memang ada (supaya proporsional)

Sebagai penyeimbang: setiap angka lewat gerbang F0 (golden anchors — nilai harapan terkunci, mis. DGS10 = 4.67 pada 2026-08-27; ICSA = 203.000; TGA = 950.804 juta USD; GCVL = 23.9999), sanity range, depth-check, dan cross-val berkarantina; identitas harian dijalankan sebelum brief (mis. yield riil ≈ nominal − breakeven); deteksi revisi via vintage; alarm anti-drift struktur respons. Detail di BUILD-PLAN §5–§6 — dan itulah alasan Anda boleh menantang angka apa pun lewat `arkwatch explore ... --trace`.

---

*Berikutnya: `docs/explained/01-block-a-policy-rates-dollar.md` dst. — satu dokumen per blok, struktur sama (kenapa ada → glosarium → peta data → logika hulu-ke-hilir → cara baca brief → keterkaitan instrumen → mode gagal).*
