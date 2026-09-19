"""fedsurvey_harvest.py — scheduled harvest of ALL federalreserve.gov surveys + reports.

One job covers: SLOOS, Beige Book, SCOOS, Charge-off, FSR, FOMC minutes (NLP),
FOMC press conference (NLP). Each source checks for new data vs the stored
latest — 404s and "no new data" are INFO (not ERROR): a quarterly source
will 404 or return unchanged data on ~95% of days, by design.

Release calendar (for reference):
  SLOOS: quarterly (Feb/May/Aug/Nov, ~2wk after quarter end)
  Beige Book: 8x/year (~2wk before each FOMC)
  SCOOS: quarterly (similar to SLOOS)
  Charge-off: quarterly (~2 months after quarter end)
  FSR: semi-annual (Apr/Nov)
  Minutes: 8x/year (+3 weeks after FOMC)
  Press conf: 8x/year (same day as FOMC, PDF appears ~2hr later)
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from .. import db
from ..fetchers import fedsurvey

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"


def _latest_stored(conn, kind: str) -> str:
    """Latest ts for a fedsurvey kind in computed_signals, or ''."""
    row = conn.execute(
        "SELECT MAX(ts) FROM computed_signals WHERE signal_id LIKE ?",
        (f"fedsurvey_{kind}%",),
    ).fetchone()
    return row[0] if row and row[0] else ""


def _store_analysis(conn, kind: str, ts: str, tone: dict, metrics: dict | None = None) -> None:
    """Store NLP tone + structural metrics as computed_signals rows."""
    now = datetime.now(UTC).isoformat(timespec="seconds")
    score = tone.get("score")
    conn.execute(
        "INSERT OR REPLACE INTO computed_signals(signal_id, ts, run_id, computed_at, value, state, inputs_json)"
        " VALUES (?,?,?,?,?,?,?)",
        (f"fedsurvey_{kind}_tone", ts, "fedsurvey", now, score,
         tone.get("summary", "")[:200], None),
    )
    if metrics:
        conn.execute(
            "INSERT OR REPLACE INTO computed_signals(signal_id, ts, run_id, computed_at, value, state, inputs_json)"
            " VALUES (?,?,?,?,?,?,?)",
            (f"fedsurvey_{kind}_bias", ts, "fedsurvey", now,
             1 if metrics.get("net_bias") == "tightening" else (-1 if metrics.get("net_bias") == "easing" else 0),
             metrics.get("net_bias", ""), None),
        )
    conn.commit()


def _check_new(available_ts: str, stored_ts: str) -> bool:
    """True if the available data is newer than what we've stored."""
    if not stored_ts:
        return True  # never harvested
    return available_ts > stored_ts


def harvest_all(conn) -> dict[str, str]:
    """Check every Fed survey/report for new data; fetch + NLP + store if new.

    Returns {source: 'new'|'unchanged'|'error: ...'} for logging.
    """
    from .fetch_log import log_collection

    out: dict[str, str] = {}
    n_new = 0

    # --- SLOOS ---
    try:
        data = fedsurvey.fetch_sloos()
        stored = _latest_stored(conn, "sloos")
        if _check_new(data["ts"], stored):
            metrics = fedsurvey.sloos_tone_metrics(data["text"])
            from ..fetchers.nlp import analyze_tone

            tone = analyze_tone(data["text"], source_type="sloos")
            _store_analysis(conn, "sloos", data["ts"], tone, metrics)
            out["sloos"] = f"new @ {data['ts']} (tone={tone.get('score')}, bias={metrics.get('net_bias')})"
            n_new += 1
        else:
            out["sloos"] = f"unchanged (stored {stored})"
    except Exception as ex:
        out["sloos"] = f"error: {str(ex)[:80]}"

    # --- Beige Book ---
    try:
        data = fedsurvey.fetch_beige_book()
        stored = _latest_stored(conn, "beige_book")
        if _check_new(data["ts"], stored):
            from ..fetchers.nlp import analyze_tone

            tone = analyze_tone(data["text"], source_type="beige_book")
            _store_analysis(conn, "beige_book", data["ts"], tone)
            out["beige_book"] = f"new @ {data['ts']} (tone={tone.get('score')})"
            n_new += 1
        else:
            out["beige_book"] = f"unchanged (stored {stored})"
    except Exception as ex:
        out["beige_book"] = f"error: {str(ex)[:80]}"

    # --- SCOOS ---
    try:
        data = fedsurvey.fetch_scoos()
        stored = _latest_stored(conn, "scoos")
        if _check_new(data["ts"], stored):
            from ..fetchers.nlp import analyze_tone

            tone = analyze_tone(data["text"], source_type="scoos")
            _store_analysis(conn, "scoos", data["ts"], tone)
            out["scoos"] = f"new @ {data['ts']} (tone={tone.get('score')})"
            n_new += 1
        else:
            out["scoos"] = f"unchanged (stored {stored})"
    except Exception as ex:
        out["scoos"] = f"error: {str(ex)[:80]}"

    # --- Financial Stability Report ---
    try:
        data = fedsurvey.fetch_fsr()
        stored = _latest_stored(conn, "fsr")
        if _check_new(data["ts"], stored):
            from ..fetchers.nlp import analyze_tone

            tone = analyze_tone(data["text"], source_type="financial_stability_report")
            _store_analysis(conn, "fsr", data["ts"], tone)
            out["fsr"] = f"new @ {data['ts']} (tone={tone.get('score')})"
            n_new += 1
        else:
            out["fsr"] = f"unchanged (stored {stored})"
    except Exception as ex:
        out["fsr"] = f"error: {str(ex)[:80]}"

    # --- FOMC Minutes (NLP) ---
    try:
        from ..fetchers.minutes import minutes_dates, nlp_sentiment, parse_minutes

        latest = minutes_dates()[0]  # newest available
        stored = _latest_stored(conn, "minutes")
        # minutes ts = meeting date (release is +3wk but URL uses meeting date)
        if _check_new(latest, stored):
            p = parse_minutes(latest)
            tone = nlp_sentiment(p["full_text"])
            _store_analysis(conn, "minutes", latest, tone, {
                "net_bias": p["dissent_direction"] or "none",
            })
            out["minutes"] = f"new @ {latest} (tone={tone.get('score')}, dissent={p['dissent_count']})"
            n_new += 1
        else:
            out["minutes"] = f"unchanged (stored {stored})"
    except Exception as ex:
        out["minutes"] = f"error: {str(ex)[:80]}"

    # --- FOMC Press Conference (NLP) ---
    try:
        from ..fetchers.pressconf import available_dates, fetch_transcript_text

        latest_pc = available_dates()[0]
        stored = _latest_stored(conn, "pressconf")
        if _check_new(latest_pc, stored):
            text = fetch_transcript_text(latest_pc)
            from ..fetchers.nlp import analyze_tone

            tone = analyze_tone(text, source_type="press_conference")
            _store_analysis(conn, "pressconf", latest_pc, tone)
            out["pressconf"] = f"new @ {latest_pc} (tone={tone.get('score')})"
            n_new += 1
        else:
            out["pressconf"] = f"unchanged (stored {stored})"
    except Exception as ex:
        out["pressconf"] = f"error: {str(ex)[:80]}"

    log_collection(
        conn, "fedsurvey", "FEDSURVEY:ALL", None, n_new,
        err=None if n_new > 0 else "all sources unchanged",
    )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch fedsurvey")
    p.add_argument("--db", default=str(DEFAULT_DB))
    a = p.parse_args(argv)
    from dotenv import load_dotenv

    load_dotenv()
    conn = db.get_conn(a.db, allow_init=True)
    print("=== Fed Surveys harvest (SLOOS + Beige Book + SCOOS + FSR + Minutes + Press Conf) ===")
    results = harvest_all(conn)
    for source, status in results.items():
        print(f"  {source:12s} {status}")
    n_new = sum(1 for v in results.values() if v.startswith("new"))
    n_err = sum(1 for v in results.values() if v.startswith("error"))
    print(f"=== done: {n_new} new, {len(results) - n_new - n_err} unchanged, {n_err} errors ===")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
