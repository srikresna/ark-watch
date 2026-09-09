"""Tests for the CME options fetch layer (fetchers/cme.py + cme_harvest options).

No network: row parsing, date/month mapping, and expiration selection are
pure functions; the harvest path is exercised with the fetchers monkeypatched.
Schema basis: migration v8 (cme_options_settlements + cme_option_underlyings,
locked in PLAN-CME-OPTIONS §2.3). The fixture DDL is CREATE IF NOT EXISTS, so
these tests run both before and after the migration lands in db.py.

Wire-format facts pinned here (live-verified 2026-09-03, all 7 products):
numeric fields are STRINGS, openInterest carries commas ("1,205"), "" or "-"
means missing → None; the single type='' row is the contract TOTAL (strike
"Total", settle "-"), never an option and never a usable underlying settle —
the underlying anchor is joined from the futures strip in cme_settlements.
"""

from __future__ import annotations

import pytest

from arkwatch import db
from arkwatch.fetchers import cme
from arkwatch.qa import cme_harvest

# Locked v8 DDL (options-build) — no-op once the migration is in db.py
SCHEMA_V8 = """
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
"""


@pytest.fixture()
def conn(tmp_path):
    c = db.get_conn(tmp_path / "t.db", allow_init=True)
    c.executescript(SCHEMA_V8)
    yield c
    c.close()


# --- pure parsing -----------------------------------------------------------


def test_parse_option_row_types_and_commas():
    row = {
        "strike": "4260",
        "type": "Call",
        "settle": "169.60",
        "volume": "2",
        "openInterest": "1,205",
    }
    o = cme.parse_option_row(row, "2026-09-02", 192, "OG", "OGV26")
    assert o == {
        "trade_date": "2026-09-02",
        "product_id": 192,
        "product_code": "OG",
        "contract_id": "OGV26",
        "option_type": "Call",
        "strike": 4260.0,
        "settle": 169.6,
        "volume": 2,
        "open_interest": 1205,  # comma stripped
    }
    p = cme.parse_option_row(
        {**row, "type": "Put", "strike": "5.65"}, "2026-09-02", 797, "HXE", "HXV26"
    )
    assert p["option_type"] == "Put"
    assert p["strike"] == 5.65  # decimal strikes (copper "5.65", ES "7100.00")


def test_parse_option_row_missing_becomes_none_not_zero():
    # "" volume/OI and "-" settle are MISSING → None; a fictional 0 would
    # poison put/call ratios and OI walls
    o = cme.parse_option_row(
        {"strike": "1000", "type": "Call", "settle": "-", "volume": "", "openInterest": ""},
        "2026-09-02",
        192,
        "OG",
        "OGV26",
    )
    assert o["settle"] is None
    assert o["volume"] is None
    assert o["open_interest"] is None


def test_parse_option_row_rejects_total_and_junk():
    # the type='' Total row (the only non-option row in a response) must not
    # enter the strike ladder — neither as option nor as underlying settle
    total_row = {
        "strike": "Total",
        "type": "",
        "settle": "-",
        "volume": "22,978",
        "openInterest": "191,774",
    }
    assert cme.parse_option_row(total_row, "2026-09-02", 192, "OG", "OGV26") is None
    assert cme.parse_option_row({"type": "Call", "strike": "abc"}, "d", 1, "OG", "OGV26") is None


def test_iso_date():
    assert cme._iso_date("09/02/2026") == "2026-09-02"
    assert cme._iso_date("12/31/1999") == "1999-12-31"
    assert cme._iso_date("") is None
    assert cme._iso_date("not-a-date") is None


def test_mmddyyyy_from_iso():
    assert cme._mmddyyyy_from_iso("2026-09-02") == "09/02/2026"
    assert cme._mmddyyyy_from_iso("1999-12-31") == "12/31/1999"
    assert cme._mmddyyyy_from_iso("") is None


def test_futures_month_from_contract():
    # prefix length varies (OG/SO/HXE/PO/ES/NQ/BTC) → parse from the right
    assert cme.futures_month_from_contract("OGV26") == "OCT 26"
    assert cme.futures_month_from_contract("ESU26") == "SEP 26"
    assert cme.futures_month_from_contract("BTCQ26") == "AUG 26"  # Q = Aug (expired 08/28)
    assert cme.futures_month_from_contract("Z") is None  # too short
    assert cme.futures_month_from_contract("OGA26") is None  # not a month code


# --- expiration selection ----------------------------------------------------


def _exp(cid, year, month, trade_dates):
    return {
        "contractId": cid,
        "label": "x",
        "expiration": {"code": "V6", "month": month, "year": year},
        "tradeDates": [{"formatedDate": d, "reportType": "Final"} for d in trade_dates],
    }


def test_pick_expirations_six_nearest_regardless_of_wire_order():
    groups = [
        {
            "optionType": "EUR",
            "expirations": [_exp("OGX27", 2027, 11, ["09/02/2026"])],  # wrong group — ignored
        },
        {
            "optionType": "AME",
            "expirations": [
                # deliberately NOT calendar-ordered (wire is nearest-first,
                # but the ladder must not depend on it)
                _exp("OGZ26", 2026, 12, ["09/02/2026"]),
                _exp("OGV26", 2026, 10, ["09/01/2026", "09/02/2026", "08/31/2026"]),
                _exp("OGF28", 2028, 1, ["09/02/2026"]),
                _exp("OGX26", 2026, 11, ["09/02/2026"]),
                _exp("OGF27", 2027, 1, ["09/02/2026"]),
                _exp("OGG27", 2027, 2, ["09/02/2026"]),
                _exp("OGH27", 2027, 3, ["09/02/2026"]),
                _exp("OGJ27", 2027, 4, []),  # no trade dates yet → skipped
            ],
        },
    ]
    picked = cme.pick_expirations(groups, 6)
    assert [cid for cid, _ in picked] == ["OGV26", "OGX26", "OGZ26", "OGF27", "OGG27", "OGH27"]
    # latest tradeDate from the list, not the first on the wire
    assert picked[0][1] == "09/02/2026"


def test_pick_expirations_falls_back_when_no_ame_group():
    # BTC options only publish a EUR group (live-verified 2026-09-03)
    groups = [{"optionType": "EUR", "expirations": [_exp("BTCQ26", 2026, 9, ["08/28/2026"])]}]
    assert cme.pick_expirations(groups, 6) == [("BTCQ26", "08/28/2026")]
    assert cme.pick_expirations([], 6) == []
    assert cme.pick_expirations([{"optionType": "AME", "expirations": []}], 6) == []


# --- storage round-trip -------------------------------------------------------


def _sample_rows():
    td = "2026-09-02"
    raw = [
        {
            "strike": "4260",
            "type": "Call",
            "settle": "169.60",
            "volume": "2",
            "openInterest": "1,205",
        },
        {
            "strike": "4260",
            "type": "Put",
            "settle": "12.30",
            "volume": "11",
            "openInterest": "8,004",
        },
        {"strike": "4300", "type": "Call", "settle": "", "volume": "", "openInterest": ""},
        {
            "strike": "Total",
            "type": "",
            "settle": "-",
            "volume": "22,978",
            "openInterest": "191,774",
        },
    ]
    return [r for r in (cme.parse_option_row(x, td, 192, "OG", "OGV26") for x in raw) if r]


def test_save_options_roundtrip_and_idempotent(conn):
    rows = _sample_rows()
    assert len(rows) == 3  # Total row dropped
    assert cme_harvest._save_options(conn, rows) == 3
    stored = conn.execute(
        "SELECT trade_date,product_id,product_code,contract_id,option_type,strike,settle,volume,open_interest"
        " FROM cme_options_settlements ORDER BY option_type, strike"
    ).fetchall()
    assert stored == [
        ("2026-09-02", 192, "OG", "OGV26", "Call", 4260.0, 169.6, 2, 1205),
        ("2026-09-02", 192, "OG", "OGV26", "Call", 4300.0, None, None, None),
        ("2026-09-02", 192, "OG", "OGV26", "Put", 4260.0, 12.3, 11, 8004),
    ]
    # CME does not restate Final settlements → a re-run is a no-op
    assert cme_harvest._save_options(conn, rows) == 0
    assert conn.execute("SELECT COUNT(*) FROM cme_options_settlements").fetchone()[0] == 3


def test_save_underlying_joins_futures_strip(conn):
    # the options response carries NO underlying settle — the anchor comes
    # from the futures strip harvested into cme_settlements the same morning
    conn.execute(
        "INSERT INTO cme_settlements(trade_date,product_id,month,settle,volume,open_interest,fetched_at)"
        " VALUES ('2026-09-02',437,'OCT 26',4380.7,1,2,'x')"
    )
    n = cme_harvest._save_underlying(conn, 192, "OG", "OGV26", "2026-09-02")
    assert n == 1
    row = conn.execute(
        "SELECT trade_date,product_id,contract_id,settle FROM cme_option_underlyings"
    ).fetchone()
    assert row == ("2026-09-02", 192, "OGV26", 4380.7)  # product_id = the OPTIONS pid

    # no futures row for that date/month → silently skipped (degradable)
    assert cme_harvest._save_underlying(conn, 797, "HXE", "HXV26", "2026-09-02") == 0
    # the futures endpoint echoes tradeDate in EITHER '2026-09-02' or
    # '09/02/2026' form (both survive the [:10] echo truncation) — the join
    # must match both spellings (live breakage 2026-09-03: 0 underlyings)
    conn.execute("DELETE FROM cme_settlements")
    conn.execute(
        "INSERT INTO cme_settlements(trade_date,product_id,month,settle,volume,open_interest,fetched_at)"
        " VALUES ('09/02/2026',437,'OCT 26',4380.7,1,2,'x')"
    )
    assert cme_harvest._save_underlying(conn, 192, "OG", "OGV26", "2026-09-02") == 1
    # matched via the alternate spelling; REPLACE keeps exactly one row
    assert conn.execute("SELECT COUNT(*), MAX(settle) FROM cme_option_underlyings").fetchone() == (
        1,
        4380.7,
    )
    # a second futures row cannot duplicate (PK trade_date+pid+month) — settle stays
    conn.execute(
        "INSERT OR IGNORE INTO cme_settlements(trade_date,product_id,month,settle,volume,open_interest,fetched_at)"
        " VALUES ('09/02/2026',437,'OCT 26',4381.0,1,2,'x')"
    )
    cme_harvest._save_underlying(conn, 192, "OG", "OGV26", "2026-09-02")
    assert conn.execute("SELECT COUNT(*), MAX(settle) FROM cme_option_underlyings").fetchone() == (
        1,
        4380.7,
    )


# --- harvest path (fetchers monkeypatched — no network) ----------------------


def test_harvest_options_offline(conn, monkeypatch):
    monkeypatch.setattr(cme_harvest, "OPTIONS_PAUSE_S", 0)
    groups = [
        {
            "optionType": "AME",
            "expirations": [_exp("OGV26", 2026, 10, ["09/02/2026"])],
        }
    ]

    def fake_expirations(code, session=None):
        if code == "SO":
            raise cme.CmeError("blocked")
        return groups

    monkeypatch.setattr(cme, "fetch_option_expirations", fake_expirations)

    def fake_settlements(code, contract_id, td_mmdd, session=None):
        assert contract_id == "OGV26" and td_mmdd == "09/02/2026"
        rows = _sample_rows()
        return rows, cme._iso_date(td_mmdd)

    monkeypatch.setattr(cme, "fetch_option_settlements", fake_settlements)
    conn.execute(
        "INSERT INTO cme_settlements(trade_date,product_id,month,settle,volume,open_interest,fetched_at)"
        " VALUES ('2026-09-02',437,'OCT 26',4380.7,1,2,'x')"
    )

    counts = cme_harvest.harvest_options(conn, products=["OG", "SO"])
    assert counts == {"OG": 3, "SO": -1}  # one bad product does not kill the run
    assert conn.execute("SELECT COUNT(*) FROM cme_options_settlements").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM cme_option_underlyings").fetchone()[0] == 1
    # idempotent re-run: nothing new, underlying still exactly one row
    assert cme_harvest.harvest_options(conn, products=["OG"]) == {"OG": 3}
    assert conn.execute("SELECT COUNT(*) FROM cme_option_underlyings").fetchone()[0] == 1
