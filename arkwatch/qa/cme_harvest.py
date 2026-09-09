"""cme_harvest.py — daily gray-zone job (08:15 WIB): settlements + options + CVOL + VOI → DB.

All snapshots are append-only; retention is ~5 trading days, so the job must
not go more than 3 trading days without running. Options run AFTER the futures
settlements so the same-day underlying anchor is already in cme_settlements.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from .. import db
from ..fetchers import cme

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"

OPTIONS_N_EXPIRATIONS = 6  # [KEPUTUSAN: expiry bulanan terdekat per produk/hari — est. 10-13k baris/hari utk 7 produk (PLAN-CME-OPTIONS §2.3); 2026-09-03]
OPTIONS_PAUSE_S = 0.3  # [KEPUTUSAN: pacing antar kontrak — sama dgn backfill SOMA; 2026-09-03]


def harvest_settlements(conn, products: list[str] | None = None) -> dict[str, int]:
    codes = products or list(cme.PRODUCTS.keys())
    out: dict[str, int] = {}
    for code in codes:
        try:
            rows = cme.fetch_settlements(code)
            n = _save_settlements(conn, rows)
            out[code] = n
        except Exception as ex:
            out[code] = -1
            print(f"  ✗ settlements {code}: {str(ex)[:100]}")
    return out


def _save_settlements(conn, rows: list[dict]) -> int:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = [
        (
            r["trade_date"],
            r["product_id"],
            r["month"],
            r["settle"],
            r["volume"],
            r["open_interest"],
            now,
        )
        for r in rows
    ]
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.executemany(
            "INSERT OR IGNORE INTO cme_settlements(trade_date,product_id,month,settle,volume,open_interest,fetched_at)"
            " VALUES (?,?,?,?,?,?,?)",
            payload,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return cur.rowcount


def harvest_cvol(conn) -> int:
    return harvest_cvol_from(conn, cme.fetch_cvol())


def harvest_cvol_from(conn, rows: list[dict]) -> int:
    payload = [
        (
            r["trade_date"],
            r["symbol"],
            r["cvol"],
            r["atm"],
            r["skew"],
            r["upvar"],
            r["dnvar"],
            r["convexity"],
        )
        for r in rows
    ]
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.executemany(
            "INSERT OR IGNORE INTO cvol_snapshots(trade_date,symbol,cvol,atm,skew,upvar,dnvar,convexity)"
            " VALUES (?,?,?,?,?,?,?,?)",
            payload,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return cur.rowcount


def harvest_voi(conn, asset_classes: list[int] | None = None) -> tuple[int, str | None]:
    ids = asset_classes or list(cme.VOI_ASSET_CLASSES.keys())
    total = 0
    voi_err: str | None = None
    for ac_id in ids:
        try:
            rows = cme.fetch_voi(ac_id)
            payload = [
                (
                    r["trade_date"],
                    r["product_id"],
                    r.get("report_type", "Preliminary"),
                    r["volume"],
                    r["oi"],
                    r["oi_diff"],
                )
                for r in rows
            ]
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.executemany(
                    "INSERT OR IGNORE INTO voi_daily(trade_date,product_id,report_type,volume,oi,oi_diff)"
                    " VALUES (?,?,?,?,?,?)",
                    payload,
                )
                conn.execute("COMMIT")
                total += len(payload)
            except Exception:
                conn.execute("ROLLBACK")
                continue
        except Exception as ex:
            voi_err = str(ex)[:140]
            print(f"  ✗ VOI class {ac_id}: {str(ex)[:90]}")
    return total, voi_err


def harvest_options(conn, products: list[str] | None = None) -> dict[str, int]:
    """Per-strike options settlements for the N nearest monthly expirations.

    Options append-only INSERT OR IGNORE per (trade_date, contract): unlike
    SOMA, CME does not restate a Final settlement, so a re-run is a no-op.
    The underlying anchor (cme_option_underlyings) is NOT in the options
    response — the single type='' row is the contract TOTAL (settle '-') on
    every product (live-verified 2026-09-03) — so it is joined from the
    futures strip the same job already harvested into cme_settlements.
    """
    from curl_cffi import requests as creq

    codes = products or list(cme.OPTIONS_PRODUCTS.keys())
    s = None  # one session shared across products/contracts (created lazily, closed at the end)
    out: dict[str, int] = {}
    for code in codes:
        try:
            if s is None:
                s = creq.Session(impersonate="chrome")
            pid = cme.OPTIONS_PRODUCTS[code]
            picked = cme.pick_expirations(
                cme.fetch_option_expirations(code, session=s), OPTIONS_N_EXPIRATIONS
            )
            n_rows = 0
            n_und = 0
            for contract_id, td_mmdd in picked:
                rows, td_iso = cme.fetch_option_settlements(code, contract_id, td_mmdd, session=s)
                n_rows += len(rows)
                if td_iso:
                    n_und += _save_underlying(conn, pid, code, contract_id, td_iso)
                _save_options(conn, rows)
                time.sleep(OPTIONS_PAUSE_S)
            out[code] = n_rows
            print(
                f"  ✓ options {code}: {len(picked)} expirations · {n_rows} rows · {n_und} underlyings"
            )
        except Exception as ex:
            out[code] = -1
            print(f"  ✗ options {code}: {str(ex)[:100]}")
    if s is not None:
        s.close()
    return out


def _save_options(conn, rows: list[dict]) -> int:
    payload = [
        (
            r["trade_date"],
            r["product_id"],
            r["product_code"],
            r["contract_id"],
            r["option_type"],
            r["strike"],
            r["settle"],
            r["volume"],
            r["open_interest"],
        )
        for r in rows
    ]
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.executemany(
            "INSERT OR IGNORE INTO cme_options_settlements"
            "(trade_date,product_id,product_code,contract_id,option_type,strike,settle,volume,open_interest)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            payload,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return cur.rowcount


def _save_underlying(
    conn, option_pid: int, product_code: str, contract_id: str, trade_date: str
) -> int:
    """Anchor one options contract to its underlying FUTURE settle.

    Joined from cme_settlements (futures strip) by month label — serial option
    months without a listed future, or a missing futures day, are silently
    skipped: underlyings feed IV math only, positioning signals never read them.
    """
    fut_code = cme.OPTIONS_UNDERLYING.get(product_code)
    month = cme.futures_month_from_contract(contract_id)
    if not fut_code or not month or fut_code not in cme.PRODUCTS:
        return 0
    row = conn.execute(
        "SELECT settle FROM cme_settlements WHERE product_id=? AND month=? AND trade_date IN (?,?)",
        (cme.PRODUCTS[fut_code], month, trade_date, cme._mmddyyyy_from_iso(trade_date) or ""),
    ).fetchone()
    if not row or row[0] is None:
        return 0
    conn.execute(
        "INSERT OR REPLACE INTO cme_option_underlyings(trade_date,product_id,contract_id,settle)"
        " VALUES (?,?,?,?)",
        (trade_date, option_pid, contract_id, row[0]),
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch cme")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--skip-voi", action="store_true")
    p.add_argument("--skip-options", action="store_true")
    a = p.parse_args(argv)
    conn = db.get_conn(a.db, allow_init=True)

    print("=== CME settlements (14 products) ===")
    s = harvest_settlements(conn)
    ok_s = sum(1 for v in s.values() if v > 0)
    print(f"  {ok_s}/{len(s)} products populated")

    o: dict[str, int] = {}
    opts_err: str | None = None
    if not a.skip_options:
        print("=== CME options (7 products x 6 nearest expirations) ===")
        try:
            o = harvest_options(conn)
        except Exception as ex:
            opts_err = str(ex)[:140]
            print(f"  ✗ {ex}")

    print("=== CVOL snapshot ===")
    cvol_rows: list[dict] = []
    cvol_err: str | None = None
    try:
        cvol_rows = cme.fetch_cvol()
        n = harvest_cvol_from(conn, cvol_rows)
        print(f"  {n} symbols saved")
    except Exception as ex:
        cvol_err = str(ex)[:140]
        print(f"  ✗ {ex}")
    # fetch_log for the gray harvesters. Status derives only from
    # exceptions; partial failures are recorded in the error text; rows counts
    # products fetched (not new rows — an idempotent re-run reports 0 new).
    from .fetch_log import log_collection

    n_prod_fail = sum(1 for v in s.values() if v < 0)
    s_err = None if n_prod_fail == 0 else f"{n_prod_fail}/{len(s)} products failed"
    log_collection(conn, "cme", "CME:settlements", None, len(s), err=s_err)
    if not a.skip_options:
        n_opt_fail = sum(1 for v in o.values() if v < 0)
        if n_opt_fail:
            opts_err = opts_err or f"{n_opt_fail}/{len(o)} products failed"
        log_collection(
            conn, "cme", "CME:options", None, sum(v for v in o.values() if v > 0), err=opts_err
        )
    log_collection(
        conn, "cme", "CME:cvol", cvol_rows[0] if cvol_rows else None, len(cvol_rows), err=cvol_err
    )

    if not a.skip_voi:
        print("=== VOI (6 asset-class) ===")
        n, voi_err = harvest_voi(conn)
        print(f"  {n} rows saved")
        log_collection(conn, "cme", "CME:voi", None, n, err=voi_err)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
