"""harvest.py — daily job: increment every routed series in the registry.

Runs 06:00 WIB: FRED fetches the last 10 observations (catches light
revisions + weekends), non-FRED fetches the latest value. All writes go
to fetch_log (status, rows, duration). Idempotent (PK + INSERT OR IGNORE).
One failing series does not fail the job — it is logged and the loop continues.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from .. import db
from ..config import load_registry
from ..qa.verify_sources import ROUTES

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"

# Any FRED series can be revised in place (GDPNOW ±8×/quarter; ICSA/CPI/PAYEMS
# revised monthly; WALCL seasonally adjusted): a dedup-only skip would freeze
# the first print forever → realtime holds the source's LATEST value (FRED
# semantics), and the previous value is preserved as a vintage row whenever it
# changes. Implemented in the harvest loop below.


def harvest(db_path: str = str(DEFAULT_DB), *, block: str | None = None) -> tuple[int, int, int]:
    from dotenv import load_dotenv

    load_dotenv()
    import hashlib
    import time as _t

    from ..qa.backfill import sync_registry

    conn = db.get_conn(db_path, allow_init=True)
    sync_registry(conn)

    reg = [e for e in load_registry() if any(e["series_id"].startswith(p) for p in ROUTES)]
    if block:
        reg = [e for e in reg if e["block"] == block.upper()]

    def _schema_fp(obj: dict | None) -> str | None:
        """Response-shape fingerprint: sha1 of the first parsed object's sorted
        keys. A silent upstream schema change could make the parser miss
        fields, so the drift check below raises an alarm."""
        if not isinstance(obj, dict) or not obj:
            return None
        return hashlib.sha1("|".join(sorted(obj.keys())).encode()).hexdigest()[:16]

    ok = fail = rows_new = 0
    now = datetime.now(UTC).isoformat(timespec="seconds")
    today = now[:10]
    for e in reg:
        sid_full = e["series_id"]
        prefix = next(p for p in ROUTES if sid_full.startswith(p))
        mod = ROUTES[prefix]
        t0 = _t.monotonic()
        status, n, err = "OK", 0, None
        fp = None
        try:
            first_obj = None
            if prefix == "FRED:":
                ref = (e.get("native_id") or e.get("primary_source") or sid_full).split(":", 1)[-1]
                obs = mod.fetch_observations(ref, sort="desc", limit=10)
                if obs:
                    first_obj = obs[0]
                # release_ts = the FRED realtime_start (the date this value
                # became effective) → point-in-time replay works for new data
                # (historical backfill stays 'na')
                rows = [
                    (sid_full, o["ts"], o["value"], "FRED", o.get("realtime_start"))
                    for o in obs
                    if o["value"] is not None
                ]
            else:
                cur = mod.fetch_latest(sid_full)
                first_obj = cur
                rows = [(sid_full, cur["ts"], cur["value"], prefix.rstrip(":"))]
            fp = _schema_fp(first_obj)
            # Anti-drift alarm: compare with the last fingerprint for this series
            if fp:
                prev = conn.execute(
                    "SELECT schema_fp FROM fetch_log WHERE target=? "
                    "AND schema_fp IS NOT NULL ORDER BY id DESC LIMIT 1",
                    (sid_full,),
                ).fetchone()
                if prev and prev[0] != fp:
                    err = f"SCHEMA_DRIFT {prev[0]}→{fp}"
                    print(f"  ⚠ {sid_full}: RESPONSE SCHEMA CHANGED ({err})")
            n = db.insert_observations(conn, rows)
            # All FRED series are in-place revisable: FRED can revise a value
            # for the same ts → realtime holds the LATEST source value; the
            # revision history lives in vintage rows (snapshotted on change).
            # Without this, the first print would be frozen forever.
            if prefix == "FRED:":
                conn.execute("BEGIN IMMEDIATE")
                try:
                    for r in rows:
                        sid, ts, val, src = r[0], r[1], r[2], r[3]
                        cur_v = conn.execute(
                            "SELECT value FROM raw_observations WHERE series_id=? "
                            "AND ts=? AND source=? AND vintage_ts='realtime'",
                            (sid, ts, src),
                        ).fetchone()
                        if cur_v is not None and abs(cur_v[0] - val) > 1e-12:
                            # Preserve the OLD value as a vintage row dated today
                            conn.execute(
                                "INSERT OR IGNORE INTO raw_observations"
                                "(series_id,ts,release_ts,value,vintage_ts,source,"
                                "precision_k,fetched_at) VALUES (?,?,?,?,?,?,?,?)",
                                (sid, ts, "na", cur_v[0], today, src, None, now),
                            )
                            conn.execute(
                                "UPDATE raw_observations SET value=?, fetched_at=? "
                                "WHERE series_id=? AND ts=? AND source=? "
                                "AND vintage_ts='realtime'",
                                (val, now, sid, ts, src),
                            )
                            n += 1
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
            ok += 1
            rows_new += n
        except Exception as ex:
            status, err = "ERROR", str(ex)[:150]
            fail += 1
        # quota_used = 1 call for PAID sources (FMP/EODHD), 0 for free
        # institutional ones; approximates the daily call count
        quota = 1 if prefix in ("FMP:", "EODHD:") else 0
        conn.execute(
            "INSERT INTO fetch_log(ts,fetcher,target,status,error,duration_ms,rows,"
            "schema_fp,quota_used) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                now,
                prefix.rstrip(":").lower(),
                sid_full,
                status,
                err,
                int((_t.monotonic() - t0) * 1000),
                n,
                fp,
                quota,
            ),
        )
        if status == "ERROR":
            print(f"  ✗ {sid_full}: {err}")
    conn.close()
    return ok, fail, rows_new


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch harvest")
    p.add_argument("--block")
    p.add_argument("--db", default=str(DEFAULT_DB))
    a = p.parse_args(argv)
    ok, fail, rows = harvest(a.db, block=a.block)
    ts = datetime.now(UTC).isoformat(timespec="seconds")
    print(f"=== harvest {ts}: {ok} OK · {fail} ERROR · {rows:,} new rows ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
