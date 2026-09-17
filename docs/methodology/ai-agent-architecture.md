# METHODOLOGY — Arsitektur AI Layer (Agent LLM sebagai Analis On-Demand)

> Seri: deep-dive metodologi. Status: **desain konseptual selesai 2026-08-30; implementasi lapisan L2 = pasca-F3** (roadmap §7).
> Posisi dalam sistem: AI layer adalah **analis on-demand di atas data yang sudah dikumpulkan dan diverifikasi engine utama** — bukan otak pengambil keputusan, bukan sumber angka, bukan jalur eksekusi order.
> Basis: eksplorasi 3 repo referensi — `references/deepseek-harness/` (laporan lengkap), `references/TradingAgents/` dan `references/AlpacaTradingAgent/` (laporan terpotong saat diterima; klaim kunci di dokumen ini diverifikasi langsung ke kode/README repo). Pola yang dipinjam dicek ke sumbernya, bukan dari ingatan.
> Dokumen saudara: [BUILD-PLAN.md](../BUILD-PLAN.md) (fase F0–F5 + skema DB), [DATA-SPEC.md](../DATA-SPEC.md) (APA), [hmm-regime-detection.md](hmm-regime-detection.md) (pembanding statistik regime).

## 1. Masalah yang dicoba dipecahkan

Engine ark-watch menghasilkan brief harian berisi angka dan state (DATA-SPEC §14). Angka sudah terverifikasi — tapi yang sering dibutuhkan trader bukan angkanya, melainkan **jawaban atas pertanyaan kontekstual**: "kenapa gold turun padahal real yield flat?", "apakah funding +0.01% ini ekstrem secara historis?", "apa saja yang berubah sejak Jackson Hole?". Pertanyaan begini butuh perangkaian data lintas blok + pengetahuan naratif — persis pekerjaan seorang analis manusia, dan persis yang diminta user di sesi perancangan sistem ini (workflow 8-agen, audit adversarial, dll — semuanya "agent LLM + akses data + skeptis").

Dokumen ini merancang bagaimana peran itu dijinakkan menjadi komponen sistem yang jujur, terukur, dan aman. Prinsip dokumen: **kejujuran teknis di atas hype** — setiap klaim kemampuan AI harus bisa ditunjukkan mekanismenya atau tidak ditulis.

## 2. Klarifikasi fundamental: LLM tidak "belajar" dengan sendirinya

### 2.1 Apa yang sebenarnya dimiliki LLM

LLM (Large Language Model — model bahasa besar seperti yang menjalankan sesi perancangan ini) dilatih sekali oleh penyedianya atas korpus teks raksasa yang **beku** (ada tanggal potong pengetahuan). Saat dipakai, ia tidak menambah pengetahuan itu. Yang berubah antar-percakapan hanyalah **konteks** — "jendela" teks terbatas (diukur dalam satuan *token*, kira-kira potongan kata) yang berisi instruksi + data yang kita sodorkan + percakapan sejauh ini. Begitu sesi selesai, jendela itu kosong lagi. Kesimpulan pentingnya:

> **"AI yang makin pintar mengikuti data harian kita" bukan properti model — itu properti sistem yang kita bangun di sekitarnya.**

Istilah yang akan dipakai di seluruh dokumen:
- **RAG** (Retrieval-Augmented Generation): sebelum menjawab, sistem *mengambil* potongan data relevan dari database kita dan memasukkannya ke konteks; model menjawab **hanya berdasarkan potongan itu**. Model tidak "hafal" WALCL — ia diberi baris WALCL.
- **Tool use**: model tidak menelusuri internet bebas; ia memanggil fungsi buatan kita (`get_series(...)`) yang mengembalikan JSON. Kita yang mengendalikan apa yang bisa diambil.
- **Agent**: LLM + daftar tool + loop "panggil tool → baca hasil → putuskan langkah berikutnya". Agen = karyawan magang yang rajin tapi harus selalu menunjukkan sumbernya.
- **Fine-tuning**: melatih ulang (atau menyetel) bobot model pada data contoh milik kita — satu-satunya cara model itu sendiri berubah. Mahal, butuh ribuan contoh berkualitas, dan sulit dievaluasi. Kita tandai "jauh, opsional" (§3.3).

### 2.1b Peta jujur kemampuan (yang menentukan pembagian kerja §2.3)

| Tugas | LLM | Kenapa |
|---|---|---|
| Menjelaskan konsep ("apa itu QT?", "apa arti backwardation VIX/VXV?") | ✅ kuat | pengetahuan beku model; konsep stabil, jarang berubah |
| Merangkai narasi lintas-blok dari data yang disodorkan | ✅ kuat | inti pekerjaan L2 |
| Menemukan pertanyaan yang tidak terpikirkan manusia | ✅ berguna | pola reviewer skeptis (sudah terbukti di audit desain) |
| Menghitung angka (rata-rata, z, probabilitas) | ❌ lemah | aritmetika = titik halusinasi; ini kerja L1/pipeline |
| Mengingat rilis kemarin tanpa disuapi konteks | ❌ lemah | tidak ada akses; karena itu injeksi segar §5.3 wajib |
| Mengetahui harga/level "sekarang" | ❌ mustahil | pengetahuan beku + tanpa tool; karena itu RAG atas DB |
| Memperbaiki diri antar-sesi | ❌ | konteks terhapus; "belajar" hanya via log (§6 G3) |

### 2.2 Tiga tempat "belajar" yang sesungguhnya

| # | Di mana belajar terjadi | Mekanisme | Status di ark-watch |
|---|---|---|---|
| (a) | **Database akumulasi + statistik** — sistem ark-watch sendiri | Setiap rilis baru = baris `raw_observations` baru; σ rolling di-update per rilis (`indicator_stats`, BUILD-PLAN §3 Blok I); window z-score memanjang. Sistem makin "paham" distribusi data **tanpa satu baris kode AI** | **Sudah dirancang penuh** — ini lapisan L1 (§3.1) |
| (b) | **Agent LLM sebagai analis on-demand** atas data (a) | RAG + tools atas DB arkwatch; "kecerdasan" = kombinasi pengetahuan beku model (konsep, bahasa) dengan data segar kita | **Dirancang di dokumen ini** — lapisan L2, bangun pasca-F3 |
| (c) | **Fine-tuning** | Melatih model pada log kasus ark-watch sendiri | Jauh; kriteria eksplisit §3.3 |

Konsekuensi desain dari tabel ini: **semua jalan "belajar" yang murah dan terukur ada di (a) dan (b)**. (a) deterministic dan bisa di-unit-test; (b) fleksibel tapi harus dijaga dengan guardrail §6. (c) tidak dibahas sebagai rencana — hanya sebagai pintu yang sengaja ditutup sampai kriterianya terpenuhi.

### 2.3 Konsekuensi kedua: pembagian kerja yang tegas

LLM itu kuat merangkai narasi dan lemah berhitung (aritmetika dan angka hafalan adalah tempat paling sering berhalusinasi). Maka aturan pembagian kerja L1/L2:

- **Semua angka di brief tetap dihitung pipeline statistik (L1)** — dari `raw_observations` lewat transform-spec terkunci (BUILD-PLAN §3). Agen AI **tidak diberi hak menghitung angka headline**, hanya membaca nilai yang sudah dihitung.
- **Agen AI menjawab "kenapa", "apa konteksnya", "apa yang aneh"** — dan setiap pernyataan faktualnya wajib menunjuk `series_id`/`event_uid`/`signal_id` di DB (§6 G2).

## 3. Arsitektur tiga lapis

### 3.1 L1 — lapisan statistik (sudah dirancang; INI "belajar"-nya ark-watch)

L1 adalah seluruh mesin yang sudah dispesifikasikan BUILD-PLAN, ditambah dua statistik probabilistik yang mengubah data akumulasi menjadi **peluang** (bahasa probabilitas, bukan bahasa narasi — ini yang tidak bisa disubsitusi LLM):

1. **P(outcome berita) — dari surprise & nowcast-vs-consensus.** Kita sudah punya `surprise_z = (actual − consensus)/σ_5y-rolling` per indikator (DATA-SPEC §9, min 30 obs, winsorized). Akumulasi historis z ini = **distribusi empiris seberapa besar berita biasanya meleset dari konsensus** per indikator. Contoh bacaan jujur: "CPI 12 bulan terakhir meleset di bawah konsensus 8 kali; z hari ini −0.4 → bukan kejutan statistik". Ditambah perbandingan **nowcast-vs-consensus** (Cleveland/Atlanta vs consensus FMP) = peluang arah kejutan *sebelum* rilis. Ini handicapper, bukan peramal.
2. **P(reaksi pasar) — dari event-study akumulasi.** *Event study* = metode standar riset keuangan: kumpulkan semua kejadian sejenis di masa lalu, luruskan pada jadwal kejadian (H−5 … H+5), lalu ukur distribusi return instrumen di jendela itu, dikelompokkan per arah/besarnya surprise. Hasilnya peluang empiris: "setelah CPI-surprise z<−1, return XAUUSD 5 hari ke depan positif 11 dari 16 kali, median +0.8%" — angka yang bisa dilawan datanya. **Syarat mutlak: anti look-ahead** (pakai kolom `release_ts`, BUILD-PLAN §2 — return hanya dari waktu pasar tahu). Mesinnya = mesin yang sama dengan regime→returns F4; L1-lah yang membuat akumulasi CVOL/xccy/esr (series muda, §19.4) bermakna: data sendiri yang tumbuh.

   Contoh mikro cara membacanya (angka ilustrasi): misalkan event-study CPI-vs-XAUUSD menghasilkan — surprise z<−1 (12 kejadian): median return H+5 = +0.9%, positif 9/12; |z|≤1 (61 kejadian): median +0.1%, ~50/50; z>+1 (15 kejadian): median −0.3%, positif 6/15. Tiga properti penting langsung terlihat: (a) ini **distribusi, bukan ramalan** — 9/12 bukan "akan naik"; (b) sampel kecil terlihat jujur sebagai angka kecil (n=12), otomatis menahan overconfidence; (c) kelompok "biasa" (|z|≤1) menunjukkan mayoritas rilis TIDAK menggerakkan apa pun — pelajaran paling mahal bagi trader harian yang menganggap tiap CPI adalah event. Saat agen L2 ditanya "CPI besok, harus takut?", jawaban yang benar bukan opini model — melainkan tiga baris distribusi ini dari L1, disitasi ke event_uid agregatnya.

Kalibrasi L1 terukur: **hit-rate dilaporkan** (gerbang F4 "hit-rate per regime terlaporkan"). Ketika L1 bilang 60%, kita tahu persis historisnya berapa — klaim LLM tidak punya properti ini tanpa §6 G3.

### 3.2 L2 — analis agentic (inti dokumen ini)

**Definisi**: agent LLM (model + loop + daftar tool read-only) yang berjalan di atas DB arkwatch, kalender, dan brief yang sudah jadi. Karakteristik:

- **Tugas**: riset kontekstual lintas blok, investigasi anomali (§11.5 DATA-SPEC), menjawab "kenapa", menyiapkan bahan tinjauan mingguan, dan — penting — berperan sebagai *reviewer skeptis* atas output sistem sendiri (pola yang terbukti bekerja di audit adversarial 28-temuan BUILD-PLAN).
- **Bukan tugas**: menghitung angka headline, memutuskan posisi, mengeksekusi apa pun, menulis ke tabel data. Tidak ada tool untuk itu (§6 G1).
- **Modal kerja**: tool baca DB (desain §5), konteks segar yang diinjeksi sistem per-run, dan pengetahuan konseptual beku model (apa itu QT, apa itu backwardation).
- **Analogi yang jujur**: analis magang yang pintar bertanya ke arsip perpustakaan yang 100% terverifikasi — tapi semua kutipannya harus mencantumkan nomor rak, dan kita mencatat tiap analisisnya untuk dinilai kemudian.

### 3.3 L3 — fine-tuning & evaluasi terjadwal (jauh, opsional)

L3 yang *dekat* hanyalah **evaluasi terjadwal** (§6 G3): resolusi klaim L2 vs data yang datang kemudian, dilaporkan di re-kalibrasi kuartalan (BUILD-PLAN §6.2). Fine-tuning sungguhan **ditunda dengan kriteria eksplisit**, bukan selamanya-dilarang: baru masuk pertimbangan bila (i) log klaim L2 sudah ≥ ribuan kasus ter-resolusi, (ii) ada pola kegagalan L2 yang berulang dan bisa diperbaiki contoh (bukan bisa diperbaiki prompt/tool), (iii) evaluasi A/B vs prompt-baseline menunjukkan peningkatan terukur. Ketiganya belum mungkin sebelum sistem berjalan ~1 tahun — itulah arti "jauh".

| Lapis | Isi | "Belajar" | Status |
|---|---|---|---|
| L1 | statistik: surprise, event-study, z/state, regime | tiap rilis menambah baris; σ rolling | dirancang (BUILD-PLAN) |
| L2 | agent LLM analis: RAG + tool read-only atas L1/DB | tidak belajar; konteks per-run + log klaim | dokumen ini; bangun pasca-F3 |
| L3 | evaluasi terjadwal klaim; (jauh) fine-tune | kalibrasi siklus; (fine-tune: bobot model) | evaluasi ikut re-kalibrasi kuartalan |

## 4. Pola yang dipinjam dari repo referensi (dan yang tidak)

### 4.1 deepseek-harness (dsh) — agent harness model-agnostic

**Dipinjam (pola, bukan kode — dsh TypeScript/Node):**
1. **"Model-visible ⟺ logged"** — semua yang sampai ke model harus bisa direkonstruksi dari log. Terjemahan ark-watch: konteks agen L2 **harus bisa direkonstruksi dari DB** (`raw_observations` + `fetch_log`), bukan state di memori → setiap sesi riset bisa di-replay dan diaudit (saudara dari replay-determinism test BUILD-PLAN §6.6).
2. **Compaction ber-jejak** — saat data harian menumpuk di konteks, jangan buang diam-diam: ringkas dengan catatan (series apa saja, dari berapa baris raw, rumus apa). Paralel langsung: brief merujuk "ringkasan blok E 30 hari (dari 630 raw rows)".
3. **Spill storage** — output tool yang besar disimpan ke disk; model hanya menerima ringkasan + pointer. Identik dengan aturan snapshot §17 DATA-SPEC (raw JSON + hasil hitung bersama); agen menerima hasil hitung, raw tinggal di DB.
4. **Injeksi konteks segar per-run** (pola time-context) — tiap run disuntik pesan ber-sumber: waktu sekarang (WIB, sadar EDT/EST), rilis terakhir per series, daftar series basi. Wajib — jangan andalkan model "hafal" tanggal (dan konsisten konvensi §0 DATA-SPEC).
5. **Interceptor waterfall** — cross-cutting concern (sitasi-wajib, freshness-check) sebagai *listener* yang menyisipkan sebelum angka masuk jawaban, bukan if-else tercecer. Titik pemasangan guardrail G2.
6. **Sub-agen dengan tool-filter + persona + structured output + depth-limit** — riset per-blok (9 blok A–I) = sub-tugas dengan tool dan persona berbeda, hasil ber-schema tervalidasi, kedalaman dibatasi anti rekursi tanpa henti.
7. **Workflow: meta tervalidasi-sebagai-data dulu, batas total agen, hasil partial = error bukan sukses** — selaras no-silent-fallback (BUILD-PLAN §0.6).
8. **Durable schedule sebagai "turn" + catch-up hanya occurrence terakhir** — jadwal fetch §13 (06:00 FRED → 06:30 kalender → 07:00 brief) = reminder yang membangunkan agen dengan prompt terstruktur; aturan catch-up mencegah badai turn setelah mesin mati beberapa hari (relevan harvester CME 5-hari-retensi).
9. **Agent Notes** — keputusan desain dicatat ber-siklus (proposed/implemented/rejected) + wajib section "Alternatives yang kalah". Ini formalisasi kebiasaan MEMORY.md/changelog yang sudah dipakai; folder `rejected/` mencegah DTWEXM/OECD CLI (§18.5) diusulkan ulang agen berikutnya.
10. **Guard advisory, bukan veto** — deteksi panggilan tool berulang identik → reminder eskalatif; keputusan tetap di model. Benar untuk riset gray-zone yang memang butuh retry beda UA (aturan retry H-1 §17). Ditambah: timeout dideklarasikan di tool, bukan di caller; tool selalu return JSON ber-schema.

**Tidak dipinjam:** framework-nya sendiri (TS/Node 22+, Cordis vendored, 48 grup paket pnpm) — ark-watch Python kecil satu-user; "everything is a plugin" itu overkill untuk 2–3 tipe agen (cukup preset tool-set di config); sub-agen continuable yang hidup berminggu-minggu — prematur. (Catatan: kalau nanti mau agen ber-DeepSeek, dsh punya Python SDK JSON-RPC-stdio — jalan tanpa menyentuh TypeScript.)

### 4.2 TradingAgents (Tauric Research) — framework riset multi-agen trading

**Dipinjam:**
1. **Structured-output agents** (v0.2.4: research manager/trader/PM memakai schema) — semua output agen L2 = JSON tervalidasi, bukan teks bebas (mudah di-unit-test, sejalan fixture-first).
2. **Decision log yang di-resolve dengan outcome kemudian + refleksi** (`TradingMemoryLog`: entri *pending* → diisi realized returns → refleksi → diinjeksi sebagai `past_context` run berikutnya) — **ini pola paling berharga untuk kita**, diadaptasi dari "trade" menjadi "klaim analitis": klaim L2 dicatat, dinilai benar/salah oleh data yang datang kemudian, dan refleksinya menjadi konteks perbaikan (§6 G3). Di sinilah satu-satunya "belajar" L2 yang sah: di log, bukan di bobot model.
3. **Debat bull/bear** sebagai teknik adversarial — kita sudah memakainya secara manual (workflow skeptis 9/9, audit 28-temuan); L2 memformalkannya sebagai pass reviewer atas klaim/draft.
4. **Backtesting date fidelity** — kedisiplinan tanggal historis; paralel anti look-ahead `release_ts` kita.
5. **Tier model** (model cepat untuk tugas ringan, model dalam untuk sintesis) — kendali biaya (§6 G5).

**Tidak dipinjam:** seluruh pipeline keputusan-eksekusinya (analis → trader menentukan timing/besaran → order ke exchange) — melanggar G1 kita, dan domainnya riset saham per-ticker, bukan blok makro; dataflows-nya (Finnhub/Reddit/StockTwits) — sumber riak sosial di luar scope monitor EOD-first kita, dan kita sudah punya sumber terkurasi ber-tier (T0–T4, BUILD-PLAN §0); memory-of-trades as-is — tidak ada trade untuk direfleksikan; kadensi re-run harian per ticker — boros untuk kebutuhan EOD.

### 4.3 AlpacaTradingAgent — fork TradingAgents dengan eksekusi live

**Dipinjam:**
1. **Pemisahan tegas advisory vs executable** — bahkan repo yang *dibuat* untuk auto-trade menulis: rating advisory = "metadata only, never directly trigger orders". Ini preseden bagus + penguat guardrail G1 kita: output L2 selamanya advisory.
2. **Penjadwalan sadar-jam-pasar per kelas aset** — paralel dan penguat jadwal §13 kita (COT Sabtu 02:30 WIB saat EDT, CVOL setelah 21:00 ET, FOMC 14:00 ET): agen hanya bangun di jam yang didefinisikan kalender, bukan interval buta.
3. **Checkpoint resume (SQLite per-run)** — riset panjang L2 yang gagal di tengah jalan bisa lanjut, bukan ulang dari nol; sejajar dengan backfill resumable F0 (BUILD-PLAN §5).

**Tidak dipinjam:** **segalanya yang berhubungan eksekusi** — live/paper trading, margin, auto-execution, UI liquidate. Repo ini justru kita pakai sebagai *anti-contoh* batas: seluruh nilai "menarik"nya ada di fitur yang by design tidak akan ark-watch punya. Web UI multi-simbolnya juga ditunda (dashboard sudah ada di roadmap terpisah, DATA-SPEC output bertahap).

### 4.4 Ringkasan

| Repo | Dipinjam | Tidak dipinjam (alasan) |
|---|---|---|
| deepseek-harness | model-visible⟺logged; compaction ber-jejak; spill; injeksi konteks segar; interceptor guard; sub-agen tool-filter; workflow tervalidasi; schedule-as-turn; agent notes; advisory guard | framework TS/Node; everything-is-plugin; agen resident berminggu |
| TradingAgents | structured output; **decision-log→outcome→refleksi**; debat adversarial; date fidelity; tier model | pipeline trading otonom; dataflows sosial; memory-of-trades; churn harian |
| AlpacaTradingAgent | advisory≠executable; scheduling sadar kalender; checkpoint resume | seluruh jalur eksekusi live/paper/margin/auto (anti-contoh); web UI |

## 5. Desain konkret L2

### 5.1 Tool (semua read-only, semua return JSON ber-schema)

```
get_series(series_id, window)      → ringkasan + pointer (spill: raw tinggal di DB)
trace_signal(signal_id)            → rantai hulu-hilir inputs_json → raw (§8 BUILD-PLAN)
get_event(event_uid) / search_events(country, from, to)
get_brief(date)                    → brief_log terakhir + quality_flags
list_stale() / freshness(series_id)
get_calendar(days)                 → radar event + konsensus
```

Perhatikan: `explore series --trace` dan `explore signal --trace` (BUILD-PLAN §8) **sudah merancang rantai baca ini untuk manusia** — agen L2 hanyalah konsumen kedua jalur yang sama. Ini alasan konkrit kenapa L2 menunggu DB & CLI jadi dulu: fondasinya bukan AI, melainkan traceability yang sudah menjadi prinsip F0–F3.

### 5.2 Dua mode operasi

1. **Q&A on-demand** (`arkwatch ask "..."`): satu turn, konteks = injeksi segar + hasil tool; jawaban tervalidasi schema; klaim masuk `ai_claims`.
2. **Tugas terjadwal** (brief annotation / weekly deep-dive): dibangunkan sebagai "turn" ber-prompt terstruktur (pola schedule dsh); output = lampiran ber-tanda `[AI]` di brief — **baris headline tetap 100% dari L1**; maksimal 1–2 baris konteks + daftar situsi.

### 5.3 Aturan konteks (dipinjam dari dsh)

- **Segar per-run**: waktu kini (WIB, sadar EDT/EST), tanggal rilis terakhir per series terkait, daftar series basi — disuntik sebagai pesan ber-sumber.
- **Bounded**: data besar tidak pernah masuk mentah-mentah — ringkasan + pointer (spill); ringkasan mencatat jejaknya (compaction ber-jejak).
- **Terisolasi dari teks eksternal**: HTML CME/Farside/dll tidak pernah masuk prompt langsung (anti prompt-injection — teks dari luar bisa berisi instruksi menyamar); agen hanya melihat hasil parse terstruktur yang sudah di DB.
- **Tiga kanal** (followup/steer/inject): perintah user = followup; data event-driven (rilis H.4.1 → refetch WALCL) = inject — antri, tidak saling serobot.

### 5.4 Contoh sesi L2 (bagaimana kelihatannya di praktik)

```text
$ arkwatch ask "kenapa gold turun minggu ini padahal real yield juga turun?"

[konteks segar diinjeksi sistem — bukan oleh model]
  now: 2026-09-02 07:15 WIB (18:15 EDT) · series basi: none · brief terakhir: 2026-09-01

[jejak tool — semua terekam, bisa di-replay]
  trace_signal(SYN:DIVERG_GOLD_RY)   → flag decoupling AKTIF sejak 12 hari
  get_series(FRED:DFII10, 30d)       → −11bps/20d, state FALLING
  get_series(SYN:XAUUSD_EOD, 30d)    → −1.8%/5d
  get_series(COT:088691, 90d)        → MM net z+1.8 (menurun dari z+2.3)
  search_events(US, 7d)              → FOMC Minutes Kam; tidak ada rilis CPI/NFP

[jawaban agen — setiap fakta bersitasi; klaim tercatat]
  Divergensi ini memang flag aktif [signal SYN:DIVERG_GOLD_RY @2026-08-21]:
  RY turun −11bps/20d [FRED:DFII10] yang normalnya tailwind gold, tapi harga
  −1.8%/5d [SYN:XAUUSD_EOD]. Dua kandidat penjelasan di data:
  (1) positioning: MM z+1.8 mulai turun dari z+2.3 [COT:088691] — crowded
  long sedang dicabut; (2) tidak ada berita makro negatif spesifik minggu
  ini [events US 7d]. Catatan: contoh sejarah divergensi serupa masih
  n<10 → Saya tidak punya basis statistik cukup.
  [AI-CLAIM #0412 · sitasi 4 · verdict: pending · horizon 10 hari]
```

Perhatikan tiga hal yang membuat sesi ini "jujur": agen **menolak menyimpulkan** saat n kecil (pengetahuan tentang batas statistik L1), klaimnya masuk log untuk dinilai 10 hari kemudian otomatis oleh data harga — dan seluruh jejak tool bisa direplay ulang besok untuk audit. Kalau H+10 XAUUSD ternyata turun lagi dengan positioning masih menipis, verdict `correct` tercatat sendiri; kalau tidak, `wrong` — keduanya sama berharganya untuk kalibrasi.

## 6. Guardrails (final, tidak dinegosiasi ulang oleh agen)

### 6.1 Daftar guardrail (G1–G5)

1. **G1 — Tidak ada auto-trading, secara struktural.** Guardrail-nya bukan kalimat "jangan" di prompt, melainkan **tidak adanya tool/jalur eksekusi** di seluruh kode. Agen L2 zero-write: satu-satunya tool menulis adalah pencatatan klaimnya sendiri. (Preceden: AlpacaTradingAgent sendiri memisahkan advisory dari executable.)
2. **G2 — Setiap klaim wajib sitasi data-id.** Jawaban tanpa `series_id`/`event_uid`/`signal_id` + timestamp = ditolak di interceptor (bukan ditegur kemudian). Klaim tak-sitasi tidak boleh sampai ke user.
3. **G3 — Evaluasi klaim dicatat dan di-resolve.** Tabel baru (masuk skema saat L2 dibangun):

```sql
CREATE TABLE ai_claims (
  claim_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
  question TEXT, claim TEXT NOT NULL, citations_json TEXT NOT NULL,  -- wajib: series/event/signal ids
  eval_horizon TEXT, verdict TEXT,          -- 'correct'|'wrong'|'unfalsifiable'|NULL (pending)
  resolved_at TEXT, evidence_json TEXT
);
```

Resolusi otomatis dari data yang datang kemudian (pola pending→outcome→refleksi TradingAgents, diubah dari trade ke klaim); hit-rate klaim dilaporkan di re-kalibrasi kuartalan bersama gerbang lain (BUILD-PLAN §6.2). Verdict `unfalsifiable` juga hasil sah — menghitung berapa banyak klaim AI kita yang ternyata tidak bisa diuji adalah bagian dari kejujuran.
4. **G4 — No silent fallback berlaku juga untuk AI**: agen gagal/timeout = laporan gagal yang terlihat, bukan jawaban setengah-karutan yang dijual sebagai sukses (paralel hasil-partial=error dsh).
5. **G5 — Biaya & kuota**: tier model (ringan vs dalam) + pagu token per run dicatat di log — agen adalah pelanggan terukur, bukan langganan tak berbatas.

### 6.2 Mekanika penegakan (siapa menjaga penjaga)

Guardrail di atas tidak mengandalkan perilaku-baik model. Penegakannya berlapis, dan tiap lapis punya yang menegakkannya:

| Guardrail | Ditegak oleh | Kalau dilanggar |
|---|---|---|
| No auto-trading | **arsitektur** — tool eksekusi tidak pernah ditulis | mustahil terpanggil; tidak ada yang perlu dipantau |
| Sitasi wajib | **interceptor post-execute** (pola waterfall dsh) — output divalidasi schema sebelum sampai user | jawaban ditolak + tercatat sebagai `rejected_no_citation`; bukan diperbaiki diam-diam |
| Angka dari L1 saja | **desain tool** — tidak ada tool "hitung"; model hanya bisa membaca nilai computed | model yang mencoba menghitung sendiri terlihat di jejak tool-nya (tidak ada tool pendukung) |
| Evaluasi klaim | **job terjadwal** (resolver) — bukan kemauan agen | klaim pending > horizon = laporan aging di re-kalibrasi |
| Anti prompt-injection | **isolasi konteks** — teks eksternal tak pernah masuk prompt | permukaan serangan tidak ada, bukan di-filter |
| Biaya | **pagu per run** di config | run berhenti di pagu + structured timeout |

Baris pertama adalah yang terpenting secara filosofis: guardrail terkuat adalah **yang tidak perlu diuji karena strukturnya tidak ada jalurnya**. Sisanya adalah sistem yang bisa gagal dengan cara terlihat — dan itu standar yang sama dengan no-silent-fallback engine utama.

## 7. Roadmap — menempel pada fase BUILD-PLAN

| Kapan | Apa | Gerbang |
|---|---|---|
| **F0–F2** (sekarang) | **Tidak ada komponen AI di engine.** Seluruh energi ke gerbang kebenaran. Catatan jujur: agen-LLM-dengan-manusia-di-loop (sesi perancangan ini) adalah bukti-konsep L2 "manual" — polanya sudah teruji, kodenya belum perlu | 0 pelanggaran gerbang F0; kalibrasi F2 |
| **Pasca-F3** → **L2a** | `arkwatch ask` (Q&A read-only): 6–7 tool §5.1, injeksi konteks segar, `ai_claims` aktif, jawaban ber-schema | 100% jawaban tersitasi di 14 hari pertama; 0 angka headline dari model |
| **Pasca-F4** → **L2b** | Riset kontekstual & anomali; sub-agen per blok (tool-filter + persona + structured output); lampiran `[AI]` di brief; resolusi klaim pertama | hit-rate klaim pertama terlaporkan; debat adversarial atas tiap deep-dive |
| **Pasca-F5** → **L2c** | Orkestrasi terjadwal penuh (schedule-as-turn, catch-up aman); Agent Notes (keputusan AI-layer ber-siklus); evaluasi masuk re-kalibrasi kuartalan permanen | evaluasi klaim jadi bagian tetap gerbang kuartalan |
| **L3** (≥12 bln data) | evaluasi terjadwal lanjut; fine-tuning HANYA bila kriteria §3.3 terpenuhi | A/B vs baseline prompt terukur |

Alur dependensinya satu kalimat: **L1 dulu (data + statistik terverifikasi), CLI traceability kedua, agen ketiga** — karena setiap kemampuan L2 adalah konsumsi ulang jalur baca yang sudah ada, bukan kecerdasan baru dari udara.

## 8. Ringkasan keputusan

1. "Belajar" hidup di **statistik akumulasi (L1)** dan **log klaim (L2)** — bukan di model. Model adalah penyewa berpengetahuan-beku yang harus selalu menunjuk sumber.
2. L1 memegang semua angka dan semua peluang (P(outcome) dari surprise; P(reaksi) dari event-study akumulasi; keduanya ber-kalibrasi hit-rate).
3. L2 = analis on-demand read-only: RAG + tool atas DB + kalender + brief; menjawab "kenapa"; tidak pernah menghitung headline, tidak pernah memegang jalur eksekusi.
4. Dari dsh: disiplin konteks (logged/compaction/spill/injection) + guard-interceptor + agent-notes. Dari TradingAgents: structured output + decision-log→outcome→refleksi (diadaptasi ke klaim). Dari AlpacaTradingAgent: advisory≠executable + scheduling sadar kalender — dan seluruh jalur eksekusinya ditolak sebagai anti-contoh.
5. Guardrail struktural, bukan nasehat: tanpa tool eksekusi, sitasi wajib di-intercept, klaim di-resolve dan hit-rate-nya dilaporkan kuartalan.
