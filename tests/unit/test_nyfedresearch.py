"""Offline unit tests for nyfedresearch — the 8 NY Fed research datasets.

Every test pins a trap the live probe caught (2026-09-19) or a calibration
anchor from the 8-agent research workflow:
  - century pivot '26:Q2' → 2026 (the probe stored 1926 — twice)
  - HHDC footnote rows skipped; the flow column is 'CC', not 'CREDIT CARD'
  - MCT: leading unnamed column (dates at parts[1]) + band invariant lo<=pt<=hi
  - SCE: columns mapped BY LABEL (job-loss vs quit share a sheet)
  - Empire: survey month-END stamp → month-start
  - GSCPI: current vintage = LAST column of the matrix
  - HLW: US r* = the 'US' column under the 'Natural Rate' group (group_col+1
    landed on Canada's 1.76 — live-caught)
  - window floors: a 10-day default must still reach the latest quarter
  - db.apply_realtime_revisions: the revision contract shared with FRED

ACM (legacy .xls via xlrd) has no offline fixture — its 16,280-row live probe
is the verification; the header-map logic mirrors Empire's.
"""

from __future__ import annotations

from datetime import datetime

import openpyxl
import pytest

from arkwatch import db
from arkwatch.fetchers import nyfedresearch as nr

# --- date/label helpers ----------------------------------------------------------


class TestQuarterLabels:
    def test_century_pivot(self):
        """'26:Q2'→2026, '03:Q1'→2003, '99:Q4'→1999 — the probe stored
        1926-04-01 with the pivot inverted (twice in a row)."""
        assert nr._quarter_start("26:Q2") == "2026-04-01"
        assert nr._quarter_start("03:Q1") == "2003-01-01"
        assert nr._quarter_start("99:Q4") == "1999-10-01"

    def test_footnote_rows_are_not_quarters(self):
        """'* 2026Q2 report includes a revision…' rides below Page 3 data —
        it must be skipped, not crash the parser (live-caught)."""
        assert not nr._is_quarter_label("* 2026Q2 report includes a revision to 2026Q1")
        assert nr._is_quarter_label("26:Q2")
        assert nr._is_quarter_label(datetime(2026, 4, 1))


# --- MCT ---------------------------------------------------------------------------


def _mct_text() -> str:
    return (
        "﻿Section/Chart Name,,MCT Common to all,,,,\n"
        "Top-Level-Route,,MCT,MCT,MCT,MCT,\n"
        "Radio Button Routes,,,,,,\n"
        "column name,Date,MCT,MCT,MCT,MCT,Headline PCE inflation (YoY)\n"
        "\n"
        ",1/1/1960,1.19,1.51,1.84,-0.32,1.69\n"
        ",7/1/2026,2.22,2.67,3.09,0.84,3.7\n"
    )


class TestMct:
    def test_leading_unnamed_column(self, monkeypatch):
        """Dates live at parts[1] (leading empty field) — parts[0] parsing
        yielded zero rows (live-caught). Anchors: Jul-2026 = 2.67 (2.2, 3.1)."""
        monkeypatch.setattr(nr, "_download", lambda k: _mct_text().encode())
        out = nr._mct()
        assert out["MCT"][-1] == ("2026-07-01", 2.67)
        assert out["MCT_BAND_LO"][-1] == ("2026-07-01", 2.22)
        assert out["MCT_BAND_HI"][-1] == ("2026-07-01", 3.09)

    def test_band_invariant_is_a_tripwire(self, monkeypatch):
        """lo<=point<=hi enforced at parse — a schema drift must FAIL loudly,
        not store scrambled columns."""
        bad = _mct_text().replace(",2.22,2.67,3.09,", ",3.5,2.67,2.1,")
        monkeypatch.setattr(nr, "_download", lambda k: bad.encode())
        with pytest.raises(nr.NyFedResearchError, match="band invariant"):
            nr._mct()


# --- GSCPI -------------------------------------------------------------------------


class TestGscpi:
    def test_current_vintage_is_last_column(self, monkeypatch):
        """Matrix semantics (live): Jul printed 0.79, revised to 0.94; the
        current vintage (LAST column) carries 0.94 for July — and Aug's first
        print appears only in the Sep column."""
        text = (
            "Date,Jul-26,Aug-26,Sep-26\n"
            "31-Jul-2026,0.79,0.94,0.94\n"
            "31-Aug-2026,,,1.0625\n"
        )
        monkeypatch.setattr(nr, "_download", lambda k: text.encode())
        out = nr._gscpi()
        assert ("2026-07-31", 0.94) in out["GSCPI"]
        assert ("2026-07-31", 0.79) not in out["GSCPI"]  # superseded print dropped
        assert out["GSCPI"][-1] == ("2026-08-31", 1.0625)


# --- Empire ------------------------------------------------------------------------


class TestEmpire:
    def test_month_end_stamp_normalized(self, monkeypatch):
        """surveyDate 2026-09-30 (survey released Sep 15!) → ts 2026-09-01."""
        text = (
            "surveyDate,GACDISA,NOCDISA,SHCDISA,PPCDISA,PRCDISA,NECDISA,AWCDISA\n"
            "2001-07-31,-13.3,,,,,,,\n"
            "2026-09-30,7.6,2.0,-3.2,63.1,28.1,10.6,17.0\n"
        )
        monkeypatch.setattr(nr, "_download", lambda k: text.encode())
        out = nr._empire()
        assert out["ESMS_HEADLINE"][-1] == ("2026-09-01", 7.6)
        assert out["ESMS_PRICES_PAID"][-1] == ("2026-09-01", 63.1)
        assert out["ESMS_HEADLINE"][0] == ("2001-07-01", -13.3)


# --- HPW ---------------------------------------------------------------------------


class TestHpw:
    def test_placeholder_row_dropped(self, monkeypatch):
        """The trailing month row is an empty placeholder — dropping keeps
        z-score units intact (NEVER percent)."""
        text = (
            "date,HPW,ECI_qoq\n"
            "7/1/2026,-0.08229775,\n"
            "8/1/2026,,\n"
        )
        monkeypatch.setattr(nr, "_download", lambda k: text.encode())
        out = nr._hpw()
        assert out["HPW_IDX_M"] == [("2026-07-01", -0.0823)]


# --- SCE ----------------------------------------------------------------------------


class TestSce:
    def test_columns_mapped_by_label(self, tmp_path, monkeypatch):
        """Job-loss and quit probabilities share one sheet — a positional read
        swaps them (13.84 vs 19.49, press-release-verified)."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Job separation expectation"
        ws.append(["Source: SCE"])
        ws.append(["Job separation expectations"])
        ws.append([None])
        ws.append([None, "Mean probability of losing a job",
                   "Mean probability of leaving a job voluntarily"])
        ws.append([202608, 13.842, 19.494])
        ws2 = wb.create_sheet("Inflation expectations")
        ws2.append([None])
        ws2.append([None])
        ws2.append([None])
        ws2.append([None, "Median one-year ahead expected inflation rate",
                    "Median three-year ahead expected inflation rate"])
        ws2.append([202608, 3.5794, 3.1878])
        path = tmp_path / "sce.xlsx"
        wb.save(path)
        monkeypatch.setattr(nr, "_download", lambda k: path.read_bytes())
        # only the two sheets the fixture carries — patch the spec table
        monkeypatch.setattr(nr, "_SCE_SPECS", [
            ("SCE_JOBLOSS", "Job separation expectation", "Mean probability of losing a job"),
            ("SCE_INFL_1Y", "Inflation expectations", "Median one-year ahead expected inflation"),
        ])
        out = nr._sce()
        assert out["SCE_JOBLOSS"] == [("2026-08-01", 13.842)]
        assert out["SCE_INFL_1Y"] == [("2026-08-01", 3.5794)]


# --- LW / HLW ------------------------------------------------------------------------


def _lw_wb(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "data"
    ws.append(["Estimates based on data available on August 26, 2026"])
    ws.append([None])
    ws.append(["Final data point: 2026Q2"])
    ws.append([None])
    ws.append([None, None, "One-Sided Estimates", None, None, None, None, "Two-Sided Estimates"])
    ws.append(["Date", None, "rstar", "g", "z", "Output gap", None, "rstar", "g", "z", "Output gap"])
    ws.append([datetime(1961, 1, 1), None, 5.1057, 4.9, 0.1, -3.7, None, 5.2, 4.9, 0.1, -3.6])
    ws.append([datetime(2026, 4, 1), None, 1.6524, 2.493, -1.014, 1.2014, None, 1.7, 2.5, -1.0, 1.2])
    lw_path = tmp_path / "lw.xlsx"
    wb.save(lw_path)

    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2.title = "HLW Estimates"
    ws2.append(["This spreadsheet..."])
    ws2.append([None])
    ws2.append([None])
    ws2.append([None])
    ws2.append([None, None, "Trend Growth (g)", None, None, None, "Other Determinants (z)",
                None, None, None, "Natural Rate (r*)", None, None, None, "Output Gap"])
    ws2.append(["Date", None, "US", "Canada", "Euro Area", None, "US", "Canada", "Euro Area",
                None, "US", "Canada", "Euro Area", None, "US", "Canada"])
    ws2.append([datetime(1961, 1, 1), None, 4.9177, 3.1650, "NA", None, 0.0047, -0.0411, "NA",
                None, 5.4773, 3.5466, "NA", None, -3.8241, -2.3919])
    ws2.append([datetime(2026, 4, 1), None, 2.4072, 1.9392, 1.2697, None, -1.6702, -0.4390,
                -1.1386, None, 1.0086, 1.7592, 0.0855, None, -0.1138, 1.4523])
    hlw_path = tmp_path / "hlw.xlsx"
    wb2.save(hlw_path)
    return {"lw": lw_path.read_bytes(), "hlw": hlw_path.read_bytes()}


class TestLw:
    def test_one_sided_rstar_and_hlw_us_col(self, tmp_path, monkeypatch):
        """group_col+1 landed on CANADA (1.7592) — the US column is the one
        LABELED 'US' under the 'Natural Rate' group (live-caught)."""
        files = _lw_wb(tmp_path)

        def fake_download(key):
            return files[key]

        monkeypatch.setattr(nr, "_download", fake_download)
        out = nr._lw()
        assert out["LW_RSTAR"][-1] == ("2026-04-01", 1.6524)  # one-sided, NOT 1.7
        assert out["LW_GAP"][-1] == ("2026-04-01", 1.2014)
        assert out["HLW_RSTAR"][-1] == ("2026-04-01", 1.0086)  # US, NOT Canada 1.7592
        assert out["LW_RSTAR"][0] == ("1961-01-01", 5.1057)


# --- routing + windows ----------------------------------------------------------------


class TestRouting:
    def test_window_floor_reaches_latest_quarter(self, monkeypatch):
        """days=10 must not starve a quarterly family — the floor (420d) has
        to reach 2026-04-01 from 2026-09-19 (live today)."""
        monkeypatch.setattr(nr, "_parsed_cache", {
            "hhdc": {"HHDC_TOTAL_DEBT": [("2026-04-01", 18770.5)]}
        })
        pts = nr.fetch_window("NYFED:HHDC_TOTAL_DEBT", days=10)
        assert pts == [{"ts": "2026-04-01", "value": 18770.5}]

    def test_knows_and_unrouted(self):
        assert nr.knows("GSCPI") and nr.knows("HHDC_TOTAL_DEBT")
        assert not nr.knows("SOFR_P1")  # markets-API series stay in nyfed.py

    def test_every_series_has_a_registry_row(self):
        """Parity guard (the sep.py FK lesson): every SERIES_FAMILY key must be
        registered, else save_history silently skips / harvest FK-fails."""
        from arkwatch.qa.verify_sources import load_registry

        reg_ids = {e["series_id"] for e in load_registry()}
        missing = [f"NYFED:{k}" for k in nr.SERIES_FAMILY if f"NYFED:{k}" not in reg_ids]
        assert not missing, f"unregistered series: {missing}"


# --- revision contract (shared with FRED) ------------------------------------------------


class TestRealtimeRevisions:
    def test_vintage_snapshot_and_update(self, tmp_path):
        conn = db.get_conn(tmp_path / "t.db", allow_init=True)
        conn.execute(
            "INSERT INTO series_registry(series_id,name,block,tier,unit,value_format,freq,"
            "ts_convention,primary_source,active) VALUES ('NYFED:GSCPI','GSCPI','C',0,"
            "'idx','level','M','report_month','test',1)"
        )
        conn.commit()
        rows = [("NYFED:GSCPI", "2026-07-31", 0.94, "NYFED")]
        assert db.insert_observations(conn, rows) == 1
        # HHDC-style whole-history revision: 0.94 → 1.06
        n = db.apply_realtime_revisions(conn, [("NYFED:GSCPI", "2026-07-31", 1.06, "NYFED")])
        assert n == 1
        rt = conn.execute(
            "SELECT value FROM raw_observations WHERE series_id='NYFED:GSCPI' "
            "AND vintage_ts='realtime'"
        ).fetchone()
        vintage = conn.execute(
            "SELECT value FROM raw_observations WHERE series_id='NYFED:GSCPI' "
            "AND vintage_ts!='realtime'"
        ).fetchone()
        assert rt[0] == 1.06           # realtime holds the LATEST source value
        assert vintage[0] == 0.94      # the old print is preserved as vintage
        # idempotent: re-applying the same value snapshots nothing
        assert db.apply_realtime_revisions(conn, [("NYFED:GSCPI", "2026-07-31", 1.06, "NYFED")]) == 0
        conn.close()
