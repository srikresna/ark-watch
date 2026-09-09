"""atl.py — Wage Growth Tracker (Atlanta Fed CHCS, XLSX).

URL verified against the official Atlanta Fed page (see the URL constant).
The workbook is multi-sheet (~19 sheets); the headline series is the
unweighted median.
"""

from __future__ import annotations

import io
from datetime import datetime

import requests
from openpyxl import load_workbook

URL = (
    "https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/"
    "datafiles/chcs/wage-growth-tracker/wage-growth-data.xlsx"
)
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
}


class AtlError(RuntimeError):
    pass


def _pick_sheet(wb) -> str:
    # Actual sheet names: data_overview, data_chart1..3, WGT_1983, RG_...
    # headline = data_overview (unweighted median); fall back to chart1,
    # then to the first data_* sheet.
    names = wb.sheetnames
    for cand in ("data_overview", "data_chart1"):
        if cand in names:
            return cand
    data_sheets = [n for n in names if str(n).lower().startswith("data")]
    if data_sheets:
        return data_sheets[0]
    raise AtlError(f"atl WGT: data-* sheet not found (available: {names[:8]})")


def fetch_latest(series_id: str = "ATL:WGT") -> dict:
    r = requests.get(URL, headers=UA, timeout=(10, 60))
    if r.status_code != 200 or r.content[:2] != b"PK":
        raise AtlError(f"atl WGT: HTTP {r.status_code} / not XLSX")
    wb = load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    ws = wb[_pick_sheet(wb)]
    rows = list(ws.iter_rows(values_only=True))
    header_i = next(
        (
            i
            for i, row in enumerate(rows[:5])
            if row and any(isinstance(c, str) and "date" in c.lower() for c in row)
        ),
        None,
    )
    if header_i is None:
        raise AtlError("atl WGT: 'date' header not found")
    header = [str(c).lower() if c else "" for c in rows[header_i]]
    di = next(i for i, c in enumerate(header) if "date" in c)
    last = None
    for row in rows[header_i + 1 :]:
        if row and row[di] is not None:
            for c in row[di + 1 :]:
                if isinstance(c, (int, float)):
                    last = (row[di], float(c))
                    break
    if last is None:
        raise AtlError("atl WGT: no value rows")
    d, v = last
    if isinstance(d, datetime):
        d = d.date().isoformat()
    return {"ts": str(d)[:10], "value": v}
