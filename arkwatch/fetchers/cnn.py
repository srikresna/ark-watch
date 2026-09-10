"""cnn.py — CNN Fear & Greed Index via the stealth graphdata endpoint.

production.dataviz.cnn.io returns JSON to browser-like headers. This source
is degradable by design: it is never the sole source for a headline, and an
outage only means the F&G line disappears from the brief.

One daily payload carries far more than the composite score:
- 7 official indicator components (momentum, strength, breadth, put/call,
  VIX, junk-bond demand, safe-haven) each with a 0-100 score + rating — the
  composite hides cross-asset divergence (e.g. equity "extreme fear" while
  credit reads "greed"), which is exactly the read that matters
- previous_close / 1w / 1m / 1y — sentiment momentum without stored history
- 250-day history for the composite AND each component — free backfill in
  the same fetch (the put/call series replaces the retired CBOE P/C, D-017)
"""

from __future__ import annotations

from datetime import UTC, datetime

import requests

URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://edition.cnn.com",
    "Referer": "https://edition.cnn.com/",
}

# official CNN score -> label bands
LABELS = [
    (0, 24, "Extreme Fear"),
    (25, 44, "Fear"),
    (45, 55, "Neutral"),
    (56, 74, "Greed"),
    (75, 100, "Extreme Greed"),
]

# the 7 indicators CNN averages into the composite (plus two extra series the
# payload carries: SP125 momentum and VIX-50d-MA — stored for cross-checks)
COMPONENTS = (
    "market_momentum_sp500",
    "stock_price_strength",
    "stock_price_breadth",
    "put_call_options",
    "market_volatility_vix",
    "market_volatility_vix_50",
    "junk_bond_demand",
    "safe_haven_demand",
    "market_momentum_sp125",
)

# component history series worth persisting as raw daily values
RAW_HISTORY = ("put_call_options", "market_volatility_vix")


def score_to_label(score: float) -> str:
    """Map a CNN Fear & Greed score to its official label (single source)."""
    for _lo, hi, label in LABELS:  # _lo kept for readability of the band table
        if score <= hi:
            return label
    return "Extreme Greed"


def _ms_to_date(ms: float) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).date().isoformat()


def fetch_fear_greed() -> dict:
    """Composite snapshot + component scores + momentum + 250d histories.

    The report timestamp lives at fd['timestamp'] (ISO 8601) — NOT
    'report_date'/'updated_at', which never existed in this payload (the
    dead-key bug that stored the F&G row under the RUN date instead of the
    report date).
    """
    r = requests.get(URL, headers=UA, timeout=(10, 30))
    if r.status_code != 200:
        raise RuntimeError(f"CNN F&G: HTTP {r.status_code}")
    j = r.json()
    fd = j.get("fear_and_greed", {})
    score = fd.get("score") or fd.get("rating_num")
    if score is None:
        raise RuntimeError("CNN F&G: score not found in response")
    score = round(float(score), 1)
    ts = str(fd.get("timestamp") or "")[:10]
    components = {}
    for name in COMPONENTS:
        c = j.get(name) or {}
        if c.get("score") is None:
            continue
        data = c.get("data") or []
        components[name] = {
            "score": round(float(c["score"]), 1),
            "rating": c.get("rating"),
            "raw": data[-1].get("y") if data else None,
        }
    history = {
        "cnn_fg": [
            {"ts": _ms_to_date(p["x"]), "value": round(float(p["y"]), 1)}
            for p in (j.get("fear_and_greed_historical", {}) or {}).get("data", [])
            if isinstance(p, dict) and p.get("y") is not None
        ]
    }
    for name in RAW_HISTORY:
        pts = (j.get(name) or {}).get("data", [])
        history[f"cnn_{name}"] = [
            {"ts": _ms_to_date(p["x"]), "value": round(float(p["y"]), 4)}
            for p in pts
            if isinstance(p, dict) and p.get("y") is not None
        ]
    return {
        "ts": ts,
        "score": score,
        "label": score_to_label(score),
        "rating": fd.get("rating"),
        "prev_close": fd.get("previous_close"),
        "prev_1w": fd.get("previous_1_week"),
        "prev_1m": fd.get("previous_1_month"),
        "prev_1y": fd.get("previous_1_year"),
        "components": components,
        "history": history,
    }
