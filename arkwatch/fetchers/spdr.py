"""spdr.py — daily GLD holdings plus SLV via FMP shares-float."""

from __future__ import annotations

import io
import os
from datetime import UTC, datetime

import requests
from curl_cffi import requests as creq

GLD_URL = "https://api.spdrgoldshares.com/api/v1/historical-archive"
FMP_URL = "https://financialmodelingprep.com/stable"


def _fetch_shares_fmp(symbol: str) -> int | None:
    """Shares outstanding via the FMP shares-float endpoint; None on failure."""
    key = os.environ.get("FMP_API_KEY", "")
    if not key:
        return None
    try:
        r = requests.get(
            f"{FMP_URL}/shares-float", params={"symbol": symbol, "apikey": key}, timeout=(10, 30)
        )
        j = r.json()
        if isinstance(j, list) and j and j[0].get("outstandingShares"):
            return int(j[0]["outstandingShares"])
    except Exception:
        pass
    return None


def fetch_gld_tonnes() -> dict:
    """GLD holdings from sheet 'US GLD Historical Archive', column 'Ounces of Gold
    per Share' (sheet 1 is a Disclaimer, sheet 2 is the data).

    Total tonnes = shares_outstanding x oz_per_share / 32,150.7466.
    The share count must be fetched live: ETF creations/redemptions change
    it, so a hardcoded value would structurally freeze the flow signal
    (delta tonnes would never reflect flows). Falls back to 291M with
    approx=True when the live count is unavailable.
    """
    from openpyxl import load_workbook

    from ..units import oz_to_tonnes

    s = creq.Session(impersonate="chrome")
    r = s.get(
        GLD_URL, params={"product": "gld", "exchange": "NYSE", "lang": "en"}, timeout=(10, 60)
    )
    if r.status_code != 200 or r.content[:2] != b"PK":
        raise RuntimeError(f"GLD: HTTP {r.status_code} / not XLSX")
    wb = load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
    # data lives in the "Historical" sheet; the first sheet is a Disclaimer
    sheet_name = [sn for sn in wb.sheetnames if "Historical" in sn]
    if not sheet_name:
        raise RuntimeError(f"GLD: Historical sheet not found in {wb.sheetnames}")
    ws = wb[sheet_name[0]]
    rows = list(ws.iter_rows(values_only=True))
    # header = row 0; columns: [Date, Closing Price, Ounces per Share, NAV, ...]
    last = None
    for row in reversed(rows):
        if row and len(row) >= 3 and isinstance(row[2], (int, float)):
            last = row
            break
    if last is None:
        raise RuntimeError("GLD: no numeric data rows")
    date_str = str(last[0]) if last[0] else ""
    oz_per_share = float(last[2])

    shares = _fetch_shares_fmp("GLD")
    approx = shares is None
    if approx:
        shares = 291_000_000  # fallback constant; only ever used with approx=True
    tonnes = oz_to_tonnes(oz_per_share * shares)
    return {
        "ts": date_str,
        "oz_per_share": oz_per_share,
        "tonnes_approx": round(tonnes, 1),
        "shares_assumed_m": shares / 1e6,
        "approx": approx,  # True = fallback share count (renderers must mark "(approx)")
    }


def fetch_slv_shares() -> dict:
    """SLV outstanding shares via FMP (weekly cadence is enough — sourced from SEC 10-Q filings)."""
    key = os.environ.get("FMP_API_KEY", "")
    r = requests.get(
        f"{FMP_URL}/shares-float", params={"symbol": "SLV", "apikey": key}, timeout=(10, 30)
    )
    if r.status_code != 200:
        raise RuntimeError(f"SLV: HTTP {r.status_code}")
    j = r.json()
    if isinstance(j, list) and j:
        shares = j[0].get("outstandingShares")
        if shares:
            return {"ts": datetime.now(UTC).date().isoformat(), "shares": int(shares)}
    raise RuntimeError("SLV: outstandingShares missing")
