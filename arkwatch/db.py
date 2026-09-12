"""db.py — SQLite connection & schema.

One get_conn() helper for the whole system (scheduler, CLI, backup, verify):
  - journal_mode=WAL (persistent, set once at init)
  - busy_timeout=10000 PER CONNECTION (not persistent!)
  - foreign_keys=ON PER CONNECTION (SQLite disables FKs by default)
  - synchronous=NORMAL (WAL; worst case loses the last commit, no corruption)
  - every write transaction must use BEGIN IMMEDIATE (isolation_level=None)
Migrations run only via numbered scripts; a connect-time guard refuses to open
a DB whose schema version is older than the code (except with allow_init).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC
from pathlib import Path

SCHEMA_VERSION = 14

SCHEMA_V1 = """
CREATE TABLE series_registry (
  series_id TEXT PRIMARY KEY, name TEXT NOT NULL, block TEXT NOT NULL,
  tier INTEGER NOT NULL, unit TEXT NOT NULL, value_format TEXT NOT NULL,
  freq TEXT NOT NULL, ts_convention TEXT,
  release_schedule TEXT, expected_start TEXT,
  sanity_min REAL, sanity_max REAL,
  primary_source TEXT NOT NULL, secondary_source TEXT, tolerance REAL,
  active INTEGER DEFAULT 1
);

CREATE TABLE raw_observations (
  series_id TEXT NOT NULL REFERENCES series_registry,
  ts TEXT NOT NULL, release_ts TEXT NOT NULL DEFAULT 'na',
  value REAL NOT NULL,
  vintage_ts TEXT NOT NULL DEFAULT 'realtime',
  source TEXT NOT NULL, precision_k INTEGER, fetched_at TEXT NOT NULL,
  PRIMARY KEY (series_id, ts, source, vintage_ts)
) WITHOUT ROWID;
CREATE INDEX idx_raw_series_ts ON raw_observations(series_id, ts DESC);

CREATE TABLE instrument_prices (
  symbol TEXT NOT NULL, ts TEXT NOT NULL, source TEXT NOT NULL,
  open REAL, high REAL, low REAL, close REAL, volume REAL,
  adjusted INTEGER DEFAULT 0,
  PRIMARY KEY (symbol, ts, source)
) WITHOUT ROWID;

CREATE TABLE events (
  event_uid TEXT PRIMARY KEY, ts_utc TEXT NOT NULL, release_ts TEXT,
  country TEXT NOT NULL, name TEXT NOT NULL, normalized_name TEXT NOT NULL,
  importance TEXT,
  consensus REAL, consensus_source TEXT, actual REAL, actual_source TEXT, previous REAL,
  surprise_z REAL, is_curated INTEGER DEFAULT 0
);
CREATE INDEX idx_events_norm_ts ON events(normalized_name, ts_utc);
CREATE TABLE indicator_stats (
  indicator TEXT NOT NULL, as_of TEXT NOT NULL,
  sigma REAL NOT NULL, n_obs INTEGER NOT NULL, window TEXT NOT NULL, low_conf INTEGER DEFAULT 0,
  PRIMARY KEY (indicator, as_of)
);

CREATE TABLE cot_raw (
  report_date TEXT NOT NULL, contract_code TEXT NOT NULL, report_type TEXT NOT NULL,
  release_ts TEXT NOT NULL,
  category TEXT NOT NULL,
  long INTEGER, short INTEGER, spread INTEGER, open_interest_all INTEGER,
  pct_of_oi REAL, conc_top4_long REAL, conc_top4_short REAL,
  source TEXT NOT NULL, fetched_at TEXT NOT NULL,
  PRIMARY KEY (report_date, contract_code, report_type, category)
);

CREATE TABLE flows_daily (
  date TEXT PRIMARY KEY, gld_tonnes REAL, slv_shares REAL,
  btc_etf_musd REAL, eth_etf_musd REAL, funding_bps REAL, oi_btc REAL, oi_eth REAL, stablecoin_usd REAL
);
CREATE TABLE flows_periodic (
  period TEXT NOT NULL, kind TEXT NOT NULL,
  value_raw REAL NOT NULL, unit_raw TEXT NOT NULL, factor REAL, value REAL,
  meta_json TEXT, PRIMARY KEY (period, kind)
);

CREATE TABLE cme_settlements (
  trade_date TEXT NOT NULL, product_id INTEGER NOT NULL, month TEXT NOT NULL,
  settle REAL, volume REAL, open_interest REAL, fetched_at TEXT,
  PRIMARY KEY (trade_date, product_id, month)
);
CREATE TABLE cvol_snapshots (
  trade_date TEXT NOT NULL, symbol TEXT NOT NULL,
  cvol REAL, atm REAL, skew REAL, upvar REAL, dnvar REAL, convexity REAL,
  PRIMARY KEY (trade_date, symbol)
);
CREATE TABLE voi_daily (
  trade_date TEXT NOT NULL, product_id INTEGER NOT NULL, report_type TEXT NOT NULL,
  volume REAL, oi REAL, oi_diff REAL,
  PRIMARY KEY (trade_date, product_id, report_type)
);
CREATE TABLE fedwatch_snapshots (
  date TEXT NOT NULL, meeting_date TEXT NOT NULL, source TEXT NOT NULL,
  prob_ease REAL, prob_hold REAL, prob_hike REAL, implied_rate REAL,
  d1 REAL, d7 REAL, d30 REAL,
  raw_json TEXT, PRIMARY KEY (date, meeting_date, source)
);

CREATE TABLE computed_signals (
  signal_id TEXT NOT NULL, ts TEXT NOT NULL, run_id TEXT NOT NULL, computed_at TEXT NOT NULL,
  value REAL, state TEXT, inputs_json TEXT,
  PRIMARY KEY (signal_id, ts)
);
CREATE TABLE fetch_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, fetcher TEXT NOT NULL, target TEXT,
  status TEXT NOT NULL, http_status INTEGER, schema_fp TEXT,
  error TEXT, duration_ms INTEGER, rows INTEGER, quota_used INTEGER
);
CREATE TABLE brief_log (
  date TEXT PRIMARY KEY, markdown TEXT NOT NULL, regime_score REAL,
  quality_flags_json TEXT, generated_at TEXT
);
CREATE TABLE brief_deliveries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brief_date TEXT NOT NULL, channel TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  telegram_message_ids TEXT, attempts INTEGER DEFAULT 0,
  last_error TEXT, sent_at TEXT, created_at TEXT NOT NULL
  -- intentionally no FK: brief_log is always written in the same transaction
);
CREATE UNIQUE INDEX uq_brief_delivery ON brief_deliveries(brief_date, channel);
CREATE TABLE alert_deliveries (
  id INTEGER PRIMARY KEY AUTOINCREMENT, alert_type TEXT NOT NULL, triggered_at TEXT NOT NULL,
  cooldown_key TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'normal',
  status TEXT NOT NULL DEFAULT 'pending', telegram_message_id INTEGER,
  attempts INTEGER DEFAULT 0, last_error TEXT, sent_at TEXT
);
CREATE INDEX idx_alert_cd ON alert_deliveries(cooldown_key, triggered_at DESC);
CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
"""

MIGRATIONS: dict[int, str] = {
    1: SCHEMA_V1,
    2: """-- v2: full COT — add traders, conc-8, weekly changes
ALTER TABLE cot_raw ADD COLUMN conc_top8_long REAL;
ALTER TABLE cot_raw ADD COLUMN conc_top8_short REAL;
ALTER TABLE cot_raw ADD COLUMN traders_long INTEGER;
ALTER TABLE cot_raw ADD COLUMN traders_short INTEGER;
ALTER TABLE cot_raw ADD COLUMN change_long INTEGER;
ALTER TABLE cot_raw ADD COLUMN change_short INTEGER;
""",
    3: """-- v3: alert retry — alert messages are persisted so failed sends can be retried
ALTER TABLE alert_deliveries ADD COLUMN message TEXT;
""",
    4: """-- v4: indicator family key for σ grouping across releases
-- (month/FINAL suffixes and US prefix stripped)
ALTER TABLE events ADD COLUMN indicator_key TEXT;
CREATE INDEX IF NOT EXISTS idx_events_indkey ON events(indicator_key, ts_utc);
""",
    5: """-- v5: (a) claimed_at so a sending row can be re-claimed after >10 min;
--     (b) drop tables with no writer and no reader (golden_anchors:
--         source is YAML; cot_snapshots: z is computed on-the-fly)
ALTER TABLE brief_deliveries ADD COLUMN claimed_at TEXT;
DROP TABLE IF EXISTS golden_anchors;
DROP TABLE IF EXISTS cot_snapshots;
""",
    6: """-- v6: alert retry pacing — retries also run on each watch cycle, with a
--     minimum 5-minute gap between attempts per row
ALTER TABLE alert_deliveries ADD COLUMN last_attempt TEXT;
""",
    7: """-- v7: SOMA per-CUSIP — Fed balance sheet granularity
-- [RISET: live-verified 2026-09-03 — NY Fed /api/soma/tsy/get/asof/{date}.json;
--  identity check vs official /api/soma/summary.json matched to the dollar]
-- UNITS: par_value/change_week/rolling_off_* are RAW USD; pct_outstanding is
-- PERCENT 0-100 (API returns a fraction: 0.6999 = the 70% Fed ownership cap).
CREATE TABLE IF NOT EXISTS soma_holdings (
  as_of_date TEXT NOT NULL,
  cusip TEXT NOT NULL,
  security_type TEXT,
  maturity_date TEXT,
  par_value REAL,
  pct_outstanding REAL,
  change_week REAL,
  PRIMARY KEY (as_of_date, cusip)
);
CREATE INDEX IF NOT EXISTS idx_soma_cusip ON soma_holdings(cusip, as_of_date);
CREATE TABLE IF NOT EXISTS soma_summary (
  as_of_date TEXT PRIMARY KEY,
  total_par REAL, bills REAL, notes_bonds REAL, tips REAL, frn REAL,
  weekly_change REAL,
  rolling_off_7d REAL, rolling_off_30d REAL, rolling_off_90d REAL,
  n_cusips INTEGER, avg_maturity_years REAL
);
""",
    8: """-- v8: CME options settlements per-strike (PLAN-CME-OPTIONS §2.3)
-- [RISET: live-verified 2026-09-03 — CmeWS /Settlements/Options/{pid}/OOF,
--  7 produk (OG/SO/HXE/PO/ES/NQ/BTC), OG satu expiry = 1.281 baris]
-- NOTE: baris type='' pada respons = baris TOTAL kontrak (settle='-'), BUKAN
-- settle futures underlying — anchor underlying cme_option_underlyings
-- di-join dari strip futures cme_settlements (lihat cme_harvest._save_underlying).
CREATE TABLE IF NOT EXISTS cme_options_settlements (
  trade_date TEXT NOT NULL,
  product_id INTEGER NOT NULL,
  product_code TEXT NOT NULL,
  contract_id TEXT NOT NULL,
  option_type TEXT NOT NULL,
  strike REAL NOT NULL,
  settle REAL,
  volume INTEGER,
  open_interest INTEGER,
  PRIMARY KEY (trade_date, product_id, contract_id, option_type, strike)
);
CREATE TABLE IF NOT EXISTS cme_option_underlyings (
  trade_date TEXT NOT NULL,
  product_id INTEGER NOT NULL,
  contract_id TEXT NOT NULL,
  settle REAL NOT NULL,
  PRIMARY KEY (trade_date, contract_id)
);
""",
    9: """-- v9: NY Fed full utilization (PLAN-NYFED-FULL §2)
-- [RISET: live-verified 2026-09-03 — transport = plain requests (curl_cffi
--  double-encodes %20 → the "agency debts" path 400s); MBS/CMBS rows carry
--  currentFaceValue (parValue is EMPTY for them — the "all" enum mixes
--  schemas, never sum parValue across it); agency-debts rows look like tsy
--  rows (parValue/coupon/maturity) and are normalized into current_face_value]
-- UNITS: soma_agency_* money is RAW USD (like soma_holdings); pd_positions
-- value_musd is NATIVE $millions; fed_operations amount is raw USD as
-- reported (tsy: totalParAmtAccepted; ambs: totalAcceptedOrigFace).
CREATE TABLE IF NOT EXISTS soma_agency_holdings (
  as_of_date TEXT NOT NULL, cusip TEXT NOT NULL, asset_type TEXT NOT NULL,
  security_description TEXT, term TEXT, issuer TEXT,
  current_face_value REAL, change_week REAL,
  PRIMARY KEY (as_of_date, cusip, asset_type)
);
CREATE TABLE IF NOT EXISTS soma_agency_summary (
  as_of_date TEXT PRIMARY KEY, mbs REAL, cmbs REAL, agency_debts REAL, total REAL
);
CREATE TABLE IF NOT EXISTS fed_operations (
  operation_id TEXT NOT NULL, family TEXT NOT NULL,
  operation_date TEXT NOT NULL, settlement_date TEXT,
  operation_type TEXT, direction TEXT, maturity_start TEXT, maturity_end TEXT,
  status TEXT, amount REAL, details_json TEXT,
  PRIMARY KEY (operation_id, family)
);
CREATE TABLE IF NOT EXISTS pd_positions (
  asofdate TEXT NOT NULL, keyid TEXT NOT NULL,
  seriesbreak TEXT, value_musd REAL,
  PRIMARY KEY (asofdate, keyid)
);
CREATE TABLE IF NOT EXISTS soma_wam (
  as_of_date TEXT NOT NULL, wam_type TEXT NOT NULL, years REAL,
  PRIMARY KEY (as_of_date, wam_type)
);
""",
    10: """-- v10: fiscaldata expansion (5 dataset audit 2026-09-04): auctions,
--     DTS public debt transactions, monthly interest expense + avg rates.
--     debt_to_penny does NOT get a table — FISCAL:DEBT_PUBLIC/INTRAGOV/TOTAL
--     are registry series (scalar-series pattern, harvested at 06:00).
-- [RISET: live-verified 2026-09-04 — fd_debt_transactions.amount_today is
--  $ MILLIONS (DTS convention), NOT raw USD: FYTD identity Σ(issues−
--  redemptions) = Δdebt_to_penny 2025-09-30→2026-09-02 matched to the DOLLAR
--  (2,479,492 $M); fd_auctions units: price_per100 = per $100 face,
--  avg_med_yield = %, bid_to_cover = ratio, allocation_pct = %.]
-- NOTE: DTS rows carry a 5th dimension security_type_desc (Bills 'Regular
-- Series' vs 'Cash Management Series'; savings 'Cash Issue Price' vs
-- 'Interest Increment') that is NOT in this locked PK — the fetcher folds it
-- into security_type ('Bills (Cash Management Series)') so no API row is
-- collapsed. fd_interest_expense nullable PK legs are stored as '' (SQLite
-- treats NULL PK values as DISTINCT — '' keeps the upsert deduplicating).
CREATE TABLE IF NOT EXISTS fd_auctions (
  auction_date TEXT NOT NULL, cusip TEXT NOT NULL,
  security_type TEXT, security_term TEXT,
  issue_date TEXT, maturity_date TEXT,
  price_per100 REAL, avg_med_yield REAL, bid_to_cover REAL,
  allocation_pct REAL, auction_format TEXT,
  PRIMARY KEY (auction_date, cusip)
);
CREATE TABLE IF NOT EXISTS fd_debt_transactions (
  record_date TEXT NOT NULL, transaction_type TEXT NOT NULL,
  security_market TEXT NOT NULL, security_type TEXT NOT NULL,
  amount_today REAL,
  PRIMARY KEY (record_date, transaction_type, security_market, security_type)
);
CREATE TABLE IF NOT EXISTS fd_interest_expense (
  record_date TEXT NOT NULL, expense_catg_desc TEXT NOT NULL,
  expense_group_desc TEXT, expense_type_desc TEXT,
  month_amt REAL, fytd_amt REAL,
  PRIMARY KEY (record_date, expense_catg_desc, expense_group_desc, expense_type_desc)
);
CREATE TABLE IF NOT EXISTS fd_avg_rates (
  record_date TEXT NOT NULL, security_desc TEXT NOT NULL,
  security_type_desc TEXT, avg_interest_rate REAL,
  PRIMARY KEY (record_date, security_desc)
);
""",
    11: """-- v11: hot-path indexes for the growing tables.
-- [RISET: scale review 2026-09-08 — cme_options_settlements grows ~23.7k
--  rows/day and the watcher scans it PER PRODUCT every 60s (options PCR
--  trigger) with product_code in NO index; at ~6M rows (12mo) that is
--  seconds per cycle, forever. The covering index turns _pcr_history into
--  an index-only range scan and MAX(trade_date) into a seek.
--  cot_raw(contract_code,...) same class: _cot_zscore full-scans every
--  cycle (bounded history, but 3 contracts x 1440 cycles/day).]
CREATE INDEX IF NOT EXISTS idx_opt_prod ON cme_options_settlements(
  product_code, trade_date, contract_id, option_type, open_interest
);
CREATE INDEX IF NOT EXISTS idx_cot_contract ON cot_raw(
  contract_code, report_type, category, report_date
);
""",
    12: """-- v12: Bybit positioning extras (audit sumber 2026-09-08).
-- [RISET: /v5/market/account-ratio + taker-volume + open-interest history —
--  public, no key; connectivity from this network is intermittent at TCP
--  level, so harvest is NULL-tolerant per the funding convention.]
CREATE TABLE IF NOT EXISTS bybit_positioning (
  symbol TEXT NOT NULL,
  date TEXT NOT NULL,
  ls_ratio REAL,            -- long-account SHARE 0..1 (Bybit accountLongRatio; neutral 0.5)
  taker_buy_ratio REAL,     -- taker buy share of volume (>0.5 = net aggressive buying)
  oi REAL,                  -- open interest (contracts) from the history endpoint
  PRIMARY KEY (symbol, date)
);
""",
    13: """-- v13: Farside per-issuer ETF flows (audit sumber 2026-09-10).
-- [RISET: the aggregate net flow hides the structural GBTC-outflow vs
--  IBIT-inflow divergence — the actual ETF-flow story. Issuer cells were
--  already in the fetched HTML and dropped by the old 1-number parser.]
CREATE TABLE IF NOT EXISTS etf_flows_issuer (
  date TEXT NOT NULL,
  etf TEXT NOT NULL,        -- 'BTC' | 'ETH'
  issuer TEXT NOT NULL,     -- IBIT, FBTC, ..., GBTC / ETHA, ..., ETHE
  flow_musd REAL,
  PRIMARY KEY (date, etf, issuer)
);
""",
    14: """-- v14: FMP earnings calendar (vendor-api audit NICE #7, owner GO
-- 2026-09-13). Data-first phase: the table is the deliverable — the
-- weekly heavy-weight share lands in computed_signals; no brief line
-- (delivery paused).
CREATE TABLE IF NOT EXISTS earnings_calendar (
  symbol TEXT NOT NULL,
  date TEXT NOT NULL,             -- announcement date
  eps_estimated REAL,
  eps_actual REAL,
  revenue_estimated REAL,
  revenue_actual REAL,
  last_updated TEXT,
  fetched_at TEXT NOT NULL,
  PRIMARY KEY (symbol, date)
);
""",
}


def get_conn(path: str | Path, *, allow_init: bool = False) -> sqlite3.Connection:
    """Connection with the standard PRAGMA pack. isolation_level=None → writes use explicit BEGIN IMMEDIATE."""
    path = Path(path)
    fresh = not path.exists()
    if fresh or allow_init:
        path.parent.mkdir(parents=True, exist_ok=True)  # sqlite does not create parent dirs
    conn = sqlite3.connect(str(path), timeout=10.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    current = _schema_version(conn)
    if current is None:
        if not (allow_init or fresh):
            conn.close()
            raise RuntimeError(
                f"{path} is not an ark-watch DB (schema_migrations table missing); "
                "use allow_init=True to initialize a new file."
            )
        # A typo'd path with allow_init=True would silently initialize a
        # parallel DB (data vanishing from the DB the brief reads) — warn
        # loudly when initializing over an existing file
        if not fresh:
            print(
                f"⚠⚠ WARNING: initializing a NEW file at {path} — make sure the path is correct (not a typo?)."
            )
        _apply_migrations(conn)
    elif current < SCHEMA_VERSION:
        if allow_init:
            _apply_migrations(conn, from_version=current)
        else:
            conn.close()
            raise RuntimeError(
                f"DB schema v{current} < code v{SCHEMA_VERSION} — run migrations "
                "(arkwatch db migrate) before continuing."
            )
    elif current > SCHEMA_VERSION:
        conn.close()
        raise RuntimeError(
            f"DB schema v{current} > code v{SCHEMA_VERSION} — code downgrade is not supported."
        )
    return conn


def _schema_version(conn: sqlite3.Connection) -> int | None:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if row is None:
        return None
    row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return row[0] if row and row[0] is not None else None


def _apply_migrations(conn: sqlite3.Connection, from_version: int = 0) -> None:
    from datetime import datetime

    conn.execute("PRAGMA journal_mode=WAL")  # persistent — once per DB lifetime
    for version in sorted(MIGRATIONS):
        if version <= from_version:
            continue
        # executescript() issues an implicit COMMIT first (stdlib behavior) —
        # hence BEGIN/COMMIT are embedded INSIDE the script so the migration
        # stays atomic.
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        script = (
            "BEGIN IMMEDIATE;\n"
            + MIGRATIONS[version]
            + f"\nINSERT INTO schema_migrations(version, applied_at) VALUES ({version}, '{ts}');\n"
            "COMMIT;"
        )
        conn.executescript(script)


def insert_observations(conn: sqlite3.Connection, rows: list[tuple]) -> int:
    """Append-only batch insert into raw_observations.

    rows: (series_id, ts, value, source[, release_ts, vintage_ts, precision_k])
    — element 5 is release_ts; fetched_at is filled automatically.
    One BEGIN IMMEDIATE per batch. Returns the number of new rows
    (duplicates skipped).
    """
    from datetime import datetime

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = []
    for r in rows:
        series_id, ts, value, source = r[0], r[1], r[2], r[3]
        release_ts = r[4] if len(r) > 4 and r[4] else "na"
        vintage_ts = r[5] if len(r) > 5 and r[5] else "realtime"
        precision_k = r[6] if len(r) > 6 else None
        payload.append((series_id, ts, release_ts, value, vintage_ts, source, precision_k, now))
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.executemany(
            "INSERT OR IGNORE INTO raw_observations"
            "(series_id, ts, release_ts, value, vintage_ts, source, precision_k, fetched_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            payload,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return cur.rowcount
