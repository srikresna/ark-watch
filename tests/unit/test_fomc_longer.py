"""Offline tests for the CAL:FOMC_LONGER wiring (owner request 2026-09-20).

The terminal-rate anchor can ONLY come from calendar events — the SEP table
has no longer-run column (probed across all 22 live vintages). These tests
pin the caldist wiring:
  - family_rows reads the events family and stamps the RELEASE month
  - fetch_window uses the quarterly 130d floor (a 62d floor would badge
    EMPTY for weeks mid-cycle between SEPs)
  - routing: CAL:FOMC_LONGER must resolve to caldist, NOT the longer
    CAL:FOMC_DOT prefix (sep cannot produce it)
"""

from __future__ import annotations

import sqlite3

from arkwatch.fetchers import caldist
from arkwatch.qa.verify_sources import ROUTES


def _db_with_longer(tmp_path):
    conn = sqlite3.connect(tmp_path / "ev.db")
    conn.execute(
        "CREATE TABLE events (event_uid TEXT PRIMARY KEY, ts_utc TEXT, release_ts TEXT,"
        " country TEXT, name TEXT, normalized_name TEXT, importance TEXT,"
        " consensus REAL, consensus_source TEXT, actual REAL, actual_source TEXT,"
        " previous REAL, surprise_z REAL, is_curated INTEGER, indicator_key TEXT)"
    )
    conn.execute(
        "INSERT INTO events VALUES ('u1','2026-09-16T18:00:00+00:00',NULL,'US',"
        "'FOMC Interest Rate Projection Longer Run','INTEREST RATE PROJECTION LONGER',"
        "'low',NULL,NULL,3.2,'FMP',3.1,NULL,0,'INTEREST RATE PROJECTION LONGER')"
    )
    conn.commit()
    conn.close()
    return str(tmp_path / "ev.db")


class TestFomcLonger:
    def test_family_rows_release_month(self, tmp_path):
        db = _db_with_longer(tmp_path)
        rows = caldist.family_rows("INTEREST RATE PROJECTION LONGER", "release_month", db_path=db)
        assert rows == [{"ts": "2026-09-01", "value": 3.2}]

    def test_fetch_latest_and_quarterly_floor(self, tmp_path, monkeypatch):
        db = _db_with_longer(tmp_path)
        monkeypatch.setattr(caldist, "DEFAULT_DB", db)
        assert caldist.fetch_latest("CAL:FOMC_LONGER") == {"ts": "2026-09-01", "value": 3.2}
        # days=10 must not starve a quarterly family — 130d floor (a 62d floor
        # would return [] mid-cycle between SEPs and badge EMPTY)
        pts = caldist.fetch_window("CAL:FOMC_LONGER", days=10)
        assert pts == [{"ts": "2026-09-01", "value": 3.2}]

    def test_routing_avoids_the_dot_prefix_trap(self):
        """CAL:FOMC_LONGER must go to caldist — startswith('CAL:FOMC_DOT') is
        FALSE for it, but a future careless prefix addition could break this;
        pin the resolution."""
        sid = "CAL:FOMC_LONGER"
        prefix = next(p for p in ROUTES if sid.startswith(p))
        assert prefix == "CAL:"
        assert ROUTES[prefix] is caldist
