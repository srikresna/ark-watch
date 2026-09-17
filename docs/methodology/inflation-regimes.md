# METHODOLOGY — Inflation Regimes & Strategi per Aset
> Seri: deep-dive metodologi (dokumen terpisah agar bisa dalam). Status: **full-text read 2026-08-30** — 30 hlm PDF versi JPM tersimpan di `docs/methodology/assets/P154_The_best_strategies.pdf`.
> Sumber: [SSRN 3813202](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3813202) · [Duke Scholars](https://scholars.duke.edu/publication/1494610) · versi jurnal: *Journal of Portfolio Management* 47(8), 2021.
> Jalur unduh: SSRN diblok Cloudflare JS-challenge (403 "Just a moment..." bahkan dengan curl_cffi chrome/safari/edge) → **berhasil via halaman author Duke**: [P154_The_best_strategies.pdf](https://people.duke.edu/~charvey/Research/Published_Papers/P154_The_best_strategies.pdf) (1,8 MB). Catatan: paper ini memenangkan **Bernstein Fabozzi/Jacobs Levy Award 2022** (best JPM article 2021).

## Paper: "The Best Strategies for Inflationary Times"
Neville, Draaisma, Funnell, **Harvey** (Duke/NBER), Van Hemert — 2021. **US + UK + Jepang, 95 tahun.** Ditulis justru karena tiga dekade sebelumnya tak ada inflasi berarti di pasar maju — sama seperti masalah kita: sample regime inflasi "hidup" itu langka.

### Temuan (terverifikasi dari abstrak)
1. **Inflasi tak terduga buruk bagi aset tradisional** — obligasi dan saham; inflasi *lokal* efeknya terbesar.
2. **Komoditas positif selama lonjakan inflasi** — TAPI "variasi cukup besar DI DALAM kompleks komoditas" (≠ semua metal sama).
3. **Trend-following = proteksi paling andal** di antara strategi dinamis saat shock inflasi penting.
4. **Faktor ekuitas aktif** (profitabilitas, value — dari ringkasan publikasi) memberi hedging sebagian.
5. Membahas pula fine art & **rasional kripto sebagai komponen proteksi inflasi**.

## Deep-read full-text (2026-08-30)

### (a) Definisi regime inflasi mereka — persis
Sumber: CPI **headline YoY** (bukan core). Aturan lengkap:
1. **Mulai**: inflasi YoY *akselerasi* dan level "naik material melewati 2%" — didefinisikan operasional sebagai **menembus ≥5%**. (Justifikasi: 2% = desil-4, 5% = desil-8 dari distribusi YoY inflasi AS 1926–2021; 2% juga anchor psikologis bank sentral.)
2. **Akhir regime**: saat YoY mencapai puncak **tanpa pernah jatuh di bawah 50% dari rate maksimum dalam jendela observasi 24-bulan berjalan** — boleh volatil di level tinggi, boleh bikin higher-highs, episode tidak putus.
3. **Episode baru**: inflasi masih >2% tapi sempat turun <50% dari puncak trailing 24-bulan lalu berakselerasi lagi menembus >5%.
4. **Durasi minimum 6 bulan** — lebih pendek dianggap bukan perubahan regime (harga aset sensitif ke inflasi jangka panjang, bukan bulanan).
5. Hasil: **8 regime AS** (1926–2021) = 19% dari bulan; 14 regime UK; 12 regime Jepang (total 34 episode). Episode AS: WW2-entry '41–'42, End-of-WW2 '46–'47, Korean War '50–'51, Bretton Woods '66–'70 (48 bln), OPEC '72–'74, Iranian Revolution '77–'80 (38 bln), Reagan Boom '87–'90 (46 bln), China Demand Boom '07–'08 (11 bln).
6. Penting: **threshold mereka di LEVEL (≥5%), bukan "kenaikan X pp dalam N bulan"**. Komponen "akselerasi" hanya menyatakan arah menuju level itu; dan regime hanya menangkap **bagian positive-surprise** (akselerasi sampai puncak) — bagian deselerasi meski level masih tinggi dikecualikan.

### (b) Hasil kuantitatif per aset (real, annualized, 8 regime AS; "Other" = di luar regime)
| Aset/strategi | Regime inflasi | Other | Hit rate | t-stat |
|---|---|---|---|---|
| **Trend all-asset** (A) | **+25%** | +15% | 8/8 | **2.8** |
| Trend komoditas (A) | +20% | +8% | 8/8 | 2.8 |
| Trend bonds (A) | +15% | +9% | 8/8 | 1.9 |
| Komoditas energi | **+41%** | –1% | 8/8 | 1.8 |
| Komoditas industri (=tembaga!) | +19% | +4% | 80% | 1.7 |
| Komoditas agregat | +14% | +1% | **8/8** | 1.7 |
| **Gold** | **+13%** | –1% | 67% (4/6) | **3.1** (tertinggi di kompleks komoditas) |
| Silver | +12% | –5% | 80% | 1.1 |
| Precious (XAU+XAG+XPT) | +11% | –2% | 80% | 1.7 |
| Softs / agris / livestock | +8% / +7% / +7% | ±0% | 60–80% | 1.6–1.8 |
| TIPS (sintetis 1959–) | +2% | +3% | 60% | –0.6 |
| Momentum ekuitas C-S (A) | +8% | +4% | 75% | 0.6 (lemah) |
| Quality QMJ (A) | +3% | +3% | 60% | –0.1 |
| Value HML (A) | –1% | +2% | 25% | –1.5 |
| Size SMB (A) | –4% | +1% | 25% | –1.8 |
| Low-vol BAB (A) | –3% | +8% | 25% | –4.2 |
| Sektor ekuitas energi | +1% | +8% | 50% | –1.4 |
| Gold miners (granular C1) | +7% | +1% | 80% | — |
| Real estate residensial AS | –2% | +2% | 25% | –5.1 |
| Ekuitas pasar (P) | **–7%** | +10% | 25% | –4.8 |
| Treasury 2Y / 10Y / 30Y | –3% / –5% / –8% | +2/+4/+5% | 13–25% | –5.0 s/d –5.8 |
| IG / HY credit | –7% / –7% | +6% | 13% | –8.1 / –7.8 |
| Portofolio 60–40 | –6% | +8% | 25% | –6.0 |
| Art / wine / stamps | +7% / +5% / +9% | +2–3% | 50–75% | — |

Catatan kunci: return = **real**; aktif sudah diberi biaya (2.0%/th faktor, 0.8%/th trend). Trend di vol-target 10% dengan bobot lag meniru BTOP50. Nuansa penting (Exhibit 5): **ekuitas justru untung dari inflasi yang naik jika level awal di bawah median (2,6%)** — efek "deflation relief"; baru hancur bila akselerasi terjadi dari level tinggi. Korelasi 12-bulan ekuitas×Δinflasi hanya positif di kuintil terbawah (level awal <1,0%, korr +0,4).

### (c) GOLD — spesifik
- +13% real annualized di regime; hit rate 67% (4 dari 6 episode berdata); **t-stat 3.1 = signifikansi tertinggi di seluruh kompleks komoditas** (yang lain 1.1–1.8).
- Per episode: OPEC '72–'74 **+166%** total real, Iranian Revolution +154%, Bretton Woods +9%, China Boom +27%; **TAPI Reagan Boom '87–'90 gold –18% total real** (energi saat itu +201%, tembaga +306%) — gold bukan hedge inflasi yang "selalu hidup".
- Footnote paper (Erb & Harvey 2013): *gold terlalu volatil untuk hedge andal; performa sejak 1975 didorong satu tahun tunggal (1979)* — kesadaran akan single-observation risk ini eksplisit.
- Di masa non-inflasi gold real **–1%**/tahun (silver –5%) — hampir seluruh nilai gold sebagai aset regime, bukan aset all-weather.

### (d) Kasus Jepang (12 regime, data 1926–2020)
- Ekuitas Jepang di regime Jepang: **nominal +11%/th (hit 83%) tapi real –10%/th** — inflasi menghancurkan secara diam-diam; obligasi pemerintah **–16% real (hit 17%)**.
- Regime WW2 (Des 1941–Agu 1946, 57 bln): level harga **+1.423%** (satu-satunya hiperinflasi di dataset; YoY puncak +780% Agu 1946) → ekuitas kehilangan **95%** daya beli, obligasi –92%. Pelajaran: diversifikasi ekuitas tidak menyelamatkan dari hiperinflasi.
- Tanah residensial Jepang: **+12% real CAGR, hit rate 100%** — terbaik dari semua aset properti di paper. Tapi penulis sendiri "hesitant": episode melewati bubble 1986 (Tokyo $139rb/m²; Istana Imperial > nilai tanah seluruh California) lalu crash — artefak bubble, jangan dibaca structural.
- Lintas negara (Exhibit 16): aset terburuk di **regime negara sendiri** (ekuitas AS –7% di regime AS, tapi +6%/+9% di regime UK/Jepang). Ekuitas baru benar-benar jatuh saat **≥2 dari 3 negara** bersamaan dalam regime; saat ketiganya sekaligus (4% waktu): trend **+41 s/d +50%**, komoditas +16–23%, ekuitas AS/UK –7%.

### (e) Temporary vs permanent — ya, dibedakan eksplisit
- Kutipan kunci (bagian *Economic Mechanism*): "It is essential to distinguish between temporary and permanent (or longer-lasting) inflation shocks." Definisi via contoh: gangguan supply singkat (contoh mereka: pipa gas putus 1 bulan) = **temporary** → dampak harga aset minimal karena pasar mengharapkan harga kembali normal; **permanent** = perubahan persepsi inflasi jangka panjang → aset berdurasi panjang (obligasi, saham growth) paling tersakiti.
- Ukuran ideal menurut mereka: **perubahan BEI (breakeven inflasi)** karena mencerminkan ekspektasi jangka panjang — tapi data hanya dari 1997 (UK 1981) → tak bisa dipakai untuk sejarah regime.
- Ukuran yang dipakai: **Δ inflasi YoY realisasi** (proxy unexpected inflation, asumsi random-walk; Ang 2014) — dan mereka mengakui limitasinya: "focuses exclusively on the short term and **unable to separate the temporary and permanent components**." (→ ini justru membenarkan blok OVX/energi kita sebagai detektor early temporary-shock.)

### (f) Batasan yang mereka akui sendiri
1. Inflasi sendiri sulit didefinisikan (hedonic adjustment subjektif; "everyone faces their own inflation rate"); hasil "largely robust" antar varian CPI/PCE/deflator tapi tidak diuji penuh.
2. Proxy unexpected inflation (ΔYoY) tak memisahkan temporary vs permanent.
3. Hasil sensitif terhadap **dating regime** — contoh mereka sendiri: momentum ekuitas tampak bagus karena regime berhenti Des 1974 (sebelum crash momentum Jan 1975) dan Jul 2008 (sebelum late-2008).
4. Sample episode tipis (8 AS) → banyak t-stat rendah (momentum 0.6); rata-rata antar-regime bisa menyesatkan karena satu regime dominan (gold-1979).
5. **Structural change**: ekonomi 1970-an bergantung minyak impor, sekarang tidak; EV/energi-transisi bisa mengikis daya lindung energi; manufaktur tinggal 11% PDB AS; modal intangible lebih tahan inflasi.
6. 5 dari 8 regime AS diikuti infleksi negatif growth → efek inflasi tercampur efek resesi.
7. Kapasitas trend terbatas vs faktor; biaya implementasi diasumsikan (2.0%/0.8%), bukan diestimasi per-era.
8. Data start-date beda-beda; interpolasi kuartalan/tahunan → bulanan (real estate, kolektibel).
9. TIPS sintetis + yield awal regime dulu +2,4% vs –0,9% saat tulis → hedge mahal ke depan.
10. **Kripto**: hanya 8 tahun data bermutu, tanpa satu pun regime inflasi; vol 5× S&P/gold; beta positif ke pasar (Mar 2020: saham –34%, gold –12%, BTC –53%) → "may not deliver positive real returns in periods of unexpected inflation". Justru kesimpulan kripto paper ini **negatif-hati-hati**, bukan endorsement.

## Pemetaan ke sistem kita

| Temuan paper | Di mana mendarat di DATA-SPEC |
|---|---|
| Regime inflasi menentukan aset pemenang | Blok C (state COOLING/REACCEL) + quadrant §11.2 → tabel implikasi instrumen §11.4 |
| "Variasi dalam kompleks komoditas" | Validasi pendekatan kita membedakan XAU/XAG/XPT/XCU secara terpisah (bukan "commodities" satu blok) + CVOL skew per metal |
| Trend-following proteksi andal | **Metrik regime baru yang layak masuk**: trend-state per instrumen (20d/60d) — sederhana, transparan, berdasar akademik. Kandidat baris brief: "XAUUSD trend 60d: UP" |
| Bond & equity disakiti inflasi tak terduga | Bias US100/US500 & yields di quadrant REACCELERATING (bukan asumsi — ada papernya) — kini dengan angka: ekuitas –7% real, 10Y –5%, 60-40 –6%, t-stat –4.8 s/d –6.0 (full-text read 2026-08-30) |
| Kripto dibahas sebagai kandidat hedge | Konteks untuk bias BTC di regime inflasi-surprise — perlakukan sebagai *hipotesis lemah* (papernya sendiri hati-hati; full-text: kesimpulan kripto mereka eksplisit skeptis — 8 thn data tanpa regime, beta positif ke pasar) |
| "Ekuitas untung dari akselerasi inflasi ber-level rendah" (Exhibit 5) | Quadrant REACCELERATING perlu kualifikasi level (lihat rekomendasi overlay di bawah) — REACCEL dari 2% ≠ REACCEL dari 5% |
| Tembaga = "industrials" paper (+19% real, hit 80%) | Validasi XCU sebagai instrumen blok metal, bukan sekadar pelengkap |

## Definisi paper vs state Blok C kita (full-text read 2026-08-30)

| Aspek | NDFHV 2021 | Blok C kita (BUILD-PLAN §3) |
|---|---|---|
| Series | CPI headline YoY (NSA) | `CPIAUCSL` (SA), **3m-annualized** `((1+m1)(1+m2)(1+m3))^4−1` |
| Penentu state | **LEVEL + arah**: akselerasi DAN level menembus ≥5% | **ARAH saja**: Δ3-bulan dari 3m-ann → COOLING/STABLE/REACCEL; level tidak masuk penentu state |
| Threshold level | 2% (desil-4, psikologis) → 5% (desil-8) = trigger regime | tidak ada (level hanya konteks naratif: "2.8% masih di atas target") |
| Akhir episode | puncak YoY tanpa jatuh <50% dari maksimum 24-bulan berjalan | tidak ada konsep akhir episode (state bulanan rolling) |
| Durasi minimum | 6 bulan | tidak ada |
| Bagian yang ditangkap | hanya fase akselerasi (positive surprise) sampai puncak | momentum 3 bulan terakhir (arah saja) |
| Horizon | episode multi-tahun (7–48 bln) | 3 bulan |

**Rekomendasi threshold Blok C (keputusan usulan):**
1. **State dasar TETAP COOLING/STABLE/REACCEL** — paper justru mengonfirmasi bahwa arah (akselerasi) adalah inti regime; momentum 3-bulan kita sejalan dengan "bagian positive-surprise" yang mereka fokuskan. Tidak perlu mengganti formula.
2. **Tambahkan overlay LEVEL sebagai kolom/kualifikasi, bukan state baru**: Exhibit 5 paper menunjukkan REACCEL dari level rendah (<median 2,6%; apalagi <1,0%) justru *baik* bagi ekuitas (deflation relief) — kerusakan hanya terjadi saat akselerasi dari level tinggi. Tanpa overlay level, "REACCEL" kita menyamakan dua dunia yang bagi paper ini berlawanan arah implikasinya. Usulan dua tingkat: `REACCEL(low)` bila 3m-ann < ~3% → jinak/bisnis-biasa; `REACCEL(high)` bila menembus ~3% dan apalagi ≥5% → setara "regime kelas NDFHV", aktifkan bias hedge (komoditas/logam, trend-state, kurangi durasi, waspadai saham).
3. **Ambil dua elemen teknis murah dari mereka**: (a) **durasi minimum** — baru sebut episode setelah REACCEL bertahan ≥3 bulan (analogi aturan 6-bulan mereka, diskalakan ke horizon 3-bulan kita) supaya satu rilis CPI noise tidak mengubah quadrant; (b) **aturan akhir ala 50%-dari-puncak** — quadrant REACCELERATING baru dianggap "selesai" bila 3m-ann turun signifikan dari puncak trailing-nya (bukan sekali tikungan bulanan) — mencegah flip-flop state.
4. Threshold 5% mereka = desil-8 dari distribusi 1926–2021 (era 1970-an masuk). Untuk sistem early-warning 2026, 5% adalah level "sudah terjadi", bukan "awal". Maka tingkat amber ~3% (setara "materially beyond 2%") lebih operasional sebagai pemicu persiapan, 5% sebagai konfirmasi penuh.

## Batas validitas (penting)
- 95 tahun tapi **3 negara saja**; episode inflasi AS modern utama = 1970-an → sample regime sesungguhnya tipis (8 episode; paper sendiri mengakui t-stat rendah dan sensitivitas terhadap dating — lihat §(f) di atas).
- **Definisi threshold regime kini sudah terekstrak** (TODO lama selesai 2026-08-30): level-based ≥5% + akselerasi + aturan 24-bulan/50% + min. 6 bln — berbeda secara fundamental dari state arah-murni kita (lihat tabel di atas).
- Reaksi aset era 1970-an ≠ era QT-dan-Fed-watch — pakai sebagai *arah prior*, bukan angka ekspektasi.
- Tambahan dari full-text: angka gold/energi didorong episode 1972–1980 (2 dari 8) dan gold bahkan **–18%** di episode Reagan — jangan perlakukan gold sebagai hedge inflasi deterministik; justru **tembaga (+19%, hit 80%) lebih konsisten** di kompleks metal.
- Paper memakai YoY headline; kita 3m-ann SA — perbandingan langsung angka level tidak apple-to-apple (3m-ann kita lebih responsif; saat memetakan threshold, konversi dulu).

## Keputusan
1. Tabel implikasi §11.4 mendapat kolom "dasar": folklore → paper ini (arah), NBER-timeline (label), akumulasi sendiri (angka, nanti).
2. **Trend-state per instrumen masuk spec** sebagai metrik regime (fitur F3, data sudah ada: harga instrumen §10).
3. ~~Deep-read full-text dijadwalkan saat modul quadrant dibangun.~~ → **SELESAI 2026-08-30** (via PDF Duke, kini di `docs/methodology/assets/P154_The_best_strategies.pdf`). Langkah lanjut: formalisasi overlay level REACCEL(low/high) + durasi minimum ke BUILD-PLAN §3 saat quadrant dibangun.
4. (Baru, full-text read 2026-08-30) Urutan preferensi hedge inflasi versi paper untuk konteks kita: trend-following (proxy kita: trend-state per instrumen) > komoditas logam (XCU paling konsisten, XAU paling signifikan-tapi-episode-driven) > TIPS > sektor energy equity (+1% saja — jangan andalkan US500-energy sebagai hedge komoditas).
