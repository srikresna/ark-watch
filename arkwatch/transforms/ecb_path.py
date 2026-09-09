"""ecb_path.py — ECB expectations (implied path) from ESR €STR settlements.

ESR €STR is CME product 10247 (~5-day settlement retention). Implied rate
= 100 - settle (settle = the month's average €STR) — the ECB counterpart
of fedwatch.py's DIY path. Returns [{contract, imm, days, implied_pct}]
for the nearest contracts ordered by start date.
"""

from __future__ import annotations

import sqlite3
from datetime import date

ESR_PID = 10247


def _imm_approx(contract_month: str) -> date | None:
    # Delegate to the single canonical definition in xccy (third Monday,
    # 2-digit-year guard) — a local copy would drift from it.
    from .xccy import _imm_approx as _imm

    return _imm(contract_month)


def compute_ecb_path(conn: sqlite3.Connection) -> list[dict]:
    """Implied €STR path across the nearest ESR contracts (quarterly, ≥30 days)."""
    td = conn.execute(
        "SELECT MAX(trade_date) FROM cme_settlements WHERE product_id=?", (ESR_PID,)
    ).fetchone()[0]
    if not td:
        return []
    rows = conn.execute(
        "SELECT month, settle FROM cme_settlements "
        "WHERE product_id=? AND trade_date=? AND settle IS NOT NULL",
        (ESR_PID, td),
    ).fetchall()
    out = []
    for month, settle in rows:
        # Quarterly contracts only: monthly ESR contracts are thin, and their
        # settlements print a spurious zigzag in the implied path.
        if month.strip().upper().split()[0] not in ("MAR", "JUN", "SEP", "DEC"):
            continue
        imm = _imm_approx(month)
        if imm is None:
            continue
        days = (imm - date.today()).days
        if days < 30:
            continue
        out.append(
            {
                "contract": month.title(),
                "imm": imm.isoformat(),
                "days": days,
                "implied_pct": round(100.0 - settle, 3),
            }
        )
    out.sort(key=lambda r: r["days"])
    return out


def format_brief(rows: list[dict], ref_pct: float | None = None) -> str:
    """'ECB path: Dec26 −4bp · Mar27 +8bp' (delta vs the current €STR reference)."""
    if not rows:
        return "ECB path: N/A"
    parts = []
    for r in rows[:3]:
        if ref_pct is not None:
            d = (r["implied_pct"] - ref_pct) * 100
            parts.append(f"{r['contract'][:3]}{r['contract'][-2:]} {d:+.0f}bp")
        else:
            parts.append(f"{r['contract'][:3]}{r['contract'][-2:]} {r['implied_pct']:.2f}%")
    return "ECB path: " + " · ".join(parts)
