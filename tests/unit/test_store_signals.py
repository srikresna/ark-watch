"""Tests for the computed_signals writer (COT and regime audit trail).

Timestamp convention: COT signals are stamped with the CFTC report_date
(the weekly dedup key); daily signals use the UTC date."""

from __future__ import annotations

import pytest

from arkwatch import db
from arkwatch.signals.compute import store_cot_signals


@pytest.fixture()
def conn(tmp_path):
    c = db.get_conn(tmp_path / "t.db", allow_init=True)
    yield c
    c.close()


def _seed_cot(conn, code="088691", n_weeks=160, base_net=50_000):
    """Seed cot_raw with n_weeks of 'mm' rows (linearly rising net so z-scores are defined)."""
    from datetime import date, timedelta

    d0 = date(2026, 8, 25) - timedelta(weeks=n_weeks - 1)
    rows = []
    for i in range(n_weeks):
        rd = (d0 + timedelta(weeks=i)).isoformat()
        lng = base_net + i * 100
        sht = 1000
        rows.append(
            (rd, code, "disagg", "mm", lng, sht, 500, -200, 20.0, 30.0, 80, rd, "cftc:socrata", rd)
        )
    conn.executemany(
        "INSERT INTO cot_raw(report_date, contract_code, report_type, category, "
        "long, short, change_long, change_short, conc_top4_long, conc_top8_long, "
        "traders_long, release_ts, source, fetched_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


def test_empty_db_stores_nothing_but_daily_signals(conn):
    """With no COT data present, only daily signals (regime score + pillars) are stored."""
    n = store_cot_signals(conn, score=0.1)
    assert n >= 7  # regime_score + 6 pillars
    ids = {r[0] for r in conn.execute("SELECT DISTINCT signal_id FROM computed_signals")}
    assert "regime_score" in ids
    assert "pillar_a" in ids
    assert not any(i.startswith("cot_") for i in ids)


def test_cot_signals_stored_with_report_date_ts(conn):
    _seed_cot(conn)
    n = store_cot_signals(conn, score=0.0)
    assert n > 0
    # COT signal ts = latest report_date (2026-08-25), not today's date
    r = conn.execute(
        "SELECT ts, value, state FROM computed_signals WHERE signal_id='cot_z_088691'"
    ).fetchone()
    assert r[0] == "2026-08-25"
    assert isinstance(r[1], float)
    assert r[2] in ("NORMAL", "CROWDED_LONG", "CROWDED_SHORT")


def test_rerun_same_week_replaces_not_duplicates(conn):
    _seed_cot(conn)
    store_cot_signals(conn, score=0.0)
    store_cot_signals(conn, score=0.5)  # re-run for the same week
    n = conn.execute(
        "SELECT COUNT(*) FROM computed_signals WHERE signal_id='cot_z_088691'"
    ).fetchone()[0]
    assert n == 1  # INSERT OR REPLACE keeps weekly history at one row per week


def test_retail_extreme_state(conn):
    # non-reportable net = 60,000 - 0 exceeds the 20,000 threshold -> LONG_EXTREME
    conn.execute(
        "INSERT INTO cot_raw(report_date, contract_code, report_type, category, "
        "long, short, release_ts, source, fetched_at) "
        "VALUES ('2026-08-25','088691','disagg','nonrep',60000,0,"
        "'2026-08-25','cftc:socrata','2026-08-25')"
    )
    conn.commit()
    store_cot_signals(conn, score=0.0)
    r = conn.execute(
        "SELECT value, state FROM computed_signals WHERE signal_id='cot_retail_extreme_gold'"
    ).fetchone()
    assert r is not None and r[1] == "LONG_EXTREME"
    assert r[0] == 60_000
