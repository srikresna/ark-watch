"""energy.py — daily curve signals: WTI backwardation, cracks, Brent-WTI spot spread."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from .. import db

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"

MONTH_CODES = "FGHJKMNQUVXZ"
MONTH_NAMES = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _front_month() -> tuple[int, int]:
    from ..fetchers import yahoo

    meta = yahoo.fetch_meta("CL=F")
    parts = meta["shortName"].split()
    for i, p in enumerate(parts):
        if p in MONTH_NAMES and i + 1 < len(parts):
            return MONTH_NAMES[p], int(parts[i + 1]) + 2000
    raise RuntimeError(f"energy: cannot parse front month from {meta.get('shortName')!r}")


def next_month_code(month: int, yy: int) -> str:
    m, y = (month + 1, yy) if month < 12 else (1, yy + 1)
    return f"{MONTH_CODES[m - 1]}{y % 100:02d}"


def _cl2_rows(days: int = 30) -> list[dict]:
    from ..fetchers import yahoo

    month, yy = _front_month()
    ticker = f"CL{next_month_code(month, yy)}.NYM"
    return yahoo.fetch_daily(ticker)[-days:]


def _latest_price(conn, symbol: str, max_age_days: int = 5) -> tuple[str, float]:
    row = conn.execute(
        "SELECT ts, close FROM instrument_prices WHERE symbol=? "
        "AND close IS NOT NULL ORDER BY ts DESC LIMIT 1",
        (symbol,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"energy: no price for {symbol}")
    age = (datetime.now(UTC).date() - datetime.fromisoformat(row[0][:10]).date()).days
    if age > max_age_days:
        raise RuntimeError(f"energy: {symbol} stale {age}d ({row[0]})")
    return row[0][:10], float(row[1])


def _spot_pair(conn, days: int = 10) -> tuple[str, float, float]:
    series = {}
    for sid in ("FRED:DCOILBRENTEU", "FRED:DCOILWTICO"):
        rows = conn.execute(
            "SELECT substr(ts,1,10), value FROM raw_observations WHERE series_id=? "
            "AND vintage_ts='realtime' ORDER BY ts DESC LIMIT ?",
            (sid, days),
        ).fetchall()
        if not rows:
            raise RuntimeError(f"energy: no spot for {sid}")
        series[sid] = {r[0]: r[1] for r in rows}
    common = set(series["FRED:DCOILBRENTEU"]) & set(series["FRED:DCOILWTICO"])
    if not common:
        raise RuntimeError("energy: no common spot date in window")
    ts = max(common)
    return ts, series["FRED:DCOILBRENTEU"][ts], series["FRED:DCOILWTICO"][ts]


def compute(conn) -> dict[str, float]:
    signals: dict[str, float] = {}
    _, cl1 = _latest_price(conn, "CL1")
    _, rb1 = _latest_price(conn, "RB1")
    _, ho1 = _latest_price(conn, "HO1")
    signals["energy_crack_gas"] = round(rb1 * 42 - cl1, 2)
    signals["energy_crack_ho"] = round(ho1 * 42 - cl1, 2)
    ts_spot, brent, wti = _spot_pair(conn)
    signals["energy_brent_wti_spot"] = round(brent - wti, 2)

    for p in _cl2_rows():
        conn.execute(
            "INSERT OR REPLACE INTO instrument_prices(symbol, ts, source, open, high, low,"
            " close, volume) VALUES ('CL2', ?, 'YAHOO', ?, ?, ?, ?, ?)",
            (p["ts"], p.get("open"), p.get("high"), p.get("low"), p["close"], p.get("volume")),
        )
    row = conn.execute(
        "SELECT close FROM instrument_prices WHERE symbol='CL2' "
        "ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    if row and row[0]:
        signals["energy_wti_bwd"] = round(cl1 - float(row[0]), 2)
    conn.commit()
    return {"ts": ts_spot, **signals}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch energy")
    p.add_argument("--db", default=str(DEFAULT_DB))
    args = p.parse_args(argv)
    from dotenv import load_dotenv

    load_dotenv()
    conn = db.get_conn(args.db, allow_init=True)
    out = compute(conn)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    for sid, val in out.items():
        if sid == "ts" or val is None:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO computed_signals(signal_id, ts, run_id, computed_at,"
            " value, state, inputs_json) VALUES (?,?,?,?,?,?,?)",
            (sid, out["ts"], "energy", now, val, None, None),
        )
    conn.commit()
    for k, v in sorted(out.items()):
        print(f"  {k:26s} {v}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
