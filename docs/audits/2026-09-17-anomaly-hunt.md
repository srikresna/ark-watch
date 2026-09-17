# Audit Sistemik Anomali — 2026-09-17

## RONDE 4 DIPERLUAS (2026-09-17 malam) — 19 agen, 641 tool-calls, 25 + 3 kritikus — DITUTUP (b5aba09)

Pemicu: pemilik belum percaya "bersih" — dan BENAR. Wilayah baru: jadwal daemon, outbox,
riwayat brief, integritas DB, vintage ALFRED, kontradiksi konfigurasi, jalur UX, kode malam itu.

**P0 — korupsi indeks server (3 lensa konvergen; ronde-2 sempat REFUTE, ronde-4 drill lebih
dalam menemukannya):** baris PK duplikat tersembunyi di computed_signals (esi@09-16, rowid 7367
vs 8049) di balik indeks rusak → backup malaman gagal 2 malam, **nol backup valid**. Scan
rowid-murni menemukan apa yang GROUP BY (pakai indeks rusak itu) tak bisa. Dihapus, REINDEX,
integrity ok, **backup valid pertama** (118MB), file korup dirotasi. Alert kegagalan-job kini
dirute ke outbox watcher (gejala: 2 malam senyap).

**P1 utama:** gate coverage false-clean (MAX TEXT = leksikal! 'unknown'>'high' → selalu 0 gap)
→ SUM()+gate rilis-distink; **27 keluarga nyata kini terlihat** (bukan defek — antrean triase:
kembar NSA/CPI-S-A/U-6/GOODS-TRADE/FED-DECISION by-design atau kandidat seri); PPIFIS fake-link
→ PRODUCER PRICE INDEX MOM + alias TV; FOMC Juni-2027 seminggu telat vs kalender kurasi + test
struktural kesetaraan; kedalaman revisi FRED freq-aware (M:36) + vintage first-print per fetch
(bebek sejak 09-02); jendela CAL max-62 hari + filter konsensus dihapus + rute backfill --cal
ber-log; rasio Sources dijangkar hari-WIB (UTC-day = 1/1 palsu di slot 07:00); header Flows:.
**P2:** redaksi kunci-API di kedua penulis fetch_log; alias/kasus explore-signal + warning tak-
terdaftar; guard export --csv; PCETRIM dobel-registrasi dinonaktifkan; residu jam 284 baris.

**Ditunda (terdokumentasi):** watcher decoupling dari job panjang (refactor berisik), progres
chunk Telegram, riwayat edisi brief.

---

## RONDE 3 (2026-09-17 malam) — 11 agen, 352 tool-calls, 9 terkonfirmasi — SEMUA DITUTUP (a940746)

Konvergensi: 31 → 27 → 9 (7 di antaranya residu fix hari-yang-sama — pola protokol normal).
Ronde-3 juga me-REFUTE dengan bukti: 9 kontrak TFF aman di-z, _reconcile_gaps terbatas,
PK flows_daily aman, tripwire sehat, render e2e LOKAL bersih 0 temuan, watcher dry-run
2× bersih (dedup bekerja).

| Temuan | Penutup |
|---|---|
| P0 GLD phantom 1.006t di brief malam tadi (baris fallback basi + misprint weekend arsip) | purge guard post-frontier + skip baris Sabtu/Minggu + purge data (2 lokal / 3 server) |
| P1 f2 crash TIAP run (loop var `a` menimpa argparse Namespace) | rename + arsip dithread (download 2× → 1×) |
| P1 VOI buta 5/6 kelas aset (exists-check global) | pre-check dihapus (PK dedup) — live: 1.068 produk |
| P1 _reconcile_gaps dead code (frontier dibaca pasca-save) | snapshot pre-save |
| P1 verify DB-fallback dead code (filter target mengecualikan routeless) | filter diperluas + conn sekali-buka |
| P1 backward-compat root-key mematikan snapshot BARU selamanya (soma/gold_ry/copper) | revert + migrasi 128+32 bare→@ keys (kedua DB), dup root soma dihapus |
| P1 σ NEW HOME SALES 1,69× (winsor memangkas kontaminan tapi tetap menggelembung) | compute_sigma EXCLUDE >10-MAD; ESI rebuild |
| P2 XVAL positif-palsu pada bar intraday berjalan | batas `ts < today` |

**Sisa antrian (feature-add, bukan defect):** ~~seri derivat ISM~~ ✅ + ~~kolom
calendar_family~~ ✅ (325e397, dikerjakan malam yang sama):
- **CAL: tipe seri baru** (fetchers/caldist.py via ROUTES): 6 keluarga ISM jadi
  seri bulanan level dari events.actual (PMI Mfg 54,6 / Svc 55,4 / Prices 71,1 &
  72,6 — cocok eksak dengan kalender). Tipe tier-4, ref-month dari token nama
  dengan rollover Jan→Des, dedup MAX.
- **calendar_family (schema v16) + gap query di coverage.py**: kelas HOUST/PERMIT
  kini terlihat struktural. 15 seri dianotasi. **Query langsung menemukan 1 celah
  nyata yang tak ada di radar audit manapun** — PERSONAL INCOME MOM (60 aktual
  high-importance) — ditutup dengan FRED:PI (811 obs sejak 1959). Coverage: **0 gap**.
- **Split NEW HOME SALES: skip dikonfirmasi live** — keluarganya level-consistent
  (~0,6jt SAAR); kontaminan residual sudah terkarantina + ter-exclude dari σ.

**Round-4 alami = soak besok pagi** (daemon jalankan siklus penuh pertama dengan
seluruh fix; pantau fetch_log + brief).

---

## RONDE 2 (2026-09-17 sore) — 17 agen, 509 tool-calls, 27 terkonfirmasi + 2 kritikus

Fokus: regresi dari fix hari ini + tabel yang belum pernah diaudit. **5 temuan = regresi
dari fix sendiri** (protokol konvergensi bekerja). 8 prioritas tertinggi diperbaiki hari
ini juga (commit `c390b12`):

| # | Temuan | Status |
|---|--------|--------|
| P0 | XCCY brief campur tanggal: futures T-1 vs spot intraday → +278bp omongkosong | ✅ spot dipin ke trade_date |
| P1↩ | demote importance PERMANEN (regresi fe96f99) | ✅ restore ter-guard di upsert+consensus |
| P1↩ | sibling-heal buta satuan → 1 kontaminasi σ (regresi fe96f99) | ✅ guard band 0.1x–10x |
| P1↩ | stablecoin ganti definisi mid-stream (regresi b86071c) | ✅ peggedUSD (bukti: cocok sen) |
| P1↩ | ECBWatch delta meeting-decided terpasang ke Oct-29 (regresi 8da5ec3) | ✅ exact impl-date match |
| P1↩ | 4+9 baris re-key terdampar di luar jendela pull | ✅ heal pull 09-01..05 |
| P1 | claims join gagal di 'SEP 05' vs 'SEP 5' | ✅ zero-pad 02d |
| P1 | FedWatch line tanpa tanggal pricing vintage | ✅ tail (ZQ 09-15) |
| P1 | CVOL MAX global tanggal campur → simbol hilang | ✅ per-simbol 4d + asof |
| P2 | ghost indicator_stats 12+17 kunci | ✅ cleanup struktural di compute_sigma |
| P2 | anchor RSAFS stale vs revisi | ✅ rekalibrasi 764.462 |
| P1 | GLD 830t fallback phantom (−17,5% palsu) | ✅ baris 08-31 NULL; archive-backfill → antrian |

**Antrian baru dari ronde 2** (menambah 21 ronde-1):
- [ ] COT render 8/13 kontrak (AUD CROWDED 3 minggu tak tampil!) — perluas loop financials brief + ETH (146021) di COT_NAMES
- [ ] cot_gate TFF fallback (9 kontrak finansial tak terverifikasi silang)
- [ ] rekonsiliasi lubang trade-date CME (retensi 5 hari, mekanisme walkback terbukti)
- [ ] VOI final restatement + filter report_type di baris Sabtu
- [ ] fetch_log CME rows semantics (selalu 14, bukan baris baru)
- [ ] GLD/SLV blind-log + backfill arsip per-tanggal-data + brief NULL-skip fallback
- [ ] gerbang validasi-silang sweep harga (XPTUSD 09-10 +5,45% vs PL1)
- [ ] kontaminasi unit-σ CME %MoM vs level (RETAIL SALES→RETAIL SALES MOM alias, PREL strip, compute_sigma pasangan-satu-baris)
- [ ] keluarga yatim n=1 tak pernah dapat z (alias nama headline → keluarga pembawa nilai)
- [ ] entri GDPNow overnight_changes mati structural (redesign, jangan naikkan max_age mentah-mentah)
- [ ] invariant recompute CNN history rusak (758 baris raw, Δ hingga 14,0)
- [ ] backward-compat cooldown key (hitung root alert_type juga di cabang permanent)
- Residual diterima: upsert harga tanpa freshness-guard (last-write-wins; tak ada observasi)

**Refuted ronde 2** (jangan di-audit ulang): int(_h) unreachable (fetcher _iso guard),
alias mis-merge (semua pasangan same-unit), sibling-heal cross-source (0 baris FIP di US-rows),
watcher keys None-safe, fedwatch bootstrap wiring benar, ES1/GC1 volume duplikat = quirk Yahoo,
surprise_z backlog self-fill 06:45, kesehatan PK computed_signals.

---

## RONDE 1 (2026-09-17 pagi)

**Metode:** 17-agen workflow adversarial (8 lensa paralel → verifikasi per-lens → kritikus
kelengkapan), 453 tool-calls, ~1,37M token. Setiap temuan wajib bukti SQL; verifikasi ulang
membantah 3 temuan (protokol bekerja). Pemicu: dua anomali ketahuan kebetulan (feed Prices
Paid mati 2023; HOUST/PERMIT tak terdaftar) — teguran pemilik: anomali kelas ini harus
ketemu dari audit, bukan kebetulan.

**Hasil: 31 temuan terkonfirmasi + 2 kritikus. Diperbaiki hari ini: 12 (P1 utama).**

## Terpenuhi (12)

| # | Temuan | Perbaikan | Commit |
|---|--------|-----------|--------|
| 1 | Bar harga parsial/NULL terkunci permanen (INSERT OR IGNORE) — ES1 8 bar salah (terburuk −1,5%), GC1/SI1/HG1/PL1 NULL-close | Upsert COALESCE (non-NULL terbaru menang, NULL tak pernah menimpa) + perbaikan penuh kaki Yahoo di kedua DB | 816f286 |
| 2 | Stub CME tak pernah membawa data (237 baris, 93 rilis tak pernah terisi) — hantu radar mingguan | Gate ingest + hapus 139/150 baris + demote pentingnya baris tanpa nilai | fe96f99 |
| 3 | Jendela heal 3 hari tak selamat dari downtime daemon (113 pasangan terdampar) | pull() → 10 hari | fe96f99 |
| 4 | Kembar TV terdampar NULL selamanya (NFP 09-04: kembar FMP bawa actual=162) | Penyembuhan antar-baris (saudara kandung) di save() + penyembuhan historis (39/41 baris) | fe96f99 |
| 5 | FMP mengganti nama keluarga (CPI→Inflation Rate, ISM Non-Mfg→ISM Services, Markit→S&P, Budget→MBS) → kunci pecah, ESI dihitung dua kali | Peta alias + re-key 533 baris, 12 keluarga melebur (196→184 indikator), ESI rebuild | fe96f99 |
| 6 | 195 baris AS pada jam mustahil (05:30Z = 01:30 ET, FMP tz-slip) | Gerbang jam saat ingest (degrade → khusus tanggal + rendah) | fe96f99 |
| 7–12 | (eskalasi hari yang sama, commit sebelumnya) feed sub Philly mati + seri HOUST/PERMIT/GAC/PPC — pemicu audit ini | 2944dc7 |

## Antrian — prioritas & pemilik perbaikan terverifikasi

### Pri 1 — tutup celah data (kelas HOUST/PERMIT)
- [x] **FRED:CPILFESL** ✅ 6ea9a77 (835 obs; YoY derivasi 2,45% vs kalender 2,4 — tervalidasi)
- [x] **Kompleks PPI** ✅ 6ea9a77 (PPIFIS FD SA + WPSFD49507 core FD — dipilih atas PPIACO agar MoM sebanding kalender)
- [x] **FRED:UMCSENT, FRED:DGORDER, FRED:CES0500000003** ✅ 6ea9a77
- [ ] **ISM PMI sebagai seri derivat dari events.actual** (CAL:ISM_MFG/SVC + Prices) — ~450 aktual menunggu.
- [ ] Kolom `calendar_family` di series_registry + query qa/coverage → kelas celah jadi terlihat struktural
      (gerbang: ≥24 aktual DAN importance tinggi — tanpa gerbang, ~120 keluarga melapor di hari pertama).

### Pri 2 — feed & gerbang
- [ ] **CMDI feed hantu** (1 obs vs 1.129 ekspektasi; log OK-0-baris menelan error): implementasi paginasi
      EODHD `page[offset]` ATAU `active=0` + log EMPTY (bukan OK).
- [ ] **LME soft-404** (stocks-september-2026.xlsx balas HTML 200; 20 hari mati senyap): bedakan 200-non-PK
      dari format tak dikenal → ERROR bernama; telusuri path arsip baru.
- [ ] **Batasan sanity longgar** (16 seri tak akan pernah menangkap apa pun; mis. BAML C0A0CM [0.4, 8] dari
      sejarah domain, bukan rentang tersimpan) + **lebarkan 5 batas** untuk ekstrem tersimpan 1974-82
      (DGS10→16, DFF→23, T5YIE→−3, T10Y3M→6, Philly diffusion→95).
- [ ] **Cadangan gerbang verify untuk prefiks tanpa ROUTE** (baca nilai terakhir realtime dari DB, terapkan
      gerbang batas) — menutup LME: + prefiks baru berikutnya.
- [ ] **Gerbang sanity: sapuan riwayat + rute alert** (kini terbaru-saja + log-saja; kirim ke outbox
      dengan mekanisme cooldown watcher, kunci per seri).
- [ ] **Plafon keusangan per-seri** (`max_staleness_days` dari release_schedule, override atas pemetaan
      freq generik) — menutup kelas OK-0-baris (CMDI) tanpa alarm palsu 8-10 seri sehat.
- [ ] **DefiLlama**: normalisator terpusat + uji payload live + backfill N-hari per eksekusi (lubang 09-09/14/15).
- [ ] **TIC gate deterministik** (error setiap eksekusi yang menerima period < cutoff, bukan hanya eksekusi
      pertama; cek kalender rilis Treasury — jika Juli-26 sudah terbit, eskalasi → P1).
- [ ] **fetch_log untuk jalur backfill** (4 seri baru tak punya baris OK).
- [ ] **Daftar kesehatan target f2 buta** (10 target: CNN:FG, FARSIDE:*, LME:OWSR, SAFE, LBMA, TIC —
      periksa di _health_detail per target+kadens, TANPA entri registry paksa).
- [ ] **Kunci params_signals**: esi_flip_min_abs, gold_ry_div_min_bp, cot_broad_div_min, cot_covering_net_min,
      cot_covering_chg_min, vix_z_stress; hapus orphan funding_extreme_bps.
- [ ] **Penjaga spam alert**: peringatan bila 1 cooldown_key >2 pengiriman/7 hari.
- [ ] **Aliran gap replay**: Farside 09-14 bisa diambil ulang (tabel historis); cnn_comp_* snapshot
      hari-jalan → gap-deteksi + alert saja.

### Dibantah (3) — dicatat supaya tidak diulang
- Indeks PK computed_signals "korup" + backup gagal 100% → integrity check BERSIH, backup berjalan.
- FMP:COT-GATE "mati 75%" → gate memang Sabtu-saja + degradable.
- DCOILWTICO "buta 5 hari" → pengisian normal pasca-akhir pekan, sumber sehat.

## Catatan arsitektur
- DB lokal kini dev-only (server = produksi 24/7 sejak 09-16). Temuan "daemon lokal mati 4 hari kerja"
  bukan anomali pasca-migrasi — tapi PC tetap perlu Task-Scheduler autostart bila dipakai sebagai fallback.
- EODHD kalender tidak pernah membawa aktual untuk baris makro (155/159 NULL) — perannya validasi-silang
  lelang/ETS/Baker Hughes; baris makro-nya didemote saat merge bila keluarga sudah tercakup sumber lain (antrian).
