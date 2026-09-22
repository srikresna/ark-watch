"""Persistent collector for OKX public liquidation events."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime

import websocket

from .. import db as _db
from .fetch_log import log_collection

URL = "wss://ws.okx.com:8443/ws/v5/public"
FAMILIES = ("BTC-USDT", "ETH-USDT")


def _events(message: dict) -> list[dict]:
    out = []
    for parent in message.get("data") or []:
        details = parent.get("details") or [parent]
        for row in details:
            merged = {**parent, **row}
            instrument = str(merged.get("instId") or parent.get("instFamily") or parent.get("uly") or "")
            raw_ts = merged.get("ts") or merged.get("uTime") or merged.get("pTime")
            if not instrument or raw_ts is None:
                continue
            stamp = datetime.fromtimestamp(int(raw_ts) / 1000, UTC).isoformat(timespec="milliseconds")
            price = float(merged.get("bkPx") or merged.get("px") or 0) or None
            size = float(merged.get("sz") or 0) or None
            notional = float(merged["notionalUsd"]) if merged.get("notionalUsd") else None
            payload = json.dumps(merged, sort_keys=True, separators=(",", ":"))
            uid = hashlib.sha256(f"OKX|{instrument}|{stamp}|{payload}".encode()).hexdigest()
            out.append({"uid": uid, "ts": stamp, "instrument": instrument, "side": merged.get("posSide") or merged.get("side"), "price": price, "size": size, "notional": notional, "raw": payload})
    return out


def _store(conn, events: list[dict]) -> int:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    values = [(e["uid"], e["ts"], "OKX", e["instrument"], e["side"], e["price"], e["size"], e["notional"], e["raw"], now) for e in events]
    if not values:
        return 0
    return conn.executemany("INSERT OR IGNORE INTO crypto_liquidations VALUES (?,?,?,?,?,?,?,?,?,?)", values).rowcount


def collect(db_path: str, seconds: int | None = None) -> int:
    deadline = time.monotonic() + seconds if seconds else None
    stored = 0
    conn = _db.get_conn(db_path, allow_init=True)
    try:
        ws = websocket.create_connection(URL, timeout=25)
        args = [{"channel": "liquidation-orders", "instType": "SWAP", "instFamily": family} for family in FAMILIES]
        ws.send(json.dumps({"op": "subscribe", "args": args}))
        while deadline is None or time.monotonic() < deadline:
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                ws.send("ping")
                continue
            if raw == "pong":
                continue
            message = json.loads(raw)
            if message.get("event") == "error":
                raise RuntimeError(f"OKX subscription error {message.get('code')}: {message.get('msg')}")
            if message.get("event") == "subscribe":
                log_collection(conn, "okx_liquidations", "OKX:liquidation-orders", message, 0, status="OK")
            stored += _store(conn, _events(message))
        ws.close()
    finally:
        conn.close()
    return stored


def run_forever(db_path: str) -> None:
    delay = 2
    while True:
        try:
            collect(db_path)
            delay = 2
        except Exception as ex:
            print(f"OKX liquidation reconnect in {delay}s: {type(ex).__name__}: {str(ex)[:160]}", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 60)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="arkwatch liquidations")
    parser.add_argument("--db", default="data/arkwatch.db")
    parser.add_argument("--seconds", type=int)
    args = parser.parse_args(argv)
    if args.seconds:
        print({"stored": collect(args.db, args.seconds)})
    else:
        run_forever(args.db)
    return 0
