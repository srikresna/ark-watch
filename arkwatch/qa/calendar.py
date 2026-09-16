"""calendar.py (qa) — union of 4 sources + dedup + curation → events table.

Rules: TIME precedence = curated > TV > CME > FMP > EODHD; VALUE precedence
(consensus/actual) = FMP > EODHD > CME > TV. 00:00 is date-only (never treat
it as a real time). Dedup key = (normalized_name, UTC date). Curation: FOMC
(from config, exact ET time, DST-aware via zoneinfo) + standard BLS/BEA/ISM/
UMich release times for 00:00 entries matching a keyword.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .. import db
from ..config import load_curated_calendar
from ..fetchers import calendar as cal

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"
ET = ZoneInfo("America/New_York")

TIME_PRECEDENCE = {"CURATED": 0, "TV": 1, "CME": 2, "FMP": 3, "EODHD": 4}
VALUE_PRECEDENCE = {"FMP": 0, "EODHD": 1, "CME": 2, "TV": 3}

# keyword → standard ET release time (from config release_times; hard-mapped for v0 matching)
STD_KEYWORDS = [
    (
        r"\bCPI\b|\bCONSUMER PRICE\b|\bPPI\b|\bPRODUCER PRICE\b|NONFARM|INITIAL JOBLESS|CONTINUING JOBLESS|RETAIL SALES|DURABLE GOODS|GDP\b|PERSONAL (INCOME|SPENDING)|CORE PCE|PCE PRICE",
        (8, 30),
    ),
    (r"\bISM\b|MICHIGAN|CONSUMER (SENTIMENT|CONFIDENCE)|PMI\b", (10, 0)),
]


def norm(name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", name.upper()).strip()


# --- indicator family keys for the σ surprise engine -------------------------
# Source names carry temporal suffixes ("AUG", "AUG 28", "FINAL", "PRELIMINARY")
# plus a "US " prefix; without stripping, every release becomes a "new
# indicator" and σ never accumulates. NOT stripped: substance qualifiers
# ("1 YEAR" vs "5 YEAR", "MM" vs "YY", "PRIVATE") — those are genuinely
# different indicators.
_STRIP_TAIL = re.compile(
    r"(\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\s+\d{1,2})?(\s+\d{4})?)+$"
    r"|\s+(FINAL|PRELIMINARY|PRELIM|ADVANCE|SECOND|THIRD)(\s+ESTIMATE)?$"
    r"|\s+Q[1-4](\s+\d{4})?$"
    r"|\s+\d{4}$"
)

# Cross-source aliases for the same (post-strip) indicator; looked up AFTER
# the "US " prefix is stripped — include both forms where needed
_ALIASES = {
    "CONSUMER SENTIMENT": "MICHIGAN CONSUMER SENTIMENT",
    "US CONSUMER SENTIMENT": "MICHIGAN CONSUMER SENTIMENT",
    "US CHICAGO PMI": "CHICAGO PMI",
    "JOBLESS CLAIMS": "INITIAL JOBLESS CLAIMS",
    "US JOBLESS CLAIMS": "INITIAL JOBLESS CLAIMS",
}


def indicator_key(name_norm: str) -> str:
    """normalized_name → stable indicator family key across releases."""
    k = name_norm.strip()
    while True:
        k2 = _STRIP_TAIL.sub("", k).strip()
        if k2 == k:
            break
        k = k2
    if k.startswith("US "):
        k = k[3:]
    k = _ALIASES.get(k, k)
    return k or name_norm


def _std_time_et(name_norm: str):
    for pat, hm in STD_KEYWORDS:
        if re.search(pat, name_norm):
            return hm
    return None


def pull(from_d: str | None = None, to_d: str | None = None) -> tuple[list[dict], dict]:
    now = datetime.now(UTC)
    from_d = from_d or (now - timedelta(days=3)).strftime("%Y-%m-%d")
    to_d = to_d or (now + timedelta(days=14)).strftime("%Y-%m-%d")
    fetched: dict[str, list[dict]] = {}
    for src, fn in (
        ("FMP", cal.fetch_fmp),
        ("TV", cal.fetch_tv),
        ("CME", cal.fetch_cme),
        ("EODHD", cal.fetch_eodhd),
    ):
        try:
            fetched[src] = fn(from_d, to_d)
        except Exception as ex:
            print(f"  ⚠ {src} failed: {str(ex)[:110]}")
            fetched[src] = []
    counts = {k: len(v) for k, v in fetched.items()}

    # Merge with precedence, tracking provenance per field: actual/consensus can
    # be won by a source other than the time winner, so a single "source"
    # column would misreport where each value came from
    merged: dict[tuple[str, str], dict] = {}
    for src in ("EODHD", "FMP", "CME", "TV"):  # low → high precedence for time
        for e in fetched.get(src, []):
            n = norm(e["name"])
            if not n:
                continue
            key = (n, e["ts_utc"][:10])
            cur = merged.get(key)
            if cur is None:
                merged[key] = {
                    **e,
                    "normalized_name": n,
                    "actual_src": e["source"],
                    "consensus_src": e["source"],
                }
                continue
            # Time: the higher-precedence source wins
            if TIME_PRECEDENCE[e["source"]] < TIME_PRECEDENCE[cur["source"]]:
                cur["ts_utc"] = e["ts_utc"]
            # Values: take the filled value from the best-precedence source
            for f, src_key in (
                ("actual", "actual_src"),
                ("consensus", "consensus_src"),
                ("previous", None),
            ):
                if (
                    cur[f] is None
                    and e[f] is not None
                    or (
                        cur[f] is not None
                        and e[f] is not None
                        and VALUE_PRECEDENCE[e["source"]] < VALUE_PRECEDENCE[cur["source"]]
                    )
                ):
                    cur[f] = e[f]
                    if src_key:
                        cur[src_key] = e["source"]
            if cur["importance"] == "unknown" and e["importance"] != "unknown":
                cur["importance"] = e["importance"]
    events = list(merged.values())

    # Curation 1: exact FOMC (day 2 of the meeting, 14:00 ET)
    kurasi = load_curated_calendar()
    fomc_dates: dict[str, dict] = {}
    f26 = kurasi.get("fomc_2026") or []
    f27 = kurasi.get("fomc_2027") or {}
    f27 = f27.get("meetings", []) if isinstance(f27, dict) else f27
    for m in list(f26) + list(f27):
        # Seed field actually used: decision_day (day 2, 14:00 ET statement) + dates
        dd = str(m.get("decision_day") or "")[:10]
        if dd:
            fomc_dates[dd] = m
    for e in events:
        d = e["ts_utc"][:10]
        if d in fomc_dates and re.search(
            r"FOMC|FEDERAL FUNDS|INTEREST RATE DECISION", e["normalized_name"]
        ):
            hh, mm = 14, 0
            dt_et = datetime.fromisoformat(d).replace(hour=hh, minute=mm, tzinfo=ET)
            e["ts_utc"] = dt_et.astimezone(UTC).isoformat(timespec="seconds")
            e["is_curated"] = 1
    # Curation 2: standard release times for date-only (00:00) entries
    for e in events:
        if e["ts_utc"][11:16] == "00:00" and not e.get("is_curated"):
            hm = _std_time_et(e["normalized_name"])
            if hm:
                dt_et = datetime.fromisoformat(e["ts_utc"][:10]).replace(
                    hour=hm[0], minute=hm[1], tzinfo=ET
                )
                e["ts_utc"] = dt_et.astimezone(UTC).isoformat(timespec="seconds")
                e["is_curated"] = 1
    return events, counts


def event_uid(normalized_name: str, ts_utc: str) -> str:
    """Canonical event uid — DATE-based: sha1(normalized_name|DATE|US)[:16].

    RONDE-4 P0 (D-027): two uid schemes lived simultaneously (this date-based
    one in calendar.save, and a FULL-TIMESTAMP one in qa/surprise.py) — 92.5%
    of stored rows carried uids the calendar upsert could never match, so
    actuals silently never filled for them. ONE canonical helper for ALL
    writers; the uid uses only the DATE because the winning TIME can change
    between pulls (dedup key is name+date)."""
    return hashlib.sha1(f"{normalized_name}|{ts_utc[:10]}|US".encode()).hexdigest()[:16]


def save(db_path: str, events: list[dict]) -> int:
    conn = db.get_conn(db_path, allow_init=True)
    rows = []
    for e in events:
        uid = event_uid(e["normalized_name"], e["ts_utc"])
        rows.append(
            (
                uid,
                e["ts_utc"],
                e["ts_utc"],
                "US",
                e["name"],
                e["normalized_name"],
                e["importance"],
                e["consensus"],
                e.get("consensus_src", e["source"]),
                e["actual"],
                e.get("actual_src", e["source"]),
                e["previous"],
                None,
                int(e.get("is_curated", 0)),
                indicator_key(e["normalized_name"]),
            )
        )
    conn.execute("BEGIN IMMEDIATE")
    try:
        # The consensus may be updated pre-release, while the actual is
        # append-only after release (fill-if-NULL). A plain INSERT OR IGNORE
        # would freeze pre-release rows — the first insert carries no actual,
        # and later fetches (post-release, with actuals) would be ignored,
        # starving surprise_z/ESI of fresh data. Two explicit statements,
        # because SQLite upsert cannot express a doubly-conditional DO UPDATE.
        cur = conn.executemany(
            "INSERT INTO events(event_uid,ts_utc,release_ts,country,name,normalized_name,"
            "importance,consensus,consensus_source,actual,actual_source,previous,surprise_z,is_curated,"
            "indicator_key)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(event_uid) DO UPDATE SET "
            "  actual=excluded.actual, actual_source=excluded.actual_source, "
            "  ts_utc=excluded.ts_utc, release_ts=excluded.release_ts "
            " WHERE events.actual IS NULL AND excluded.actual IS NOT NULL",
            rows,
        )
        conn.executemany(
            "UPDATE events SET consensus=?2, consensus_source=?3 "
            "WHERE event_uid=?1 AND actual IS NULL "
            "AND (?2 IS NOT NULL AND events.consensus IS NOT ?2)",
            [(r[0], r[7], r[8]) for r in rows],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    conn.close()
    return cur.rowcount


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch calendar")
    p.add_argument("--from", dest="from_d")
    p.add_argument("--to", dest="to_d")
    p.add_argument("--db", default=str(DEFAULT_DB))
    a = p.parse_args(argv)
    from dotenv import load_dotenv

    load_dotenv()
    events, counts = pull(a.from_d, a.to_d)
    n_new = save(a.db, events)
    hi = sum(1 for e in events if e["importance"] == "high")
    print(
        f"=== calendar union-4: fetch={counts} · unique={len(events)} (high={hi}) · new rows={n_new} ==="
    )
    for e in sorted([x for x in events if x["importance"] == "high"], key=lambda x: x["ts_utc"])[
        :10
    ]:
        mark = " ★curated" if e.get("is_curated") else ""
        cons = f" cons={e['consensus']}" if e["consensus"] is not None else ""
        print(f"  {e['ts_utc']}  {e['name'][:44]:<44}{cons}{mark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
