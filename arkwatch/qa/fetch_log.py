"""fetch_log.py — fetch_log helpers for harvesters outside the registry (CME/f2).

Only registry harvesters wrote fetch_log natively; the others were invisible
to the brief health check. schema_fp fingerprints the response shape (sha1
of the first parsed row's sorted keys).
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime


def schema_fp(first_obj: dict | None) -> str | None:
    if not isinstance(first_obj, dict) or not first_obj:
        return None
    return hashlib.sha1("|".join(sorted(first_obj.keys())).encode()).hexdigest()[:16]


def log(
    conn: sqlite3.Connection,
    fetcher: str,
    target: str,
    status: str,
    rows_n: int,
    err: str | None = None,
    fp: str | None = None,
    duration_ms: int | None = None,
) -> None:
    conn.execute(
        "INSERT INTO fetch_log(ts,fetcher,target,status,error,duration_ms,rows,schema_fp)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (
            datetime.now(UTC).isoformat(timespec="seconds"),
            fetcher,
            target,
            status,
            err,
            duration_ms,
            rows_n,
            fp,
        ),
    )
    conn.commit()


def log_collection(
    conn: sqlite3.Connection,
    fetcher: str,
    target: str,
    first_obj: dict | None,
    rows_n: int,
    err: str | None = None,
) -> None:
    """One call per collection (settlements/cvol/voi/flows-extra): status is OK
    when rows_n > 0, ERROR when err, with a drift check against the previous
    fingerprint."""
    fp = schema_fp(first_obj)
    status = "ERROR" if err else ("OK" if rows_n > 0 else "EMPTY")
    if fp:
        prev = conn.execute(
            "SELECT schema_fp FROM fetch_log WHERE target=? AND schema_fp IS NOT NULL "
            "ORDER BY id DESC LIMIT 1",
            (target,),
        ).fetchone()
        if prev and prev[0] != fp:
            err = (err or "") + f" |SCHEMA_DRIFT {prev[0]}→{fp}"
            print(f"  ⚠ {target}: RESPONSE SCHEMA CHANGED")
    log(conn, fetcher, target, status, rows_n, err, fp)
