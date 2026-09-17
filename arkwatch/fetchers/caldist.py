"""caldist.py — calendar-derived series: events.actual → raw_observations.

No HTTP: the source is the events table itself. A CAL: series names an
indicator_key family (the post-alias canonical key); the fetcher maps each
release to its REFERENCE month and lands ONE level observation per month.
Twins of the same release dedup via MAX(actual) per (key, month) — the same
deterministic convention compute_sigma uses (duplicate rows carry identical
actuals after the sibling-heal).

Reference-month derivation (verified live 2026-09-17 on the ISM families):
the month token embedded in normalized_name ('... PMI AUG', released
2026-09-01 → 2026-08-01) wins; a token-less row falls back to the family's
release convention (ISM reports land on the 1st-3rd business day of month M
for reference month M−1). Token-vs-release cross-checks agreed on every
sampled row.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"

# series_id suffix → (indicator_key family, release convention)
FAMILIES = {
    "ISM_MFG_PMI": ("ISM MANUFACTURING PMI", "m_minus_1"),
    "ISM_SVC_PMI": ("ISM SERVICES PMI", "m_minus_1"),
    "ISM_MFG_PRICES": ("ISM MANUFACTURING PRICES", "m_minus_1"),
    "ISM_SVC_PRICES": ("ISM SERVICES PRICES", "m_minus_1"),
    "ISM_MFG_EMPLOYMENT": ("ISM MANUFACTURING EMPLOYMENT", "m_minus_1"),
    "ISM_MFG_NEW_ORDERS": ("ISM MANUFACTURING NEW ORDERS", "m_minus_1"),
}

_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
_TOKEN = re.compile(r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(?:\s+\d{1,2})?\s*$")


class CalDistError(RuntimeError):
    pass


def _ref_month(name_norm: str, ts_utc: str, convention: str) -> tuple[int, int] | None:
    """(year, month) of the REFERENCE period for one release row."""
    y, mon = int(ts_utc[:4]), int(ts_utc[5:7])
    m = _TOKEN.search(name_norm)
    if m:
        mm = _MONTHS[m.group(1)]
        # the token may belong to the release year or the previous one
        # (a Jan release references Dec of the prior year)
        return (y, mm) if mm <= mon else (y - 1, mm)
    if convention == "m_minus_1":
        return (y - 1, 12) if mon == 1 else (y, mon - 1)
    return (y, mon)


def family_rows(indicator_key: str, convention: str = "m_minus_1",
                db_path: str | Path = DEFAULT_DB) -> list[dict]:
    """All months of a family, deduped: [{ts, value}] ascending."""
    conn = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT normalized_name, substr(ts_utc,1,10) d, actual FROM events"
            " WHERE indicator_key=? AND actual IS NOT NULL AND consensus IS NOT NULL"
            " ORDER BY ts_utc",
            (indicator_key,),
        ).fetchall()
    finally:
        conn.close()
    by_month: dict[tuple[int, int], float] = {}
    for name_norm, d, actual in rows:
        rm = _ref_month(name_norm, d, convention)
        if rm is None or actual is None:
            continue
        # MAX = deterministic twin dedup (identical after sibling-heal; MAX
        # only arbitrates if a stale twin somehow differs)
        cur = by_month.get(rm)
        if cur is None or float(actual) > cur:
            by_month[rm] = float(actual)
    return [
        {"ts": f"{y:04d}-{m:02d}-01", "value": v}
        for (y, m), v in sorted(by_month.items())
    ]


def fetch_latest(series_id: str) -> dict:
    fam = FAMILIES.get(series_id.split(":", 1)[1] if ":" in series_id else series_id)
    if fam is None:
        raise CalDistError(f"caldist: unrouted series {series_id}")
    key, convention = fam
    rows = family_rows(key, convention)
    if not rows:
        raise CalDistError(f"caldist: no actuals for family {key}")
    return rows[-1]


def fetch_window(series_id: str, days: int = 10) -> list[dict]:
    """Points inside the trailing window (the harvest's gap-heal contract)."""
    from datetime import UTC, datetime, timedelta

    cutoff = (datetime.now(UTC).date() - timedelta(days=days)).isoformat()
    fam = FAMILIES.get(series_id.split(":", 1)[1] if ":" in series_id else series_id)
    if fam is None:
        raise CalDistError(f"caldist: unrouted series {series_id}")
    return [p for p in family_rows(*fam) if p["ts"] >= cutoff]
