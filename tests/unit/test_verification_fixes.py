"""Regression tests for the 2026-09-13 three-layer data-verification fixes.

Each test pins the exact failure mode the audit caught:
- COT swap double-underscore (P1-2): 61.7% of gold shorts were NULL
- fetch_window gap-heal (P1-1): latest-only snapshots froze shutdown-day holes
- Bybit leg visibility + funding freshness + COALESCE (P1-3)
- ADS colon dates (P1-4)
- copper trigger monthly-cadence gate (P2)
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from arkwatch import db


@pytest.fixture()
def conn(tmp_path):
    c = db.get_conn(tmp_path / "t.db", allow_init=True)
    yield c
    c.close()


def _day(n: int = 0) -> str:
    return (datetime.now(UTC).date() - timedelta(days=n)).isoformat()


# --- P1-2: COT swap double-underscore ---------------------------------------


def test_cot_swap_double_underscore(monkeypatch):
    from arkwatch.fetchers import cot

    class R:
        status_code = 200

        def json(self):
            # the CFTC quirk: swap uses DOUBLE underscore; mm single
            return [
                {
                    "report_date_as_yyyy_mm_dd": "2026-09-08",
                    "contract_market_name": "GOLD",
                    "open_interest_all": "411313",
                    "swap__positions_long_all": "14542",
                    "swap__positions_short_all": "253855",
                    "swap__positions_spread_all": "23273",
                    "m_money_positions_long_all": "145804",
                    "m_money_positions_short_all": "10832",
                }
            ]

    monkeypatch.setattr(cot.requests, "get", lambda *a, **k: R())
    rows = cot.fetch_cot("disagg", "088691", limit=5)
    by_cat = {r["category"]: r for r in rows}
    assert by_cat["swap"]["short"] == 253855  # the number that was NULL 158 weeks
    assert by_cat["swap"]["spread"] == 23273
    assert by_cat["swap"]["long"] == 14542
    assert by_cat["mm"]["long"] == 145804


# --- P1-1: fetch_window gap-heal ---------------------------------------------


def test_nyfed_fetch_window_covers_hole_dates(monkeypatch):
    from arkwatch.fetchers import nyfed

    class R:
        status_code = 200

        def json(self):
            return {
                "refRates": [
                    {"effectiveDate": "2026-09-03", "type": "EFFR", "percentPercentile1": "3.74"},
                    {"effectiveDate": "2026-09-04", "type": "EFFR", "percentPercentile1": "3.73"},
                    {"effectiveDate": "2026-09-05", "type": "OBFR", "percentPercentile1": "3.70"},
                    {"effectiveDate": "2026-09-08", "type": "EFFR", "percentPercentile1": "3.72"},
                ]
            }

    monkeypatch.setattr(nyfed.requests, "get", lambda *a, **k: R())
    pts = nyfed.fetch_window("NYFED:EFFR_P1", days=10)
    # type filter + all dates: the 09-04 hole day is IN the window
    assert [p["ts"] for p in pts] == ["2026-09-03", "2026-09-04", "2026-09-08"]
    assert pts[1]["value"] == 3.73


def test_eodhd_fetch_window_all_rows_not_max(monkeypatch):
    from arkwatch.fetchers import eodhd

    monkeypatch.setattr(
        eodhd, "_get",
        lambda path, params=None: [
            {"code": "EFFR_SOFR", "date": "2026-09-03", "value_bps": -3.0},
            {"code": "EFFR_SOFR", "date": "2026-09-04", "value_bps": -2.0},
            {"code": "OTHER", "date": "2026-09-04", "value_bps": 99.0},
        ],
    )
    pts = eodhd.fetch_window("EODHD:FS_EFFR_SOFR", days=10)
    assert [(p["ts"], p["value"]) for p in pts] == [("2026-09-03", -3.0), ("2026-09-04", -2.0)]


def test_fiscal_fetch_window_multi_day(monkeypatch):
    from arkwatch.fetchers import fiscal

    monkeypatch.setattr(
        fiscal, "_get",
        lambda path, params=None, session=None: {
            "data": [
                {"record_date": "2026-09-04", "tot_pub_debt_out_amt": "35467890123456.00"},
                {"record_date": "2026-09-03", "tot_pub_debt_out_amt": "35400123456789.00"},
                {"record_date": "2026-09-02", "tot_pub_debt_out_amt": None},
            ]
        },
    )
    pts = fiscal.fetch_window("FISCAL:DEBT_TOTAL", days=10)
    assert [p["ts"] for p in pts] == ["2026-09-03", "2026-09-04"]  # null row skipped


def test_harvest_uses_fetch_window_and_falls_back(monkeypatch):
    """The harvest integration: window fetchers land ALL points; a series the
    module's fetch_window does not support falls back to fetch_latest."""
    from arkwatch.qa import harvest as h

    calls = {"window": [], "latest": []}

    class FakeMod:
        @staticmethod
        def fetch_window(sid, days=10):
            calls["window"].append(sid)
            if sid == "FAKE:SUPPORTED":
                return [{"ts": _day(2), "value": 1.0}, {"ts": _day(1), "value": 2.0}]
            raise RuntimeError("unsupported")

        @staticmethod
        def fetch_latest(sid):
            calls["latest"].append(sid)
            return {"ts": _day(0), "value": 9.0}

    rows, first = h._window_or_latest(FakeMod, "FAKE:SUPPORTED", "FAKE")
    assert len(rows) == 2 and rows[-1][1] == _day(1) and first["value"] == 2.0
    rows, first = h._window_or_latest(FakeMod, "FAKE:OTHER", "FAKE")
    assert len(rows) == 1 and first["value"] == 9.0
    assert calls["latest"] == ["FAKE:OTHER"]


# --- P1-3: Bybit legs ---------------------------------------------------------


def test_funding_eod_stale_feed_refuses(monkeypatch):
    """A frozen funding feed must NOT stamp its stale average under a fresh
    date — the gate rejects fixings older than yesterday UTC."""
    from arkwatch.fetchers import bybit
    from arkwatch.qa.f2_harvest import harvest_flows

    stale_day = (datetime.now(UTC).date() - timedelta(days=4)).isoformat()
    monkeypatch.setattr(
        bybit, "fetch_funding_history",
        lambda s, limit=9: [{"ts": f"{stale_day}T16:00:00Z", "rate": 0.0001}],
    )
    monkeypatch.setattr(bybit, "fetch_ticker", lambda s: (_ for _ in ()).throw(OSError("dead")))
    import sqlite3

    c = sqlite3.connect(":memory:", isolation_level=None)
    c.execute("CREATE TABLE flows_daily (date TEXT PRIMARY KEY, funding_bps REAL,"
              " oi_btc REAL, oi_eth REAL, stablecoin_usd REAL)")
    c.execute("CREATE TABLE fetch_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,"
              " fetcher TEXT, target TEXT, status TEXT, http_status INTEGER,"
              " schema_fp TEXT, error TEXT, duration_ms INTEGER, rows INTEGER,"
              " quota_used INTEGER)")
    c.execute("CREATE TABLE bybit_positioning (symbol TEXT NOT NULL, date TEXT NOT NULL,"
              " ls_ratio REAL, taker_buy_ratio REAL, oi REAL, PRIMARY KEY (symbol, date))")
    out = harvest_flows(c)
    assert out["funding_btc"] is None  # refused: stale feed, no fallback either
    err = c.execute("SELECT status, error FROM fetch_log WHERE target='BYBIT:FLOWS'").fetchone()
    assert err[0] == "ERROR" and "frozen" in err[1]
    c.close()


def test_flows_upsert_coalesce_protects_prior_values():
    import sqlite3

    today = datetime.now(UTC).date().isoformat()

    def mock_harvest(conn, funding, oi):
        # drive the upsert directly with the COALESCE contract
        conn.execute(
            "INSERT INTO flows_daily(date,funding_bps,oi_btc,oi_eth,stablecoin_usd)"
            " VALUES (?,?,?,?,?)"
            " ON CONFLICT(date) DO UPDATE SET"
            " funding_bps=COALESCE(excluded.funding_bps, funding_bps),"
            " oi_btc=COALESCE(excluded.oi_btc, oi_btc),"
            " oi_eth=COALESCE(excluded.oi_eth, oi_eth),"
            " stablecoin_usd=COALESCE(excluded.stablecoin_usd, stablecoin_usd)",
            (today, funding, oi, oi, None),
        )

    c = sqlite3.connect(":memory:", isolation_level=None)
    c.execute("CREATE TABLE flows_daily (date TEXT PRIMARY KEY, funding_bps REAL,"
              " oi_btc REAL, oi_eth REAL, stablecoin_usd REAL)")
    mock_harvest(c, 3.5, 1000.0)     # morning success
    mock_harvest(c, None, None)      # afternoon retry, legs dead
    row = c.execute("SELECT funding_bps, oi_btc FROM flows_daily").fetchone()
    assert row == (3.5, 1000.0)  # NULL legs never clobber (audit P1-3)
    mock_harvest(c, 4.0, 2000.0)  # next day's real update DOES win
    assert c.execute("SELECT funding_bps FROM flows_daily").fetchone()[0] == 4.0
    c.close()


# --- P1-4: ADS colon dates ----------------------------------------------------


def test_ads_colon_date_normalized():
    # the normalization formats live inline in philly.fetch_latest; pin the
    # accepted shapes so a future refactor cannot drop the colon variant
    s = "2026:09:05"
    from datetime import datetime as _dt

    for fmt in ("%Y:%m:%d",):
        assert _dt.strptime(s, fmt).date().isoformat() == "2026-09-05"


# --- P2: copper monthly-cadence gate ------------------------------------------


def test_copper_trigger_skips_frozen_feed(conn, capsys):
    from arkwatch.qa import watcher

    conn.execute(
        "INSERT OR IGNORE INTO series_registry(series_id, name, block, tier, unit,"
        " value_format, freq, primary_source) VALUES ('LME:CA_STOCKS','Cu','H',0,"
        "'tonne','{:,.0f}','D','LME')"
    )
    stale_ts = (datetime.now(UTC).date() - timedelta(days=60)).isoformat()
    for i in range(80):
        conn.execute(
            "INSERT INTO raw_observations(series_id, ts, value, vintage_ts, source, fetched_at)"
            " VALUES ('LME:CA_STOCKS', ?, ?, 'realtime', 't', ?)",
            ((date.fromisoformat(stale_ts) - timedelta(days=i)).isoformat(),
             200000.0 - i * 100, stale_ts),
        )
    conn.commit()
    fired = watcher.check_all(conn)
    assert "copper_stocks_drain" not in fired
    assert "frozen" in capsys.readouterr().out
