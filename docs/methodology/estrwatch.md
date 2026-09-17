# ESTRWatch — Metodologi (D-006)

*Probabilitas hike/cut/hold ECB per rapat Governing Council, dari futures
€STR 3 bulan (CME code ESR). Dibangun 2026-09-10 dari riset 5-agen
(metodologi publik + spesifikasi kontrak + kalender resmi) + review
adversarial. Versi Bahasa sederhana: `docs/explained/` seri kebijakan.*

## Rantai logika dalam satu paragraf

Harga futures ESR memberi tahu **rata-rata suku bunga malam-malam Eropa
(€STR) yang diharapkan pasar** untuk tiap kuartal ke depan. Karena
keputusan bunga ECB mengubah €STR secara bertangga (step), dan rapatnya 8x
setahun sementara kontrak kuartalan hanya 4/tahun, satu kontrak memuat
1–2 lompatan — maka seluruh kurva diselesaikan **serentak** (least
squares berbobot hari), lalu tiap lompatan diubah ke probabilitas lewat
grid 25bp ala FedWatch resmi CME.

## Fakta kontrak (terverifikasi)

| Fakta | Nilai | Bukti |
|---|---|---|
| Harga settle | `100 − rata-rata aritmetika €STR` atas Reference Quarter | CME Rulebook Ch.480 |
| Reference Quarter | [Rabu ke-3 bulan kontrak, Rabu ke-3 +3 bulan) | CME settlement-calc PDF |
| Bulan kontrak | **AWAL** masa akrual (SEP26 = Sep16→Des16) | empiris: implied JUN26 2.1925 ≈ realized €STR Jun-17→Sep-9 |
| Seri bulanan (OCT/NOV/…) | tidak dipakai — print tipis/zigzag (OCT26 1.945 vs NOV26 1.415) | data produksi |
| Kontrak kadaluarsa | masih di-print CME — difilter `e ≤ anchor` | JUN26 muncul di strip 09-09 |

## Fakta kalender ECB (ecb.europa.eu, diakses 2026-09-10)

- Rapat kebijakan 8x/tahun, 2 hari (Rabu–Kamis), **keputusan hari ke-2
  14:15 CET** (waktu Frankfurt, sadar-DST), konferensi pers 14:45.
- Rapat **bukan**-kebijakan (mis. 2026-09-30, 2026-11-25, rapat virtual
  2027) TIDAK menghasilkan keputusan bunga — tidak masuk jadwal.
- Implementasi keputusan: **Rabu pertama setelah Kamis pengumuman** (awal
  periode reserve-maintenance baru). Bukti empiris: €STR melompat
  1.931→2.182 tepat di 2026-06-17, enam hari setelah keputusan 2026-06-11.
- Jadwal lengkap disimpan 2 tempat (preseden FOMC): konstanta
  `ECB_GC_DECISIONS` di transform + `config/curated_calendar.yaml`
  seksi `ecb_gc_*`. Refresh kuartalan; 2028 ditambah saat ECB rilis.

## Formula

Unknown: δ_j = perubahan €STR di tanggal implementasi rapat j (hanya
rapat dengan implementasi setelah anchor). Untuk tiap kontrak k dengan
jendela [s_k, e_k), N_k hari, forward-implied F_k:

```
A_kj = |{d : max(s_k, a+1) ≤ d < e_k, d ≥ t_j}| / N_k     # bobot hari
c_k  = (Σ realized(d) − n_real·r_a) / N_k                  # koreksi jendela berjalan
b_k  = F_k − r_a − c_k
solve: min_δ Σ_k (A_k δ − b_k)²   → minimum-norm (numpy lstsq, rcond 1e-6)
```

- `r_a` = **fixing €STR terakhir** (ECB:ESTR) — BUKAN DFR dan BUKAN
  DFR−spread: kesalahan anchor ±5bp menggeser probabilitas ±20pp.
- Weekend-carry pada realized (Sabtu/Minggu bawa fixing Jumat); libur
  TARGET diabaikan di v1 (<0,5bp/kuartal, L5).
- **Mengapa minimum-norm**: matriks desain rank-7-dari-11 secara
  STRUKTURAL (SVD live 2026-09-10: 4 arah nol persis) — dua rapat dalam
  satu kuartal hanya bisa dibedakan lewat beda bobot hari di satu baris.
  Persamaan-normal OLS biasa kolaps (pivot 1e-15, solusi sampah ±362bp).
  Min-norm = satu-satunya solusi tanpa komponen arah-nol = paling tidak
  arbitrer; rapat-rapat depan (yang ditampilkan brief) berada di
  subruang teridentifikasi-baik (singular values teratas).

Probabilitas (konvensi resmi CME FedWatch, characteristic/mantissa):

```
E = |δ_j| / 0.25;  k = floor(E);  m = frac(E)
P(k×25bp) = 1−m,  P((k+1)×25bp) = m
|δ| < 1bp → hold 100%
```

`implied DFR` setelah rapat j = `dfr_now + Σ_{i≤j} δ_i` — basis €STR−DFR
dibekukan per snapshot (konvensi €STRWatch resmi CME; hari ini −6,1bp);
basis menghapus diri pada PERUBAHAN rate.

## Gerbang kualitas

- **RMS residual ≤ 3bp** — lebih dari itu: flag `degraded` + "⚠ fit" di
  brief (live 2026-09-09: 0,68bp; fitted = aktual semua kontrak, deviasi
  maks 1,5bp — konsisten dengan `ecb_path`).
- Σ(ease+hold+hike) = 1 semua baris (assert test).
- Anchor hilang → snapshot DILEWATI dengan warning (preseden FedWatch:
  tidak pernah membekukan rate hard-coded).
- `exact` = rapat satu-satunya unknown di kuartalnya; kalau berbagi →
  `noise_amp = 1/|w1−w2|` (mis. 1,86×) — hanya rapat pertama yang
  ditampilkan di brief.

## Keterbatasan (jujur)

1. **Pecahan dua-rapat-satu-kuartal = konvensi**, bukan observasi —
   min-norm memilih pemecahan paling tidak-arbitrer, tapi rapat ke-2
   dalam satu kuartal lemah (flag `null_space_split`).
2. Basis €STR−DFR beku; basis melebar >15bp → flag `basis_wide`
   (indikasi patah rezim).
3. Futures = ramalan risk-adjusted (bias term premium membesar di
   horizon jauh) — rapat ke-3+ paling lemah; jangan baca sebagai
   probabilitas netral-risiko murni.
4. Grid 25bp; langkah >25bp di-split mantissa (sizes di raw_json).
5. Arithmetic ≈ compounded <1bp pada level 2–3% (sederhana disengaja).
6. Seri bulanan ESR tidak dipakai (print rusak) → resolusi
   intra-kuartal bulanan hilang. Roadmap: futures ECB-dated (Eurex/ICE)
   bila sumber gratis tersedia.
7. Tanpa oracle probabilitas resmi (CME €STRWatch = tool SKENARIO, bukan
   oracle) → validasi eksternal hanya situs riset (ecb-watch.eu,
   centralbank.watch; MAE mereka 4,1pp = skala diskripsi wajar) +
   konsistensi internal vs `ecb_path`.
8. Retensi strip CME ~5 hari → tidak ada backfill; kalibrasi
   point-in-time (raw_json menyimpan diag per snapshot, histori
   terakumulasi otomatis).
9. `xccy._imm_approx` (Rabu→Senin ke-3, 2 hari awal) TIDAK dipakai di
   sini; perbaikan xccy = tiket terpisah (L11).

## Sejarah sikap

Dokumen lama (docs/explained/01-block-a) pernah menolak probabilitas
per-rapat ECB ("mengarang presisi palsu") dan memilih path-only.
Pembalikan ini beralasan: (a) OLS-serentak menyelesaikan
under-determination secara eksplisit dan bergerbang, bukan mengarang;
(b) konvensi split kini di-mark (null_space_split/noise_amp), bukan
disembunyikan; (c) kasus 1-rapat-per-kuartal — mayoritas rapat —
terduit tepat ke aljabar FedWatch yang sudah terverifikasi ≤3pp.
