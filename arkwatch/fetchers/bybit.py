"""bybit.py — stablecoin supply (DefiLlama).

RETIRED 2026-09-16 (owner decision): Bybit is unreachable from both the PC
(TCP-intermittent, D-020) and the server (Indonesian ISP DNS/SNI block);
Coinglass aggregator is paid. The funding/OI/positioning legs served one
brief line + one alert at 22% fill rate — not worth the complexity.

The stablecoin total (DefiLlama) STAYS: it is a different provider, works
from any network, and feeds the "Stablecoin $XXB" brief line daily.
The module keeps its historical name to avoid churn in imports; it now
contains only the DefiLlama fetcher.
"""

from __future__ import annotations

import requests

LLAMA = "https://stablecoins.llama.fi"


def fetch_stablecoin_total() -> dict:
    """Total stablecoin circulating USD (single call, full history)."""
    r = requests.get(f"{LLAMA}/stablecoincharts/all", timeout=(10, 60))
    if r.status_code != 200:
        raise RuntimeError(f"llama: HTTP {r.status_code}")
    rows = r.json()
    if not rows:
        raise RuntimeError("llama: empty response")
    latest = rows[-1]
    raw = latest.get("totalCirculatingUSD")
    if isinstance(raw, dict):
        # 2026-09-17 schema change — ROUND-2 CORRECTION: the old scalar
        # carried ONLY the USD-pegged total (live evidence:
        # totalCirculating.peggedUSD 309,298,108,635.74 == the stored 09-16
        # scalar to the cent). Summing ALL pegs silently changed the series
        # DEFINITION mid-stream (a level jump on the brief line). Keep the
        # definition: peggedUSD first, chained fallbacks after.
        v = raw.get("peggedUSD")
        if v is None:
            v = (latest.get("totalCirculating") or {}).get("peggedUSD")
        if v is None:
            v = sum(x for x in raw.values() if isinstance(x, (int, float)))
        raw = v
    raw_date = latest.get("date")
    ts = str(raw_date or "")[:10]
    if len(ts) == 10 and ts.isdigit():
        # same schema change: `date` became an epoch (int or numeric string —
        # live it arrives as a string). str()[:10] fed the stale gate
        # "1789603200", which lexically sorts BEFORE every ISO date and
        # fails the gate forever. Convert to ISO like the old shape.
        from datetime import UTC, datetime

        ts = datetime.fromtimestamp(int(ts), tz=UTC).date().isoformat()
    return {"ts": ts, "total_usd": float(raw)}
