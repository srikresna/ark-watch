"""eodhd.py — EODHD fetchers (funding-stress, CMDI, CDS, policy rates).

Verified pitfalls:
  - `code=`/`central_bank=` params are IGNORED by the server (the response
    contains all codes) -> filter client-side
  - key via env EODHD_API_TOKEN; the auth param MUST be `api_token=` (not api_key)
  - browser UA required (some plain clients are rejected)
  - CDS_US is annual Damodaran data in FRACTIONS (x10^4 = bps)
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

    if key == "POLICY_BOE":
        rows = [r for r in _get("/rates/policy-rates") if r.get("central_bank") == "BOE"]
        if not rows:
            raise EodhdError("policy-rates: no BOE rows")
        bank = [r for r in rows if "BANK" in (r.get("code") or "").upper()]
        r0 = max(bank or rows, key=lambda r: r["date"])
        return {"ts": r0["date"], "value": float(r0["rate"])}

    raise EodhdError(f"unknown EODHD series: {key}")
