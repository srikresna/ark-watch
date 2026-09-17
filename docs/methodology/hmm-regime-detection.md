# METHODOLOGY — Deteksi Regime Markov-Switching / HMM (Sinyal Pembanding)
> Seri: deep-dive metodologi. Status: **riset + desain selesai 2026-08-30; implementasi DITUNDA ke fase eksperimen pasca-F4** (gerbang di §8).
> Posisi dalam sistem: **PEMBANDING statistik terhadap regime score rule-based** (DATA-SPEC §11.1) — bukan pengganti. Alasan di §5.4.
> Fakta menyenangkan: sistem kita *sudah* memakai output model semacam ini — series `smoothedUSRecessionProbabilities` (FMP, Blok D) adalah produk model Markov-switching Chauvet–Piger. Dokumen ini merancang versi milik kita sendiri, dengan fitur kita.

## 1. Masalah yang dicoba dipecahkan

Regime score kita (§11.1) bekerja dengan cara *rule-based*: kita definisikan sendiri ambang (z ±0.5), bobot pilar (A .20 … F .15), dan label state. Pendekatan ini transparan dan bisa diaudit — tapi membawa pertanyaan sah: **bagaimana jika data macro punya "state" yang strukturnya tidak kita definisikan?** Markov-switching / Hidden Markov Model (HMM) adalah jawaban klasik literatur: biarkan statistik *menemukan* state itu sendiri dari pola data, lalu bandingkan dengan definisi kita. Kalau dua metode independen sepakat → keyakinan naik. Kalau bentrok → ada yang perlu diperiksa. Itu seluruh filosofi modul ini.

## 2. Konsep untuk awam (tanpa rumus dulu)

### 2.1 State tersembunyi
Bayangkan kamu tidak bisa keluar rumah, tapi ingin tahu cuaca. Yang kamu punya hanyalah laporan tetangga: "hari ini dia bawa payung", "hari ini dia pakai topi". Cuaca = *state tersembunyi* (tidak terlihat langsung); perilaku tetangga = *observasi*. Kamu tidak pernah melihat cuaca, tapi dari pola laporan bertahun-tahun kamu bisa menyimpulkan: "hari-hari dia bawa payung cenderung berkelompok — dan besoknya kemungkinan besar payung lagi." Di pasar: **"regime" (keadaan pasar/makro) adalah state tersembunyi**; VIX, HY spread, slope kurva = laporan tetangga kita.

### 2.1b Contoh mikro: bagaimana mesin ini "berpikir" (angka main-main)
Andaikan 2 state (ON/STRESS) dan model sudah terlatih: dari sejarah diketahui P(besok STRESS | hari ini ON) = 2%, dan "suara" tiap state — VIX rata-rata 14 di ON vs 28 di STRESS. Hari ini VIX tercatat 25. Bagaimana kesimpulan dibentuk? Dua suara bersaing: (a) *kemungkinan transisi* bilang: kemarin ON, jadi hari ini hampir pasti masih ON; (b) *observasi* bilang: VIX 25 jauh lebih khas STRESS. Keduanya dikalikan (Bayes), hasilnya misal P(STRESS hari ini) = 35% — transisi menahan, observasi mendorong. Besok, proses berulang dari 35% itu sebagai titik berangkat: **observasi hari ini menggerakkan keyakinan sedikit; yang menggerakkan besar adalah observasi yang bertahan**, karena setiap hari keyakinan dikompromikan dengan peluang transisi. Inilah mengapa output HMM alaminya "lambat tapi sulit dibohongi satu spike" — sifat yang kita manfaatkan sebagai konfirmator (§7.4).

### 2.2 Rantai Markov: state punya "ingatan" sepanjang satu langkah
Inti rantai Markov: **peluang state besok HANYA tergantung state hari ini**, bukan jalur lengkap sebelumnya. Cukup realistis untuk market regime — kalau hari ini "risk-on", besok kemungkinan besar masih risk-on (regime itu *lengket*). Angka lengkapnya ditulis dalam **matriks transisi**. Contoh 2 state:

| | besok RISK-ON | besok STRESS |
|---|---|---|
| **hari ini RISK-ON** | 0.98 | 0.02 |
| **hari ini STRESS** | 0.05 | 0.95 |

Dari diagonal ini terbaca sifat kunci regime: dari risk-on, 98% bertahan; rata-rata lama tinggal (durasi ekspektasi) = 1/(1−0.98) = 50 hari. Angka transisi ini *diperkirakan dari data* saat model dilatih, bukan kita isi sendiri.

### 2.3 "Suara" tiap state (emission)
Tiap state punya karakter statistik berbeda pada data yang kita amati: state tenang → VIX rendah, HY spread sempit; state stress → VIX tinggi, HY melebar. Dalam GaussianHMM, tiap state digambarkan sebagai satu **distribusi Gaussian** (punya rata-rata dan sebaran sendiri per fitur). Model belajar dua hal sekaligus: (a) seperti apa "suara" tiap state, (b) seberapa sering pindah state.

### 2.4 Tersaring vs dihaluskan (filtered vs smoothed) — penting untuk real-time
- **Filtered** P(state hari ini | data s/d hari ini) = kesimpulan yang jujur untuk *hari ini*: hanya pakai masa lalu.
- **Smoothed** P(state hari-t | data s/d HARI TERAKHIR) = kesimpulan yang sudah "dilihat masa depannya" — bagus untuk analisis sejarah (backtest chart), **TIDAK boleh dipakai sebagai sinyal live** karena itu look-ahead bias (memakai informasi yang belum ada saat hari-t).
- Kasus istimewa yang kita manfaatkan: pada **baris terakhir** jendela data, smoothed = filtered (tidak ada "masa depan" lagi dalam jendela). Maka sinyal harian kita = ambil baris terakhir `predict_proba` — math-nya benar, dan tidak perlu implementasi filter terpisah.

## 3. Matematika ringan

Model (notasi standar): state laten S_t ∈ {1..K} berupa rantai Markov orde-1 dengan matriks transisi P = [p_ij], p_ij = Pr(S_{t+1}=j | S_t=i). Observasi vektor fitur x_t ∈ R^D dipancarkan (emission) per state: GaussianHMM memodelkan x_t | S_t=k ~ N(μ_k, Σ_k). Estimasi parameter (P, μ_k, Σ_k) via **EM / Baum-Welch**: iterasi E-step (hitung probabilitas state per titik waktu dengan algoritma forward-backward) dan M-step (update parameter agar likelihood maksimum). Kuantitas berguna lain:
- Durasi ekspektasi state k: **1/(1−p_kk)** — sanity check wajib (state "recession" yang durasinya 3 tahun jelas salah).
- Distribusi stasioner (`get_stationary_distribution()`) — porsi waktu jangka panjang di tiap state; sanity check kedua (recession harus jarang, ±10-15% dari waktu).
- Jumlah parameter: K state × D fitur, kovarians `diag`: K·D (means) + K·D (varians) + K(K−1) (transisi) ≈ **44 parameter untuk K=3, D=6**; `full`: K·D(D+1)/2 kovarians → 89 parameter. Bandingkan dengan jumlah observasi (§5.2) untuk melihat margin overfitting.
- **Intuisi forward algorithm** (mesin di balik §2.1b, tanpa rumus penuh): keyakinan hari ini = (keyakinan kemarin × matriks transisi) × kecocokan observasi hari ini, dinormalisasi. Dua faktor yang saling menarik itulah jantung filter Hamilton — persis yang di §2.1b.
- **Intuisi EM/Baum-Welch**: masalah ayam-telur — untuk menaksir parameter state butuh tahu state mana yang aktif kapan; untuk mengetahui state aktif butuh parameter. EM memecahnya dengan iterasi: tebak parameter awal (acak) → hitung probabilitas state (E-step) → perbarui parameter dari taksiran itu (M-step) → ulang sampai berhenti berubah. Konsekuensi praktis: **hasil bergantung tebakan awal** → multi-seed wajib (§6, §7.2).
- Model Hamilton (1989) aslinya lebih spesifik: **rata-rata pertumbuhan** suatu series tunggal (GNP) yang berganti nilai per state — di statsmodels ini adalah `MarkovRegression`; GaussianHMM hmmlearn adalah generalisasi multi-fitur.

## 4. Apa kata literatur — dan relevansinya untuk kita

| Temuan sumber | Relevansi ark-watch |
|---|---|
| Hamilton (1989): pertumbuhan GNP AS lebih baik dimodelkan shift diskrit 2-state (resesi/ekspansi) via rantai Markov; algoritma infere probabilitas state real-time (Hamilton filter) | Fondasi; memvalidasi ide "regime = state diskrit yang bisa diinfer" — presisi penyebutan resesi era 1989-90 terkenal bagus |
| Kim & Nelson (1999): gabungkan Hamilton-switching dengan factor model & Kalman filter (Kim filter) → state dari *banyak* indikator sekaligus | Preseden arsitektur kita: multi-fitur (§5.1), bukan series tunggal |
| Chauvet & Piger (2008): model Markov-switching dynamic-factor **mengalahkan/menyamai kecepatan NBER** dalam memanggil turning point real-time | Bukti terbaik bahwa sinyal P(state) bisa *lebih cepat* dari label resmi — dan output model mereka (RECPROUSM156N) sudah kita konsumsi via FMP → benchmark eksternal gratis untuk validasi modul kita |
| Praktisi (QuantStart dkk.): HMM 2-3 state pada return saham → state "low-vol bull" & "high-vol bear/crisis"; dipakai sebagai filter risk-management, bukan sinyal entry | Dukungan untuk posisi "pembanding" kita; juga peringatan: fit pada return instrumen = state volatilitas pasar SAJA (§5.1 catatan circularity) |
| Wang (2020, MDPI): regime HMM → rotasi faktor kondisional state | Konteks penggunaan (bukan langsung — kita bukan factor-investor) |
| Two Sigma: alternatif GMM/clustering pada faktor | Peta jalan kalau HMM terbukti rapuh — dicatat sebagai cadangan, tidak diprioritaskan |

## 5. Desain untuk ark-watch

### 5.1 Fitur masukan (semua dari data yang SUDAH kita panen)

| # | Fitur | Series (registry) | Freq | Peran dalam "suara" state | Kedalaman historis |
|---|---|---|---|---|---|
| 1 | Aktivitas ekonomi | `ADS` (Philly Fed, Blok D) | D | inti growth — sudah komposit 6 indikator | 1960→ |
| 2 | Growth coincident | `CFNAI` (FRED, Blok D) | M | konfirmasi growth (as-of join, telat ±3 mgg) | 1967→ |
| 3 | Slope kurva | `T10Y3M` (FRED, Blok A) | D | ekspektasi resesi pasar | 1982→ |
| 4 | Vol equity | `VIXCLS` (FRED, Blok F) | D | ketakutan pasar | 1990→ |
| 5 | Distress kredit | `CMDI` via EODHD (Blok F; **mingguan, as-of join** ke harian) | W→D | risk appetite kredit | ~2005→ (1.129 minggu) — ⚠️ koreksi 2026-08-30: `BAMLH0A0HYM2` FRED terpotong jadi 3 thn (2023-08→, lisensi ICE; ALFRED vintage-lama 400) sehingga tak layak jadi fitur inti |
| 6 | Momentum dolar | `DTWEXBGS` Δ20d (Blok A) | D | driver silang book kita | 2006→ |

Transform: **z-score window 5y (σ populasi)** persis konvensi transform-spec BUILD-PLAN §3 — fitur berada di satuan yang sama, kovarians antar fitur jadi masuk akal. Join antar frekuensi: **as-of join pakai `release_ts`** (CFNAI hanya masuk setelah rilis — bukan forward-fill buta yang menyelundupkan data masa depan).

**Trade-off jumlah fitur vs sample** (alasan berhenti di 6):
1. **Parameter tumbuh kuadratik di D untuk kovarians full** (D=6 → 21 elemen per state); `diag` meredam ini tapi korelasi antar fitur (VIX↔HY OAS berkorelasi kuat saat stress) tetap membuat efektif-dimensi < 6 — fitur ke-7 ke atas menambah marginal kecil.
2. **Kedalaman menentukan jendela**: tiap fitur punya start berbeda (tabel di atas); fitur termuda memotong seluruh jendela (depth-gate F4). Dolar (2006→) memotong 9 tahun data — bayar mahal untuk 1 fitur.
3. **Frekuensi campur = stale join**: hanya ADS/CFNAI yang meng-cover "growth"; sudah cukup — tidak perlu menambah ICSA/Sahm yang bulanan-mingguan dan mengulang informasi ADS.
4. **Catatan circularity**: implementasi blog umumnya mem-fit HMM pada return S&P. Kita **sengaja tidak** memakai return instrumen sebagai fitur — sinyal ini harus independen dari harga yang nanti ia "komentari", jika tidak pembandingnya terkontaminasi targetnya.

**Cakupan pilar**: enam fitur ini sengaja mengambil dari tiga pilar yang paling menentukan hidup-mati book kita — growth (ADS, CFNAI ≈ pilar D), harga uang & ekspektasi (slope T10Y3M ≈ pilar A), dan stress pasar (VIX, HY OAS ≈ pilar F) — plus dolar (pilar A, tier-2). Pilar likuiditas (E) sengaja tidak diwakili: net-liquidity mulai bermakna 2010-an (RRP baru 2013) sehingga depth-nya memotong jendela paling dalam; sebagai gantinya, cross-check vs pilar E tetap bisa dibaca dari *brief* karena keduanya tampil berdampingan. **Kriteria fitur ke-7** (kalau suatu saat mau menambah): menambah dimensi informasi BARU (bukan korelasi >0.7 dengan fitur eksisting), depth ≥ jendela inti, freq ≥ mingguan, dan lolos depth-gate F0.

### 5.2 Jendela data & frekuensi — keputusan: HARIAN, 2 tier
- **Tier 1 (inti, dipakai reguler)**: 5 fitur (tabel di atas minus dolar), mulai **2005-01** (constraint CMDI ~2005; BAML OAS terpotong 2023→ — lihat catatan fitur #5) ≈ 5.500 observasi harian efektif. Rasio 44 parameter : 5.500 obs = masih aman.
- **Tier 2 (sensitivitas)**: + momentum dolar `DTWEXBGS`, mulai 2006-01 ≈ 5.200 obs — dijalankan paralel; perbedaan state antar tier = catatan diagnostik, bukan alarm.
- Alternatif DXY (Yahoo, 1971→, §10) sebagai surrogate dolar pra-2006 ditolak untuk v1: break struktural definisi index (goods-only vs ICE basket) menambah non-stationarity yang tidak sepadan.
- **Kenapa harian, bukan bulanan** (padahal ritme macro bulanan): model bulanan 1997→ hanya ~350 obs vs 44 parameter = terlalu tipis; fitur kita memang mayoritas harian (ADS harian, VIX harian, dst.), dan jitter harian output diredam oleh persistensi transisi + EMA tampilan. *Semua angka kedalaman diverifikasi ulang di depth-gate F0.*
- Refit pada **jendela expanding penuh** (bukan rolling 10y): transisi resesi itu langka — membuang 1997-2010 berarti membuang 2 dari 4 event regime terbesar. Rolling-10y disimpan hanya sebagai uji sensitivitas.

### 5.3 Arsitektur pipeline

```
raw_observations ──(z 5y, as-of join)──> matriks fitur harian X
        │                                      │
        │ minggu pertama tiap bulan            │ tiap pagi (setelah fetch 06:00)
        ▼                                      ▼
   FIT BULANAN: GaussianHMM K=3, diag cov,   SCORING HARIAN: predict_proba(X)[-1]
   multi-seed → fix label order → simpan       (baris terakhir = filtered, §2.4)
   params (transmat/means/covars) ke                │
   computed_signals.inputs_json                    ▼
                              computed_signals: signal_id=HMM_REGIME,
                              value=P(stress), state=argmax + P per state
                                                 │
                                                 ▼
                       BRIEF (baris pembanding, di bawah regime score):
   "HMM (statistik, pembanding): P(calm) 12% · P(mid) 55% · P(stress) 33% (Δ+9pt/W)
    — vs regime score +1.2 → SETUJU risk-on"  …atau "…BEDA: cek Blok F"
```

Aturan implementasi mengikuti prinsip build: model params di-serialisasi ke `inputs_json` (derived recomputable, §0.2); refit terjadwal minggu pertama bulan berikut (setelah CFNAI rilis); `run_id` dicatat (replay determinism).

### 5.4 Kenapa PEMBANDING, bukan pengganti regime score
1. **Opasitas.** Regime score bisa dibaca hulu-ke-hilir: z mana naik, bobot berapa, threshold apa (CLI `explore signal REGIME_SCORE --trace`, §8 BUILD-PLAN). HMM merangkum semuanya jadi 44 parameter yang tidak punya makna ekonomi langsung — ketika sinyal salah, tidak ada yang bisa diinterogasi. Untuk pemakai solo yang sedang belajar, auditability > kecanggihan.
2. **Label switching.** State HMM TIDAK punya identitas bawaan — state #2 hari ini bisa saja state #0 bulan depan dengan isi sama (§7.1). Sinyal yang bisa diam-diam bertukar nama tidak boleh duduk di kursi keputusan.
3. **Sample regime tipis.** Sejak 2005 (jendela tier-1) hanya ada 2–3 episode resesi NBER (2008-09, 2020, +2026?) dan segelintir episode stress non-resesi. Matriks transisi ditaksir dari event sesering itu — estimasinya lebar. Rule-based kita setidaknya salah dengan cara yang bisa diprediksi.
4. (bonus) **Kredit ganda.** Dua sinyal berkorelasi tinggi yang keduanya masuk keputusan = ilusi diversifikasi; sebagai pembanding independen justru nilainya maksimal saat keduanya *tidak* sepakat.

### 5.4b Kapan masing-masing unggul (peta komplementer)

| Situasi | Rule-based regime score | HMM pembanding |
|---|---|---|
| Perubahan bertahap (grinding slowdown) | unggul — z pilar bergerak lebih dulu, per-pilar terbaca | telat — persistensi transisi menahan |
| Break mendadak tanpa satu indikator ekstrem (koridor sempit: semuanya medioker tapi kombinasinya aneh) | lemah — tiap pilar di bawah threshold, skor diam | unggul — justru berpikir dalam kombinasi distribusi |
| Verifikasi sebuah keputusan sizing besar | cukup | tambah nilai — dua metode independen sepakat = keyakinan naik |
| Menjelaskan "kenapa" ke diri sendiri / audit | unggul — rantai z→state→bobot terbaca penuh | lemah — 44 parameter tanpa nama ekonomi |
| Regime yang belum pernah ada di sampel (mis. stagflasi CB-buying era kini) | bisa salah dengan cara yang bisa dideteksi | bisa salah dengan cara yang *tidak* terlihat |

### 5.5 Penamaan state: ordering by variance
Setelah fit, state diurutkan ulang berdasar **total varians emission** (jumlah varians antar fitur): state 0 = sebaran paling sempit = "CALM", state terakhir = sebaran terluas = "STRESS". Ini identifiability constraint standar (Jasra 2005) yang menstabilkan label antar-refit — dan kebetulan selaras intuisi: regime buruk selalu lebih *bising* daripada regime baik. State tengah (K=3) diberi label netral "MID". Nama label TIDAK di-interpretasikan lebih jauh (state HMM = kluster statistik, bukan diagnosis ekonomi).

### 5.6 Non-goals eksplisit (apa yang TIDAK dilakukan modul ini)
- **Tidak** memakai return instrumen sebagai fitur (§5.1 poin 4).
- **Tidak** memakai K > 4, kovarians full, atau fitur > 7 (§7.2).
- **Tidak** menghasilkan probabilitas intra-hari — EOD-first, konsisten filosofi sistem.
- **Tidak** mengubah bias/sizing apa pun sebelum gerbang E3 (§8) — pelanggaran = modul dicabut.
- **Tidak** menggantikan `smoothedUSRecessionProbabilities` FMP — series itu justru naik kelas jadi benchmark eksternal (§10.5).

## 6. Sketsa kode (hmmlearn)

```python
# arkwatch/signals/hmm_regime.py — SKETSA (verifikasi API vs hmmlearn stable 2026-08)
import numpy as np, pandas as pd
from hmmlearn import hmm

FEATURES = {"ADS": "level", "CFNAI": "level", "T10Y3M": "level",
            "VIXCLS": "level", "CMDI": "level"}           # tier-1 (§5.2; CMDI mingguan→as-of)

def load_matrix(start="2005-01-01") -> pd.DataFrame:
    cols = [read_series_asof(sid) if m == "level" else read_series_asof(sid).pct_change(20)
            for sid, m in FEATURES.items()]          # as-of join pakai release_ts (anti look-ahead)
    X = pd.concat(cols, axis=1).loc[start:]
    z = (X - X.rolling(1260).mean()) / X.rolling(1260).std(ddof=0)   # z 5y, σ populasi (BUILD-PLAN §3)
    return z.dropna()

def fit_hmm(X: pd.DataFrame, k: int = 3):
    best, best_ll = None, -np.inf
    for rs in (1, 7, 42):                             # multi-seed: EM rawan lokal-optima
        m = hmm.GaussianHMM(n_components=k, covariance_type="diag",
                            n_iter=500, tol=1e-4, random_state=rs).fit(X.values)
        ll = m.monitor_.history[-1]
        if m.monitor_.converged and ll > best_ll:
            best, best_ll = m, ll
    order = np.argsort(best.covars_.sum(axis=1))      # LABEL-SWITCHING FIX (§5.5):
    best.transmat_ = best.transmat_[np.ix_(order, order)]   # urut state dari total varians
    best.means_, best.covars_ = best.means_[order], best.covars_[order]
    best.startprob_ = best.startprob_[order]
    return best                                       # state 0=CALM … k-1=STRESS

# --- refit bulanan (terjadwal) + scoring harian ---
X = load_matrix()
model = fit_hmm(X)
post = model.predict_proba(X.values)                  # smoothed (forward-backward)
p_today = post[-1]                                    # baris terakhir == filtered (§2.4) → sinyal live
durasi = 1.0 / (1.0 - np.diag(model.transmat_))       # sanity: durasi ekspektasi per state
save_signal("HMM_REGIME", value=p_today[-1],          # value = P(STRESS)
            state=int(p_today.argmax()), params=model, # params → inputs_json (recomputable)
            diag={"durasi": durasi.tolist(),
                  "stationary": model.get_stationary_distribution().tolist()})
```

Catatan pemakaian: pilih K via `model.aic(X.values)` / `model.bic(X.values)` per K ∈ {2,3,4} — BIC diprioritaskan (menghukum kompleksitas lebih berat). API diverifikasi: `aic`, `bic`, `get_stationary_distribution`, `predict_proba`, `monitor_` semuanya publik di hmmlearn stable; method `filter()` TIDAK eksis — karenanya pola "baris terakhir predict_proba" di atas adalah cara yang benar mendapatkan probabilitas tersaring. Alternatif statsmodels `MarkovRegression` (Hamilton-style, series tunggal + `smoothed_marginal_probabilities`) dicadangkan untuk replikasi gaya Chauvet–Piger di atas ADS saja — pembanding internal kedua yang murah.

Detail operasional sketsa: `read_series_asof()` = helper as-of join dari `raw_observations` (placeholder nama, implementasi ikut mekanisme `release_ts` F4); tier-1/tier-2 dicatat sebagai field `inputs_json["tier"]`; artefak refit (transmat/means/covars versi JSON + hash fitur) diarsipkan per `run_id` sehingga setiap P(state) historis bisa direproduksi persis (prinsip replay-determinism §6.6 BUILD-PLAN); `save_signal()` = pembungkus upsert `computed_signals`.

## 7. Jebakan & mitigasi

### 7.1 Label switching
**Masalah**: likelihood model invarian terhadap permutasi nama state — state "1" dan "2" bisa bertukar tempat antar refit tanpa apa pun terlihat berubah di angka fit. Sinyal P(state=1) melompat dari 0.9 ke 0.1 padahal dunia tidak berubah. **Mitigasi**: (a) constraint identifiability ordering-by-variance (§5.5, kode §6); (b) setelah tiap refit, cek korelasi series P(state) baru vs lama — korelasi negatif = indikasi permutasi terjadi → reorder & log; (c) jangan pernah menyimpan interpretasi ekonomi yang melekat pada nomor state, hanya pada posisi urutannya.

### 7.2 Overfitting
**Masalah**: K besar + kovarians full = model menghafal noise; in-sample P(state) terlihat sempurna, out-of-sample acak. EM juga rawan lokal-optima (hasil bergantung inisialisasi). **Mitigasi**: K=2-3 saja (BIC untuk meneguhkan); `covariance_type="diag"`; multi-seed dan ambil likelihood terbaik; tol ketat; tolak model yang `monitor_.converged=False`. Uji terkuat: *out-of-sample log-likelihood* — score data 12 bulan terakhir dengan model yang dilatih tanpanya.

### 7.3 Non-stationarity
**Masalah**: model mengasumsikan distribusi emission state berulang dengan parameter sama — padahal VIX era-1990an dan era-QT punya level struktural berbeda; z-score 5y meredam sebagian besar, bukan semuanya. **Mitigasi**: fitur semuanya di-z-score (level mentah tidak pernah masuk); refit bulanan menyerap drift pelan; uji sensitivitas jendela (expanding vs rolling-10y, §5.2); catat break struktural diketahui (analog kasus CVOL Mar-2026 §19.4) di registry bila ditemukan.

### 7.4 Transisi jarang (kelemahan paling mendasar)
**Masalah**: matriks transisi ditaksir dari event yang hampir tidak pernah terjadi — 4 resesi dalam 29 tahun. Akibat khas: (a) interval kepercayaan p_ij sangat lebar; (b) model cenderung over-persist ("kalau stress, akan stress lama") sehingga telat memanggil perubahan; (c) episode pendek (COVID 2020 = ~2 bulan) bisa menggelembungkan durasi state stress. **Mitigasi**: laporkan durasi ekspektasi + distribusi stasioner sebagai disclaimer di sinyal (bukan angka rahasia); jadikan lambannya sinyal ini *fitur yang disadari* — dia konfirmator, bukan detektor dini (deteksi dini tetap tugas z-score pilar kita yang cepat); evaluasi khusus: bandingkan tanggal P(stress)>0.5 pertama vs peak NBER pada 4 episode historis.

### 7.5 Look-ahead (dua pintu)
**Masalah**: (a) smoothing memakai masa depan (§2.4); (b) fitur join curang — CFNAI bulan yang baru rilis minggu lalu tidak boleh muncul di baris tanggal sebelum rilisnya. **Mitigasi**: sinyal live hanya dari baris terakhir predict_proba; semua join as-of via `release_ts`; backtest replay pakai kolom release_ts (mekanisme F4 yang sama untuk seluruh sinyal lain).

### 7.6 Jitter state di sekitar batas (kegagalan mode praktis paling sering)
**Masalah**: saat P(STRESS) berayun di sekitar ambang (mis. 0.45-0.55 selama dua minggu), label `state=argmax` berkedip ON→STRESS→ON→STRESS — baris brief jadi tak terbaca dan kesan "sinyal gila" merusak kepercayaan pada seluruh modul. **Mitigasi**: (a) tampilkan **probabilitas kontinu** (P per state + Δ7 hari), bukan hanya label; (b) **histeresis dua ambang** untuk label: masuk STRESS bila P ≥ 0.60, keluar bila P < 0.40 — di antaranya label "transisi"; (c) EMA 5 hari untuk kolom Δ di brief. Label histeresis disimpan sebagai `state`, probabilitas mentah tetap di `value` — tidak ada informasi dibuang.

## 8. Kapan upgrade jadi layak (gerbang bertahap)

| Fase | Kapan | Gerbang masuk |
|---|---|---|
| **E1 — Riset/backtest** (murni offline, tidak menyentuh brief) | setelah F4 selesai | Data surrogate ADS/CFNAI/CMDI/VIX/T10Y3M depth ≥2005 lolos depth-gate F0; kode §6 + unit test (replay determinism, label order stabil 3 refit berturut) |
| **E2 — Shadow mode** | setelah E1 lulus + **±12 bulan akumulasi snapshot harian** (logika sama CVOL §19.4: historis sendiri dulu, baru percaya) | Laporan kinerja: (a) agreement HMM vs label NBER pada 4 episode; (b) agreement & lead/lag vs regime score; (c) stabilitas label antar-refit (korelasi P-series > 0.8); (d) out-of-sample LL stabil — semuanya tertulis di docs, baru baris pembanding masuk brief |
| **E3 — Bobot keputusan** (mempengaruhi bias/sizing, masih di bawah rule-based) | minimal 6 bulan setelah E2, HANYA jika E2 menunjukkan value tambah nyata (mis. lead konsisten atas regime score di ≥2 turning point) + user bisa menjelaskan output HMM ke diri sendiri tanpa dokumentasi (tes edukasi — prinsip hulu-ke-hilir §8 BUILD-PLAN) |

Posisi default tetap: **E1 dijadwalkan pasca-F4, E2/E3 adalah opsi yang harus MEMPEROLEH hak via data, bukan hak otomatis.**

Metrik E2 yang dinilai (didefinisikan sekarang supaya tidak di-fitur pasca-hoc):
| Metrik | Definisi | Target minimal E2 |
|---|---|---|
| Recall NBER | episode resesi NBER dengan P(STRESS)>0.5 di puncaknya | 4/4 |
| Median lead/lag vs NBER peak | tanggal crossing pertama − tanggal NBER | lag ≤ 3 bulan (konfirmator) |
| Agreement regime score | % hari label ter-mapping HMM == arah regime score | ≥ 70% (di bawah itu = informasi berbeda, tetap berguna sebagai pembanding, bukan kandidat E3) |
| Stabilitas refit | korelasi P-series antar refit bulan berturut (pasca reorder) | > 0.8 |
| Out-of-sample LL | score 12 bln terakhir dengan model tanpa mereka, per refit | tidak menurun monoton 3 refit berturut |

## 9. Literatur

**Akademik inti:**
- Hamilton, J.D. (1989), *A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle*, Econometrica 57(2) — [jstor.org/stable/1912559](https://www.jstor.org/stable/1912559)
- Kim, C.-J. & Nelson, C.R. (1999), *State-Space Models with Regime Switching*, MIT Press — [direct.mit.edu/books/monograph/3265](https://direct.mit.edu/books/monograph/3265/State-Space-Models-with-Regime-SwitchingClassical)
- Chauvet, M. & Piger, J. (2008), *A Comparison of the Real-Time Performance of Business Cycle Dating Methods*, JBES — [PDF penulis](https://jeremypiger.com/assets/files/Chauvet_Piger_2008_JBES.pdf) · [penerbit](https://www.tandfonline.com/doi/abs/10.1198/073500107000000296) · output live model mereka: [FRED RECPROUSM156N](https://fred.stlouisfed.org/series/recprousm156n) · [FAQ Piger](https://jeremypiger.com/recession_probs_faq/)
- Jasra, A. (2005), *MCMC Methods and the Label Switching Problem* — [PDF Duke](http://www2.stat.duke.edu/homeweb/scs/Courses/Stat376/Papers/Mixtures/MixtureLabelSwitchingStatSci.pdf) (dasar solusi §5.5/§7.1)
- Wang, G.-J. et al. (2020), *Regime-Switching Factor Investing with Hidden Markov Models*, Financial Systems Research (MDPI) — [mdpi.com/1911-8074/13/12/311](https://www.mdpi.com/1911-8074/13/12/311)

**Praktisi:**
- QuantStart, *Market Regime Detection using HMMs in QSTrader* — [quantstart.com](https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/)
- QuantInsti, *Regime Adaptive Trading in Python* — [blog.quantinsti.com](https://blog.quantinsti.com/regime-adaptive-trading-python/)
- Two Sigma, *A Machine Learning Approach to Regime Modeling* — [twosigma.com](https://www.twosigma.com/articles/a-machine-learning-approach-to-regime-modeling/)

**Dokumentasi library (API diverifikasi 2026-08-30):**
- hmmlearn (stable) — API & contoh saham — [hmmlearn.readthedocs.io/en/stable](https://hmmlearn.readthedocs.io/en/stable/) · [contoh stock analysis](https://hmmlearn.readthedocs.io/en/stable/auto_examples/plot_hmm_stock_analysis.html)
- statsmodels `MarkovRegression` — [notebook resmi](https://www.statsmodels.org/stable/examples/notebooks/generated/markov_regression.html) · [MarkovAutoregression (replikasi Kim-Nelson)](https://www.statsmodels.org/devel/examples/notebooks/generated/markov_autoregression.html)

## 10. Keputusan
1. HMM masuk sistem sebagai **sinyal pembanding** (`signal_id=HMM_REGIME`) — tidak pernah menggantikan regime score §11.1 (alasan §5.4).
2. Fitur inti tier-1 = ADS, CFNAI, T10Y3M, VIXCLS, CMDI (as-of join `release_ts`; CMDI mingguan); tier-2 +DTWEXBGS Δ20d sebagai uji sensitivitas. **Tanpa return instrumen** (anti-circularity).
3. Spesifikasi: K=3 (CALM/MID/STRESS via ordering-by-variance), kovarians diag, jendela expanding 2005→, refit bulanan, sinyal harian = baris terakhir `predict_proba`.
4. Implementasi menunggu F4; tahapan E1→E2→E3 dengan gerbang eksplisit (§8) — E2 butuh ±12 bulan snapshot sendiri.
5. `smoothedUSRecessionProbabilities` (FMP) tetap di Blok D dan mendapat peran baru: **benchmark eksternal** untuk validasi E1/E2 (dua model independen seharusnya sepakat di resesi besar).
6. Jebakan diterima secara eksplisit (label switching, overfitting, non-stationarity, transisi jarang, look-ahead, jitter) dengan mitigasi masing-masing (§7) — bukan alasan menolak, tapi alasan memposisikannya sebagai pembanding.

## Glosarium cepat (istilah yang muncul di dokumen ini)
- **Regime** — "keadaan/mood" pasar atau ekonomi yang bertahan berminggu-minggu hingga bertahun-tahun (mis. risk-on, resesi, vol tinggi).
- **State laten / tersembunyi** — besaran yang tidak bisa diamati langsung, hanya disimpulkan dari efeknya pada data.
- **Rantai Markov** — proses acak yang peluang langkah berikutnya hanya tergantung keadaan sekarang.
- **Matriks transisi** — tabel peluang pindah state; diagonal besar = regime lengket.
- **Emission** — pola statistik data observasi yang "dipancarkan" tiap state (Gaussian = bel kurva, punya rata-rata & sebaran).
- **EM / Baum-Welch** — algoritma latih iteratif: tebak → evaluasi → perbaiki, sampai stabil.
- **Filtered probability** — kesimpulan state hari ini hanya dari data masa lalu (sah untuk live); **smoothed** — kesimpulan yang boleh melihat masa depan (hanya untuk analisis sejarah).
- **Look-ahead bias** — kesalahan memakai informasi yang belum tersedia pada saat keputusan dibuat; membuat backtest terlihat lebih pintar dari aslinya.
- **Overfitting** — model menghafal noise sampel, bukan pola; in-sample bagus, out-of-sample buruk.
- **Label switching** — kegagalan identitas: nomor state bisa tertukar antar pelatihan walau isinya sama.
- **BIC/AIC** — ukuran kualitas model yang menghukum jumlah parameter; dipakai memilih jumlah state.
- **Histeresis** — dua ambang berbeda untuk masuk vs keluar sebuah state, agar label tidak berkedip di batas.
