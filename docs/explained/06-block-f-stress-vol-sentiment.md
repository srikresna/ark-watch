# Blok F — Stress, Volatilitas & Sentiment (dijelaskan dari nol)

> Bagian dari seri dokumen edukasi `docs/explained/`. Dituju untuk pemilik sistem: trader ritel swing (hari–minggu) di XAU/XAG/XPT/XCU, BTC/ETH, US100/500/30, EURUSD & majors, DXY.
> Rujukan teknis: [DATA-SPEC.md](../DATA-SPEC.md) §6 (Blok F), §0 (prinsip), §11 (sinyal komposit), §19.4 (CVOL); [BUILD-PLAN.md](../BUILD-PLAN.md) §3 (transform Blok F), §8 (eksplorasi hulu-ke-hilir).
> Semua contoh angka bertanda **(contoh nilai Agt-2026)** diambil langsung dari spec — bukan ilustrasi karangan.

---

## 1. Kenapa blok ini ada

Blok-blok lain di mesin ini menjawab "bagaimana kondisi ekonominya". Blok F menjawab tiga pertanyaan yang berbeda sifatnya:

1. **Seberapa takut pasar?** (stress) — kredit, funding, CDS.
2. **Seberapa besar getaran yang pasar harapkan?** (volatilitas) — ini yang menentukan **ukuran posisi Anda**.
3. **Suasana hati pasar sekarang apa?** (sentiment) — biasanya dibaca terbalik: euforia = hati-hati, panik = sering titik beli.

**Analogi rumah sakit.** Bayangkan pasar sebagai pasien. Blok A–E adalah hasil laboratorium organ: jantung (policy Fed), tekanan darah (yield), paru-paru (likuiditas). Blok F adalah **monitor denyut jantung + alat ukur tekanan + wajah pasien** — bukan diagnosis penyakitnya, tapi kondisi *saat ini*: apakah pasien panik, tenang berlebihan, atau getir-getir manis. Pasien yang sehat bisa tiba-tiba panik, dan pasien yang sakit bisa tampak tenang karena sedang dibius. Monitor ini yang paling cepat berubah — sering berubah *sebelum* laboratorium keluar.

**Kenapa penting untuk Anda khususnya:**

- Semua instrumen Anda bergerak dalam dua "mode" besar: **risk-on** (orang berani ambil risiko — saham & BTC naik, emas kalah pamor) dan **risk-off** (orang cari aman — emas naik, saham & BTC ditekan). Blok F adalah alat deteksi mode paling langsung. Korelasi antar-instrumen Anda berubah mengikuti mode ini — saat stress tinggi, "diversifikasi" antara BTC dan US500 bisa menguap karena keduanya jatuh bersamaan.
- **Volatilitas = bahan baku sizing.** Bukan "harga akan naik atau turun", tapi "berapa besar ayunan yang diharapkan". Vol silver ~2x vol gold **(contoh nilai Agt-2026: SIVL 45.9 vs GCVL ~24.0)** — artinya posisi silver harus kira-kira setengah ukuran posisi gold agar risikonya sama. Ini dijelaskan penuh di §6.
- Blok F punya **bobot 15%** pada regime score (bobot resmi §11: A .20, B .20, C .15, D .15, E .15, **F .15**). Saat stress melonjak, skor bisa membalik dari risk-on ke risk-off meski fundamental tak berubah.

---

## 2. Glosarium istilah Blok F

| Istilah | Arti dalam bahasa sehari-hari | Kenapa penting buat Anda |
|---|---|---|
| **Credit spread** | Selisih bunga obligasi perusahaan vs obligasi pemerintah AS = "premi asuransi gagal bayar". Perusahaan berisiko harus bayar bunga lebih tinggi; selisihnya itulah spread. | Barometer keberanian pasar paling halus. Melebar cepat = pasar mulai takut perusahaan bangkrut. |
| **HY (high yield) / "junk"** | Obligasi perusahaan peringkat kredit rendah — peminjam "penghasilan tidak tetap, belum cek hisab keuangan". Premi asuransinya mahal dan sensitif. | HY adalah bagian pasar yang pertama panik. Sinyal dini risk-off. |
| **IG (investment grade)** | Obligasi perusahaan peringkat baik — "penghasilan tetap, koperasi kredibel". Spreadnya lebih kaku. | Divergensi IG vs HY informatif: kalau HY melebar tapi IG tidak, paniknya lokal; kalau keduanya melebar, paniknya sistemik. |
| **OAS (option-adjusted spread)** | Cara menghitung spread yang "memurnikan" obligasi ber-opsi. Teknis — cukup tahu ini standar penghitungan BAML. | Supaya angka spread HY/IG konsisten dibanding antarwaktu. |
| **NFCI** | Indeks Kondisi Keuangan Chicago Fed — komposit banyak ukuran (rate, spread, dolar, dll; kerap dikutip ~100 indikator — *konteks umum, bukan angka spec*) dalam satu angka. Negatif = kondisi longgar, positif = ketat. | "Rata-rata rapor" seluruh sistem keuangan, gratis, resmi. Contoh: **NFCI −0.57 = longgar (contoh nilai Agt-2026)**. |
| **CMDI** | Corporate Market Distress Index buatan NY Fed — indikator distress pasar kredit perusahaan, skala membaca seperti probabilitas 0–1 (*konteks umum, bukan dari spec*). Ada varian market/IG/HY. | **Leading** (mendahului), pendamping spread BAML yang **lagging** (menyusul). Lift sebelum harga obligasi benar-benar jatuh. |
| **CDS (credit default swap) sovereign** | Asuransi gagal bayar negara. Kalau premi asuransi utang AS naik = pasar mulai mempertanyakan keuangan AS. | Tail risk fiskal. Naiknya CDS AS biasanya sejalan "debasement trade" — cerita positif emas. |
| **VIX** | Indeks volatilitas tersirat saham S&P 500 dari harga opsi = "harga asuransi terhadap saham anjlok 30 hari ke depan". Naik = asuransi mahal = takut. | Regime vol ekuitas; menular ke BTC & risk assets. |
| **Volatilitas tersirat (implied vol)** | Getaran yang *dipertaruhkan uang sungguhan* di pasar opsi — bukan getaran masa lalu. | Lebih maju dari vol historis: pasar opsi membeli "informasi" tentang event mendatang. |
| **Term structure vol** | Bentuk kurva asuransi: premi 30 hari (VIX) vs 90 hari (VIX3M/VXV) vs 9 hari (VIX9D) vs 6 bulan (VIX6M). | Bentuk kurva = psikologi: panik sesaat atau tenang structural. |
| **Contango** | Kondisi normal: asuransi jangka panjang lebih mahal dari jangka pendek (VIX < VXV). Seperti asuransi perjalanan 90 hari pasti lebih mahal dari 30 hari — waktu lebih lama, risiko tercover lebih banyak. | Latar normal; pasar "mengharga waktu". |
| **Backwardation** | Abnormal: premi 30 hari LEBIH MAHAL dari 90 hari (VIX > VXV). Orang panik butuh perlindungan SEKARANG, tidak peduli besok. | Salah satu **anomali alarm** resmi sistem (§11.5). Sering muncul di titik klimaks jualan. |
| **VXN** | "VIX-nya Nasdaq-100" — vol tersirat indeks US100. | Level mentahnya struktural selalu > VIX (Nasdaq memang lebih "gugup") — karena itu dipakai sebagai **rasio VXN/VIX** (lihat §4). |
| **GVZ** | Indeks vol tersirat gold (CBOE, dari opsi ETF emas GLD). | Regime vol emas → langsung menentukan sizing XAUUSD. |
| **OVX** | Indeks vol tersirat minyak. | Event risk energi — kanal inflasi headline (blok C). Contoh: **OVX 46 (contoh nilai Agt-2026)** → "waspadai energi". |
| **CVOL** | Indeks vol tersirat buatan CME untuk futures — mencakup **metal (GCVL gold, SIVL silver, HGVL copper, POVL platinum), FX major, energi, rates**. Plus suite lengkap: atm, **skew**, upvar/dnvar, convexity. | **Vol tersirat silver/copper/platinum tidak ada di sumber gratis mana pun selain ini** — alasan utama backdoor CME dipertahankan. |
| **Skew** | Perbedaan harga opsi naik vs opsi turun. Di metal, call mahal = ada pihak buru-buru lindungi/hitung pergerakan NAIK. | "Tell" squeeze/rally (kata spec §6): demand searah naik sebelum harga bergerak. |
| **Upvar / dnvar / convexity** | Variasi vol saat pasar naik vs turun; convexity = kelengkungan harga opsi. Detail lanjutan suite CVOL. | Pelengkap analisis skew; disimpan di tabel `cvol_snapshots`. |
| **MOVE (proxy)** | "VIX-nya obligasi" — volatilitas yield. Versi kami = **proksi yang dihitung sendiri** dari getaran yield 10Y (formula §4). | Vol rates = ketidakpastian kebijakan; naik biasanya ramah gold, menekan saham growth. |
| **Put/call ratio** | Perbandingan volume opsi "beli asuransi turun" (put) vs "tiket naik" (call). | Sentiment. Ekstrem rendah = euforia (semua beli tiket naik); ekstrem tinggi = kapitulasi. |
| **Fear & Greed (CNN)** | Skor 0–100 dari ~7 komponen (momentum, kekuatan harga, breadth, put/call, vol, demand junk bond, safe haven). | Barometer suasana cepat; sumber gray — bisa mati (lihat §7). |
| **Persentil** | Posisi nilai hari ini di ranking 5 tahun terakhir. Persentil 8 = hanya 8% waktu dalam 5 tahun lebih rendah dari ini. | Alat baku Blok F: **lebih penting dari level mentah** (kenapa — lihat §4.1). |
| **Z-score** | Jarak nilai dari rata-rata, diukur dalam satuan "simpangan baku". z=+2 = dua kali tingkat getar normal di atas rata-rata. | Bahasa umum seluruh pilar regime score. |
| **Notional** | Nilai total sebuah posisi (jumlah kontrak × harga satuan) — "berapa rupiah yang sebenarnya dipertaruhkan gerak pasar". | Kata kunci rumus sizing §6.1: `notional XAG ≈ ½ notional XAU` untuk risiko setara. |
| **Flight-to-quality** | "Lari ke aset aman": saat takut, dana pindah dari aset berisiko (saham, kredit junk) ke Treasury/gold. | Kenapa stress tinggi justru sering menjadi angin baik arah gold (§6.2). |
| **Debasement (trade)** | "Perdagangan penurunan mutu uang": taruhan bahwa utang/defisit besar akan menurunkan nilai mata uang jangka panjang → beli emas. | Cerita di balik CDS AS naik + term premium naik → ramah gold (§6.2). |

---

## 3. Peta data — apa, siapa, kapan, kenapa, cara baca

Konvensi tier (BUILD-PLAN §0): T0 institusi resmi · T1 langganan berbayar · T2 market-data gratis · T3 gray/backdoor. Jadwal fetch keseluruhan: FRED 06:00 WIB; sumber gray harian; brief 07:00 WIB (DATA-SPEC §13).

### 3.1 Kredit & stress sistemik

| Series | Apa itu sebenarnya | Penerbit & jadwal | Kenapa dipilih (alternatif ditolak) | Cara baca angka |
|---|---|---|---|---|
| `BAMLH0A0HYM2` — HY spread | Yield obligasi junk AS minus Treasury, OAS, harian | ICE BofA (dulu Bank of America Merrill Lynch) dihitung; FRED memuat harian setelah sesi AS tutup (T0) | Standar industri, historis panjang, resmi | **Persentil 5y, bukan level mentah** (§4.1). Contoh: **HY 263bps = persentil 8 (contoh nilai Agt-2026)** → pasar sangat percaya diri |
| `BAMLC0A0CM` — IG spread | Idem untuk perusahaan peringkat baik | Idem (T0) | Melengkapi HY | Bandingkan dengan HY: divergensi = panik lokal vs sistemik |
| `NFCI` | Komposit indikator kondisi keuangan (kerap dikutip ~100 — *konteks umum, bukan angka spec*) | Chicago Fed, mingguan (T0) | Satu angka buatan bank sentral — sulit ditandingi | Negatif = longgar. Contoh: **−0.57 = longgar (contoh nilai Agt-2026)** |
| CMDI (EODHD `/credit-risk/corporate/cmdi`) | Indikator distress kredit perusahaan versi NY Fed (skala probabilitas-like 0–1 — *konteks umum, bukan dari spec*); varian market/IG/HY | NY Fed, **mingguan**, 1.129 minggu historis; diambil via EODHD (T1) | **Tidak ada di FRED** — EODHD satu-satunya jalur rapi (temuan audit §16); leading, melengkapi BAML yang lagging | Level + Δ mingguan; **divergensi IG-vs-HY sendiri informatif** (kata spec §6) |
| CDS sovereign AS (EODHD `/credit-risk/sovereign/cds-spreads`) | Premi asuransi gagal bayar utang AS | EODHD, harian (T1) | Tail risk fiskal tidak tercover BAML/NFCI | Spread + Δ; tren naik = cerita debasement → ramah gold |

### 3.2 Volatilitas ekuitas

| Series | Apa | Penerbit & jadwal | Kenapa dipilih | Cara baca |
|---|---|---|---|---|
| `VIXCLS` — VIX | Vol tersirat SPX 30 hari | CBOE menghitung (real-time); FRED memuat nilai penutupan harian; sekunder TradingView (T0 → T2) | Standar dunia | Level + **persentil**; >30 umumnya panik, <13 komplacen — tapi tetap baca persentil |
| `VXVCLS` — VIX3M | Vol tersirat 3 bulan. **Catatan spec: VXV = VIX3M adalah SATU series — jangan didaftarkan dua kali** | FRED, harian (T0) | Kaki panjang term structure | Dibandingkan dengan VIX: `VIX < VXV` = contango (normal); `VIX > VXV` = **backwardation = anomali alarm (§11.5)** |
| VIX9D, VIX6M | Ujung pendek & panjang kurva | CBOE CSV dari `cdn.cboe.com` (T0). Catatan §18.5: VIX1D memang tidak ada di FRED — CDN satu-satunya | Melengkapi kurva jadi rasio 9D/30D/3M/6M | Kurva "terbalik penuh" = panik akut |
| `VXNCLS` — VXN | Vol tersirat Nasdaq-100 | FRED, harian (T0) | Vol US100 | **JANGAN baca levelnya langsung** — VXN struktural selalu di atas VIX. Dipakai sebagai **RASIO VXN/VIX** dibandingkan historis rasio itu sendiri (z-sendiri). Rasio di persentil tinggi = Nasdaq relatif lebih ditakuti → condong US500 daripada US100. Contoh: **rasio di persentil 80 → US500 > US100 (contoh nilai Agt-2026, baris brief §14)** |

### 3.3 Volatilitas komoditas — jantung blok ini buat instrumen Anda

| Series | Apa | Penerbit & jadwal | Kenapa dipilih | Cara baca |
|---|---|---|---|---|
| `GVZCLS` — GVZ | Vol tersirat gold (dari opsi GLD) | FRED, harian (T0) | Historis panjang untuk z gold | **Persentil → sizing**. Contoh: **"GVZ persentil 75 → sizing kecil" (contoh kalimat spec §6)** |
| `OVXCLS` — OVX | Vol tersirat minyak | FRED, harian (T0) | Event risk energi → kanal CPI | Flag; contoh: **OVX 46 = persentil ekstrem → "pantau energi" (contoh nilai Agt-2026)** |
| **CVOL suite** (backdoor CME `GET /services/cvol?symbol=GCVL,SIVL,HGVL,POVL,MVL,EUVL,GBVL,JPVL,ADVL,CAVL,FXVL,CLVL,NGVL,TYVL,USVL,SRVL`) | Vol tersirat futures: logam (GCVL gold, SIVL silver, HGVL copper, POVL platinum, MVL), FX major (EUVL/GBVL/JPVL/ADVL/CAVL, FXVL), energi (CLVL minyak, NGVL gas), rates (TYVL 10Y, USVL 30Y, SRVL SOFR — dalam basis poin). Suite per simbol: cvol, atm, **skew**, upvar, dnvar, convexity | CME, anonim, **harian; fetch setelah 21:00 ET** (fixing dari pre-clearing settlement terbit ≤21:00 ET → fetch pagi WIB aman). Tier T3 gray | **Vol metal non-gold (silver/copper/platinum) tidak ada di sumber gratis mana pun** — ini unik. Skew = tell squeeze/rally. Bonus: vol FX major (untuk jarak stop EURUSD dll) & bp-vol rates | **Contoh nilai Agt-2026: SIVL silver 45.9 · HGVL copper 26.8 · POVL platinum 38.9 · GCVL ~24.0** (anchor F0: GCVL 23.9999 @ 2026-08-28). Cross-section antar-logam valid langsung — "vol silver 46 vs gold 24 → sizing XAG ½ XAU" |

### 3.4 Volatilitas rates

| Series | Apa | Penerbit | Kenapa | Cara baca |
|---|---|---|---|---|
| MOVE proxy (computed) | Vol yield Treasury 10Y: `std(ΔDGS10, 20d) · √252 · 100` dalam bps — dihitung sendiri dari `DGS10` FRED | Computed (T4); indeks MOVE resmi milik ICE = berlisensi/berbayar → ditolak, proksi memenuhi prinsip raw+derived (§0.4) | Vol rates = ketidakpastian kebijakan/fiskal | Level + spike; spike = yield bergerak liar |

### 3.5 Sentiment

| Series | Apa | Penerbit & jadwal | Kenapa | Cara baca |
|---|---|---|---|---|
| Put/call total (`totalpc.csv`) & S&P saja (`spxpc.csv`) | Rasio volume put vs call | CBOE CDN, harian (T0) | Satu-satunya sumber sentiment berbasis transaksi opsi riil; tetap hidup walau F&G mati | **Z-score**; ekstrem kedua arah = kontraindikator |
| Fear & Greed CNN | Skor 0–100 komposit ~7 komponen | CNN dataviz, harian; **stealth = gray, degradable (T3)** | Barometer suasana yang orang banyak kenal | 0–100; >75 greed / <25 fear sebagai patokan kasar untuk *menahan diri*, bukan sinyal entry |

Yang **tidak** dipakai dan kenapa: FMP `/sentiments` digugurkan di audit §16 (proxy GLD saja, crypto diam-diam dihapus dari response); historis CVOL resmi = lisensi DataMine berbayar → digantikan harvester append-only sendiri (§19.4); futures VX (VIX-futures) tidak ada di CME (milik Cboe) — bukan masalah karena term structure dibangun dari indeks VIX/VXV saja.

---

## 4. Logika hilir-ke-hulu: dari angka mentah ke regime score

Rantai penuh bisa ditelusuri sendiri: `arkwatch explore block F` → `arkwatch explore series SYN:MOVE --trace` → sampai `raw_observations` + `fetch_log` (BUILD-PLAN §8).

### 4.1 Konsep transform, dijelaskan dulu

- **Persentil — kenapa dipakai, bukan level mentah.** "HY 263bps" tidak mengatakan apa-apa tanpa konteks: di era rate rendah 263bps bisa sudah mahal, di era stress bisa sangat murah. Yang stabil bermakna adalah posisinya di ranking 5 tahun terakhir: **persentil 8** berarti " pasar lebih percaya diri dari 92% waktu dalam 5 tahun". Analogi: nilai 7 dalam ulangan tidak berarti apa-apa sampai tahu median kelas.
- **Z-score.** `(x − rata-rata) / simpangan baku` — "berapa 'deviasi' dari normal". Beda dengan persentil: z menjaga jarak (z 2.0 lebih ekstrem daripada 1.2), persentil hanya ranking. Spesifikasi resmi (BUILD-PLAN §3): z dihitung pada **level**, σ **populasi**, window **5 tahun sesuai frekuensi** (harian = 1.260 hari trading), **min-obs 80%** — kalau data kurang, state = `INSUFFICIENT`, bukan angka ngawur. Persentil = rank pada window yang sama.
- **Rasio (kasus VXN).** Banyak series punya "level normal" yang berbeda-beda strukturalnya. VXN selalu > VIX karena Nasdaq memang lebih volatile — membandingkan level mentahnya seperti membandingkan denyut nadi pelari marathon dengan pengangkat beban saat jalan. Solusi spec: bandingkan **VXN/VIX dengan historis rasio itu sendiri** (z rasio). Rasio naik = ketakutan berkonsentrasi di sisi growth/tech.
- **Momentum** = arah pergerakan N hari trading (untuk series harian). Dipakai sebagai pelengkap arah.
- **Aritmetika proksi MOVE.** Ambil perubahan yield 10Y tiap hari selama 20 hari → hitung simpangan bakunya (getaran harian rata-rata) → tahunkan dengan `√252` (aturan akar-waktu: getaran menumpuk seperti pekerjaan acak, bukan linear) → kalikan 100 jadi bps. Hasil: "yield 10Y berayun ±X bps setahun ke depan jika getaran terkini berlanjut".
- **Rata-rata pilar.** Pilar F = rata-rata z anggota-anggotanya (arah dibakukan: z positif = lebih stress), lalu masuk regime score dengan bobot.

**Contoh hitung terperinci (mekanisme; angka ilustrasi)** — mis. HY spread 5 tahun terakhir punya rata-rata 350bps dan simpangan baku 110bps:
- Hari ini HY = 263bps (level nyata dari spec, contoh nilai Agt-2026) → `z = (263 − 350)/110 ≈ −0.79` → jauh di bawah normal = sangat tenang/komplacen.
- Persentil: dari 1.260 hari trading, hanya ~8% hari lebih rendah → **persentil 8** (angka persis seperti baris spec "HY 263bps = persentil 8").
- Perhatikan dua ukuran ini sepakat arah, tapi z juga memberi tahu "seberapa jauh" (−0.79 ≈ hampir satu deviasi), sementara persentil memberi tahu "seberapa jarang".

**Contoh hitung term structure (ilustrasi mekanisme):**
- Kondisi normal (contango): VIX 16, VXV 18 → rasio VIX/VXV ≈ 0.89 < 1 → premi 30 hari lebih murah dari 90 hari — sehat, waktu dihargai wajar.
- Stress (backwardation): VIX 27, VXV 22 → rasio ≈ 1.23 > 1 → asuransi bulan ini lebih mahal dari 3 bulan = pasar membeli kepanikan *sekarang*. Inilah pemicu anomali §11.5.

### 4.2 Pipeline per kelompok (sesuai transform-spec Blok F, BUILD-PLAN §3)

1. **Kredit**: HY & IG → z 5y + persentil; CMDI level+Δ (leading); CDS spread+Δ. Anomali resmi §11.5: **"HY percentile ekstrem"** memicu alert di kedua arah (terlalu ketat = komplacen; terlalu lebar = distress).
2. **VIX family**: VIX → level+persentil; **term structure VIX/VXV → state contango/backwardation** (backwardation = anomali alarm §11.5); VIX9D/VIX6M melengkapi kurva sebagai rasio; VXN → **rasio VXN/VIX → z-sendiri → persentil**.
3. **Vol komoditas**: GVZ & OVX → persentil (historis panjang FRED). CVOL → lihat aturan interim di bawah.
4. **MOVE proxy**: formula §3.4 → level + deteksi spike. Uji resmi: spot-check terhadap publikasi MOVE & percentile vs scipy (gerbang F3).
5. **Put/call → z-score. F&G → skor 0–100 apa adanya.**

### 4.3 Aturan interim CVOL (keputusan v1.4, penting dipahami)

CVOL **tidak punya historis** (parameter tanggal diabaikan diam-diam oleh endpoint; historis = produk DataMine berbayar). Konsekuensinya:

- **Tahun pertama**: tampilkan **level mentah** + **persentil relatif antar-simbol CVOL** (cross-section: SIVL vs GCVL vs POVL vs HGVL dibandingkan sesama — valid tanpa historis karena satuan sama).
- **Setelah ±1 tahun data sendiri terkumpul** (harvester append-only mulai hari pertama build; hari tak ter-fetch = **hilang permanen**) → z/percentile masing-masing simbol diaktifkan.
- **GVZCLS tetap primer historis gold** — GCVL dan GVZ beda konstruksi (futures vs opsi ETF), jadi **z masing-masing terhadap historisnya sendiri, jangan dicampur**.
- **Break struktural tercatat di registry**: GCVL/SIVL ganti tenor-group Mar-2026; komposisi MVL berubah Nov-2025 → **window z di-reset per tanggal break** (mencampur sebelum/sesudah break = membandingkan apel dengan jeruk).

### 4.4 Dari pilar ke regime score

Formula resmi §11: `regime score (−2…+2) = Σ (bobot_pilar × z̄_pilar)`; state flip di ±0.5. Blok F bobot **0.15**.

Ilustrasi aritmetika (angka rekaan untuk mekanisme, bukan angka spec): jika rata-rata z Blok F bergerak dari 0 ke +1.0 (stress naik satu deviasi), skor komposit bergerak 0.15 ke arah risk-off. Besar? Tidak — sendiri. Tapi blok F sering jadi yang bergerak *pertama* dan *serentak* (semua anggotanya naik bersamaan saat kepanikan), sehingga kontribusi riilnya di momen kritis lebih terasa dari bobotnya. Contoh tampilan brief **(contoh baris Agt-2026)**: `Stress=CALM (HY p8)` — state pilar disebut + angka kuncinya.

---

## 5. Membaca baris Blok F di brief + jebakan salah-baca

Baris-blok-F dalam contoh brief §14 **(contoh nilai Agt-2026)**:

```text
Pilar  : ... Stress=CALM (HY p8)
Inflasi=COOLING (WTI 83.9 tenang, OVX 46 tinggi → waspadai)
• US500>US100 (rasio VXN/VIX persentil 80)
• XCUUSD : China PMI 49.8 tipis — netral
Anomali: OVX 46 persentil ekstrem — pantau energi
```

Cara membaca contoh di atas: stress kredit tenang (HY hanya persentil 8 → risk-on berjalan, tapi pasar "lupa sabuk pengaman"); OVX tinggi = ada kegelisahan spesifik energi (kanal inflasi — pantau CPI headline); ketakutan berkonsentrasi di Nasdaq (rasio VXN/VIX persentil 80) → relatif lebih aman di US500.

**Jebakan salah-baca umum:**

| Jebakan | Salah baca | Yang benar |
|---|---|---|
| Persentil rendah = aman | "HY persentil 8, bagus, santai" | Persentil rendah = **komplacen** — asuransi murah justru saat bahan bakar kejutan menumpuk. Baca sebagai "risk-on TAPI rawan kejutan", bukan "aman" |
| Level VXN dibanding VIX | "VXN 28 > VIX 18 → jual Nasdaq" | VXN struktural selalu > VIX. Yang bermakna hanyalah **rasio VXN/VIX vs historisnya sendiri** |
| VXV didobel | Memasukkan VIX3M dan VXV sebagai dua series | **Satu series yang sama** (spec §6) — dobel = pilar ter-bobot ganda |
| Backwardation dibaca terlambat | Menunggu brief besok | Term structure terbalik sering hanya bertahan hitungan jam–hari; ini anomali *real-time-ish* |
| GCVL vs GVZ dicampur | "GVZ 24, GCVL 24, z gabung saja" | Beda konstruksi — z masing-masing terhadap historis sendiri (§4.3) |
| CVOL di-z-kan di tahun pertama | "SIVL z +1.5" | Belum ada historis — hanya level & cross-section antar simbol sampai ±1 tahun data sendiri |
| Put/call dibaca literal | "Put/call naik = pasar pasti turun" | Ekstrem tinggi justru sering menandai *dasar* (kapitulasi). Ini alat kontra-indikator |
| F&G sebagai sinyal entry | "Greed 80 → short sekarang" | Skor komposit lambat & bias momentum; gunanya menahan diri saat euforia, bukan timing |
| MOVE diangkap indeks resmi | "MOVE 110 (ICE)" | Ini **proksi computed** — angka dekat tapi tidak identik dengan indeks berlisensi |
| Angka mentah CVOL diangkap closing resmi | "SIVL 45.9 = penutupan resmi kemarin" | Endpoint mengembalikan **snapshot print live terakhir**, bukan fixing EOD resmi (spec §19.4) |

---

## 6. Keterkaitan spesifik per instrumen Anda

### 6.1 Vol → sizing: hubungan paling praktis di seluruh blok ini

Prinsip: **risiko posisi ≈ ukuran × volatilitas**. Kalau target risiko per posisi konstan, maka `ukuran ∝ 1/vol`. Analogi: jalanan berlubang = pelankan mobil; jalanan mulus = boleh gas. Vol tersirat adalah "peta lubang" versi pasar opsi — dan pasar opsi menang taruhan uang sungguhan, jadi peta mereka layak diikuti.

Contoh konkret dari angka spec **(contoh nilai Agt-2026)**:

- Gold vol (GCVL/GVZ) ~**24**% tahunan → getaran harian kira-kira `24/√252 ≈ 1.5%` per hari.
- Silver vol (SIVL) **45.9**% → `≈ 2.9%` per hari — hampir **2x** gold.
- Maka untuk risiko setara: `notional XAG ≈ notional XAU × (24/45.9) ≈ setengah`. Persis baris spec: **"vol silver 46 vs gold 24 → sizing XAG ½ XAU"**.
- Contoh kalimat spec lain: **"GVZ persentil 75 → sizing kecil"** — bahkan tanpa membandingkan antar-logam, vol gold yang duduk di kuartil teratas historisnya sendiri sudah cukup alasan memperkecil posisi XAUUSD.

Ini juga alasan rasio stop-loss: jarak stop yang masuk akal ~ berbanding lurus vol — vol 2x = stop 2x lebar = posisi ½ agar rupiah yang dipertaruhkan sama.

### 6.2 Tabel implikasi arah

| Instrumen | Saluran utama dari Blok F | Cara pakai |
|---|---|---|
| **XAUUSD** | Stress (HY/VIX spike) → flight-to-quality → bid. MOVE spike → ketidakpastian policy → ramah gold. CDS AS naik → debasement → ramah gold. GVZ/GCVL → sizing | Stress tinggi = angin baik arah naik; TAPI vol juga tinggi → posisi kecil dengan stop lebar, bukan besar |
| **XAGUSD** | Arah sama dengan gold, amplifikasi beta ~1.5–2x *(konteks umum, bukan dari spec — vol ~2x terverifikasi via SIVL 45.9 vs GCVL ~24)*. Skew CVOL = tell squeeze | Sizing ±½ XAU; skew call mahal = waspadai gerak vertikal naik (jangan kosong saat squeeze) |
| **XPTUSD** | POVL 38.9 **(contoh nilai Agt-2026)** — vol platinum lebih liar dari gold | Sizing proporsional lebih kecil lagi; platinum juga bawa sisi industri (risk-off membekap demand) |
| **XCUUSD** | Copper = logam "pertumbuhan": HY melebar / NFCI naik = kabar buruk sisi demand | Stress naik = bias turun XCU; gabungkan blok D (China PMI, §4) & stok COMEX (blok H) |
| **BTC/ETH** | Asset risk-on penuh: VIX backwardation + HY spike historis menekan BTC. Sentiment crypto spesifik (funding, F&G crypto) ada di blok H — CNN F&G di blok F adalah sentiment pasar umum | Stress sistemik = perkecil/cover; F&G CNN jangan diterapkan literal ke crypto |
| **US100/500/30** | VIX & persentil = sizing indeks. **Rasio VXN/VIX persentil 80 → US500 > US100** (contoh baris spec) | Saat rasio tinggi: rotasi ke US500/US30, kurangi US100 |
| **EURUSD & majors** | Risk-off → USD dicari (dolar naik, majors turun — terhubung "dolar smile" blok A). CVOL FX (EUVL/GBVL/JPVL/ADVL dll) = jarak stop & sizing per pair | Vol FX naik = perdalam stop/kecilkan posisi; arah dibaca lewat dolar (blok A) |
| **XAUEUR / XAGGBP / crosses** | Cross metal = gabungan dua kaki: vol logam (CVOL/GVZ) + vol leg FX (CVOL FX) | Stress di euro-area tidak terlihat dari VIX — cek EUVL & leg ECB (blok A); sintetis XAGGBP memakai GBPUSD (§10) |
| **DXY** | Dolar adalah "asuransi" global — stress naik = USD bid | Konfirmasi silang arah majors; positioning DXY di blok G |

### 6.3 Checklist praktis sebelum entry swing (memakai Blok F saja)

1. **Cek dulu sizing, baru arah.** Berapa persentil vol instrumen ini (GVZ/SIVL/POVL/HGVL atau VIX/EUVL)? Di kuartil atas → posisi otomatis lebih kecil, stop lebih lebar. Di persentil rendah → pasar mungkin terlalu tenang; jangan terkejut oleh kejutan (lihat juga HY persentil).
2. **Cek mode.** `VIX < VXV`? HY tidak sedang melesat? → mode risk-on berjalan: bias umumnya ramah BTC/indeks, netral-berat gold. `VIX > VXV` atau HY melompat persentil dalam hitungan hari → mode risk-off: emas diuntungkan arah, tapi vol tinggi = ukuran kecil.
3. **Cek relative value indeks.** Rasio VXN/VIX di persentil tinggi → rotasi US500/US30 dari US100 (baris spec: "US500>US100").
4. **Cek skew kalau main silver/platinum.** Call mahal relatif (skew naik) = pasar opsi menyiapkan gerak vertikal — jangan kosong total saat squeeze, dan sadari stop mungkin tersapu dulu.
5. **Jangan pakai F&G/put/call untuk timing entry** — gunakan untuk menahan diri saat euforia ("semua sudah di dalam") dan mengenali kapitulasi.

---

## 7. Yang bisa salah: degradasi, kualitas data, keterbatasan

### 7.0 Gerbang uji khusus Blok F (dari BUILD-PLAN)

Sebelum angka Blok F dipercaya, pipeline harus lulus uji resmi (gerbang F3):

- **MOVE proxy spot-check** terhadap publikasi indeks MOVE — memastikan proksi tidak melenceng dari rujukan dunia nyata.
- **Percentile vs scipy** — persentil pipeline harus identik dengan pustaka statistik standar (anti bug ranking).
- **Unit test bersama z-score/percentile** (spesifikasi umum §3 BUILD-PLAN): σ populasi, window 5y, min-obs 80% → `INSUFFICIENT`.
- **Golden anchor** (gerbang F0): nilai terkunci dari riset — contoh **GCVL = 23.9999 @ 2026-08-28** — fetcher yang tiba-tiba balas nilai lain = alarm drift, bukan "data baru".

### 7.1 Mode degradasi per sumber (prinsip §0.3: semua gray degradable)

| Sumber mati | Mode degradasi resmi |
|---|---|
| **Fear & Greed (CNN stealth)** | Baris sentiment **dihilangkan dari brief** — CBOE put/call tetap tampil (aturan §11.4 eksplisit) |
| **CVOL (backdoor CME)** | Vol metal non-gold jadi "N/A" — **tidak ada pengganti gratis** (alasan endpoint ini dipertahankan walau gray); GVZ/OVX dari FRED tetap hidup; kolom ditandai basi, bukan diam-diam dikosongkan |
| **TradingView (sekunder VIX)** | FRED primer (T0) tetap cukup — single-source resmi diperbolehkan asal freshness check aktif (§0.1–0.2) |
| **CBOE CDN** | VIX9D/VIX6M & put/call hilang → kurva vol tak lengkap; VIX/VXV inti tetap dari FRED |
| **EODHD** | CMDI & CDS hilang → kredit tinggal keluarga BAML/NFCI (FRED) |
| **FRED (DGS10 untuk MOVE)** | Failover kurva: FMP `/stable/treasury-rates` / Treasury XML par (§16, §18.3) |

### 7.2 Kualitas data & jebakan operasional

- **CVOL tanpa historis & bolong permanen**: harvester append-only; hari tak ter-fetch = hilang selamanya (logika retensi §17). Bolong >3 hari trading = alarm. Snapshot ≠ fixing resmi; parameter tanggal diabaikan diam-diam — jangan pernah mencoba "backfill".
- **Break struktural CVOL** (tenor-group Mar-2026, MVL Nov-2025): z harus di-reset per tanggal break; lupa = z palsi.
- **Fixing vs brief**: CVOL terbit ≤21:00 ET (= ±08:00 WIB pagi saat EDT) — baris brief pagi memakai fixing sesi terakhir yang sudah final, bisa T-1 untuk komponen ini. Wajar, bukan bug. Kalimat ini dan jebakan "snapshot, bukan closing resmi" di §5 melukiskan DUA konsep berbeda, bukan kontradiksi: endpoint memang selalu mengembalikan snapshot print live terakhir kapan pun ditanya (itulah jebakan §5 untuk pemakai intraday); karena harvester kita baru jalan SETELAH fixing ≤21:00 ET terbit, snapshot yang tertangkap justru fixing final sesi tersebut — itulah yang dipakai brief pagi.
- **VIX di hari pendek/Jumat** dan pasca-libur: sampel opsi tipis, angka bisa liar — persentil menolong di sini.
- **Put/call bergeser struktural** seiring kebiasaan hedging institusi berubah: z jangka bergerak lebih dapat dipercaya daripada level absolut.
- **F&G komposit** menggabungkan komponen yang sebagian sudah dipakai blok lain (vol, put/call, demand junk bond) — jangan diperlakukan sebagai informasi *tambahan* independen dari pilar; lebih tepat dibaca sebagai "ringkasan suasana".
- **Min-obs 80%**: series muda otomatis state `INSUFFICIENT` — brief jujur menampilkan kekosongan, bukan angka ngawur.

### 7.3 Keterbatasan konseptual (yang perlu Anda tantang kalau dirasa kurang)

1. **Vol tersirat bukan prediksi arah** — ia mengukur lebar ayunan, bukan arah. pasar opsi terkenal salah ukur saat regime berganti total (crash yang "tidak masuk akal" datang justru saat vol rendah/komplacen — persentil 8 itu).
2. **Sentiment = alat disiplin, bukan sinyal timing.** Ekstrem bisa bertahan berminggu-minggu lebih lama dari margin trader bertahan.
3. **Bobot F 15% adalah pilihan desain** — bisa diperdebatkan (beberapa aliran menomorsatukan credit spread sebagai indikator siklus utama). Kalibrasi formula v1 memang dinyatakan bisa berubah (§11), dan semua sinyal bisa dihitung ulang dari raw (`inputs_json`) kalau kalibrasi direvisi.
4. **Cross-section CVOL tahun pertama** membandingkan logam sesama CVOL — valid, tapi tidak bisa menjawab "apakah silver 46 ini tinggi *menurut sejarah silver*". Untuk itu harus menunggu ±1 tahun akumulasi sendiri.

---

*Dokumen edukasi; kebenaran teknis merujuk DATA-SPEC v1.4 §6/§19.4 dan BUILD-PLAN v1.1 §3. Rantai angka siapa pun di brief dapat ditelusuri: `arkwatch explore block F` / `arkwatch explore series <id> --trace`.*
