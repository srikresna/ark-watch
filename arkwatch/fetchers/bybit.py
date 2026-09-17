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
        # 2026-09-17: the field became a per-peg breakdown
        # {"peggedUSD": N, "peggedEUR": N, ...} — float(dict) crashed the
        # harvest. The total is the sum across pegs (same definition the
        # old scalar carried).
        raw = sum(v for v in raw.values() if isinstance(v, (int, float)))
    return {"ts": str(latest.get("date", ""))[:10], "total_usd": float(raw)}
