"""Tests for the CBOE revival (vixterm signal) + Bybit positioning harvest."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from arkwatch import db
from arkwatch.fetchers import bybit
from arkwatch.signals.vixterm import (
    store_vixterm_signals,
    vix9d_ratio,
    vixterm_brief_line,
)


@pytest.fixture()
def conn(tmp_path):
    c = db.get_conn(tmp_path / "t.db", allow_init=True)
    yield c
    c.close()


def _day(n: int = 0) -> str:
    return (datetime.now(UTC).date() - timedelta(days=n)).isoformat()


# --- CBOE fetcher parser --------------------------------------------------------


def test_cboe_parser_two_header_shapes(monkeypatch):
    from arkwatch.fetchers import cboe

    class R:
        status_code = 200
        text = (
            "DATE,OPEN,HIGH,LOW,CLOSE\n"
            "9/2/2026,12.0,12.5,11.8,11.97\n"
            "9/4/2026,11.0,12.0,11.2,11.5\n"  # newest MIDDLE (unsorted)
            "9/3/2026,11.4,11.6,11.1,11.4\n"
        )

    monkeypatch.setattr(cboe.requests, "get", lambda *a, **k: R())
    assert cboe.fetch_latest("CBOE:VIX9D") == {"ts": "2026-09-04", "value": 11.5}  # max-date scan
    assert cboe.fetch_first_ts("CBOE:VIX9D") == "2026-09-02"


def test_cboe_single_column_shape(monkeypatch):
    """Single-column files carry DATE,{FILE-SYM} not OHLC — the CLOSE
    fallback reads the file-symbol column (the VXV/GVZ/OVX files on the same
    CDN use this shape; our two routed files are OHLC today)."""
    from arkwatch.fetchers import cboe

    class R:
        status_code = 200
        text = "DATE,VIX9D\n9/4/2026,12.73\n9/3/2026,12.66\n"

    monkeypatch.setattr(cboe.requests, "get", lambda *a, **k: R())
    assert cboe.fetch_latest("CBOE:VIX9D") == {"ts": "2026-09-04", "value": 12.73}


def test_cboe_stale_placeholder_rows_skipped(monkeypatch):
    from arkwatch.fetchers import cboe

    class R:
        status_code = 200
        text = "DATE,OPEN,HIGH,LOW,CLOSE\n9/4/2026,1,1,1,11.5\n9/5/2026,,,,0\n"

    monkeypatch.setattr(cboe.requests, "get", lambda *a, **k: R())
    rows = cboe.fetch_history_rows("VIX9D")
    assert len(rows) == 1  # the CLOSE=0 placeholder row skipped


def test_cboe_unrouted_raises():
    from arkwatch.fetchers import cboe

    with pytest.raises(cboe.CboeError, match="retired"):
        cboe.fetch_latest("CBOE:PUTCALL_TOTAL")


# --- vixterm signal ---------------------------------------------------------------


def _seed(conn, sid, ts, value):
    conn.execute(
        "INSERT OR IGNORE INTO series_registry(series_id, name, block, tier, unit, "
        "value_format, freq, primary_source) VALUES (?,?,'F',0,'?','{:,.1f}','D',?)",
        (sid, sid, sid),
    )
    conn.execute(
        "INSERT OR REPLACE INTO raw_observations(series_id, ts, value, vintage_ts, "
        "source, fetched_at) VALUES (?,?,?,?, 'test', ?)",
        (sid, ts, value, "realtime", ts),
    )
    conn.commit()


def test_ratio_math_and_states(conn):
    _seed(conn, "CBOE:VIX9D", _day(0), 14.0)
    _seed(conn, "FRED:VIXCLS", _day(0), 16.0)
    r = vix9d_ratio(conn)
    assert r["ratio"] == pytest.approx(0.875)
    assert vixterm_brief_line(conn) == "VIX term: 9d/spot 0.88 (NORMAL)"
    store_vixterm_signals(conn)
    ts, value, state = conn.execute(
        "SELECT ts, value, state FROM computed_signals WHERE signal_id='vix9d_vix_ratio'"
    ).fetchone()
    assert ts == _day(0)
    assert value == pytest.approx(0.875)
    assert state == "NORMAL"


def test_ratio_backwardation_and_steep(conn):
    _seed(conn, "CBOE:VIX9D", _day(0), 18.0)
    _seed(conn, "FRED:VIXCLS", _day(0), 16.0)
    assert "(BACKWARDATION)" in vixterm_brief_line(conn)
    _seed(conn, "CBOE:VIX9D", _day(0), 11.0)
    assert "(STEEP_CONTANGO)" in vixterm_brief_line(conn)


def test_ratio_stale_leg_degrades(conn):
    _seed(conn, "CBOE:VIX9D", _day(8), 14.0)  # > 5d D-window
    _seed(conn, "FRED:VIXCLS", _day(0), 16.0)
    assert vix9d_ratio(conn) is None
    assert vixterm_brief_line(conn) is None
    assert store_vixterm_signals(conn) == 0


def test_ratio_missing_leg_degrades(conn):
    _seed(conn, "FRED:VIXCLS", _day(0), 16.0)
    assert vix9d_ratio(conn) is None


# --- Bybit positioning harvest -----------------------------------------------------


def _mock_bybit(monkeypatch, ls=None, tk=None, oi=None):
    ls = ls or []
    tk = tk or []
    oi = oi or []

    monkeypatch.setattr(bybit, "fetch_account_ratio", lambda s, limit=30: ls)
    monkeypatch.setattr(bybit, "fetch_taker_volume", lambda s, limit=30: tk)
    monkeypatch.setattr(bybit, "fetch_open_interest_history", lambda s, limit=30: oi)


def test_positioning_upsert_and_selfheal(conn, monkeypatch):
    from arkwatch.qa.f2_harvest import _harvest_positioning

    # day 1: only the ls leg answers (Bybit window half-open).
    # The tk leg is GONE from the harvest loop — Bybit retired taker-volume
    # (404, D-020) — so taker_buy_ratio stays NULL forever here.
    _mock_bybit(
        monkeypatch,
        ls=[{"ts": "2026-09-07", "ls_ratio": 1.2}, {"ts": "2026-09-08", "ls_ratio": 1.3}],
    )
    n = _harvest_positioning(conn)
    assert n == 4  # 2 dates x 2 symbols
    row = conn.execute(
        "SELECT ls_ratio, taker_buy_ratio, oi FROM bybit_positioning"
        " WHERE symbol='BTCUSDT' AND date='2026-09-08'"
    ).fetchone()
    assert row == (1.3, None, None)

    # day 2: both live legs answer — COALESCE fills the NULL legs, keeps old
    _mock_bybit(
        monkeypatch,
        ls=[{"ts": "2026-09-08", "ls_ratio": 9.9}],  # would overwrite…
        oi=[{"ts": "2026-09-08", "oi": 56157.0}],
    )
    _harvest_positioning(conn)
    row = conn.execute(
        "SELECT ls_ratio, taker_buy_ratio, oi FROM bybit_positioning"
        " WHERE symbol='BTCUSDT' AND date='2026-09-08'"
    ).fetchone()
    # non-NULL incoming legs DO update (ls 1.3→9.9); NULL legs never clobber
    assert row == (9.9, None, 56157.0)


def test_bybit_account_ratio_new_shape(monkeypatch):
    """D-020 REGRESSION: Bybit removed accountLongRatio — the endpoint now
    returns buyRatio/sellRatio (same 0..1 share). Either shape must parse."""

    class R:
        status_code = 200

        def json(self):
            return {
                "retCode": 0,
                "result": {"list": [
                    {"symbol": "BTCUSDT", "buyRatio": "0.573",
                     "sellRatio": "0.427", "timestamp": "1788998400000"},
                ]},
            }

    monkeypatch.setattr(bybit.requests, "get", lambda *a, **k: R())
    rows = bybit.fetch_account_ratio("BTCUSDT")
    assert rows == [{"ts": "2026-09-10", "ls_ratio": 0.573}]


def test_bybit_taker_volume_retired(monkeypatch):
    with pytest.raises(bybit.BybitError, match="retired"):
        bybit.fetch_taker_volume("BTCUSDT")


def test_positioning_total_outage_noop(conn, monkeypatch):
    from arkwatch.qa.f2_harvest import _harvest_positioning

    def dead(*a, **k):
        raise bybit.BybitError("connection refused")

    monkeypatch.setattr(bybit, "fetch_account_ratio", dead)
    monkeypatch.setattr(bybit, "fetch_taker_volume", dead)
    monkeypatch.setattr(bybit, "fetch_open_interest_history", dead)
    assert _harvest_positioning(conn) == 0  # no rows, no crash, prints warnings


def test_bybit_v5_no_retry_on_api_error(monkeypatch):
    """API-level answers (404/param) must not retry — they don't heal; only
    transport errors get the second attempt."""

    class R:
        status_code = 404
        text = "{}"

    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        return R()

    monkeypatch.setattr(bybit.requests, "get", fake_get)
    with pytest.raises(bybit.BybitError, match="404"):
        bybit._v5("/v5/market/taker-volume", {})
    assert len(calls) == 1


def test_bybit_v5_transport_error_retries_once(monkeypatch):
    """The OTHER half of the retry policy: a transport error (connection
    refused — the documented TCP-intermittency) gets exactly one re-attempt,
    and a success on attempt 2 is returned."""
    import time

    calls = []

    class R:
        status_code = 200

        def json(self):
            return {"retCode": 0, "result": {"list": [{"a": 1}]}}

    def fake_get(*a, **k):
        calls.append(1)
        if len(calls) == 1:
            raise bybit.requests.ConnectionError("refused")
        return R()

    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.setattr(bybit.requests, "get", fake_get)
    assert bybit._v5("/v5/market/account-ratio", {}) == [{"a": 1}]
    assert len(calls) == 2


def test_ratio_common_date_join(conn):
    """REGRESSION (review ronde-1): the two legs must quote the SAME trade
    date — FRED VIXCLS lags the CDN a day, and dividing VIX9D@today by
    VIX@yesterday states a mixed-vintage number (live: 0.836 mixed vs 0.816
    same-day)."""
    _seed(conn, "CBOE:VIX9D", _day(0), 11.97)  # CDN: today
    _seed(conn, "CBOE:VIX9D", _day(1), 11.68)  # CDN: yesterday too
    _seed(conn, "FRED:VIXCLS", _day(1), 14.32)  # FRED: only yesterday
    r = vix9d_ratio(conn)
    assert r is not None
    assert r["ts"] == _day(1)  # the common date
    assert r["vix9d"] == 11.68  # the SAME-DAY numerator, not 11.97
    assert r["ratio"] == pytest.approx(11.68 / 14.32, abs=0.002)


def test_ratio_no_common_date_degrades(conn):
    """VIX9D only exists at today; VIX only at yesterday → no same-day pair
    → None (never a mixed-vintage number)."""
    _seed(conn, "CBOE:VIX9D", _day(0), 11.97)
    _seed(conn, "FRED:VIXCLS", _day(1), 14.32)
    assert vix9d_ratio(conn) is None


def test_ratio_mirror_direction_also_joined(conn):
    """REGRESSION (review ronde-2): round-1's join only re-read the
    NUMERATOR — when FRED VIX is NEWER than the CDN (harvest missed a day /
    placeholder row), the mirror direction still divided VIX9D@old by
    VIX@new AND overwrote the good stored row at the old ts. Both legs must
    quote the common (older) date."""
    _seed(conn, "FRED:VIXCLS", _day(0), 14.32)  # FRED leads (today)
    _seed(conn, "FRED:VIXCLS", _day(1), 14.10)  # yesterday too
    _seed(conn, "CBOE:VIX9D", _day(1), 11.68)  # CDN stuck at yesterday
    r = vix9d_ratio(conn)
    assert r is not None
    assert r["ts"] == _day(1)
    assert r["vix"] == 14.10  # VIX re-read DOWN to the common date, not 14.32
    assert r["ratio"] == pytest.approx(11.68 / 14.10, abs=0.002)
    # and no overwriting of a future good row: store + verify single row at ts
    store_vixterm_signals(conn)
    ts, value = conn.execute(
        "SELECT ts, value FROM computed_signals WHERE signal_id='vix9d_vix_ratio'"
    ).fetchone()
    assert (ts, value) == (_day(1), pytest.approx(11.68 / 14.10, abs=0.002))


def test_cboe_rejects_non_calendar_dates(monkeypatch):
    """REGRESSION (review ronde-1): '13/45/2026' would produce
    '2026-13-45' — lexicographically AFTER real dates, poisoning the
    max-date scan. The parser must reject non-calendar strings."""
    from arkwatch.fetchers import cboe

    class R:
        status_code = 200
        text = "DATE,OPEN,HIGH,LOW,CLOSE\n9/4/2026,1,1,1,11.5\n13/45/2026,9,9,9,99.0\n"

    monkeypatch.setattr(cboe.requests, "get", lambda *a, **k: R())
    rows = cboe.fetch_history_rows("VIX9D")
    assert len(rows) == 1
    assert rows[0]["ts"] == "2026-09-04"  # the garbage row never lands
