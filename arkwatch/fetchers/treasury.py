"""treasury.py — official par yield curve via per-year XML.

Verified fields: BC_1MONTH, BC_1_5MONTH (1.5 MONTHS, not 1.5 years),
BC_2/3/4/6MONTH, BC_1/2/3/5/7/10/20/30YEAR — there is no 4YEAR field.
Depth/backfill is done by looping years; v0 verification covers the latest
value only.
"""

from __future__ import annotations

import re
from datetime import datetime

import requests

URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"

# series_id (without prefix) -> XML field
TENOR_MAP = {
    "PAR_1_5Y": "BC_1_5MONTH",  # 1.5 MONTHS despite the series_id name
    "PAR_7Y": "BC_7YEAR",
    "PAR_20Y": "BC_20YEAR",
}


class TreasuryError(RuntimeError):
    pass


def _entries(year: int) -> list[dict]:
    r = requests.get(
        URL,
        params={
            "data": "daily_treasury_yield_curve",
            "field_tdr_date_value": str(year),
        },
        timeout=(10, 30),
    )
    if r.status_code != 200:
        raise TreasuryError(f"treasury xml {year}: HTTP {r.status_code}")
    out = []
    for m in re.finditer(r"<entry>(.*?)</entry>", r.text, re.S):
        body = m.group(1)
        dm = re.search(r"<d:NEW_DATE[^>]*>([^<]+)</d:NEW_DATE>", body)
        if not dm:
            continue
        row = {"ts": dm.group(1)[:10]}
        for f in re.finditer(r"<d:(BC_\w+)[^>]*>([^<]*)</d:\1>", body):
            if f.group(2).strip():
                row[f.group(1)] = float(f.group(2))
        out.append(row)
    return out


def fetch_latest(series_id: str) -> dict:
    key = series_id.split(":", 1)[1] if ":" in series_id else series_id
    field = TENOR_MAP.get(key)
    if field is None:
        raise TreasuryError(f"unknown tenor: {key}")
    rows = _entries(datetime.utcnow().year)
    rows = [r for r in rows if field in r]
    if not rows:
        raise TreasuryError(f"treasury: no rows with {field} this year")
    r0 = max(rows, key=lambda r: r["ts"])
    return {"ts": r0["ts"], "value": r0[field]}
