"""cnn.py — CNN Fear & Greed Index via the stealth graphdata endpoint.

production.dataviz.cnn.io returns JSON to browser-like headers. This source
is degradable by design: it is never the sole source for a headline, and an
outage only means the F&G line disappears from the brief.
"""

from __future__ import annotations

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


def score_to_label(score: float) -> str:
    """Map a CNN Fear & Greed score to its official label (single source)."""
    for _lo, hi, label in LABELS:  # _lo kept for readability of the band table
        if score <= hi:
            return label
    return "Extreme Greed"


def fetch_fear_greed() -> dict:
    """Returns {ts, score, label, prev_close} — latest snapshot."""
    r = requests.get(URL, headers=UA, timeout=(10, 30))
    if r.status_code != 200:
        raise RuntimeError(f"CNN F&G: HTTP {r.status_code}")
    j = r.json()
    fd = j.get("fear_and_greed", {})
    score = fd.get("score") or fd.get("rating_num")
    if score is None:
        raise RuntimeError("CNN F&G: score not found in response")
    score = round(float(score), 1)
    label = next((lb for lo, hi, lb in LABELS if lo <= score <= hi), "?")
    ts = (fd.get("report_date") or j.get("updated_at") or "")[:10]
    return {"ts": ts, "score": score, "label": label, "prev_close": fd.get("previous_close")}
