"""Retain the current UTC week's collected GDELT records."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .. import db as _db
from .backup import BACKUP_DIR

TABLES = ("gdelt_mentions", "gdelt_gkg", "gdelt_events")
WEEK_DAYS = 7


def _cutoff(now: datetime) -> str:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    utc_now = now.astimezone(UTC)
    days_since_sunday = (utc_now.weekday() + 1) % WEEK_DAYS
    start_of_week = (utc_now - timedelta(days=days_since_sunday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start_of_week.isoformat(timespec="seconds")


def _summary(conn: sqlite3.Connection, table: str, cutoff: str) -> dict[str, int]:
    extra = (
        " AND NOT EXISTS (SELECT 1 FROM gdelt_mentions m "
        "WHERE m.event_id=gdelt_events.event_id AND m.fetched_at>=?)"
        if table == "gdelt_events"
        else ""
    )
    params = (cutoff, cutoff) if extra else (cutoff,)
    count, payload_bytes = conn.execute(
        f"SELECT COUNT(*), COALESCE(SUM(COALESCE(length(raw_record_gzip), "
        f"length(raw_record_json))),0) FROM {table} "
        f"WHERE fetched_at < ?{extra}",
        params,
    ).fetchone()
    return {"rows": count, "payload_bytes": payload_bytes}


def _protected_events(conn: sqlite3.Connection, cutoff: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM gdelt_events e WHERE e.fetched_at < ? "
        "AND EXISTS (SELECT 1 FROM gdelt_mentions m "
        "WHERE m.event_id=e.event_id AND m.fetched_at>=?)",
        (cutoff, cutoff),
    ).fetchone()[0]


def _verify_backup(db_path: Path, backup_path: Path, now: datetime) -> dict[str, int]:
    if not backup_path.is_file():
        raise FileNotFoundError(f"verified daily pre-cleanup backup required: {backup_path}")
    modified = datetime.fromtimestamp(backup_path.stat().st_mtime, UTC)
    age = now.astimezone(UTC) - modified
    if age < timedelta(0) or age > timedelta(hours=12):
        raise ValueError("daily pre-cleanup backup timestamp is outside the 12-hour window")

    source = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
    backup = sqlite3.connect(backup_path.as_uri() + "?mode=ro", uri=True)
    try:
        if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("pre-cleanup backup integrity check failed")
        counts = {}
        for table in ("gdelt_events", "gdelt_mentions", "gdelt_gkg"):
            live_count = source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            backup_count = backup.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if live_count != backup_count:
                raise ValueError(f"pre-cleanup backup row count mismatch: {table}")
            counts[table] = live_count
        return counts
    finally:
        source.close()
        backup.close()


def clean(
    db_path: str | Path,
    *,
    now: datetime | None = None,
    apply: bool = False,
    backup_path: str | Path | None = None,
) -> dict:
    """Preview or apply age-based GDELT deletion; preview is the default."""
    instant = now or datetime.now(UTC)
    cutoff = _cutoff(instant)
    path = Path(db_path).resolve()
    _require_database(path)
    conn = (
        _db.get_conn(path, allow_init=False)
        if apply
        else sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    )
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        result = {
            "applied": apply,
            "cutoff_utc": cutoff,
            "window": "current_utc_week",
            "tables": {table: _summary(conn, table, cutoff) for table in TABLES},
            "protected_events": _protected_events(conn, cutoff),
        }
        if not apply:
            return result

        daily_backup = (
            Path(backup_path).resolve()
            if backup_path
            else BACKUP_DIR / f"arkwatch-{instant.astimezone(UTC):%Y%m%d}.db"
        )
        result["backup_counts"] = _verify_backup(path, daily_backup, instant)
        conn.execute("BEGIN IMMEDIATE")
        try:
            for table, backup_count in result["backup_counts"].items():
                live_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                if live_count != backup_count:
                    raise RuntimeError(f"GDELT changed after backup verification: {table}")
            deleted = {}
            for table in TABLES:
                extra = (
                    " AND NOT EXISTS (SELECT 1 FROM gdelt_mentions m "
                    "WHERE m.event_id=gdelt_events.event_id AND m.fetched_at>=?)"
                    if table == "gdelt_events"
                    else ""
                )
                params = (cutoff, cutoff) if extra else (cutoff,)
                cursor = conn.execute(f"DELETE FROM {table} WHERE fetched_at < ?{extra}", params)
                deleted[table] = cursor.rowcount
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        result["deleted"] = deleted
        result["freelist_pages"] = conn.execute("PRAGMA freelist_count").fetchone()[0]
        return result
    finally:
        conn.close()


def _require_database(path: Path) -> int:
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        names = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "schema_migrations" not in names:
            raise ValueError("refusing to modify a database without ARK Watch schema")
        version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        if version is None or version > _db.SCHEMA_VERSION:
            raise ValueError(f"unsupported ARK Watch schema version: {version}")
        for table in ("gdelt_events", "gdelt_mentions", "gdelt_gkg"):
            if table not in names:
                raise ValueError(f"ARK Watch database is missing {table}")
            columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if not {"fetched_at", "raw_record_json", "raw_record_gzip"} <= columns:
                raise ValueError(f"ARK Watch table {table} is missing retention columns")
        return version
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arkwatch gdelt-retention")
    parser.add_argument("--db", default="data/arkwatch.db")
    parser.add_argument("--apply", action="store_true", help="delete eligible records")
    parser.add_argument("--backup", help="verified pre-cleanup database backup")
    args = parser.parse_args(argv)
    result = clean(
        args.db,
        apply=args.apply,
        backup_path=args.backup,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
