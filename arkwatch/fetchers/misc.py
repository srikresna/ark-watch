"""misc.py — Atlanta Fed mortgage rate, FMP holidays + recession probability, small fetchers."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import requests

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
}


def fetch_latest(series_id: str) -> dict:
    """ROUTES dispatcher (06:00 harvest): {ts, value} for the misc-owned series."""
    key = series_id.split(":", 1)[1] if ":" in series_id else series_id
    if key == "RECESSION_PROB":
        return fetch_recession_prob()
    raise RuntimeError(f"misc: unrouted series {series_id}")


def fetch_recession_prob(lookback_days: int = 200) -> dict:
    """Smoothed US recession probability (FMP economic-indicators, monthly).

    Live-verified 2026-09-04: {date: 2026-07-01, value: 0.76} — value is the
    probability on a 0-100 scale, one observation per month (publication lags
    the reference month). Window ≥180d so at least ~6 monthly points can
    return; we store only the newest.
    """
    key = os.environ.get("FMP_API_KEY", "")
    if not key:
        raise RuntimeError("FMP_API_KEY not set (env/.env)")
    to = datetime.now(UTC).date()
    fr = to - timedelta(days=lookback_days)
    r = requests.get(
        "https://financialmodelingprep.com/stable/economic-indicators",
        params={
            "name": "smoothedUSRecessionProbabilities",
            "from": fr.isoformat(),
            "to": to.isoformat(),
            "apikey": key,
        },
        timeout=(10, 30),
    )
    if r.status_code != 200:
        raise RuntimeError(f"FMP recession-prob: HTTP {r.status_code}")
    rows = [x for x in r.json() if x.get("date") and x.get("value") is not None]
    if not rows:
        raise RuntimeError("FMP recession-prob: empty response")
    newest = max(rows, key=lambda x: x["date"][:10])
    return {"ts": newest["date"][:10], "value": float(newest["value"])}


def fetch_fmp_holidays(exchange: str = "NYSE", year: int | None = None) -> list[dict]:
    """Exchange holiday calendar via FMP holidays-by-exchange.

    Used to detect CME harvest windows colliding with equity holidays.
    """
    key = os.environ.get("FMP_API_KEY", "")
    params = {"apikey": key, "exchange": exchange}
    if year:
        params["year"] = year
    r = requests.get(
        "https://financialmodelingprep.com/stable/holidays-by-exchange",
        params=params,
        timeout=(10, 30),
    )
    if r.status_code != 200:
        raise RuntimeError(f"FMP holidays: HTTP {r.status_code}")
    rows = r.json()
    if not isinstance(rows, list):
        return []
    return [
        {"date": x.get("date"), "name": x.get("name", ""), "closed": x.get("closed", True)}
        for x in rows
        if x.get("date")
    ]


def fetch_mpt_mortgage() -> dict | None:
    """Atlanta Fed Mortgage Analytics Tool (30Y fixed mortgage rate).

    Simple scrape of the public page for the latest rate.
    """
    from curl_cffi import requests as creq

    s = creq.Session(impersonate="chrome")
    r = s.get("https://www.atlantafed.org/cqer/research/mortgage-analytics", timeout=(10, 30))
    if r.status_code != 200:
        return None
    # find an "X.XX%" figure near the '30-Year Fixed Rate' label
    import re

    m = re.search(r"30[- ]Year[^%]*?(\d+\.\d+)\s*%", r.text)
    if m:
        return {"rate_30y": float(m.group(1))}
    return None
