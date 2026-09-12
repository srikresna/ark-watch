"""eodhd.py — EODHD fetchers (funding-stress, CMDI, CDS, UST curves, sentiments).

Verified pitfalls:
  - `code=`/`central_bank=` params are IGNORED by the server (the response
    contains all codes) -> filter client-side
  - key via env EODHD_API_TOKEN; the auth param MUST be `api_token=` (not api_key)
  - browser UA required (some plain clients are rejected)
  - CDS_US is annual Damodaran data in FRACTIONS (x10^4 = bps)
  - /ust/* returns {meta, data, links} with data = flat [{date, tenor, rate}]
    rows for ALL tenors (window params are advisory — filter client-side)
  - /api/sentiments is NEWS-based and SPARSE (a few points per month for
    btc-usd.cc), scale −1..+1 — every display carries its date
  - policy-rates RETIRED 2026-09-13 (vendor-api audit): the endpoint hosts
    FED+ECB only and the BoE branch never had rows; FRED:DFF + the ECB Data
    Portal cover both free, so the branch is deleted, not dormant
"""

from __future__ import annotations

import os

import requests

BASE = "https://eodhd.com/api"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
}


class EodhdError(RuntimeError):
    pass


def _token() -> str:
    t = os.environ.get("EODHD_API_TOKEN", "")
    if not t:
        raise EodhdError("EODHD_API_TOKEN not set (env/.env)")
    return t


def _get(path: str, params: dict | None = None) -> dict:
    p = {"api_token": _token(), "fmt": "json"}
    p.update(params or {})
    r = requests.get(f"{BASE}{path}", params=p, headers=UA, timeout=(10, 30))
    if r.status_code != 200:
        raise EodhdError(f"EODHD {path}: HTTP {r.status_code} — {r.text[:200]}")
    j = r.json()
    if not isinstance(j, dict) or "data" not in j:
        raise EodhdError(f"EODHD {path}: unrecognized response shape")
    return j["data"]


def fetch_ust_real_yields(tenor: str, days: int = 10) -> list[dict]:
    """Daily TIPS real yields (5Y/7Y/10Y/20Y/30Y) — the block-B secondary
    leg the registry has promised all along. [{ts, value}] ascending."""
    rows = [r for r in _get("/ust/real-yield-rates") if r.get("tenor") == tenor]
    if not rows:
        raise EodhdError(f"ust/real-yield: tenor {tenor} missing")
    rows.sort(key=lambda r: r["date"])
    return [{"ts": r["date"], "value": float(r["rate"])} for r in rows[-days:]]


def fetch_ust_nominal(tenor: str, days: int = 10) -> list[dict]:
    """Daily nominal UST curve (1M..30Y) — crossval leg for FRED:DGS*."""
    rows = [r for r in _get("/ust/yield-rates") if r.get("tenor") == tenor]
    if not rows:
        raise EodhdError(f"ust/yield: tenor {tenor} missing")
    rows.sort(key=lambda r: r["date"])
    return [{"ts": r["date"], "value": float(r["rate"])} for r in rows[-days:]]


def fetch_sentiments(tickers: str = "btc-usd.cc,eth-usd.cc") -> dict[str, list[dict]]:
    """News-based sentiment per ticker, scale −1..+1 (sparse). One call
    carries all tickers. {'BTC-USD.CC': [{ts, value, count}]} descending by
    the API's own ordering (latest first per ticker in practice; we sort)."""
    p = {"api_token": _token(), "fmt": "json", "s": tickers}
    r = requests.get(f"{BASE}/sentiments", params=p, headers=UA, timeout=(10, 30))
    if r.status_code != 200:
        raise EodhdError(f"sentiments: HTTP {r.status_code}")
    j = r.json()
    if not isinstance(j, dict):
        raise EodhdError("sentiments: unrecognized response shape")
    out = {}
    for tick, rows in j.items():
        pts = [{"ts": x["date"], "value": float(x["normalized"]), "count": x.get("count", 0)}
               for x in rows if isinstance(x, dict) and x.get("normalized") is not None]
        pts.sort(key=lambda x: x["ts"])
        out[tick.upper()] = pts
    return out


def fetch_latest(series_id: str) -> dict:
    """Takes a series_id without prefix (e.g. FS_EFFR_SOFR). Returns {ts, value}."""
    key = series_id.split(":", 1)[1] if ":" in series_id else series_id

    if key.startswith("FS_"):
        code = key[3:]
        rows = [r for r in _get("/spreads/funding-stress") if r.get("code") == code]
        if not rows:
            raise EodhdError(f"funding-stress: code {code} missing from response")
        r0 = max(rows, key=lambda r: r["date"])
        return {"ts": r0["date"], "value": float(r0["value_bps"])}

    if key == "CMDI":
        rows = _get("/credit-risk/corporate/cmdi")
        r0 = max(rows, key=lambda r: r["as_of_date"][:10])
        return {"ts": r0["as_of_date"][:10], "value": float(r0["market_cmdi"])}

    if key == "CDS_US":
        rows = [
            r
            for r in _get("/credit-risk/sovereign/cds-spreads", {"filter[country]": "USA"})
            if r.get("country_iso3") == "USA"
        ]
        if not rows:
            raise EodhdError("cds-spreads: no USA rows")
        r0 = max(rows, key=lambda r: r["as_of_date"][:10])
        return {"ts": r0["as_of_date"][:10], "value": float(r0["cds_spread"])}

    if key.startswith("USTR"):
        # USTR10 / USTR5 → TIPS real yield (block-B secondary)
        tenor = key[4:]
        if not tenor.endswith("Y"):
            tenor += "Y"
        rows = fetch_ust_real_yields(tenor, days=5)
        return rows[-1]

    if key.startswith("SENT_"):
        tick = {"BTC": "BTC-USD", "ETH": "ETH-USD"}.get(key[5:])
        if not tick:
            raise EodhdError(f"sentiments: unknown ticker {key}")
        data = fetch_sentiments()
        pts = next((v for k, v in data.items() if k.startswith(tick)), None)
        if not pts:
            raise EodhdError(f"sentiments: no points for {tick}")
        return {"ts": pts[-1]["ts"], "value": pts[-1]["value"]}

    raise EodhdError(f"unknown EODHD series: {key}")
