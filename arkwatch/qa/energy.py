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
    """YAHOO-pinned completed-bar read. The table holds YAHOO+EODHD twins per
    day whose continuous contracts track DIFFERENT expiry months during roll
    windows (4-8% apart live) — an unpinned read mixes roll calendars."""
    row = conn.execute(
        "SELECT ts, close FROM instrument_prices WHERE symbol=? AND source='YAHOO' "
        "AND close IS NOT NULL AND ts < date('now') ORDER BY ts DESC LIMIT 1",
        (symbol,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"energy: no completed YAHOO bar for {symbol}")
    age = (datetime.now(UTC).date() - datetime.fromisoformat(row[0][:10]).date()).days
    if age > max_age_days:
        raise RuntimeError(f"energy: {symbol} stale {age}d ({row[0]})")
    return row[0][:10], float(row[1])


def _same_date_legs(conn) -> tuple[str, dict[str, float]]:
    legs = {s: _latest_price(conn, s) for s in ("CL1", "RB1", "HO1")}
    dates = {d for d, _ in legs.values()}
    if len(dates) != 1:
        raise RuntimeError(f"energy: futures legs on different dates {sorted(dates)}")
    d = dates.pop()
    return d, {s: v for s, (_, v) in legs.items()}


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


def _write_cl2(conn, rows: list[dict]) -> None:
    """Rolling spread input, not a history series: keep only the recent tail —
    at each roll the 'CL2' label re-binds to the new next-month, so older rows
    under the same label would silently change meaning."""
    for p in rows[-10:]:
        conn.execute(
            "INSERT OR REPLACE INTO instrument_prices(symbol, ts, source, open, high, low,"
            " close, volume) VALUES ('CL2', ?, 'YAHOO', ?, ?, ?, ?, ?)",
            (p["ts"], p.get("open"), p.get("high"), p.get("low"), p["close"], p.get("volume")),
        )
    conn.execute(
        "DELETE FROM instrument_prices WHERE symbol='CL2' AND ts NOT IN "
        "(SELECT ts FROM instrument_prices WHERE symbol='CL2' ORDER BY ts DESC LIMIT 10)"
    )


def compute(conn) -> dict[str, dict]:
    ts_f, px = _same_date_legs(conn)
    out: dict[str, dict] = {
        "energy_crack_gas": {"ts": ts_f, "value": round(px["RB1"] * 42 - px["CL1"], 2)},
        "energy_crack_ho": {"ts": ts_f, "value": round(px["HO1"] * 42 - px["CL1"], 2)},
    }
    ts_spot, brent, wti = _spot_pair(conn)
    out["energy_brent_wti_spot"] = {"ts": ts_spot, "value": round(brent - wti, 2)}

    _write_cl2(conn, _cl2_rows())
    row = conn.execute(
        "SELECT ts, close FROM instrument_prices WHERE symbol='CL2' AND source='YAHOO' "
        "AND close IS NOT NULL ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    if row and row[0][:10] == ts_f:
        out["energy_wti_bwd"] = {"ts": ts_f, "value": round(px["CL1"] - float(row[1]), 2)}
    conn.commit()
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch energy")
    p.add_argument("--db", default=str(DEFAULT_DB))
    args = p.parse_args(argv)
    from dotenv import load_dotenv

    load_dotenv()
    conn = db.get_conn(args.db, allow_init=True)
    out = compute(conn)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    for sid, rec in out.items():
        conn.execute(
            "INSERT OR REPLACE INTO computed_signals(signal_id, ts, run_id, computed_at,"
            " value, state, inputs_json) VALUES (?,?,?,?,?,?,?)",
            (sid, rec["ts"], "energy", now, rec["value"], None, None),
        )
    conn.commit()
    for k in sorted(out):
        print(f"  {k:26s} {out[k]['value']:>8} @ {out[k]['ts']}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
