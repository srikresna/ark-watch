"""Offline unit tests for the db/ layer: schema bootstrap, migration guard, storage contracts."""

from __future__ import annotations

import sqlite3

import pytest

from arkwatch import db


@pytest.fixture()
def conn(tmp_path):
    c = db.get_conn(tmp_path / "t.db", allow_init=True)
    yield c
    c.close()


def test_init_creates_all_tables_and_version(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    expected = {
        "series_registry",
        "raw_observations",
        "instrument_prices",
        "events",
        "indicator_stats",
        "cot_raw",
        "flows_daily",
        "flows_periodic",
        "cme_settlements",
        "cvol_snapshots",
        "voi_daily",
        "fedwatch_snapshots",
        "computed_signals",
        "fetch_log",
        "brief_log",
        "brief_deliveries",
        "alert_deliveries",
        "schema_migrations",
    }
    assert expected <= tables, f"missing tables: {expected - tables}"
    # Regression guard: golden_anchors and cot_snapshots were dropped as ghost
    # tables and must never reappear.
    assert "golden_anchors" not in tables and "cot_snapshots" not in tables
    assert (
        conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        == db.SCHEMA_VERSION
    )


def test_pragma_pack(conn):
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 10000
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_guard_rejects_older_schema(tmp_path, monkeypatch):
    p = tmp_path / "t.db"
    # Bootstrap with a minimal migration registry: v1 must itself create
    # schema_migrations, and SCHEMA_VERSION is patched to match the registry.
    monkeypatch.setattr(
        db,
        "MIGRATIONS",
        {
            1: "CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL); CREATE TABLE t1(a);",
            2: "CREATE TABLE t2(b);",
        },
    )
    monkeypatch.setattr(db, "SCHEMA_VERSION", 2)
    c = db.get_conn(p, allow_init=True)
    assert c.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 2
    c.close()
    # Rewind to a genuine v1 database: drop the v2 table and rewrite the version
    # table via DELETE+INSERT (a bulk UPDATE would collide with the PK).
    fc = sqlite3.connect(p)
    fc.execute("DROP TABLE t2")
    fc.execute("DELETE FROM schema_migrations")
    fc.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (1, '2026-08-31')")
    fc.commit()
    fc.close()
    with pytest.raises(RuntimeError, match="migration"):
        db.get_conn(p)
    # allow_init=True only replays missed migrations on top of intact state
    # (v2 does not conflict with anything v1 already created).
    c2 = db.get_conn(p, allow_init=True)
    assert c2.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 2
    n2 = c2.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='t2'").fetchone()[0]
    assert n2 == 1
    c2.close()


def test_guard_rejects_non_arkwatch_db(tmp_path):
    foreign = tmp_path / "foreign.db"
    fc = sqlite3.connect(foreign)
    fc.execute("CREATE TABLE x(a)")
    fc.commit()
    fc.close()
    with pytest.raises(RuntimeError, match="not an ark-watch DB"):
        db.get_conn(foreign)


def test_insert_observations_append_only_and_dedup(conn):
    conn.execute(
        "INSERT INTO series_registry(series_id,name,block,tier,unit,value_format,freq,primary_source)"
        " VALUES ('FRED:DGS10','10Y','A',0,'pct','pct','D','FRED')"
    )
    rows = [("FRED:DGS10", "2026-08-27", 4.67, "FRED", "2026-08-31T00:00:00+00:00")]
    assert db.insert_observations(conn, rows) == 1
    assert db.insert_observations(conn, rows) == 0  # duplicates are skipped (idempotent)
    # A revision becomes a new vintage row, never an UPDATE (append-only contract).
    rows2 = [
        (
            "FRED:DGS10",
            "2026-08-27",
            4.68,
            "FRED",
            "2026-09-01T00:00:00+00:00",
            "na",
            "2026-09-01T00:00:00+00:00",
            4,
        )
    ]
    assert db.insert_observations(conn, rows2) == 1
    n = conn.execute("SELECT COUNT(*) FROM raw_observations").fetchone()[0]
    assert n == 2
