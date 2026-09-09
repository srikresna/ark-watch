"""cboe.py — CBOE index history CSVs from the official CDN (no key needed).

REVIVED 2026-09-08 (audit sumber): the old /resources/options/... put/call
CSVs are frozen at 2019-10-04 (D-017) and the legacy /data/volatility path
403s — but the us_indices daily_prices path is ALIVE and current:

  https://cdn.cboe.com/api/global/us_indices/daily_prices/{SYM}_History.csv

Two header shapes (live-verified 2026-09-08, all rows through 09/04/2026):
  OHLC  : DATE,OPEN,HIGH,LOW,CLOSE   (VIX, VIX9D, VIX6M, VXN, RVX)
  single: DATE,{SYM}                  (VXV, OVX, GVZ)
Dates are M/D/YYYY; we store the CLOSE (the level FRED also carries).

Put/call stays RETIRED (D-017); equity P/C sentiment = CME options PCR.
"""

from __future__ import annotations

import csv
import io
from datetime import date

import requests

BASE = "https://cdn.cboe.com/api/global/us_indices/daily_prices"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
}

# sid suffix -> CDN symbol (the _History.csv stem). Dict order = display order.
HISTORY_FILES = {
    "VIX9D": "VIX9D",
    "VIX6M": "VIX6M",
}


class CboeError(RuntimeError):
    pass


def fetch_history_rows(symbol: str) -> list[dict]:
    """Full history [{ts, close}] for one CDN symbol (ascending, as served)."""
    r = requests.get(f"{BASE}/{symbol}_History.csv", headers=UA, timeout=(10, 60))
    if r.status_code != 200 or not r.text.lstrip().startswith("DATE"):
        raise CboeError(f"cboe {symbol}: HTTP {r.status_code} / not CSV")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    out = []
    for row in rows:
        d = (row.get("DATE") or "").strip()
        if not d:
            continue
        try:
            m, day, y = d.split("/")
            ts = f"{int(y):04d}-{int(m):02d}-{int(day):02d}"
            # reject non-calendar strings ('13/45/2026') — they would sort
            # lexicographically AFTER real dates and poison the max-scan
            date.fromisoformat(ts)
        except ValueError:
            continue
        close = row.get("CLOSE") or row.get(symbol)
        if close in (None, "", "0"):  # '0' appears on stale placeholder rows
            continue
        try:
            out.append({"ts": ts, "value": float(close)})
        except ValueError:
            continue
    if not out:
        raise CboeError(f"cboe {symbol}: no parseable rows")
    return out


def fetch_latest(series_id: str) -> dict:
    key = series_id.split(":", 1)[1] if ":" in series_id else series_id
    if key not in HISTORY_FILES:
        raise CboeError(
            f"CBOE series unknown/unrouted: {key} (put/call retired 2026-09-04, D-017; "
            "equity P/C sentiment = CME options PCR)"
        )
    # newest by ts scan, never rows[-1] (sortedness not a contract)
    return max(fetch_history_rows(HISTORY_FILES[key]), key=lambda x: x["ts"])


def fetch_first_ts(series_id: str) -> str:
    """Depth-gate helper: earliest ts of the symbol's history."""
    key = series_id.split(":", 1)[1] if ":" in series_id else series_id
    if key not in HISTORY_FILES:
        raise CboeError(f"CBOE series unknown/unrouted: {key}")
    return min(r["ts"] for r in fetch_history_rows(HISTORY_FILES[key]))
