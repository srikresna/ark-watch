"""Tests for the CBOE revival (vixterm signal).

Bybit positioning/funding tests REMOVED 2026-09-16 (owner decision): the
Bybit API endpoints were retired — unreachable from all our networks.
The file keeps its name for git-blame continuity; only the CBOE/vixterm
tests below remain.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from arkwatch import db


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


# import at the bottom to avoid the circular-import at module scope in tests
from arkwatch.signals.vixterm import (  # noqa: E402
    store_vixterm_signals,
    vix9d_ratio,
    vixterm_brief_line,
)
