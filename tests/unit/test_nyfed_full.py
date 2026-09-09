"""Offline unit tests for the NY Fed full-utilization fetch layer (PLAN-NYFED-FULL,
migration v9): agency holdings parsing/normalization, desk operations, PD survey,
and the new rate feeds. No network — fixtures are live-verified rows captured
2026-09-03 (probe of the real endpoints; see module docstrings in fetchers/nyfed.py).

Schema basis: migration v9. The fixture DDL is CREATE IF NOT EXISTS (the
test_soma_signals.py pattern), so these run before and after the migration is
applied to a real DB.
"""

from __future__ import annotations

import json

import pytest

from arkwatch import db
from arkwatch.fetchers import nyfed
from arkwatch.qa.nyfed_harvest import store_fed_operations, store_pd_positions
from arkwatch.qa.soma_harvest import harvest_wam, store_agency_week

AS_OF = "2026-08-26"

# Locked v9 DDL — no-op once the migration is in db.py
SCHEMA_V9 = """
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
"""

# --- live-captured fixtures (2026-09-03) ----------------------------------------

MBS_ROW = {
    "asOfDate": AS_OF,
    "cusip": "3132DVGB5",
    "securityDescription": "UMBS MORTPASS 2% 10/51",
    "term": "30yr",
    "currentFaceValue": "62424844198.24",
    "isAggregated": "Y",
    "securityType": "MBS",
}
CMBS_ROW = {
    "asOfDate": AS_OF,
    "cusip": "3138LM4F7",
    "securityDescription": "FNMA MORTPASS 3.56% 06/28",
    "term": "",
    "currentFaceValue": "124200000.00",
    "securityType": "CMBS",
}
DEBT_ROW = {
    "asOfDate": AS_OF,
    "cusip": "31359MEU3",
    "maturityDate": "2029-05-15",
    "issuer": "FNMA",
    "spread": "",
    "coupon": "6.250",
    "parValue": "486000000",
    "inflationCompensation": "",
    "percentOutstanding": "",
    "changeFromPriorWeek": "0",
    "changeFromPriorYear": "0",
    "securityType": "Agency Debts",
}
TSY_OP_ROW = {
    "operationId": "OR 083126 25",
    "auctionStatus": "Results",
    "operationType": "Outright Bill Purchase",
    "operationDate": "2026-08-31",
    "settlementDate": "2026-09-01",
    "maturityRangeStart": "2026-10-01",
    "maturityRangeEnd": "2026-12-24",
    "operationDirection": "P",
    "auctionMethod": "Multiple Price",
    "releaseTime": "09:00",
    "closeTime": "09:20",
    "totalParAmtSubmitted": "39346000000",
    "totalParAmtAccepted": "4243000000",
    "note": "",
    "lastUpdated": "2026-08-31 09:20:55",
}
AMBS_OP_ROW = {
    "auctionStatus": "Results",
    "operationId": "OR 081426 25",
    "operationDate": "2026-08-14",
    "operationType": "Outright Specified Pool Sale",
    "operationDirection": "S",
    "method": "Multiple Price",
    "releaseTime": "10:00",
    "closeTime": "10:20",
    "classType": "C",
    "note": "",
    "totalSubmittedOrigFace": "2424000000",
    "totalAcceptedOrigFace": "130453820",
    "totalSubmittedCurrFace": "1364000097.36",
    "totalAcceptedCurrFace": "73999999.1158832",
    "totalAmtSubmittedPar": "",
    "totalAmtAcceptedPar": "",
    "settlementDate": "2026-08-20",
    "lastUpdated": "2026-08-14 10:20:30",
}
UNSECURED_FEED = {
    "refRates": [
        {
            "effectiveDate": "2026-09-02",
            "type": "EFFR",
            "percentRate": 3.63,
            "percentPercentile1": 3.6,
            "percentPercentile25": 3.62,
            "percentPercentile75": 3.63,
            "percentPercentile99": 3.65,
            "targetRateFrom": 3.5,
            "targetRateTo": 3.75,
            "volumeInBillions": 114,
            "revisionIndicator": "",
        },
        {
            "effectiveDate": "2026-09-02",
            "type": "OBFR",
            "percentRate": 3.63,
            "percentPercentile1": 3.55,
            "percentPercentile25": 3.62,
            "percentPercentile75": 3.63,
            "percentPercentile99": 3.69,
            "targetRateFrom": 3.5,
            "targetRateTo": 3.75,
            "volumeInBillions": 216,
            "revisionIndicator": "",
        },
    ]
}
SECURED_FEED = {
    "refRates": [
        {
            "effectiveDate": "2026-09-03",
            "type": "SOFRAI",
            "average30day": 3.64586,
            "average90day": 3.64537,
            "average180day": 3.65859,
            "index": 1.25731603,
            "revisionIndicator": "",
        },
        {
            "effectiveDate": "2026-09-02",
            "type": "TGCR",
            "percentRate": 3.63,
            "percentPercentile1": 3.56,
            "percentPercentile25": 3.63,
            "percentPercentile75": 3.63,
            "percentPercentile99": 3.67,
            "volumeInBillions": 1153,
            "revisionIndicator": "",
        },
        {
            "effectiveDate": "2026-09-02",
            "type": "BGCR",
            "percentRate": 3.63,
            "revisionIndicator": "",
        },
    ]
}
PD_FEED = {
    "pd": {
        "timeseries": [
            {"asofdate": "2024-07-03", "keyid": "PDPOSGST-TOT", "value": "312736"},
            {"asofdate": "2026-08-19", "keyid": "PDPOSGST-TOT", "value": "436406"},
        ]
    }
}


class FakeResp:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    """Records requested URLs; answers from a {path-suffix: payload} map."""

    def __init__(self, answers: dict[str, dict]):
        self.answers = answers
        self.urls: list[str] = []

    def get(self, url, params=None, timeout=None):
        self.urls.append(url)
        path = url.replace(nyfed.BASE, "")
        for suffix, payload in self.answers.items():
            if path == suffix:
                return FakeResp(payload)
        raise AssertionError(f"unexpected URL: {url}")


@pytest.fixture()
def conn(tmp_path):
    c = db.get_conn(tmp_path / "t.db", allow_init=True)
    c.executescript(SCHEMA_V9)
    yield c
    c.close()


@pytest.fixture(autouse=True)
def _clear_rate_cache():
    nyfed._latest_cache.clear()
    yield
    nyfed._latest_cache.clear()


# --- agency holdings ------------------------------------------------------------


class TestAgencyFetch:
    def test_space_enum_single_encoded(self):
        """THE transport pitfall: "agency debts" must arrive at the API as ONE
        %20 (curl_cffi double-encodes to %2520 → HTTP 400)."""
        s = FakeSession(
            {
                "/soma/agency/get/agency%20debts/asof/2026-08-26.json": {
                    "soma": {"holdings": [DEBT_ROW]}
                }
            }
        )
        rows = nyfed.fetch_agency_holdings("agency_debts", AS_OF, session=s)
        assert s.urls == [f"{nyfed.BASE}/soma/agency/get/agency%20debts/asof/{AS_OF}.json"]
        assert "%2520" not in s.urls[0]
        assert rows[0]["issuer"] == "FNMA"

    def test_mbs_row_uses_current_face_value(self):
        s = FakeSession(
            {f"/soma/agency/get/mbs/asof/{AS_OF}.json": {"soma": {"holdings": [MBS_ROW]}}}
        )
        rows = nyfed.fetch_agency_holdings("mbs", AS_OF, session=s)
        r = rows[0]
        assert r["asset_type"] == "mbs"
        assert r["current_face_value"] == pytest.approx(62_424_844_198.24)
        assert r["security_description"] == "UMBS MORTPASS 2% 10/51"
        assert r["term"] == "30yr"
        # MBS rows carry NO changeFromPriorWeek — must be None, not a fake 0.0
        assert r["change_week"] is None
        assert r["issuer"] is None

    def test_agency_debt_row_normalizes_par_value(self):
        """The agency-debts schema looks like a tsy row (parValue, not
        currentFaceValue) — it must land in the same normalized column."""
        s = FakeSession(
            {
                f"/soma/agency/get/agency%20debts/asof/{AS_OF}.json": {
                    "soma": {"holdings": [DEBT_ROW]}
                }
            }
        )
        rows = nyfed.fetch_agency_holdings("agency_debts", AS_OF, session=s)
        r = rows[0]
        assert r["current_face_value"] == 486_000_000.0
        assert r["change_week"] == 0.0
        assert r["issuer"] == "FNMA"

    def test_cmbs_empty_term_becomes_none(self):
        s = FakeSession(
            {f"/soma/agency/get/cmbs/asof/{AS_OF}.json": {"soma": {"holdings": [CMBS_ROW]}}}
        )
        rows = nyfed.fetch_agency_holdings("cmbs", AS_OF, session=s)
        assert rows[0]["term"] is None
        assert rows[0]["current_face_value"] == 124_200_000.0

    def test_unknown_asset_type_rejected(self):
        with pytest.raises(nyfed.NyFedError, match="unknown agency"):
            nyfed.fetch_agency_holdings("all", AS_OF, session=FakeSession({}))

    def test_empty_payload_refused(self):
        s = FakeSession({f"/soma/agency/get/mbs/asof/{AS_OF}.json": {"soma": {"holdings": []}}})
        with pytest.raises(nyfed.NyFedError, match="empty"):
            nyfed.fetch_agency_holdings("mbs", AS_OF, session=s)


class TestAgencySummary:
    def test_summary_sums_per_type(self):
        rows = [
            nyfed.fetch_agency_holdings(
                "mbs",
                AS_OF,
                session=FakeSession(
                    {f"/soma/agency/get/mbs/asof/{AS_OF}.json": {"soma": {"holdings": [MBS_ROW]}}}
                ),
            ),
            nyfed.fetch_agency_holdings(
                "cmbs",
                AS_OF,
                session=FakeSession(
                    {f"/soma/agency/get/cmbs/asof/{AS_OF}.json": {"soma": {"holdings": [CMBS_ROW]}}}
                ),
            ),
            nyfed.fetch_agency_holdings(
                "agency_debts",
                AS_OF,
                session=FakeSession(
                    {
                        "/soma/agency/get/agency%20debts/asof/2026-08-26.json": {
                            "soma": {"holdings": [DEBT_ROW]}
                        }
                    }
                ),
            ),
        ]
        flat = [r for chunk in rows for r in chunk]
        s = nyfed.compute_agency_summary(flat)
        assert s["mbs"] == pytest.approx(62_424_844_198.24)
        assert s["cmbs"] == pytest.approx(124_200_000.0)
        assert s["agency_debts"] == 486_000_000.0
        assert s["total"] == pytest.approx(s["mbs"] + s["cmbs"] + s["agency_debts"])
        assert s["n_cusips"] == 3


class TestAgencyStore:
    def _holdings(self):
        return [
            {
                "as_of_date": AS_OF,
                "cusip": "3132DVGB5",
                "asset_type": "mbs",
                "security_description": "UMBS MORTPASS 2% 10/51",
                "term": "30yr",
                "issuer": None,
                "current_face_value": 2e12,
                "change_week": None,
            },
            {
                "as_of_date": AS_OF,
                "cusip": "3138LM4F7",
                "asset_type": "cmbs",
                "security_description": None,
                "term": None,
                "issuer": None,
                "current_face_value": 7.42e9,
                "change_week": None,
            },
            {
                "as_of_date": AS_OF,
                "cusip": "31359MEU3",
                "asset_type": "agency_debts",
                "security_description": None,
                "term": None,
                "issuer": "FNMA",
                "current_face_value": 0.486e9,
                "change_week": 0.0,
            },
        ]

    def test_round_trip_and_idempotency(self, conn):
        summary = store_agency_week(conn, self._holdings())
        assert summary["total"] == pytest.approx(2e12 + 7.42e9 + 0.486e9)
        rows = conn.execute(
            "SELECT asset_type, current_face_value FROM soma_agency_holdings ORDER BY asset_type"
        ).fetchall()
        assert rows == [
            ("agency_debts", 0.486e9),
            ("cmbs", 7.42e9),
            ("mbs", 2e12),
        ]
        stored = conn.execute(
            "SELECT mbs, cmbs, agency_debts, total FROM soma_agency_summary"
        ).fetchone()
        assert stored[0] == pytest.approx(2e12)
        assert stored[3] == pytest.approx(summary["total"])
        # idempotent re-run: REPLACE week, no duplicates
        store_agency_week(conn, self._holdings())
        n = conn.execute("SELECT COUNT(*) FROM soma_agency_holdings").fetchone()[0]
        assert n == 3
        assert conn.execute("SELECT COUNT(*) FROM soma_agency_summary").fetchone()[0] == 1

    def test_restatement_replaces_week(self, conn):
        store_agency_week(conn, self._holdings())
        restated = [dict(self._holdings()[0], current_face_value=2.1e12)] + self._holdings()[1:]
        store_agency_week(conn, restated)
        # one mbs row only, with the corrected value — no ghost duplicate
        row = conn.execute(
            "SELECT current_face_value FROM soma_agency_holdings WHERE asset_type='mbs'"
        ).fetchone()
        assert row[0] == pytest.approx(2.1e12)
        total = conn.execute("SELECT total FROM soma_agency_summary").fetchone()[0]
        assert total == pytest.approx(2.1e12 + 7.42e9 + 0.486e9)

    def test_mixed_as_of_refused(self, conn):
        rows = self._holdings() + [dict(self._holdings()[0], as_of_date="2026-08-19")]
        with pytest.raises(nyfed.NyFedError, match="mixed"):
            store_agency_week(conn, rows)

    def test_empty_refused(self, conn):
        with pytest.raises(nyfed.NyFedError, match="empty"):
            store_agency_week(conn, [])


# --- WAM --------------------------------------------------------------------------


class TestWam:
    def test_fetch_per_type(self):
        answers = {
            f"/soma/tsy/wam/{t}/asof/{AS_OF}.json": {
                "soma": {"wam": w, "asOfDate": AS_OF, "securityTypes": []}
            }
            for t, w in (
                ("all", 8.26),
                ("bills", 0.20),
                ("notesbonds", 9.47),
                ("tips", 8.89),
                ("frn", 1.16),
            )
        }
        rows = nyfed.fetch_wam(AS_OF, session=FakeSession(answers))
        assert [r["wam_type"] for r in rows] == ["all", "bills", "notesbonds", "tips", "frn"]
        assert rows[0]["years"] == pytest.approx(8.26)

    def test_harvest_wam_persists(self, conn, monkeypatch):
        fake = [
            {"as_of_date": AS_OF, "wam_type": t, "years": w}
            for t, w in (("all", 8.26), ("bills", 0.2))
        ]
        monkeypatch.setattr(nyfed, "fetch_wam", lambda as_of, session=None: fake)
        harvest_wam(conn, AS_OF)
        rows = dict(conn.execute("SELECT wam_type, years FROM soma_wam").fetchall())
        assert rows == {"all": 8.26, "bills": 0.2}
        harvest_wam(conn, AS_OF)  # REPLACE, no duplicates
        assert conn.execute("SELECT COUNT(*) FROM soma_wam").fetchone()[0] == 2


# --- desk operations ---------------------------------------------------------------


class TestOpsParsing:
    def test_url_construction_latest_vs_last(self):
        """latest = current-day announcements window; history = results last/N
        (semantics locked by URL shape — no network here)."""
        s = FakeSession(
            {
                "/tsy/all/results/summary/last/14.json": {"treasury": {"auctions": [TSY_OP_ROW]}},
                "/tsy/all/announcements/summary/latest.json": {"treasury": {"auctions": []}},
                "/ambs/all/announcements/summary/latest.json": {"ambs": {"auctions": []}},
            }
        )
        nyfed.fetch_operations("tsy", 14, session=s)
        nyfed.fetch_announcements("tsy", session=s)
        nyfed.fetch_announcements("ambs", session=s)
        assert s.urls == [
            f"{nyfed.BASE}/tsy/all/results/summary/last/14.json",
            f"{nyfed.BASE}/tsy/all/announcements/summary/latest.json",
            f"{nyfed.BASE}/ambs/all/announcements/summary/latest.json",
        ]

    def test_parse_tsy_row(self):
        s = FakeSession(
            {"/tsy/all/results/summary/last/14.json": {"treasury": {"auctions": [TSY_OP_ROW]}}}
        )
        rows = nyfed.fetch_operations("tsy", 14, session=s)
        r = rows[0]
        assert r["operation_id"] == "OR 083126 25"  # spaces survive (PK component)
        assert r["family"] == "tsy"
        assert r["operation_date"] == "2026-08-31"
        assert r["settlement_date"] == "2026-09-01"
        assert r["direction"] == "P"
        assert r["maturity_start"] == "2026-10-01"
        assert r["maturity_end"] == "2026-12-24"
        assert r["status"] == "Results"
        assert r["amount"] == 4_243_000_000.0  # totalParAmtAccepted, raw USD
        assert json.loads(r["details_json"])["totalParAmtSubmitted"] == "39346000000"

    def test_parse_ambs_row_prefers_orig_face(self):
        s = FakeSession(
            {"/ambs/all/results/summary/last/14.json": {"ambs": {"auctions": [AMBS_OP_ROW]}}}
        )
        rows = nyfed.fetch_operations("ambs", 14, session=s)
        r = rows[0]
        # ambs par fields are "" — orig face is the par-like measure, NOT curr face
        assert r["amount"] == 130_453_820.0
        assert r["direction"] == "S"
        assert r["maturity_start"] is None  # ambs rows carry no maturity range

    def test_amount_fallback_chain(self):
        base = dict(AMBS_OP_ROW, totalAcceptedOrigFace="", operationId="OR X")
        r = nyfed._parse_operation({**base, "totalAcceptedCurrFace": "74.5"}, "ambs")
        assert r["amount"] == 74.5
        r = nyfed._parse_operation(
            {**base, "totalAcceptedCurrFace": "", "operationId": "OR Y"}, "ambs"
        )
        assert r["amount"] is None

    def test_unknown_family_rejected(self):
        with pytest.raises(nyfed.NyFedError, match="unknown operations family"):
            nyfed.fetch_operations("fxs")


class TestFedOpsStore:
    def test_round_trip_and_lifecycle_replace(self, conn):
        ann = nyfed._parse_operation(
            dict(TSY_OP_ROW, auctionStatus="Announced", totalParAmtAccepted=""), "tsy"
        )
        res = nyfed._parse_operation(TSY_OP_ROW, "tsy")
        ambs = nyfed._parse_operation(AMBS_OP_ROW, "ambs")
        # announcements first — the results row for the same id must win
        n = store_fed_operations(conn, [ann, ambs])
        assert n == 2
        store_fed_operations(conn, [res])
        rows = conn.execute(
            "SELECT operation_id, family, status, amount FROM fed_operations ORDER BY operation_id"
        ).fetchall()
        assert rows == [
            ("OR 081426 25", "ambs", "Results", 130_453_820.0),
            ("OR 083126 25", "tsy", "Results", 4_243_000_000.0),  # Announced → replaced
        ]
        # idempotent re-run of the same batch
        store_fed_operations(conn, [res, ambs])
        assert conn.execute("SELECT COUNT(*) FROM fed_operations").fetchone()[0] == 2

    def test_same_operation_id_across_families_coexist(self, conn):
        """operationId namespaces are NOT globally unique — the family leg of the
        PK keeps a tsy and an ambs operation with a colliding id apart."""
        a = nyfed._parse_operation(TSY_OP_ROW, "tsy")
        b = nyfed._parse_operation(dict(TSY_OP_ROW, operationType="Outright TBA Purchase"), "ambs")
        store_fed_operations(conn, [a, b])
        assert conn.execute("SELECT COUNT(*) FROM fed_operations").fetchone()[0] == 2


# --- fxs ---------------------------------------------------------------------------


class TestFxs:
    def test_normal_feed_empty_operations_with_counterparties(self):
        s = FakeSession(
            {
                "/fxs/all/latest.json": {"fxSwaps": {"operations": []}},
                "/fxs/list/counterparties.json": {
                    "fxSwaps": {"counterparties": ["Banco de Mexico", "Bank of Canada"]}
                },
            }
        )
        out = nyfed.fetch_fxs_latest(session=s)
        assert out["operations"] == []
        assert out["counterparties"] == ["Banco de Mexico", "Bank of Canada"]

    def test_operation_row_gets_keyed(self):
        row = {
            "operationId": "FX 0903 01",
            "operationDate": "2026-09-03",
            "operationType": "USD Swap",
            "operationDirection": "P",
            "auctionStatus": "Results",
            "totalAmtAcceptedPar": "1000000000",
        }
        s = FakeSession(
            {
                "/fxs/all/latest.json": {"fxSwaps": {"operations": [row]}},
                "/fxs/list/counterparties.json": {"fxSwaps": {"counterparties": []}},
            }
        )
        out = nyfed.fetch_fxs_latest(session=s)
        assert out["operations"][0]["family"] == "fxs"
        assert out["operations"][0]["amount"] == 1e9
        # unkeyed rows get a synthesized id rather than crashing on the PK
        row2 = dict(row, operationId="")
        s2 = FakeSession(
            {
                "/fxs/all/latest.json": {"fxSwaps": {"operations": [row2]}},
                "/fxs/list/counterparties.json": {"fxSwaps": {"counterparties": []}},
            }
        )
        assert nyfed.fetch_fxs_latest(session=s2)["operations"][0]["operation_id"]


# --- Primary Dealer survey ----------------------------------------------------------


class TestPd:
    def test_fetch_parses_native_musd(self):
        s = FakeSession({"/pd/get/SBN2024/timeseries/PDPOSGST-TOT.json": PD_FEED})
        rows = nyfed.fetch_pd_series("PDPOSGST-TOT", session=s)
        assert rows[0] == {
            "asofdate": "2024-07-03",
            "keyid": "PDPOSGST-TOT",
            "seriesbreak": "SBN2024",
            "value_musd": 312_736.0,
        }
        assert rows[-1]["value_musd"] == 436_406.0  # $436.4B — the live tail print

    def test_store_append_only_and_idempotent(self, conn):
        rows = nyfed.fetch_pd_series(
            "PDPOSGST-TOT",
            session=FakeSession({"/pd/get/SBN2024/timeseries/PDPOSGST-TOT.json": PD_FEED}),
        )
        assert store_pd_positions(conn, rows) == 2
        assert store_pd_positions(conn, rows) == 0  # full-history re-pull adds nothing
        assert conn.execute("SELECT COUNT(*) FROM pd_positions").fetchone()[0] == 2

    def test_seriesbreak_guard_first_write_wins(self, conn):
        """A future methodology break must never silently overwrite stored
        values: the PK (asofdate, keyid) makes SBN2024 win over a same-date
        SBP20xx row (z-scores may not cross breaks)."""
        rows = nyfed.fetch_pd_series(
            "PDPOSGST-TOT",
            session=FakeSession({"/pd/get/SBN2024/timeseries/PDPOSGST-TOT.json": PD_FEED}),
        )
        store_pd_positions(conn, rows)
        future = [dict(rows[0], seriesbreak="SBP2027", value_musd=999_999.0)]
        assert store_pd_positions(conn, future) == 0
        stored = conn.execute(
            "SELECT seriesbreak, value_musd FROM pd_positions WHERE asofdate=?",
            (rows[0]["asofdate"],),
        ).fetchone()
        assert stored == ("SBN2024", 312_736.0)

    def test_curated_keyids_all_sbn2024_shape(self):
        for kid in nyfed.PD_KEYIDS:
            assert kid == kid.upper() and "-" in kid
        # the financing legs the plan called for are present
        assert {"PDFTR-USTET", "PDFTR-FGM", "PDFTD-USTET"} <= set(nyfed.PD_KEYIDS)


# --- rates ----------------------------------------------------------------------------


class TestRates:
    def _patch_get(self, monkeypatch):
        calls = []

        def fake_get(path, params=None, session=None, timeout=None):
            calls.append(path)
            if path == "/rates/unsecured/all/latest.json":
                return UNSECURED_FEED
            if path == "/rates/secured/all/latest.json":
                return SECURED_FEED
            raise AssertionError(f"unexpected path {path}")

        monkeypatch.setattr(nyfed, "_get", fake_get)
        return calls

    def test_effr_volume_native_billions(self, monkeypatch):
        self._patch_get(monkeypatch)
        cur = nyfed.fetch_latest("NYFED:EFFR_VOL")
        # volumeInBillions=114 means $114B — a 1000x slip (114e9) is the bug class
        assert cur == {"ts": "2026-09-02", "value": 114}

    def test_percentiles_and_secured(self, monkeypatch):
        self._patch_get(monkeypatch)
        assert nyfed.fetch_latest("NYFED:OBFR_P99") == {"ts": "2026-09-02", "value": 3.69}
        assert nyfed.fetch_latest("NYFED:EFFR_P1") == {"ts": "2026-09-02", "value": 3.6}
        assert nyfed.fetch_latest("NYFED:TGCR") == {"ts": "2026-09-02", "value": 3.63}
        assert nyfed.fetch_latest("NYFED:BGCR") == {"ts": "2026-09-02", "value": 3.63}
        # SOFRAI = the compounded index (unregistered twin of FRED:SOFRINDEX)
        assert nyfed.fetch_latest("SOFRAI") == {
            "ts": "2026-09-03",
            "value": pytest.approx(1.25731603),
        }

    def test_memo_one_http_hit_per_endpoint(self, monkeypatch):
        calls = self._patch_get(monkeypatch)
        for sid in ("NYFED:OBFR", "NYFED:OBFR_P1", "NYFED:OBFR_P99", "NYFED:EFFR_VOL"):
            nyfed.fetch_latest(sid)
        assert calls.count("/rates/unsecured/all/latest.json") == 1

    def test_missing_type_raises(self):
        with pytest.raises(nyfed.NyFedError, match="not in feed"):
            nyfed._rate_value(UNSECURED_FEED["refRates"], "SOFR", "percentRate")

    def test_registry_yaml_declares_the_new_series(self):
        """The registry YAML (single source of truth for series) must carry every
        key the fetcher can resolve from the two 'all' feeds — except SOFRAI,
        deliberately unregistered (FRED:SOFRINDEX already carries the index)."""
        from arkwatch.config import load_registry

        reg = {e["series_id"] for e in load_registry(active_only=False)}
        for key in nyfed.UNSECURED_ALL_SERIES:
            assert f"NYFED:{key}" in reg, key
        for key in nyfed.SECURED_ALL_SERIES:
            if key == "SOFRAI":
                assert "NYFED:SOFRAI" not in reg  # one-source rule (FRED:SOFRINDEX)
            else:
                assert f"NYFED:{key}" in reg, key
        assert "FRED:SOFRINDEX" in reg
