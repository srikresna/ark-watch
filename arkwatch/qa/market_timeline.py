"""Five-minute cross-asset timeline and sector ETF breadth proxy."""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from .. import db as _db
from ..fetchers import yahoo
from .fetch_log import log_collection
from .okx_market import collect as collect_okx_market

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"
INTERVAL = "5m"
TRACKED = {"NQ1": "NQ=F", "ES1": "ES=F", "YM1": "YM=F", "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD", "CL1": "CL=F", "BZ1": "BZ=F", "DXY": "DX-Y.NYB", "TNX": "^TNX", "VIX": "^VIX", "SPY": "SPY", "RSP": "RSP", "XLK": "XLK", "XLY": "XLY", "XLC": "XLC", "XLF": "XLF", "XLV": "XLV", "XLI": "XLI", "XLB": "XLB", "XLE": "XLE", "XLP": "XLP", "XLRE": "XLRE", "XLU": "XLU", "SMH": "SMH", "SOXX": "SOXX"}
EODHD = {"NQ1": "NQ.COMM", "ES1": "ES.COMM", "BTCUSD": "BTC-USD.CC", "ETHUSD": "ETH-USD.CC", "CL1": "CL.COMM", "BZ1": "BZ.COMM", "DXY": "DXY.INDX", "TNX": "TNX.INDX"}
FMP = {symbol: ticker for symbol, ticker in TRACKED.items() if ticker.isalpha()}
FMP.update({"BTCUSD": "BTCUSD", "ETHUSD": "ETHUSD"})
SECTORS = ("XLK", "XLY", "XLC", "XLF", "XLV", "XLI", "XLB", "XLE", "XLP", "XLRE", "XLU")


def _store(conn, symbol: str, source: str, rows: list[dict]) -> int:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    values = [(symbol, r["bar_ts_utc"], INTERVAL, source, r.get("open"), r.get("high"), r.get("low"), r.get("close"), r.get("volume"), now) for r in rows]
    if not values:
        return 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.executemany("INSERT OR IGNORE INTO intraday_bars (symbol,bar_ts_utc,interval,source,open,high,low,close,volume,fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?)", values)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return cur.rowcount


def _utc_stamp(value, *, source: str, ticker: str) -> str:
    if isinstance(value, int | float) or str(value).isdigit():
        stamp = float(value)
        if stamp > 10_000_000_000:
            stamp /= 1000
        return datetime.fromtimestamp(stamp, UTC).isoformat(timespec="seconds")
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        zone = UTC if source == "EODHD" or ticker in ("BTCUSD", "ETHUSD") else ZoneInfo("America/New_York")
        dt = dt.replace(tzinfo=zone)
    return dt.astimezone(UTC).isoformat(timespec="seconds")


def _normalized_rows(payload: list[dict], *, source: str, ticker: str) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(days=2)
    completed = datetime.now(UTC).replace(second=0, microsecond=0)
    completed -= timedelta(minutes=completed.minute % 5)
    out = []
    for row in payload:
        raw_ts = row.get("timestamp") or row.get("datetime") or row.get("date")
        if raw_ts is None or row.get("close") is None:
            continue
        stamp = _utc_stamp(raw_ts, source=source, ticker=ticker)
        dt = datetime.fromisoformat(stamp)
        if dt < cutoff or dt >= completed:
            continue
        out.append({"bar_ts_utc": stamp, "open": row.get("open"), "high": row.get("high"), "low": row.get("low"), "close": row.get("close"), "volume": row.get("volume")})
    return sorted(out, key=lambda row: row["bar_ts_utc"])


def _eodhd_bars(symbol: str) -> list[dict]:
    token = os.environ.get("EODHD_API_TOKEN", "")
    if not token or symbol not in EODHD:
        return []
    now = datetime.now(UTC)
    response = requests.get(f"https://eodhd.com/api/intraday/{EODHD[symbol]}", params={"api_token": token, "interval": INTERVAL, "fmt": "json", "from": int((now - timedelta(days=2)).timestamp()), "to": int(now.timestamp())}, timeout=(10, 45))
    response.raise_for_status()
    payload = response.json()
    return _normalized_rows(payload if isinstance(payload, list) else [], source="EODHD", ticker=EODHD[symbol])


def _fmp_bars(symbol: str) -> list[dict]:
    key = os.environ.get("FMP_API_KEY", "")
    if not key or symbol not in FMP:
        return []
    now = datetime.now(UTC)
    ticker = FMP[symbol]
    response = requests.get("https://financialmodelingprep.com/stable/historical-chart/5min", params={"symbol": ticker, "from": (now - timedelta(days=2)).date().isoformat(), "to": now.date().isoformat(), "apikey": key}, timeout=(10, 45))
    response.raise_for_status()
    payload = response.json()
    return _normalized_rows(payload if isinstance(payload, list) else [], source="FMP", ticker=ticker)


def _provider_bars(symbol: str) -> tuple[str, list[dict]]:
    for source, fetch in (("EODHD", _eodhd_bars), ("FMP", _fmp_bars)):
        try:
            rows = fetch(symbol)
        except requests.RequestException:
            continue
        if rows:
            return source, rows
    raise RuntimeError("no exact intraday fallback available")


def _breadth(conn) -> int:
    marks = ",".join("?" * len(SECTORS))
    rows = conn.execute(f"SELECT symbol,bar_ts_utc,open,close FROM intraday_bars WHERE source='YAHOO' AND interval=? AND symbol IN ({marks}) ORDER BY bar_ts_utc DESC", (INTERVAL, *SECTORS)).fetchall()
    latest = {}
    for row in rows:
        latest.setdefault(row[0], row)
    if any(s not in latest or not latest[s][2] or not latest[s][3] for s in SECTORS):
        return 0
    ret = {s: latest[s][3] / latest[s][2] - 1 for s in SECTORS}
    stamp = max(latest[s][1] for s in SECTORS)
    refs = conn.execute("SELECT symbol,open,close FROM intraday_bars WHERE source='YAHOO' AND interval=? AND bar_ts_utc=? AND symbol IN ('SPY','RSP')", (INTERVAL, stamp)).fetchall()
    refs = {r[0]: r[2] / r[1] - 1 for r in refs if r[1] and r[2]}
    adv, dec = sum(v > 0 for v in ret.values()), sum(v < 0 for v in ret.values())
    conn.execute("INSERT OR REPLACE INTO market_breadth VALUES (?,?,?,?,?,?,?,?,?,?)", (stamp, "US_SECTOR_ETF_PROXY", "YAHOO", adv, dec, len(SECTORS)-adv-dec, adv/len(SECTORS), sum(ret.values())/len(ret), refs.get("SPY"), json.dumps({"rsp_return": refs.get("RSP"), "sector_returns": ret}, sort_keys=True)))
    return 1


def run(db_path: str = str(DEFAULT_DB), *, only: str | None = None, force_fallback: bool = False) -> dict[str, int]:
    conn = _db.get_conn(db_path, allow_init=True)
    result = {}
    for symbol, ticker in TRACKED.items():
        if only and symbol != only:
            continue
        try:
            if force_fallback:
                raise RuntimeError("forced fallback verification")
            rows = yahoo.fetch_intraday(ticker)
            result[symbol] = _store(conn, symbol, "YAHOO", rows)
            log_collection(conn, "market", f"{symbol}:YAHOO:5m", rows[-1]["bar_ts_utc"] if rows else None, len(rows))
        except Exception as ex:
            try:
                source, rows = _provider_bars(symbol)
                result[symbol] = _store(conn, symbol, source, rows)
                log_collection(conn, "market", f"{symbol}:{source}:5m", rows[-1], len(rows))
            except Exception as fallback_ex:
                result[symbol] = -1
                print(f"{symbol} fallback: {type(fallback_ex).__name__}: {str(fallback_ex)[:160]}")
                log_collection(conn, "market", f"{symbol}:YAHOO:5m", None, 0, err=f"{ex}; fallback: {fallback_ex}")
    result["breadth"] = _breadth(conn)
    conn.close()
    try:
        result.update({f"okx:{name}": count for name, count in collect_okx_market(db_path).items()})
    except Exception as ex:
        result["okx:collector"] = -1
        print(f"OKX market: {type(ex).__name__}: {str(ex)[:160]}")
    return result


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser(prog="arkwatch market")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--only", choices=sorted(TRACKED))
    parser.add_argument("--force-fallback", action="store_true")
    args = parser.parse_args(argv)
    result = run(args.db, only=args.only, force_fallback=args.force_fallback)
    failed = [name for name, value in result.items() if value < 0]
    print(f"=== market timeline: {len(result)-len(failed)} completed, {len(failed)} failed ===")
    return 1 if failed else 0
