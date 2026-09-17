# Blok E — Likuiditas & Fiskal (dijelaskan dari nol)

> Bagian dari seri dokumen edukasi `docs/explained/`. Dituju untuk pemilik sistem: trader ritel swing (hari–minggu) di XAU/XAG/XPT/XCU, BTC/ETH, US100/500/30, EURUSD & majors, DXY.
> Rujukan teknis: [DATA-SPEC.md](../DATA-SPEC.md) §5 (Blok E), §18.3 (pengayaan CP/SOFR-percentile/SOMA), §19.1 + §19.3 (QuikStrike referrer & xccy basis), §0 (prinsip), §11 (sinyal komposit), §13 (jadwal fetch), §14 (contoh brief); [BUILD-PLAN.md](../BUILD-PLAN.md) §3 "BLOK E — Likuiditas & Fiskal" (transform terkunci), §4 (kedalaman backtest), §5 (golden anchor), §6.3 (identitas harian), §8 (eksplorasi hulu-ke-hilir).
> Blok ini punya **rantai teknis terpadat dari sembilan blok** — dokumen ini karenanya membedahnya paling pelan-pelan. Semua contoh angka bertanda **(contoh nilai Agt-2026)** diambil langsung dari spec dan tabel golden-anchor F0 — bukan karangan. Angka buatan semata untuk memperagakan mekanisme hitung ditandai eksplisit **(ilustrasi)**.

---

## 1. Kenapa blok ini ada — kolam renang dan pompa airnya

### 1.1 Satu kalimat dulu

Blok A–D menjawab "bagaimana kondisi ekonominya dan berapa mahal bunganya". Blok E menjawab pertanyaan yang lebih fisik lagi: **ada berapa uang yang benar-benar beredar dan bisa dipakai membeli aset — dan jumlah itu sedang ditambah atau disedot?** Harga aset adalah pertemuan dua sisi: aset di satu tangan, uang mengejarnya di tangan lain. Blok E mengukur sisi uangnya langsung.

### 1.2 Analogi kolam renang (kerangka utama blok ini)

Bayangkan pasar keuangan sebagai **kolam renang**, dan semua instrumen yang Anda pegang — BTC, emas, silver, indeks — sebagai **perahu-perahu di dalamnya**.

- **Air kolam = likuiditas**: dolar yang benar-benar mengalir dan bisa dipakai membeli aset. Bukan uang yang "secara teori ada", tapi uang yang siap pakai di tangan bank, dana pasar uang, dan pelaku pasar.
- **QE (quantitative easing) = pompa air masuk.** Saat krisis, Fed membeli obligasi dari pasar dan membayarnya dengan uang yang baru diciptakan — air dipompa masuk kolam. Neraca Fed (balance sheet) membengkak, air naik, semua perahu terangkat.
- **QT (quantitative tightening) = pompa air keluar.** Fed berhenti mengganti obligasi yang jatuh tempo — air tersedot sedikit demi sedikit (istilah teknisnya *roll-off*, lihat glosarium). Permukaan turun; perahu yang paling "mengapung tipis" kandas duluan.
- **Laci Fed = RRP dan TGA.** Sebagian "air" tidak berada di kolam, melainkan menginap di laci Fed (detail §4.1): uang dana pasar uang yang diparkir semalam di Fed (RRP), dan saldo rekening giro pemerintah AS (TGA). Air di laci **tidak bisa menopang perahu** — karena itu dalam perhitungan net liquidity keduanya **dikurangkan**.

Kenapa ini menggerakkan BTC & risk asset secara khusus? Saat air melimpah, uang mencari tempat parkir sampai ke aset paling spekulatif — BTC dan saham growth adalah penerima terakhir sekaligus paling rakus dari kelebihan air. Saat air disedot, aset tanpa arus kas (tanpa dividen, tanpa kupon — BTC) tidak punya "jangkar nilai" lain, jadi paling cepat diturunkan harganya. Itulah alasan spec menulis net liquidity sebagai **"driver BTC & risk"**.

### 1.3 Fiskal: cerita kepercayaan pada utang AS

Blok E juga memuat dua series fiskal (defisit & beban bunga pemerintah). Ini bukan untuk timing harian — datanya paling lambat di seluruh mesin (tahunan/kuartalan) — melainkan untuk **cerita besar**: pemerintah yang terus defisit besar sementara beban bunganya membengkak harus menarik tabungan dunia lewat yield yang lebih tinggi (*term premium*, blok A) atau dipandang "mencetak" jalannya — keduanya adalah cerita yang secara historis ramah emas dan memberatkan dolar. Spec menyebutnya "kanal fiskal (teman term premium)".

### 1.4 Peran di mesin komposit

1. **Regime score** (−2…+2): pilar Likuiditas = rata-rata z anggotanya; **bobot E = 0,15** (§11: A .20, B .20, C .15, D .15, **E .15**, F .15).
2. **State pilar**: `EXPANDING` / `CONTRACTING` — masuk label regime; contoh label lengkap dari brief: **"EASING + LIQUIDITY EXPANDING"** (contoh nilai Agt-2026).
3. **Dua alarm resmi** memakai blok ini: *net-liquidity reversal* (anomali §11.5) dan *SRF take-up* sebagai **alarm akhir-QT** (§5 baris SRF).

---

## 2. Glosarium istilah Blok E

Dibaca berurutan atas ke bawah = dari institusi ke alat statistik. Istilah lain yang belum ada di sini akan muncul lagi di §3–§4 dengan penjelasan menyatu.

| Istilah | Arti dalam bahasa sehari-hari | Kenapa penting buat Anda |
|---|---|---|
| **Balance sheet / neraca Fed** | Daftar aset & utang bank sentral, seperti isi kas dan hutang sebuah perusahaan — hanya saja "kas"-nya bisa menciptakan dolar | Wadah semua air: total aset (`WALCL`) = ukuran pompa kolam |
| **QE (quantitative easing)** | Fed membeli obligasi dengan uang cetak → pompa air masuk kolam | Era QE 2020–2021 = banjir yang mengangkat semua risk asset |
| **QT (quantitative tightening)** | Fed membiarkan obligasi jatuh tempo tanpa diganti → air tersedot | Regime sekarang; yang ingin diketahui blok E: kapan sedotannya mulai mengganggu |
| **Roll-off** | Obligasi di neraca Fed yang jatuh tempo dan tidak dibeli ulang — kebocoran air pelan-pelan, bukan keran besar | QT dijalankan lewat *cap* roll-off, bukan penjualan besar-besaran |
| **SOMA** | System Open Market Account — "rekening portofolio" Fed tempat seluruh obligasinya disimpan | Roll-off dihitung **per obligasi** dari sini (§3.3) |
| **CUSIP** | Nomor identitas tiap emitmen obligasi, seperti NIK-nya satu piutang | Memungkinkan hitung QT eksak per sekuritas, bukan tebakan |
| **WAM** | Weighted average maturity — rata-rata umur kupon portofolio SOMA | Durasi QT: portofolio muda =QT selesai lebih cepat. Kini **8,26 tahun** (contoh nilai Agt-2026) |
| **MBS / TBA** | Obligasi beragun hipotek di neraca Fed; TBA = pasar kontraknya | Roll-off MBS tak menentu (tergantung orang refinancing rumah) |
| **Reserves (cadangan bank)** | Saldo uang bank komersial yang "menyimpan tabungannya" di Fed | **Variabel constraint sesungguhnya** (spec §5) — air yang benar-benar dipakai bank untuk bertransaksi |
| **Repo** | Pinjam uang berjam semalam dengan obligasi sebagai jaminan ("gadaikan BPKB-nya obligasi") | Pasar uang antarbank harian; suhunya = `SOFR` |
| **Reverse repo (dari sudut Fed)** | Fed *meminjamkan* obligasi & menerima uang semalam — menyerap uang sementara | Alat halus kelola suku bunga; saldonya = laci |
| **RRP / ON RRP** | Fasilitas reverse repo semalam: dana pasar uang memarkir uangnya di Fed semalam | "Laci Fed" #1. Saldonya hampir nol sekarang — penyangga QT habis (§4.5) |
| **TGA** | Treasury General Account — rekening giro pemerintah AS di Fed, seperti rekening koran kantor kamu | "Laci Fed" #2; naik-turun mengikuti pajak & belanja pemerintah |
| **DTS** | Daily Treasury Statement — laporan kas harian Treasury | Sumber TGA harian; satuan **$ juta** (jebakan! §5) |
| **H.4.1** | Rilis statistik neraca Fed tiap Kamis (posisi Rabu) | Pemicu refetch event-driven `WALCL`/`WRESBAL` (§13) |
| **SOFR** | Bunga repo semalam terjamin — suhu pasar uang hari ini | Kaki pertama spread funding stress |
| **IORB** | Bunga yang Fed bayarkan atas saldo bank — "lantai" resmi rate | Kaki kedua; `SOFR−IORB` = tekanan ke atas = scarcity |
| **EFFR / TGCR / BGCR / OBFR** | Variasi-variasi bunga semalam (efektif Fed funds, tri-party, dsb) | Bahan spread pendamping dari EODHD (§3.2) |
| **Target range / target band** | Koridor kebijakan rate Fed (mis. 4,25–4,50%) | `SOFR_TARGET_LOWER` dll = posisi SOFR di dalam koridor = radar scarcity dini |
| **SRF (Standing Repo Facility)** | "Pintu darurat permanen": bank boleh gadai obligasi ke Fed kapan pun untuk dapat uang | Pemakaian yang tiba-tiba naik = sinyal uang mulai langka → alarm akhir-QT |
| **CP (commercial paper)** | "Bilyet giro" korporasi: pinjaman tanpa jaminan jangka pendek | Funding non-bank; sukunya melonjak saat kredit macet |
| **DTB3** | Bunga T-bill 3 bulan (obligasi pemerintah, paling aman) | Pembanding: `DCPN3M−DTB3` = premi risiko korporasi jangka pendek |
| **Net liquidity** | Air bersih kolam: `WALCL − RRP − TGA` | Angka utama blok ini; driver BTC & risk |
| **M2** | Ukuran uang beredar luas (uang tunai + tabungan + deposito) | Peta besar bulanan; lebih lambat & berbeda sifat dari net liq (§5) |
| **Term premium** | Imbalan ekstra yang dituntut investor untuk memegang obligasi panjang | Jembatan fiskal → yield (blok A `THREEFYTP10`) → gold |
| **Xccy basis** | Biaya *implisit* meminjam dolar lewat negara lain (pinjam euro, tukar ke dolar, kembalikan nanti) | Termometer stress funding dolar global — "setara FXBAS Bloomberg" (spec §5) |
| **CIP (covered interest parity)** | Rumus teori "berapa seharusnya kurs forward kalau dunia tanpa gesekan" | Deviasi kecilnya itulah basis; formula penuh di §4.6 |
| **IMM / settlement / strip** | Titik-titik tanggal futures reguler; harga penutupan resmi harian; deretan kontrak berurutan | Bahan mentah xccy dari 3 futures CME |
| **Basis point (bp)** | Satuan 1/100 persen; 4bp = 0,04% | Satuan xccy & semua spread rate di blok ini |
| **Persentil** | Ranking nilai hari ini dalam 5 tahun terakhir | Standar baku membaca ekstremitas (sama dengan blok F) |
| **Z-score** | Jarak dari rata-rata dalam satuan simpangan baku | Bahasa umum regime score; spesifikasi penuh di §4.3 |
| **Vintage (ALFRED)** | "Cetakakan" data pada tanggal rilis tertentu — data bisa direvisi belakangan | Mekanisme jujur menangani revisi `WALCL`/`M2SL` (§7) |

---

## 3. Peta data — apa, siapa, kapan, kenapa, cara baca

Konvensi tier (BUILD-PLAN §0): T0 institusi resmi · T1 langganan berbayar · T2 market-data gratis · T3 gray/backdoor · T4 computed. Blok E adalah blok yang paling biru-tua (T0 dominan) — institusi: FRED, NY Fed API, fiscaldata Treasury, BEA. Jadwal umum: FRED & sekutunya 06:00 WIB, brief 07:00 WIB; H.4.1 memicu refetch event-driven (DATA-SPEC §13). Rantai angka siapa pun bisa dibuka sendiri: `arkwatch explore block E` → `arkwatch explore series SYN:NETLIQ --trace` (BUILD-PLAN §8).

### 3.1 Inti net liquidity

| Series | Apa itu sebenarnya | Penerbit & jadwal | Kenapa dipilih | Cara baca angka |
|---|---|---|---|---|
| `WALCL` — balance sheet Fed | Total aset neraca Fed: seluruh obligasi Treasury + MBS + pinjaman yang Fed pegang; posisi **Rabu**, terbit Kamis sore | Federal Reserve (H.4.1) via FRED; **mingguan**; event-driven refetch saat H.4.1 (T0) | Ukuran pompa air resmi; tak ada substitut | Level $ triliun. **BS $6.73T (contoh nilai Agt-2026)**; arah ΔWoW = QT berjalan |
| `RRPONTSYD` — reverse repo | Saldo uang yang dana pasar uang parkir semalam di Fed (laci #1) | NY Fed via FRED; **harian** (T0); juga tersedia dari API NY Fed langsung (§3.3) | Kaki pengurang net liq; indikator penyangga | Level $ miliar. **RRP $0.2B = "exhausted" (contoh nilai Agt-2026)** — laci kosong, pesan khusus (§4.5) |
| TGA — DTS harian | Saldo rekening giro pemerintah AS di Fed (laci #2). Endpoint `operating_cash_balance` fiscaldata; **resep 3-era + COALESCE** (dibedah §4.2) | US Treasury DTS `api.fiscaldata.treasury.gov`; **harian**; sekunder FRED `WTREGEN` mingguan (T0) | Satu-satunya TGA **harian** — tanpa ini, net liq cuma bisa mingguan | **Satuan $ juta**: TGA 950.804 juta = **$950,8 miliar** (golden anchor F0: 950.804 @ 2026-08-27, contoh nilai Agt-2026) |
| **Net liquidity** (computed) | `WALCL − RRP − TGA` = air bersih di kolam | Computed (T4); **mingguan (snapshot Rabu) → harian begitu DTS siap** (aturan §4.2) | Driver BTC & risk asset; seri kunci blok ini | **Net liq $5.8T, +$45B/mgg → EXPANDING (contoh nilai Agt-2026)** — cek aritmetikanya di §4.1 |
| `WRESBAL` — reserves | Saldo bank komersial di Fed: uang yang benar-benar dipakai bank untuk settle transaksi & beli aset | Federal Reserve (H.4.1) via FRED; mingguan Rabu (T0) | **"Variabel constraint sesungguhnya"** (spec) + kaki identitas cek (§4.1) + konteks `SOFR−IORB` | **Reserve $2.92T (contoh nilai Agt-2026)** — pertanyaan yang menempel di brief: *"menipis?"* |
| `M2SL` — M2 | Uang beredar luas (tunai + deposito); bulanan | FRED (T0); masuk daftar job revisi ALFRED (§18.2) | Konteks siklus uang jangka panjang; kontras dengan net liq | YoY. **M2 YoY +3.8% (contoh nilai Agt-2026)** |

### 3.2 Funding stress harian — "suhu" pasar uang

| Series | Apa itu sebenarnya | Penerbit & jadwal | Kenapa dipilih | Cara baca angka |
|---|---|---|---|---|
| `SOFR`−`IORB` (computed) | Selisih suhu pasar vs lantai resmi. SOFR di atas IORB = bank/broker bayar premium untuk uang semalam = scarcity | FRED (T0) + computed (T4); harian | Deteksi scarcity paling langsung, gratis, resmi | Spread bps + state; melebar = waspada |
| EODHD `/spreads/funding-stress` | Paket spread harian **lengkap dengan rumus & kedua kaki rate** per spread | EODHD (T1); harian | Kode valid terverifikasi: `EFFR_SOFR`, `OBFR_EFFR`, `TGCR_BGCR`, `SOFR_TARGET_LOWER`, `EFFR_TARGET_MID`, `TARGET_UPPER_SOFR`. **`SOFR_OIS` pada contoh docs = error 422 — kode itu tidak valid** | `SOFR_TARGET_LOWER` mengecil = SOFR menekan ke **atas** range = **scarcity dini** |
| `DCPN3M` + `COMPOUT` (CP) | Bunga commercial paper 3 bulan & total CP beredar | FRED (T0) | `DCPN3M−DTB3` = funding non-bank; **kontraksi CP outstanding = pola drain klasik pra-krisis**; `CPFF`+`DPCREDIT` = flag langka (fasilitas darurat — sejarahnya hanya "menyala" di episode akut) | Spread melebar + outstanding menyusut = tekanan riil sektor korporasi |
| SOFR percentile p1/p25/p75/p99 | Distribusi suku bunga repo hari itu — bukan cuma satu angka rata-rata | NY Fed API (T0; **wajib suffix `.json`, tanpa itu 400**) | **p75−p25 = repo-tail stress**: sebaran lebar = sebagian pemain bayar jauh lebih mahal dari median | Spread antar-persentil melebar duluan sebelum SOFR rata-rata bergerak |
| `sofrai30`−`SOFR` | Rata-rata SOFR 30 hari minus SOFR semalam = **proksi term-SOFR/OIS** | NY Fed API (T0) | Tidak ada di FRED (spec §18.3) | Premi jangka pendek: positif & naik = pasar bayar untuk kepastian uang >1 hari |
| `SOFRINDEX` | Indeks kompaun SOFR (bunga harian menumpuk, seperti tabungan berbunga harian) | NY Fed API (T0) | Bahan internal konsistensi rata-rata 30 hari | Pembanding, bukan sinyal mandiri |

### 3.3 Operasional NY Fed — SRF, ON RRP, dan QT eksak per obligasi

| Series | Apa itu sebenarnya | Endpoint & jadwal | Kenapa dipilih | Cara baca |
|---|---|---|---|---|
| SRF usage | Take-up pintu darurat permanen Fed (repo full-allotment) | `markets.newyorkfed.org/api/rp/results/search.json?operationTypes=Repo`, filter `operationMethod=Full Allotment` (= SRF; 2 operasi/hari) (T0) | **Alarm akhir-QT**: bank yang biasanya tak memakai pintu darurat tiba-tiba antre = uang sungguhan langka | Take-up + flag; lonjakan = sinyal, bukan kebisingan |
| ON RRP propositions | Take-up harian fasilitas reverse repo | `/api/rp/reverserepo/propositions/search.json` (T0) | Sumber resmi harian, sejajar `RRPONTSYD` | ⚠️ **Jumlah = USD mentah; label "($Billions)" di CSV menyesatkan** — salah baca = salah 1000x |
| SOMA per-CUSIP `changeFromPriorWeek` | Perubahan kepemilikan Fed **per satu obligasi** per minggu = QT roll-off eksak, bukan tebakan | NY Fed API (T0) + WAM (**8,26y**, contoh nilai Agt-2026) | Bahan identitas harian §6.3: ΣΔSOMA ≈ ΔWALCL | Dijumlahkan → angka QT mingguan; diverifikasi vs WALCL (§4.4) |
| Treasury outright ops per-CUSIP + MBS TBA pace | Operasi beli/sell-drain Fed; rasio accepted/submitted = resistensi pasar; pace TBA = ritme pembelian MBS | NY Fed API (T0) | Melihat "mesin" di balik angka agregat | Rasio turun = pasar ogah menjual ke Fed pada harga itu |
| Modul Primary Dealer | 1.539 series statistik dealer primer | NY Fed API (T0) | **Opsional, episodik** — dinyalakan saat funding mulai rusak | Konteks investigasi, bukan baris brief rutin |

### 3.4 EUR/USD xccy basis — stress funding dolar global

| Series | Apa itu sebenarnya | Penerbit & jadwal | Kenapa dipilih | Cara baca |
|---|---|---|---|---|
| **Xccy basis EUR/USD** (computed) | Selisih kurs forward *eksak* vs kurs forward *teoretis CIP* — yaitu premi tersembunyi yang dibayar untuk mendapatkan dolar lewat Eropa (penjelasan awam penuh §4.6) | **Computed (T4) dari 3 settlement CME: SR3 `8462` + ESR `10247` + 6E `58`**; harian; formula CIP **terverifikasi ±0,00bp vs tool resmi** (§19.3) | Setara FXBAS Bloomberg — sinyal institusional mahal yang berhasil direproduksi gratis; prinsip raw+derived §0.4: selalu bisa dihitung ulang dari 3 harga mentah | **"xccy Dec26 −4.0bp → funding normal" (contoh nilai Agt-2026)**. Kini **\|basis\| ≤ 4bp = tenang**; yang dicari = perlebaran mendadak |
| Cross-check mingguan: XCCY Basis Watch | Tabel basis resmi CME/QuikStrike (EUR/USD, 6 periode IMM forward) | QuikStrike view via referrer-trick (T3 gray, §19.1) | Kalibrasi eksternal mingguan — computed tetap primer | Selisih vs computed harus ≤ ±0,1bp (gerbang F2) |

### 3.5 Fiskal

| Series | Apa itu sebenarnya | Penerbit & jadwal | Kenapa dipilih | Cara baca |
|---|---|---|---|---|
| `FYFSGDA188S` — defisit federal | Selisih penerimaan vs belanja pemerintah AS sebagai % PDB, per tahun fiskal | FRED (T0); **tahunan** | Kanal fiskal — "teman term premium" (blok A) | **"%GDP −5.8%" (contoh nilai Agt-2026)** — tanda minus = defisit 5,8% PDB (bukan surplus terbalik) |
| `A091RC1Q027SBEA` — bunga federal | Pembayaran bunga pemerintah AS atas utangnya | BEA via FRED (T0); **kuartalan** | Beban bunga → tekanan fiskal → cerita debasement | **"bunga $1.25T/thn, naik" (contoh nilai Agt-2026)** — tren naik lebih penting dari levelnya |

Yang **tidak** dipakai: OIS-on-FRED (tidak ada — digantikan proksi `sofrai30−SOFR`, §18.5); FXBAS Bloomberg (berbayar — digantikan computed §3.4); tool xccy non-EUR (tool resmi hanya punya EUR/USD — keterbatasan tercatat §7.3).

---

## 4. Logika hilir-ke-hulu: dari laci Fed sampai regime score

### 4.1 Kenapa RRP dan TGA DIKURANGKAN — neraca sebagai persamaan

Neraca apa pun punya dua sisi yang selalu sama: **Aset = Liabilitas**. Di Fed:

```
Aset (WALCL)  =  Reserves (WRESBAL)  +  RRP  +  TGA  +  uang kartal  +  liabilitas kecil lain
```

Pindahkan dua suku ke kiri:

```
WALCL − RRP − TGA  ≈  Reserves + uang kartal + liabilitas kecil   ← inilah "air kolam"
```

Intuisinya dengan analogi laci: uang yang menginap di laci Fed — baik parkiran semalam dana pasar uang (RRP) maupun giro pemerintah (TGA) — **secara teknis berada di dalam neraca Fed, tapi tidak beredar di pasar**; ia tidak bisa dipakai siapa pun membeli BTC, emas, atau saham. Net liquidity sengaja membuangnya supaya yang tersisa benar-benar "air yang menopang perahu".

**Cek angka nyata (semua contoh nilai Agt-2026):** BS $6.73T − RRP $0.0002T − TGA $0.9508T ≈ **$5.78T ≈ "Net liq $5.8T"** — persis baris spec. Perhatikan juga: net liq $5.78T **lebih besar** dari reserves $2.92T. Selisihnya bukan anomali — itu persis identitas di atas (uang kartal + liabilitas kecil). Karena itulah `WRESBAL` dipasang sebagai **kaki identitas**: kalau `net liq` dan `WRESBAL + uang kartal` berpisah, ada komponen yang salah baca — gerbang uji resmi *"identitas net-liq vs WRESBAL+"* (BUILD-PLAN §3 E). Dan kenapa reserves disebut spec "variabel constraint sesungguhnya"? Karena air kolam yang paling bergerak dan paling bisa "habis" untuk transaksi adalah reserves — uang kartal itu pasif di dompet masyarakat. Saat reserves menipis, `SOFR−IORB` naik dan SRF mulai dipakai: tiga seri itu saling mengunci sebagai satu cerita.

### 4.2 Resep TGA 3-era + COALESCE, dan aturan snapshot Rabu

**Kenapa resep TGA wajib (bukan detail kosmetik).** Treasury berkali-kali mengganti *nama baris* rekeningnya di API DTS: `Federal Reserve Account` (2005–2021) → `TGA` (2021–22) → `TGA Closing Balance` (2022–kini). Harvester naif yang hanya menanyakan label terkini akan mendapat data mulai 2022 dan **celah sejarah diam-diam** — musuh persis yang diperangi prinsip anti-drift (BUILD-PLAN §6.4). Resep resmi: query **ketiga label**, jahitan waktunya diuji (**toleransi: tanpa gap > 5 hari kerja** — gerbang F3), dan nilai per hari = `COALESCE(close_today_bal, open_today_bal)`: pakai saldo penutupan, dan kalau null (baris data setengah jadi), jatuh ke saldo pembukaan — bukan hari kosong. Satuan asli **$ juta** disimpan mentah + faktor di unit registry (BUILD-PLAN §0.3), sehingga konversi ke triliun untuk net liq tidak pernah "dikira-kira".

**Aturan snapshot Rabu (alignment).** `WALCL` dan `WRESBAL` adalah posisi **Rabu** (rilis Kamis); RRP & TGA harian. Kalau komponen dicampur asal timestamp — WALCL Rabu dikurangi TGA Jumat — perubahan palsu langsung muncul, karena TGA bisa bergerak puluhan miliar dalam 2–3 hari hanya karena tanggal pajak. Aturan transform (BUILD-PLAN §3 E): **semua komponen di-timestamp ke snapshot Rabu yang sama** sampai mode harian aktif; setelah DTS harian siap, net liq jadi **harian** dengan WALCL tetap membawa snapshot Rabu terakhirnya — sehingga pergerakan antar-hari dalam seminggu murni dibaca dari RRP/TGA, dan perbandingan mingguan (Δ/w) selalu Rabu-ke-Rabu, bersih dari artefak.

### 4.3 Transform: Δ, z, state — spesifikasi umum

- **Δ mingguan ($B/minggu)** adalah bacaan pertama net liq — contoh brief: "+$45B/w". Z-score dihitung sesuai spesifikasi umum BUILD-PLAN §3: window **5 tahun sesuai frekuensi series** (mingguan = 260 obs), **σ populasi**, **min-obs 80%** — data kurang → state `INSUFFICIENT`, bukan angka ngawur. Net liq tergolong seri yang dibaca sebagai **perubahan** (Δ) — ditandai demikian di spesifikasi umum ("z dihitung pada level kecuali ditandai Δ").
- **State pilar** `EXPANDING`/`CONTRACTING` dari arah perubahan; labelnya menempel di regime (contoh: "EASING + LIQUIDITY EXPANDING"). Ambang umum flip state ±0.5 berlaku pada z pilar (BUILD-PLAN §3).
- **Anomali resmi §11.5: net-liquidity reversal** — arah Δ berbalik setelah tren panjang → alert, karena historically jadi titik belok regime risk asset.

### 4.4 Identitas QT: ΣΔSOMA ≈ ΔWALCL (±$15B)

Dua cara mengukur sedotan QT: (a) dari hasil — `ΔWALCL` mingguan; (b) dari proses — jumlah `changeFromPriorWeek` **per-CUSIP** SOMA. Keduanya harus cocok **±$15B/minggu**. Kenapa ada toleransi? Karena WALCL berisi hal-hal di luar roll-off terjadwal: aset lain (fasilitas pinjaman, fx swap line) ikut naik-turun, dan MBS bisa jatuh tempo lebih cepat/slow. Identitas ini dijalankan **harian sebagai gerbang brief** (BUILD-PLAN §6.3) — kalau merah, berarti salah satu fetcher bohong, dan angka QT tidak boleh dipakai diam-diam.

### 4.5 Skenario ujung QT — kenapa "RRP $0.2B" adalah pesan besar

Urutan logika yang membuat seluruh blok ini saling mengunci:

1. QT menyedot air kolam tiap minggu (§4.4) — tak terhindarkan selama roll-off jalan.
2. Selama laci RRP masih penuh, sedotan itu **didahulukan menguras laci dulu**: dana pasar uang menarik parkirannya dari Fed → uang kembali ke kolam → reserves relatif terlindungi. RRP turun justru berarti net liq **naik** (dikuranginya berkurang).
3. Sekarang RRP ±nol — **"exhausted ($0.2B)" (contoh nilai Agt-2026)** — penyangga itu habis.
4. Konsekuensi: setiap sedotan berikutnya (QT terus, ditambah penarikan TGA untuk belanja pemerintah) **langsung memakan reserves** — di sinilah `WRESBAL $2.92T, "menipis?"` menjadi pertanyaan headline, bukan formalitas.
5. Alarm lanjutannya bertingkat: `SOFR−IORB` melebar → `SOFR_TARGET_LOWER` menekan ke atas range → sebaran persentil repo (p75−p25) lebar → lonjakan SRF. Jika rantai ini menyala serentak, itulah **"alarm akhir-QT"** yang oleh spec dijadikan alasan SRF dipantau harian.

### 4.6 Xccy basis untuk awam + contoh hitung

**Ceritanya:** sebuah bank Eropa butuh dolar (mis. untuk nasabah yang bermain di pasar AS). Ia tidak punya dolar, tapi punya euro. Solusinya: pinjam euro, tukar ke dolar hari ini, dan *mengunci* kurs pengembalian di masa depan (kontrak forward). Kalau dunia nyaman, biaya jalur ini ≈ biaya pinjam dolar langsung — selisihnya nol. Saat dolar global langka, bank Eropa terpaksa menerima kurs forward yang sedikit lebih murah dari seharusnya — selisih kecil itulah **basis** (dinyatakan dalam bp per tahun). Jadi: **basis = harga pinjam dolar lintas negara**. Makin negatif/melar = makin mahal = stress funding dolar — biasanya mendahului tekanan yang terlihat di EURUSD spot, dan historis muncul di akhir QT / episode kepanikan dolar.

**Formula resmi (dipindah verbatim dari script verifikasi saat F2, BUILD-PLAN §3):**

```
F_cip      = S · (1 + r_US·τ) / (1 + r_EU·τ)
basis_bps  = ((F_actual − F_cip) / F_cip) / τ · 10^4
τ          = ACT/360 per periode IMM
```

dengan S = spot EURUSD, r_US & r_EU = rate implied dari strip futures SR3 (dolar) & ESR (euro), dan `F_actual` = harga forward eksak dari futures 6E.

**Contoh ter-kerja (mekanisme; angka bulat = ilustrasi, bukan angka spec):** S = 1,0850; r_US = 4,0%; r_EU = 2,2%; τ = 0,25.
1. `F_cip = 1,0850 × (1 + 0,040×0,25)/(1 + 0,022×0,25) = 1,0850 × 1,0100/1,0055 ≈ 1,08986`.
2. Forward pasar sesungguhnya `F_actual = 1,08980` — sedikit *lebih murah* dari teori.
3. `basis = ((1,08980 − 1,08986)/1,08986)/0,25 × 10^4 ≈ −2,0bp`.

Dibaca: peminjam dolar via Eropa "membayar" ±2bp setahun — nyaris nol, funding tenang. Bandingkan dengan keadaan nyata spec: **|basis| ≤ 4bp, contoh "xccy Dec26 −4.0bp → funding normal" (contoh nilai Agt-2026)**. Validasi F2: computed vs tool resmi **±0,1bp** (reproduksi riset: ±0,00bp); cross-check mingguan via QuikStrike (referrer-trick §19.1).

### 4.7 Dari pilar ke regime score

`regime score (−2…+2) = Σ (bobot_pilar × z̄_pilar)`. Blok E bobot **0,15**. Ilustrasi mekanisme (angka rekaan): z̄ pilar Likuiditas bergerak +1,0 → skor naik 0,15 ke arah risk-on — sendiri moderat, tapi blok E adalah pilar yang **arahnya paling sulit dibalik oleh narasi** (uang sungguhan masuk/keluar sistem), sehingga sering jadi penentu saat pilar lain saling bertengkar. Contoh tampilan brief: `Likuiditas=EXPANDING (+$45B/w)` (contoh nilai Agt-2026).

---

## 5. Membaca baris Blok E di brief + jebakan salah-baca

Baris-blok-E dalam contoh brief §14 **(contoh nilai Agt-2026)**:

```text
REGIME : EASING + LIQUIDITY EXPANDING   (score +1.2 → risk-on)
Pilar  : ... Likuiditas=EXPANDING (+$45B/w) ...
• BTC    : likuiditas ↑ + flow ↑, funding sehat
```

Diikuti baris-baris khas blok ini dari spec §5: `BS $6.73T` · `RRP exhausted ($0.2B)` · `reserve $2.92T, menipis?` · `M2 YoY +3.8%` · `xccy Dec26 −4.0bp → funding normal` · `%GDP −5.8%` · `bunga $1.25T/thn, naik`. Cara membaca ceritanya: air kolam masih ditambah (+$45B/mgg) meski pompa QT menyala — karena penyumbangnya bukan QE, melainkan laci yang sedang dikosongkan (RRP) dan setoran TGA; sementara funding global tenang (xccy ≤4bp) dan TGA dalam mode netral. Untuk book: ramah BTC & risk asset, netral-positif metals.

**Jebakan salah-baca umum:**

| Jebakan | Salah baca | Yang benar |
|---|---|---|
| **Net liq naik = Fed melonggarkan** | "+$45B/mgg → Fed kembali QE!" | Cek komponennya. Kenaikan karena **TGA turun / RRP dikosongkan = netral-baik, bukan easing** — itu uang pindah laci ke kolam, jumlah dolar di sistem tidak bertambah. Easing sejati = WALCL naik |
| RRP turun dibaca buruk | "RRP jatuh = likuiditas menyusut" | RRP turun justru **menambah** air kolam (pengurang berkurang). Yang buruk adalah keadaan **sesudahnya**: RRP habis → sedotan berikutnya makan reserves |
| Salah koma satuan TGA | "TGA 950.804 = $950 triliun?!" | Satuan DTS = **$ juta** → 950.804 juta = **$950,8 miliar**. Unit registry menyimpan satuan asli + faktor (BUILD-PLAN §0.3) persis untuk ini |
| Label "($Billions)" NY Fed | Ambil kolom begitu saja | Jumlah di API NY Fed = **USD mentah**; label CSV itu menyesatkan (spec §5) — salah baca = salah 1000x |
| `SOFR_OIS` dipakai | Ikut contoh docs EODHD | Kode itu **422 (salah)** — tidak valid. Daftar valid: `EFFR_SOFR`, `OBFR_EFFR`, `TGCR_BGCR`, `SOFR_TARGET_LOWER`, `EFFR_TARGET_MID`, `TARGET_UPPER_SOFR` |
| Timestamp campur aduk | WALCL (Rabu) − TGA hari ini | Artefak Δ palsu; aturan snapshot Rabu (§4.2) ada persis untuk ini |
| WALCL dianggap segar | "Angka Kamis pagi" | Posisi **Rabu** rilis Kamis — di brief hari Senin angkanya 3 hari tua; H.4.1 = pemicu refetch event-driven |
| Xccy negatif dibaca anjlok | "Basis minus = sinyal jual EUR" | Basis memang biasanya negatif kecil. Sinyalnya = **perlebaran mendadak** dari baseline, bukan tanda minusnya |
| M2 disamakan net liq | "M2 +3,8% ≈ likuiditas naik 3,8%" | Beda binatang: M2 bulanan, lewat penciptaan deposito bank, lambat; net liq = uang pasar Fed/Treasury, mingguan-harian |
| Defisit minus dibaca terbalik | "−5,8% = surplus?" | Konvensi seri: minus = **defisit** 5,8% PDB |
| Reserves turun selalu panik | "WRESBAL turun → jual semua" | Turun saat RRP masih besar = pemindahan laci. Yang menakutkan: turun **setelah** RRP habis, apalagi bareng `SOFR−IORB` melebar + SRF dipakai |
| Satu minggu = tren | "+$45B sekali → EXPANDING, all-in" | Cek beberapa minggu + anomali net-liquidity reversal; label state bisa berbalik cepat di sekitar tanggal pajak/pengeluaran pemerintah |

---

## 6. Keterkaitan spesifik per instrumen Anda

### 6.1 Filosofi umum

Blok E adalah pilar yang paling dekat ke mekanika "uang mencari aset". Aturan praktis: **net liq menentukan angin besar; funding stress menentukan badai; fiskal menentukan iklim.**

### 6.2 Tabel implikasi

| Instrumen | Saluran utama dari Blok E | Cara pakai |
|---|---|---|
| **BTC** | **Paling sensitif di seluruh book** — spec menulis net liquidity "driver BTC & risk". Air naik → uang rakus masuk dulu ke sini; air disedot → tanpa cashflow, kandas duluan | Net liq EXPANDING + funding crypto sehat (blok H: funding rate, ETF flow) = konfirmasi ganda; likuiditas CONTRACTING = perkecil eksposur riil meski chart bagus |
| **XAUUSD** | Tiga jalur: (1) fiskal/debasement — defisit −5,8% PDB + bunga $1.25T naik → term premium (blok A) → ramah gold; (2) ujung QT = kepanikan funding = flight-to-quality; (3) air melimpah = inflasi aset | Anginnya cenderung satu arah ramah — hampir semua keadaan blok E (banjir maupun badai) historisnya baik untuk emas, yang beda cuma kecepatannya. Sizing tetap dari vol (blok F) |
| **XAGUSD / XPTUSD** | Beta lebih tinggi terhadap cerita yang sama dengan gold + sisi industri (risk-on) | EXPANDING = amplifikasi naik; CONTRACTING = jatuh lebih dalam dari gold — kombinasi dengan blok D/F untuk sizing |
| **XCUUSD** | Copper = logam pertumbuhan: air melimpah + risk-on = demand; drain funding = beban | Gunakan sebagai konfirmasi risk appetite, bukan sinyal mandiri (utamanya tetap blok D China) |
| **US100/500/30** | Risk asset klasik: EXPANDING = bias naik, terutama US100 (paling rakus air); funding stress = kompresi multiple | Saat `SOFR−IORB` melebar + xccy melar: indeks bias lemah, US100 tertekan paling dulu |
| **EURUSD & majors** | **Xccy basis = jendela funding dolar**: basis melar negatif = dunia bayar mahal untuk dolar = USD bid → majors tertekan — sering sebelum terlihat di spot | Pantau xccy sebagai radar dini arah dolar; konfirmasi arah tetap blok A (DTWEXBGS, differential rate, smile) |
| **XAUEUR / XAGGBP / crosses** | Dua kaki: likuiditas dolar global (xccy) + kebijakan lokal (blok A ESR/ECB path) | Cross menarik saat funding dolar tegang tapi cerita lokal tenang — divergence kaki adalah sinyalnya |
| **DXY** | Ujung QT & fiskal (beban bunga) = tekanan struktural dolar; kepanikan funding = dolar naik jangka pendek | Bedakan dorongan jangka pendek (stress) vs panjang (debasement fiskal) — arahnya bisa berlawanan |
| **Stablecoin/BTC native** | Spec menyarankan cek silang: stablecoin supply (blok H) vs net liq — likuiditas dolar vs likuiditas crypto-native | Dua-duanya naik = konfluensi; beda arah = teliti sebelum percaya narasi "likuiditas" |

### 6.3 Checklist praktis sebelum entry swing (memakai Blok E saja)

1. **Δ net liq mingguan + komponen penyumbangnya.** Naik dari WALCL (easing sejati) ≠ naik dari TGA turun (netral) ≠ naik dari RRP terkuras (baik tapi hitung mundur — penyangga berkurang).
2. **Posisi reserves & status RRP.** RRP masih tebal = longgar aman; RRP habis → langsung cek trio alarm: `SOFR−IORB`, `SOFR_TARGET_LOWER`, SRF take-up (§4.5).
3. **Xccy basis.** Melar melewati 4bp = funding dolar global mulai tegang → waspada majors & risk asset, siap-siap USD bid.
4. **Fiskal hanya untuk cerita.** Defisit & bunga tidak berubah dalam sehari — pakai untuk keyakinan arah besar gold/dolar jangka minggu-bulan, jangan untuk timing entry.

---

## 7. Yang bisa salah: degradasi, kualitas data, keterbatasan

### 7.0 Gerbang uji khusus Blok E (dari BUILD-PLAN)

- **Identitas net-liq vs WRESBAL+** (reserves + uang kartal + liabilitas kecil) — konsisten setiap minggu.
- **ΣΔSOMA per-CUSIP ≈ ΔWALCL (±$15B)** — identitas harian gerbang brief (§6.3 BUILD-PLAN).
- **TGA 3-era tanpa gap > 5 hari kerja** — jahitan label teruji.
- **Golden anchor F0**: TGA = 950.804 @ 2026-08-27 — fetcher yang tiba-tiba membalas nilai lain = alarm drift, bukan "data baru".
- **Xccy computed vs tool resmi ±0,1bp** (fixture + live) di gerbang F2.
- Spesifikasi umum z/percentile: σ populasi, window 5y, min-obs 80% → `INSUFFICIENT`.

### 7.1 Mode degradasi per sumber (prinsip §0.3 — dan blok E hampir semuanya T0)

| Sumber mati | Mode degradasi resmi |
|---|---|
| **FRED** | `WALCL`/`WRESBAL`/`M2SL`/fiscal series basi → flag freshness, **tidak diganti diam-diam**; TGA tetap hidup dari fiscaldata; RRP punya jalur ganda (FRED `RRPONTSYD` ↔ API NY Fed propositions — ingat jebakan satuan) |
| **fiscaldata DTS** | TGA jatuh ke sekunder `WTREGEN` (FRED, mingguan Rabu) — net liq kehilangan resolusi harian, kembali mode mingguan; flag di brief |
| **NY Fed API** | SRF/ON-RRP/SOMA-per-CUSIP/percentile hilang → QT roll-off fallback ke `ΔWALCL` (kurang presisi, toleransi identitas dilonggarkan & dicatat); alarm akhir-QT melemah jadi SOFR−IORB saja |
| **EODHD** | Spread funding-stress hilang → trio funding tetap hidup dari `SOFR−IORB` (FRED) + percentile NY Fed |
| **Backdoor CME** | Settlements SR3/ESR/6E mati → **xccy computed mati** (SR3/ESR tidak punya pengganti Yahoo yang konsisten — spec §10) → fallback = QuikStrike XCCY view (peran dibalik: cross-check jadi primer, turunkan frekuensi jadi mingguan) |
| **QuikStrike view** | Cross-check xccy mingguan hilang → computed tetap primer (filosofi raw+derived: tidak tergantung tool) |

### 7.2 Kualitas data & jebakan operasional

- **Revisi**: `WALCL` & `M2SL` masuk job mingguan ALFRED vintage (§18.2) — revisi masuk sebagai baris baru, tak pernah menimpa (raw append-only).
- **Delay struktural**: WALCL/WRESBAL posisi Rabu rilis Kamis; M2 bulanan; fiskal tahunan/kuartalan — baris brief selalu membaca data semuda yang resmi tersedia, bukan semuda kejadian.
- **ESR muda** → xccy = snapshot mulai hari build; **backtest jangka menengah terbatas** — tercatat resmi sebagai pengecualian di BUILD-PLAN §4.
- **Depth gate F0**: WALCL 2002+, TGA-DTS 2005+, RRP 2013/2015 (akan dikunci `expected_start` di F0) — net liq 10-tahun penuh tercakup; xccy tidak.
- **Endpoint NY Fed tanpa suffix `.json` = 400** — jebakan syntactic yang gampang menyerupai "sumber mati".
- **Primary Dealer (1.539 series)** opsional & episodik — jangan dibuat dependensi rutin brief.

### 7.3 Keterbatasan konseptual (yang layak Anda tantang)

1. **Net liquidity bukan ramalan BTC.** Hubungan air→aset paling kuat di era banjir 2020–2022; strukturnya berubah ketika laci RRP ikut main (kenapa RRP dikurangkan sekarang padahal dulu sering diabaikan orang). Sistem memakai Δ + state + anomali reversal, bukan regresi kaku — dan semua bisa dihitung ulang dari raw jika kalibrasi direvisi.
2. **Batas "reserve menipis" tidak diketahui siapa pun.** Fed sendiri kaget 2019; tidak ada level ajaib. Karena itu desain memakai **sistem alarm bertingkat** (SOFR−IORB → percentile → SRF), bukan satu threshold.
3. **Xccy hanya EUR/USD** — tool resmi tidak punya JPY/CHF (basis yen adalah barometer stress klasik yang terkenal). Pilihan ini konsekuensi reproduksinya dari futures CME yang tersedia; pengembangan berikutnya butuh sumber lain.
4. **Fiskal paling lambat dari semua seri** — kanal cerita, bukan timing; jangan dipakai membenarkan entry harian.
5. **Bobot E 0,15 adalah pilihan desain** v1 (§11 menyatakan kalibrasi bisa berubah). Argumen menaikkannya: uang adalah bahan bakar tunggal risk asset. Argumen menahannya: sinyalnya mingguan & sering tertinggal dari funding stress (yang sudah terwakili blok F).

---

*Dokumen edukasi; kebenaran teknis merujuk DATA-SPEC v1.4 §5/§18.3/§19.1/§19.3 dan BUILD-PLAN v1.1 §3-E/§4/§6.3. Rantai angka siapa pun di brief dapat ditelusuri: `arkwatch explore block E` / `arkwatch explore series SYN:NETLIQ --trace`.*
