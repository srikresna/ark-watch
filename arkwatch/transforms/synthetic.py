"""synthetic.py — synthetic XAGGBP & XAUGBP crosses.

EODHD does not list XAGGBP/XAUGBP, so they are derived from their components
in instrument_prices:
  XAGGBP = XAGUSD / GBPUSD
  XAUGBP = XAUUSD / GBPUSD
(division, not multiplication — sanity check: XAGUSD 66 / GBPUSD 1.36 gives
XAGGBP ≈ 48.5.)

Both legs use source='EODHD' and are paired on the SAME timestamp (a join),
not each leg's own latest bar, so the cross is valid for that ts.
"""

from __future__ import annotations

import sqlite3

# Metal leg (parameter) / GBPUSD leg, latest EODHD bar where the dates match.
# g.close != 0 guards against division by zero; NOT NULL on both legs.
SQL_CROSS = """
SELECT m.ts, m.close / g.close
FROM instrument_prices m
JOIN instrument_prices g
  ON  g.symbol = 'GBPUSD' AND g.ts = m.ts AND g.source = m.source
WHERE m.symbol = ? AND m.source = 'EODHD'
  AND m.close IS NOT NULL AND g.close IS NOT NULL AND g.close != 0
ORDER BY m.ts DESC
LIMIT 1
"""


def _compute_cross(conn: sqlite3.Connection, metal: str) -> dict:
    row = conn.execute(SQL_CROSS, (metal,)).fetchone()
    if row is None:
        raise LookupError(
            f"{metal}GBP: no {metal} + GBPUSD pair (source EODHD) in instrument_prices"
        )
    return {"ts": row[0], "value": float(row[1])}


def compute_xaggbp(conn: sqlite3.Connection) -> dict:
    """XAGGBP = XAGUSD / GBPUSD → {ts, value}."""
    return _compute_cross(conn, "XAGUSD")


def compute_xaugbp(conn: sqlite3.Connection) -> dict:
    """XAUGBP = XAUUSD / GBPUSD → {ts, value}."""
    return _compute_cross(conn, "XAUUSD")


def compute_all_synthetic(conn: sqlite3.Connection) -> dict:
    """Both crosses at once → {'XAGGBP': {ts, value}, 'XAUGBP': {ts, value}}."""
    return {
        "XAGGBP": compute_xaggbp(conn),
        "XAUGBP": compute_xaugbp(conn),
    }
