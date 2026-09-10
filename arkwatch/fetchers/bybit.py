"""bybit.py — funding rate, open interest, and stablecoin supply.

Bybit v5 public API needs no auth for market data;
the DefiLlama stablecoins API likewise needs no auth.
"""

from __future__ import annotations

from datetime import UTC

import requests

BYBIT = "https://api.bybit.com"
LLAMA = "https://stablecoins.llama.fi"


class BybitError(RuntimeError):
    pass


def fetch_ticker(symbol: str = "BTCUSDT") -> dict:
    """fundingRate + openInterest in a single call (/v5/market/tickers)."""
    r = requests.get(
        f"{BYBIT}/v5/market/tickers",
        params={"category": "linear", "symbol": symbol},
        timeout=(10, 30),
    )
    if r.status_code != 200:
        raise BybitError(f"bybit tickers: HTTP {r.status_code}")
    j = r.json()
    if j.get("retCode") != 0:
        raise BybitError(f"bybit: {j.get('retMsg')}")
    lst = j.get("result", {}).get("list", [])
    if not lst:
        raise BybitError(f"bybit {symbol}: empty")
    t = lst[0]
    return {
        "symbol": symbol,
        "funding_rate": float(t.get("fundingRate", 0)),
        "open_interest": float(t.get("openInterest", 0)),
        "last_price": float(t.get("lastPrice", 0)),
    }


def fetch_funding_history(symbol: str = "BTCUSDT", limit: int = 200) -> list[dict]:
    """8-hour funding history — [{ts: ISO-UTC, rate: fraction}].

    Checks retCode and converts ms epochs to ISO-UTC per fetcher convention.
    """
    from datetime import datetime

    r = requests.get(
        f"{BYBIT}/v5/market/funding/history",
        params={"category": "linear", "symbol": symbol, "limit": limit},
        timeout=(10, 30),
    )
    if r.status_code != 200:
        raise BybitError(f"bybit funding: HTTP {r.status_code}")
    j = r.json()
    if j.get("retCode") != 0:
        raise BybitError(f"bybit funding: {j.get('retMsg')}")
    out = []
    for item in j.get("result", {}).get("list", []):
        ts = datetime.fromtimestamp(int(item["fundingRateTimestamp"]) / 1000, tz=UTC)
        out.append({"ts": ts.isoformat(timespec="seconds"), "rate": float(item["fundingRate"])})
    return out


def fetch_stablecoin_total() -> dict:
    """Total stablecoin circulating USD (single call, full history)."""
    r = requests.get(f"{LLAMA}/stablecoincharts/all", timeout=(10, 60))
    if r.status_code != 200:
        raise BybitError(f"llama: HTTP {r.status_code}")
    rows = r.json()
    if not rows:
        raise BybitError("llama: empty")
    latest = rows[-1]
    from datetime import datetime

    ts = datetime.fromtimestamp(int(latest["date"]), tz=UTC).date().isoformat()
    return {"ts": ts, "total_usd": float(latest.get("totalCirculating", {}).get("peggedUSD", 0))}


# --- Positioning extras (audit 2026-09-08; all public, no key) ---------------
# Bybit connectivity from this network is INTERMITTENT at the TCP level
# (verified 2026-09-08: refused for minutes, then a brief 200-window, then
# refused again — the production f2 job succeeds in some windows and lands
# NULL-on-failure in others). Every call here therefore gets one quick retry
# and callers treat any exception as "no data today" (the funding NULL
# convention), never as a sentinel.


def _v5(path: str, params: dict) -> list[dict]:
    import time

    for attempt in (1, 2):
        try:
            r = requests.get(f"{BYBIT}{path}", params=params, timeout=(8, 20))
            if r.status_code != 200:
                raise BybitError(f"bybit {path}: HTTP {r.status_code}")
            j = r.json()
            if j.get("retCode") != 0:
                raise BybitError(f"bybit {path}: {j.get('retMsg')}")
            return j.get("result", {}).get("list", [])
        except BybitError:
            raise  # an API-level answer (bad param/path) will not heal on retry
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)
    return []  # unreachable (attempt 2 re-raises); satisfies the return contract


def fetch_account_ratio(symbol: str = "BTCUSDT", period: str = "1d", limit: int = 30) -> list[dict]:
    """Daily long/buy-account SHARE — [{ts, ls_ratio}] (retail positioning).

    UNIT WARNING (review ronde-1): this is a SHARE (0..1, neutral 0.5), NOT a
    long/short ratio (neutral 1.0). The column name ls_ratio is historical.

    SHAPE CHANGE (D-020, verified live 2026-09-10): Bybit removed
    `accountLongRatio`; the endpoint now returns buyRatio/sellRatio (same
    0..1 share semantics — buy side share). buyRatio is the primary field,
    accountLongRatio kept as a fallback so either shape parses.

    Period vocabulary is 5min/15min/30min/1h/4h/1d ('D' returns an EMPTY
    list — verified live).
    """
    from datetime import datetime

    rows = _v5(
        "/v5/market/account-ratio",
        {"category": "linear", "symbol": symbol, "period": period, "limit": limit},
    )
    out = []
    for r in rows:
        raw = r.get("accountLongRatio", r.get("buyRatio"))
        if raw is None:
            continue
        ts = datetime.fromtimestamp(int(r["timestamp"]) / 1000, tz=UTC).date().isoformat()
        out.append({"ts": ts, "ls_ratio": float(raw)})
    return sorted(out, key=lambda x: x["ts"])


def fetch_taker_volume(symbol: str = "BTCUSDT", period: str = "1d", limit: int = 30) -> list[dict]:
    """RETIRED BY BYBIT (verified live 2026-09-10: HTTP 404 — path removed,
    apparently folded into account-ratio's buyRatio/sellRatio shape).

    Kept as a loud named error so the f2 leg reports the true cause once and
    can be re-pointed if Bybit revives the endpoint. bybit_positioning.
    taker_buy_ratio stays NULL until then.
    """
    raise BybitError("bybit taker-volume: retired by Bybit (404)")


def fetch_open_interest_history(symbol: str = "BTCUSDT", limit: int = 30) -> list[dict]:
    """Daily open-interest HISTORY (contracts) — [{ts, oi}].

    flows_daily.oi_* is the live snapshot; this endpoint supplies the series
    (and backfill) from the source itself. intervalTime vocabulary is
    5min/15min/30min/1h/1d/1w/1M (NOT 'D').
    """
    from datetime import datetime

    rows = _v5(
        "/v5/market/open-interest",
        {"category": "linear", "symbol": symbol, "intervalTime": "1d", "limit": limit},
    )
    out = []
    for r in rows:
        ts = datetime.fromtimestamp(int(r["timestamp"]) / 1000, tz=UTC).date().isoformat()
        out.append({"ts": ts, "oi": float(r["openInterest"])})
    return sorted(out, key=lambda x: x["ts"])
