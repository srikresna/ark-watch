"""backfill.py — populate the DB with full history (FRED + TGA 3-era).

Other sources are not backfilled here: EODHD has a short history window
(daily accumulation instead) and TREASURY is per-year.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

from .. import db
from ..config import load_registry
from ..fetchers import fred
from ..fetchers.fiscal import BASE as FISCAL_BASE
from ..fetchers.fiscal import ERAS

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"

REQUIRED_FIELDS = (
    "series_id",
    "name",
    "block",
    "tier",
    "unit",
    "value_format",
    "freq",
    "primary_source",
)


def sync_registry(conn) -> int:
    """Sync upstream config into series_registry (FK target for raw_observations)."""
    rows = []
    for e in load_registry(active_only=False):
        rows.append(
            (
                e["series_id"],
                e["name"],
                e["block"],
                int(e.get("tier", 0)),
                e["unit"],
                e["value_format"],
                e["freq"],
                e.get("ts_convention"),
                e.get("release_schedule"),
                e.get("expected_start"),
                e.get("sanity_min"),
                e.get("sanity_max"),
                e["primary_source"],
                e.get("secondary_source"),
                e.get("tolerance"),
                int(e.get("active", 1)),
            )
        )
    conn.execute("BEGIN IMMEDIATE")
    conn.executemany(
        "INSERT OR REPLACE INTO series_registry(series_id,name,block,tier,unit,value_format,freq,"
        "ts_convention,release_schedule,expected_start,sanity_min,sanity_max,"
        "primary_source,secondary_source,tolerance,active) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.execute("COMMIT")
    return len(rows)


def backfill_fred(conn, entries, *, dry: bool = False) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in entries:
        sid_native = (e.get("native_id") or e.get("primary_source") or e["series_id"]).split(
            ":", 1
        )[-1]
        start = str(e.get("expected_start") or "1900-01-01")[:10]
        obs = fred.fetch_observations(sid_native, start=start, sort="asc")
        rows = [
            (e["series_id"], o["ts"], o["value"], "FRED") for o in obs if o["value"] is not None
        ]
        if dry:
            out[e["series_id"]] = len(rows)
        else:
            out[e["series_id"]] = db.insert_observations(conn, rows)
            # ROUND-2: one-shot full-history loads were invisible to every
            # fetch_log-based health join (the 4 new 2026-09-17 series showed
            # ZERO fetch_log rows while holding 700-800 obs each)
            try:
                from .fetch_log import log_collection

                log_collection(
                    conn, "backfill", e["series_id"],
                    {"ts": rows[-1][1], "value": rows[-1][2]} if rows else None,
                    out[e["series_id"]],
                )
            except Exception:
                pass  # logging must never break the load
    return out


def _tga_rows(account_type: str) -> list[tuple]:
    rows, url, params = (
        [],
        FISCAL_BASE,
        {
            "filter": f"account_type:eq:{account_type}",
            "sort": "record_date",
            "page[size]": 10000,
        },
    )
    while url:
        j = requests.get(url, params=params, timeout=(10, 60)).json()
        for r in j.get("data", []):
            for k in ("close_today_bal", "open_today_bal"):
                v = r.get(k)
                if v not in (None, "", "null"):
                    rows.append(("FISCAL:TGA_DAILY", r["record_date"], float(v), "FISCAL"))
                    break
        nxt = (j.get("links") or {}).get("next")
        url, params = (nxt, None) if nxt else (None, None)
    return rows


def backfill_tga(conn, *, dry: bool = False) -> dict[str, int]:
    rows: list[tuple] = []
    for era, _s, _e in ERAS:
        rows.extend(_tga_rows(era))
    # Cross-era dedup (the PK + INSERT OR IGNORE also handles it)
    n = len(rows) if dry else db.insert_observations(conn, rows)
    return {"FISCAL:TGA_DAILY": n}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch backfill")
    p.add_argument("--block", help="filter by block (e.g. A)")
    p.add_argument("--limit", type=int)
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--dry", action="store_true", help="count without writing")
    p.add_argument("--source", choices=["fred", "tga"], default="fred")
    args = p.parse_args(argv)

    from dotenv import load_dotenv

    load_dotenv()

    reg = load_registry()
    if args.block:
        reg = [e for e in reg if e["block"] == args.block.upper()]
    if args.limit:
        reg = reg[: args.limit]

    if args.source == "tga":
        result = backfill_tga(None, dry=args.dry) if args.dry else _run_tga(args.db)
    else:
        fred_targets = [e for e in reg if e["series_id"].startswith("FRED:")]
        if args.dry:
            result = backfill_fred(None, fred_targets, dry=True)
        else:
            conn = db.get_conn(args.db, allow_init=True)
            n_reg = sync_registry(conn)
            print(f"registry synced: {n_reg} entries")
            result = backfill_fred(conn, fred_targets)
            conn.close()

    total = sum(result.values())
    print(f"=== backfill ({args.source}) · new rows: {total} · series: {len(result)} ===")
    for sid, n in sorted(result.items()):
        print(f"  {sid:<26} {n:>7,}")
    return 0


def _run_tga(db_path: str) -> dict[str, int]:
    conn = db.get_conn(db_path, allow_init=True)
    sync_registry(conn)
    out = backfill_tga(conn)
    conn.close()
    return out


if __name__ == "__main__":
    sys.exit(main())
