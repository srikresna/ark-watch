"""surprise.py — σ surprise engine + ESI.

  z = (actual − consensus) / σ          — macro vs macro, NO price term
  σ  = stdev(historical surprises, rolling 5y, updated per release,
       winsorized ±4σ so a single 10σ event cannot poison it)
  n<30 obs → permanently low_conf in indicator_stats (quarterly indicators etc.)
  ESI = Σ z·e^(−Δt/90d) / Σ e^(−Δt/90d) — exponential decay; empty days carry
       the previous value (not 0)
EOD suffices for every use case: z does not involve price; price reaction is
later measured on the daily bar.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .. import db
from .calendar import indicator_key, norm

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"

# Engine parameters come from config (params_signals.yaml); the literals below
# are only the fallback if the file is unreadable. Values must stay identical
# to the shipped config — this is a definition move, not a recalibration.
try:
    from ..config import load_params_signals

    _PS = load_params_signals()
except Exception:
    _PS = {}
WINDOW_YEARS = int(_PS.get("surprise_window_years", 5))
MIN_OBS = int(_PS.get("surprise_min_obs", 30))  # below this, σ is flagged low_conf (quarterly indicators etc.)
WINSOR_SIGMA = float(_PS.get("surprise_winsor_sigma", 4.0))
ESI_TAU_DAYS = float(_PS.get("surprise_esi_tau_days", 90.0))


def backfill_keys(conn) -> int:
    """Fill indicator_key for legacy rows (one-time, post migration v4)."""
    rows = conn.execute(
        "SELECT DISTINCT normalized_name FROM events WHERE indicator_key IS NULL"
    ).fetchall()
    n = 0
    conn.execute("BEGIN IMMEDIATE")
    for (nn,) in rows:
        conn.execute(
            "UPDATE events SET indicator_key=? WHERE normalized_name=?", (indicator_key(nn), nn)
        )
        n += 1
    conn.execute("COMMIT")
    return n


def backfill_fmp(conn, years: int = 5, db_path: str | None = None) -> int:
    """Pull the FMP historical calendar per quarter → append-only (INSERT OR IGNORE).

    FMP /stable/economic-calendar supports past from/to ranges with
    actual+estimate filled; quarterly chunks for safety.
    """
    from ..fetchers import calendar as cal

    now = datetime.now(UTC)
    total = 0
    start = now - timedelta(days=365 * years)
    q = datetime(start.year, ((start.month - 1) // 3) * 3 + 1, 1, tzinfo=UTC)
    while q < now:
        q_end = min(q + timedelta(days=95), now)
        try:
            evs = cal.fetch_fmp(q.strftime("%Y-%m-%d"), q_end.strftime("%Y-%m-%d"))
        except Exception as ex:
            print(f"  ⚠ {q:%Y-%m}: {str(ex)[:90]}")
            q = q_end + timedelta(days=1)
            continue
        rows = []
        for e in evs:
            if e["actual"] is None or e["consensus"] is None:
                continue  # without a pair it is useless for σ
            nn = norm(e["name"])
            if not nn:
                continue
            # RONDE-4 P0 (D-027): the CANONICAL date-based uid — the old
            # full-timestamp uid here created a parallel row population the
            # calendar upsert could never reach (actuals froze)
            from .calendar import event_uid

            uid = event_uid(nn, e["ts_utc"])
            rows.append(
                (
                    uid,
                    e["ts_utc"],
                    e["ts_utc"],
                    "US",
                    e["name"],
                    nn,
                    e["importance"],
                    e["consensus"],
                    "FMP",
                    e["actual"],
                    "FMP",
                    e["previous"],
                    None,
                    0,
                    indicator_key(nn),
                )
            )
        added = 0
        if rows:
            conn.execute("BEGIN IMMEDIATE")
            # RONDE-5 P1 (D-028): INSERT OR IGNORE could never fill an existing
            # canonical row's NULL actual — the Aug-2026 NFP stayed frozen
            # because the daily pull window (now-3d) had already passed it.
            # The conditional upsert mirrors calendar.save's heal semantics:
            # fill-if-NULL, never overwrite a filled value.
            cur = conn.executemany(
                "INSERT INTO events(event_uid,ts_utc,release_ts,country,name,"
                "normalized_name,importance,consensus,consensus_source,actual,actual_source,"
                "previous,surprise_z,is_curated,indicator_key)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(event_uid) DO UPDATE SET"
                " actual=excluded.actual, actual_source=excluded.actual_source,"
                " previous=COALESCE(events.previous, excluded.previous)"
                " WHERE events.actual IS NULL AND excluded.actual IS NOT NULL",
                rows,
            )
            conn.execute("COMMIT")
            added = cur.rowcount
            total += added
        print(f"  {q:%Y-%m}: +{len(rows)} pairs ({added} new/healed)")
        q = q_end + timedelta(days=1)
        time.sleep(0.4)  # polite rate limit
    return total


def compute_sigma(conn, as_of: str | None = None) -> dict:
    """Compute σ per indicator_key (rolling 5y, winsorized) → indicator_stats.

    Returns {'n_indicators': n, 'low_conf': n_lc}.
    """
    now = as_of or datetime.now(UTC).isoformat(timespec="seconds")
    cutoff = (datetime.now(UTC) - timedelta(days=365 * WINDOW_YEARS)).isoformat(timespec="seconds")
    # One row per (key, date) — deterministic dedup across sources: a
    # NOT-EXISTS-by-rowid filter is not deterministic (the surviving row
    # depends on insertion order, so σ could change between runs without any
    # data change); GROUP BY + MAX is deterministic — duplicate rows of the
    # same event carry identical actual/consensus.
    rows = conn.execute(
        "SELECT indicator_key, substr(ts_utc,1,10) d, MAX(actual), MAX(consensus) "
        "FROM events "
        "WHERE indicator_key IS NOT NULL AND actual IS NOT NULL AND consensus IS NOT NULL "
        "AND ts_utc >= ? "
        "GROUP BY indicator_key, substr(ts_utc,1,10) "
        "ORDER BY indicator_key, d",
        (cutoff,),
    ).fetchall()

    by_key: dict[str, list[float]] = {}
    for key, _d, actual, cons in rows:
        # Quantize to source precision BEFORE differencing: calendar data is
        # rounded to 0.1, but two float representations of −0.1 leave
        # MAD ≈ 1e−16 (dust) → winsor bounds at ±4e−15 would clip every diff
        # to dust → σ ≈ 2e−15 → z in the trillions.
        by_key.setdefault(key, []).append(round(actual - cons, 10))

    n_lc = 0
    conn.execute("BEGIN IMMEDIATE")
    for key, diffs in by_key.items():
        n = len(diffs)
        # Winsor bounds come from MAD (median absolute deviation; 1.4826×MAD ≈ σ
        # for a normal distribution), NOT the sample σ: the sample σ is
        # already contaminated by outliers → ±4σ bounds would be too wide to
        # clip them (masking).
        srt = sorted(diffs)
        med = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2
        mad = sorted(abs(d - med) for d in diffs)
        mad = mad[n // 2] if n % 2 else (mad[n // 2 - 1] + mad[n // 2]) / 2
        sigma_robust = 1.4826 * mad
        if sigma_robust > 0:
            lo, hi = (med - WINSOR_SIGMA * sigma_robust, med + WINSOR_SIGMA * sigma_robust)
            clipped = [min(max(d, lo), hi) for d in diffs]
        else:
            clipped = list(diffs)
        mean_c = sum(clipped) / n
        sigma = math.sqrt(sum((d - mean_c) ** 2 for d in clipped) / max(n - 1, 1))
        low_conf = 1 if n < MIN_OBS else 0
        n_lc += low_conf
        conn.execute(
            "INSERT OR REPLACE INTO indicator_stats"
            "(indicator, as_of, sigma, n_obs, window, low_conf)"
            " VALUES (?,?,?,?,?,?)",
            (key, now[:10], sigma, n, f"{WINDOW_YEARS}y-winsor{WINSOR_SIGMA:g}MAD", low_conf),
        )
    conn.execute("COMMIT")
    return {"n_indicators": len(by_key), "low_conf": n_lc}


def update_surprise_z(conn) -> int:
    """Fill surprise_z for paired events (using the latest σ per key).

    Historical FMP rows with MIXED UNITS (thousands vs %) produce z ≈ +112;
    genuine macro surprises rarely exceed 8σ → |z|>10 is almost certainly
    data corruption → quarantined (NULL), not used. Distrusted numbers must
    never reach the brief.
    """
    # Dedup by as_of: with multi-day stats rows, a plain dict comprehension
    # would keep whichever row was scanned last; MAX(as_of) is explicit
    sigma_by_key = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT indicator, sigma FROM indicator_stats s "
            "WHERE as_of=(SELECT MAX(as_of) FROM indicator_stats s2 "
            "             WHERE s2.indicator=s.indicator)"
        )
    }
    n = 0
    quarantined = 0
    conn.execute("BEGIN IMMEDIATE")
    for key, sigma in sigma_by_key.items():
        if not sigma or sigma <= 0:
            continue
        cur = conn.execute(
            "UPDATE events SET surprise_z = (actual - consensus) / ? "
            "WHERE indicator_key=? AND surprise_z IS NULL "
            "AND actual IS NOT NULL AND consensus IS NOT NULL "
            "AND ABS((actual - consensus) / ?) <= 10",
            (sigma, key, sigma),
        )
        n += cur.rowcount
        q = conn.execute(
            "SELECT COUNT(*) FROM events WHERE indicator_key=? "
            "AND surprise_z IS NULL AND actual IS NOT NULL "
            "AND consensus IS NOT NULL AND ABS((actual - consensus) / ?) > 10",
            (key, sigma),
        ).fetchone()[0]
        quarantined += q
    conn.execute("COMMIT")
    if quarantined:
        print(f"  quarantined: {quarantined} events with |z|>10 (mixed units/bad data)")
    return n


def compute_esi(conn, as_of: datetime | None = None, lookback_days: int = 365) -> float | None:
    """ESI = Σ z·e^(−Δt/τ) / Σ e^(−Δt/τ), τ=90 days.

    z is clipped to ±4 entering the ESI — same philosophy as the σ winsorize:
    one corrupted row must not steer the index. Only low_conf=0 indicators
    contribute: a once-quarterly σ from n<30 is not reliable enough to drive
    the index.
    """
    now = as_of or datetime.now(UTC)
    # Dedup per (key, date) — cross-source duplicates must not double-weight
    rows = conn.execute(
        "SELECT substr(e.ts_utc,1,10) d, AVG(e.surprise_z) FROM events e "
        "JOIN indicator_stats s ON s.indicator = e.indicator_key AND s.low_conf = 0 "
        "AND s.as_of=(SELECT MAX(as_of) FROM indicator_stats s2 "
        "             WHERE s2.indicator = s.indicator) "
        "WHERE e.surprise_z IS NOT NULL AND e.ts_utc >= ? "
        "GROUP BY e.indicator_key, substr(e.ts_utc,1,10) "
        "ORDER BY d",
        ((now - timedelta(days=lookback_days)).isoformat(timespec="seconds"),),
    ).fetchall()
    num = den = 0.0
    for d, z_avg in rows:
        z_c = min(max(z_avg, -WINSOR_SIGMA), WINSOR_SIGMA)
        # Use midday for the age (±12h precision is enough for 90-day decay)
        dt = (now - datetime.fromisoformat(d + "T12:00:00+00:00")).total_seconds() / 86400.0
        w = math.exp(-dt / ESI_TAU_DAYS)
        num += z_c * w
        den += w
    return (num / den) if den > 0 else None


def store_esi(conn) -> float | None:
    """Daily ESI → computed_signals (audit trail + input to the flip trigger)."""
    esi = compute_esi(conn)
    if esi is None:
        return None
    now = datetime.now(UTC)
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        "INSERT OR REPLACE INTO computed_signals"
        "(signal_id, ts, run_id, computed_at, value, state, inputs_json)"
        " VALUES (?,?,?,?,?,?,?)",
        (
            "esi",
            now.date().isoformat(),
            now.isoformat(timespec="seconds"),
            now.isoformat(timespec="seconds"),
            round(esi, 4),
            "POSITIVE" if esi > 0 else "NEGATIVE",
            f'{{"tau_days": {ESI_TAU_DAYS:g}}}',
        ),
    )
    conn.execute("COMMIT")
    return esi


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch surprise")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument(
        "--backfill",
        type=int,
        metavar="YEARS",
        help="pull N years of the FMP historical calendar (one-shot run)",
    )
    a = p.parse_args(argv)
    try:
        from dotenv import load_dotenv

        load_dotenv()  # needed when run directly as a module (not via -m arkwatch)
    except ImportError:
        pass
    conn = db.get_conn(a.db, allow_init=True)

    n_keys = backfill_keys(conn)
    print(f"indicator_key filled for {n_keys} names (legacy rows)")

    if a.backfill:
        print(f"=== FMP backfill {a.backfill} years ===")
        total = backfill_fmp(conn, years=a.backfill)
        print(f"total new rows: {total}")

    print("=== σ engine (rolling 5y, winsorized ±4σ) ===")
    r = compute_sigma(conn)
    print(f"  {r['n_indicators']} indicators · {r['low_conf']} low_conf (n<{MIN_OBS})")
    for row in conn.execute(
        "SELECT indicator, sigma, n_obs, low_conf FROM indicator_stats ORDER BY n_obs DESC LIMIT 8"
    ).fetchall():
        lc = " ⚠low_conf" if row[3] else ""
        print(f"  {row[0][:40]:42} σ={row[1]:9.2f} n={row[2]:3}{lc}")

    n_z = update_surprise_z(conn)
    print(f"=== surprise_z filled: {n_z} events ===")

    esi = store_esi(conn)
    if esi is not None:
        print(f"=== ESI = {esi:+.3f} ({'positive' if esi > 0 else 'negative'}) ===")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
