"""alfred.py — weekly job: DB maintenance + vintage audit.

Revision detection is absorbed by the daily harvest (realtime upsert + a
vintage snapshot whenever a value changes). This weekly job performs
maintenance instead:
  1. PRAGMA wal_checkpoint(TRUNCATE) — shrink the WAL file
  2. ANALYZE — refresh query-planner statistics
  3. foreign_key_check + integrity_check — detect corruption
  4. Report vintage rows created this week (evidence FRED revisions are captured)
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .. import db

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"


def maintenance(conn) -> dict:
    out = {}
    out["wal_checkpoint"] = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0]
    conn.execute("ANALYZE")
    conn.commit()
    out["integrity"] = conn.execute("PRAGMA integrity_check").fetchone()[0]
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    out["fk_violations"] = len(fk)
    since = (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
    out["vintage_rows_week"] = conn.execute(
        "SELECT COUNT(*) FROM raw_observations WHERE vintage_ts != 'realtime' AND fetched_at >= ?",
        (since,),
    ).fetchone()[0]
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch alfred")
    p.add_argument("--db", default=str(DEFAULT_DB))
    a = p.parse_args(argv)
    conn = db.get_conn(a.db, allow_init=True)
    r = maintenance(conn)
    conn.close()
    print("=== weekly maintenance ===")
    print(f"  wal_checkpoint: {r['wal_checkpoint']} (0=ok, 1=retry, -1=busy)")
    print(f"  integrity: {r['integrity']}")
    print(f"  fk_violations: {r['fk_violations']}")
    print(f"  vintage rows last 7 days: {r['vintage_rows_week']} (>0 = FRED revisions captured ✓)")
    ok = r["integrity"] == "ok" and r["fk_violations"] == 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
