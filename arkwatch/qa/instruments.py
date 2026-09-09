"""instruments.py — backfill + daily sweep of instrument prices.

Primary per class: EODHD for spot metals & the crypto backtest; Yahoo for
futures/indexes/DXY/majors. Both write to instrument_prices (distinct sources
coexist; cross-validation of the two sources happens elsewhere).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

from .. import db as _db
from ..config import _load_yaml

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
}


def instruments() -> list[dict]:
    return _load_yaml("instruments.yaml")["instruments"]


def insert_prices(conn, symbol: str, source: str, rows: list[dict]) -> int:
    payload = [
        (
            symbol,
            r["ts"],
            source,
            r.get("open"),
            r.get("high"),
            r.get("low"),
            r.get("close"),
            r.get("volume"),
        )
        for r in rows
    ]
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.executemany(
            "INSERT OR IGNORE INTO instrument_prices(symbol,ts,source,open,high,low,close,volume,adjusted)"
            " VALUES (?,?,?,?,?,?,?,?,0)",
            payload,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return cur.rowcount


def fetch_eodhd_daily(token: str, ticker: str, *, days: int | None = None) -> list[dict]:
    p = {"api_token": token, "fmt": "json"}
    if days:
        p["period"] = f"{days}d"
    r = requests.get(f"https://eodhd.com/api/eod/{ticker}", params=p, headers=UA, timeout=(10, 60))
    if r.status_code != 200:
        raise RuntimeError(f"EODHD {ticker}: HTTP {r.status_code}")
    return [
        {
            "ts": x["date"][:10],
            "open": x.get("open"),
            "high": x.get("high"),
            "low": x.get("low"),
            "close": x.get("close"),
            "volume": x.get("volume"),
        }
        for x in r.json()
    ]


def backfill(
    db_path: str = str(DEFAULT_DB),
    *,
    only: str | None = None,
    yahoo: bool = True,
    eodhd: bool = True,
) -> dict[str, int]:
    import os

    from ..fetchers import yahoo as yh

    conn = _db.get_conn(db_path, allow_init=True)
    out: dict[str, int] = {}
    tok = os.environ.get("EODHD_API_TOKEN", "")
    for ins in instruments():
        sym = ins["symbol"]
        if only and sym != only:
            continue
        if eodhd and ins.get("eodhd"):
            try:
                out[f"{sym}|EODHD"] = insert_prices(
                    conn, sym, "EODHD", fetch_eodhd_daily(tok, ins["eodhd"])
                )
            except Exception as ex:
                out[f"{sym}|EODHD"] = -1
                print(f"  ✗ {sym} EODHD: {str(ex)[:90]}")
        if yahoo and ins.get("yahoo"):
            try:
                out[f"{sym}|YAHOO"] = insert_prices(
                    conn, sym, "YAHOO", yh.fetch_daily(ins["yahoo"])
                )
            except Exception as ex:
                out[f"{sym}|YAHOO"] = -1
                print(f"  ✗ {sym} YAHOO: {str(ex)[:90]}")
    conn.close()
    return out


def sweep(db_path: str = str(DEFAULT_DB)) -> dict[str, int]:
    """Daily sweep: only the last 7 days per symbol (lightweight)."""
    import os

    from ..fetchers import yahoo as yh

    conn = _db.get_conn(db_path, allow_init=True)
    out: dict[str, int] = {}
    tok = os.environ.get("EODHD_API_TOKEN", "")
    start_ts = int(time.time()) - 7 * 86400
    for ins in instruments():
        sym = ins["symbol"]
        if ins.get("eodhd"):
            try:
                out[f"{sym}|EODHD"] = insert_prices(
                    conn, sym, "EODHD", fetch_eodhd_daily(tok, ins["eodhd"], days=7)
                )
            except Exception:
                out[f"{sym}|EODHD"] = -1
        if ins.get("yahoo"):
            try:
                out[f"{sym}|YAHOO"] = insert_prices(
                    conn, sym, "YAHOO", yh.fetch_daily(ins["yahoo"], start_ts=start_ts)
                )
            except Exception:
                out[f"{sym}|YAHOO"] = -1
    conn.close()
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch instruments")
    p.add_argument("mode", choices=["backfill", "sweep"])
    p.add_argument("--only", help="a single symbol only (e.g. XAUUSD)")
    p.add_argument("--db", default=str(DEFAULT_DB))
    a = p.parse_args(argv)
    from dotenv import load_dotenv

    load_dotenv()
    result = backfill(a.db, only=a.only) if a.mode == "backfill" else sweep(a.db)
    ok = sum(1 for v in result.values() if v > 0)
    fail = [k for k, v in result.items() if v < 0]
    print(f"=== instruments {a.mode}: {ok} symbol-sources populated · {len(fail)} failed ===")
    for k, v in sorted(result.items()):
        if v >= 0:
            print(f"  {k:<22} {v:>7,}")
    for k in fail:
        print(f"  ✗ {k}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
