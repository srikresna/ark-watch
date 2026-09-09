"""yahoo.py — Yahoo chart API (primary for futures/indexes/DXY/majors/crypto).

Verified pitfalls: the LAST bar can be null (drop it); a browser UA is
required; period1=0&period2=9999999999 fetches full history in one request.
"""

from __future__ import annotations

import time

import requests

BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
}
THROTTLE_S = 0.6  # polite pacing for sweeps of ~25 symbols
_last = 0.0


class YahooError(RuntimeError):
    pass


def fetch_daily(symbol: str, *, start_ts: int = 0, end_ts: int = 9999999999) -> list[dict]:
    """Returns [{ts:YYYY-MM-DD, open, high, low, close, volume}] ascending; null bars dropped."""
    global _last
    wait = THROTTLE_S - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.monotonic()

    r = requests.get(
        f"{BASE}/{symbol}",
        params={
            "interval": "1d",
            "period1": start_ts,
            "period2": end_ts,
        },
        headers=UA,
        timeout=(10, 60),
    )
    if r.status_code != 200:
        raise YahooError(f"yahoo {symbol}: HTTP {r.status_code} — {r.text[:120]}")
    res = r.json().get("chart", {}).get("result")
    if not res:
        err = r.json().get("chart", {}).get("error", {})
        raise YahooError(f"yahoo {symbol}: {err.get('description') or 'empty response'}")
    res = res[0]
    ts = res.get("timestamp") or []
    q = (res.get("indicators", {}).get("quote") or [{}])[0]
    out = []
    import datetime as _dt

    for i, t in enumerate(ts):
        close = q.get("close", [None] * len(ts))[i]
        if close is None:  # null bar (including the live last bar) -> drop
            continue
        out.append(
            {
                "ts": _dt.datetime.fromtimestamp(t, tz=_dt.UTC).date().isoformat(),
                "open": q.get("open", [None] * len(ts))[i],
                "high": q.get("high", [None] * len(ts))[i],
                "low": q.get("low", [None] * len(ts))[i],
                "close": close,
                "volume": q.get("volume", [None] * len(ts))[i],
            }
        )
    return out
