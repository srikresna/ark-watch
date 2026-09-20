"""Offline tests for the energy curve job (tier 2)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from arkwatch import db
from arkwatch.qa import energy


class TestMonthCodes:
    def test_next_month(self):
        assert energy.next_month_code(11, 26) == "Z26"  # Nov -> Dec
        assert energy.next_month_code(12, 26) == "F27"  # Dec rolls the year
        assert energy.next_month_code(1, 26) == "G26"


class TestCompute:
    def _seed(self, conn):
        for sid in ("FRED:DCOILBRENTEU", "FRED:DCOILWTICO"):
            conn.execute(
                "INSERT OR IGNORE INTO series_registry(series_id,name,block,tier,unit,"
                "value_format,freq,ts_convention,primary_source,active)"
                " VALUES (?,'t','C',0,'x','level','D','obs_day','test',1)",
                (sid,),
            )
        today = datetime.now(UTC).date().isoformat()
        for sym, px in (("CL1", 96.08), ("RB1", 3.2555), ("HO1", 4.844)):
            conn.execute(
                "INSERT INTO instrument_prices(symbol, ts, source, close) VALUES (?,?, 'YAHOO', ?)",
                (sym, today, px),
            )
        for sid, v in (("FRED:DCOILBRENTEU", 130.80), ("FRED:DCOILWTICO", 107.02)):
            conn.execute(
                "INSERT INTO raw_observations(series_id, ts, release_ts, value, vintage_ts,"
                " source, fetched_at) VALUES (?,?,'na',?,'realtime','FMP','t')",
                (sid, today, v),
            )
        conn.commit()
        return today

    def test_cracks_and_spot_spread(self, tmp_path, monkeypatch):
        conn = db.get_conn(tmp_path / "t.db", allow_init=True)
        today = self._seed(conn)
        monkeypatch.setattr(energy, "_cl2_rows", lambda days=30: [
            {"ts": today, "open": 92.0, "high": 92.5, "low": 91.5, "close": 92.05, "volume": 1},
        ])
        out = energy.compute(conn)
        assert out["energy_crack_gas"] == round(3.2555 * 42 - 96.08, 2)   # 40.65
        assert out["energy_crack_ho"] == round(4.844 * 42 - 96.08, 2)     # 107.38
        assert out["energy_wti_bwd"] == 4.03                              # backwardation
        assert out["energy_brent_wti_spot"] == 23.78                       # crisis spread
        row = conn.execute(
            "SELECT close FROM instrument_prices WHERE symbol='CL2'"
        ).fetchone()
        assert row[0] == 92.05
        conn.close()

    def test_spot_pair_requires_common_date(self, tmp_path):
        """Cross-date subtraction bug: Brent@T vs WTI@T-4 produced a phantom
        33.5 spread — the pair must align on the newest COMMON date."""
        conn = db.get_conn(tmp_path / "t.db", allow_init=True)
        for sid in ("FRED:DCOILBRENTEU", "FRED:DCOILWTICO"):
            conn.execute(
                "INSERT INTO series_registry(series_id,name,block,tier,unit,"
                "value_format,freq,ts_convention,primary_source,active)"
                " VALUES (?,'t','C',0,'x','level','D','obs_day','test',1)",
                (sid,),
            )
        d = datetime.now(UTC).date()
        conn.execute(
            "INSERT INTO raw_observations(series_id, ts, release_ts, value, vintage_ts,"
            " source, fetched_at) VALUES ('FRED:DCOILBRENTEU', ?, 'na', 130.8, 'realtime','FMP','t')",
            ((d - timedelta(days=0)).isoformat(),),
        )
        conn.execute(
            "INSERT INTO raw_observations(series_id, ts, release_ts, value, vintage_ts,"
            " source, fetched_at) VALUES ('FRED:DCOILWTICO', ?, 'na', 97.3, 'realtime','FMP','t')",
            ((d - timedelta(days=4)).isoformat(),),
        )
        conn.commit()
        with pytest.raises(RuntimeError, match="no common spot date"):
            energy._spot_pair(conn, days=10)
        conn.close()
