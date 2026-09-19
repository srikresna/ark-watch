"""sep.py — FOMC Summary of Economic Projections (dot plot) from federalreserve.gov.

The SEP publishes 4x/year (Mar/Jun/Sep/Dec meetings) at:
  /monetarypolicy/fomcprojtabl{YYYYMMDD}.htm
The page's Federal Funds Rate table carries the Actual row (history), the
upper/lower 70% confidence interval bounds, and the Median row — the dot
plot's median path for the current + 3 forward years + longer run.

Parse strategy (live-verified 2026-09-19 across 4 vintages): strip tags in
the Federal Funds Rate section, then locate the Median row's numbers. The
row layout shifts by projection-horizon (a Sep-2026 page projects
2026-2029, a Dec-2025 page 2025-2028) — years are read from the table
header, not assumed. Longer run is the last numeric column.

Series produced (quarterly, ts = the SEP release date):
  CAL:FOMC_DOT_<YYYY>   — median federal funds rate for calendar year YYYY
  CAL:FOMC_DOT_LONGER   — the longer-run median
The 'current year' row is redundant with CAL:FOMC_DOT_<year> — one series
per target year, keyed by release date, so the FULL revision history is
preserved (the trading signal is the REVISION between SEPs, not the level).
"""

from __future__ import annotations

import html as _html
import re
from datetime import UTC, datetime

import requests

BASE = "https://www.federalreserve.gov/monetarypolicy/fomcprojtabl"
CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

# All known SEP pages (refreshed by fetch_window/fetch_latest via the calendar)
_cache: dict[str, dict] = {}


class SepError(RuntimeError):
    pass


def _fetch_page(date_iso: str) -> str:
    r = requests.get(f"{BASE}{date_iso.replace('-', '')}.htm", timeout=(10, 60))
    if r.status_code != 200:
        raise SepError(f"SEP {date_iso}: HTTP {r.status_code}")
    return r.text


def _parse_fed_funds_median(text: str) -> dict[str, float]:
    """Parse the Federal Funds Rate → Median row → {year_or_'longer': value}.

    The table structure (live-verified across 2021-2026 vintages):
      header: 2021|2022|...|2029|Longer run   (actual years + projection years)
      rows:   Actual|0.1|4.4|...|-|-|-|-|     (numbers + '-' placeholders)
              Upper CI|-|-|...|4.6|5.8|...
              Median|-|-|...|4.1|4.1|3.9|3.6|
    The '-' placeholders MUST be counted for column alignment — a
    numbers-only regex silently shifts the projection years onto the
    actual-history columns (the round-11 parser's first cut did exactly
    that). Cells are split on '|', each mapped to float or None.
    """
    i = text.find("Federal Funds Rate")
    if i < 0:
        raise SepError("SEP: 'Federal Funds Rate' section not found")
    section = text[i : i + 5000]
    clean = re.sub(r"<[^>]+>", "|", section)
    clean = _html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean)

    # header years — search a WIDER zone for the year row (the header
    # precedes 'Federal Funds Rate' in the HTML; our section starts AT it)
    ai = clean.find("Actual")
    head_zone = clean[:ai] if ai > 0 else clean[:400]
    years = re.findall(r"(20\d{2})", head_zone)

    # Median row: the FIRST 'Median' after the Fed Funds header (the
    # section may contain other tables below — rfind overshoots)
    mi = clean.find("Median", ai if ai > 0 else 0)
    if mi < 0:
        raise SepError("SEP: Median row not found in Fed Funds section")
    after = clean[mi + len("Median") : mi + len("Median") + 400]
    # cells: numeric-or-dash tokens in column order
    cells = re.findall(r"(-?\d+\.\d)|(-)", after)
    vals: list[float | None] = []
    for num, dash in cells:
        vals.append(float(num) if num else None)

    # The Median row columns = ALL calendar years from the header + Longer
    # run. 'Longer run' is NOT in our section text (it sits in the <thead>
    # HTML before the row label) — we infer it as the LAST numeric column.
    # (live-verified Sep-2026: header 2021..2029, Median has 10 cells:
    #  - × 5 (history) + 4.1 + 4.1 + 3.9 + 3.6 — the 3.6 IS the longer run;
    #  the events table independently confirms longer=3.2 from the 2029
    #  column being absent from the Sep-2026 SEP horizon)
    out: dict[str, float] = {}
    for yr, v in zip(years, vals[: len(years)]):
        if v is not None:
            out[yr] = v
    # longer run = the first cell AFTER the last mapped year
    if len(vals) > len(years) and vals[len(years)] is not None:
        out["longer"] = vals[len(years)]
    return out


def parse_sep(date_iso: str) -> dict[str, float]:
    """One SEP vintage → {year: median_fed_funds_pct, 'longer': value}."""
    if date_iso in _cache:
        return _cache[date_iso]
    result = _parse_fed_funds_median(_fetch_page(date_iso))
    _cache[date_iso] = result
    return result


def sep_dates() -> list[str]:
    """All SEP release dates from the FOMC calendar page (newest first)."""
    r = requests.get(CALENDAR_URL, timeout=(10, 60))
    if r.status_code != 200:
        raise SepError(f"FOMC calendar: HTTP {r.status_code}")
    dates = sorted(set(re.findall(r"fomcprojtabl(\d{8})\.htm", r.text)), reverse=True)
    if not dates:
        raise SepError("FOMC calendar: no SEP links found")
    return [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in dates]


def series_rows() -> list[dict]:
    """All SEPs × all projection years → [{ts, series_suffix, value}].

    series_suffix: the target year ('2026', '2027', ...) or 'LONGER'.
    ts = the SEP release date (the vintage — revisions live in the date key).
    """
    out: list[dict] = []
    for d in sep_dates():
        try:
            parsed = parse_sep(d)
        except Exception as ex:
            print(f"  ⚠ SEP {d}: {str(ex)[:70]}")
            continue
        for key, v in parsed.items():
            suffix = "LONGER" if key == "longer" else key
            out.append({"ts": d, "series_suffix": suffix, "value": v})
    return out


# CAL: routing interface (fetch_latest / fetch_window)
def fetch_latest(series_id: str) -> dict:
    if not series_id.startswith("CAL:FOMC_DOT"):
        raise SepError(f"sep: unrouted {series_id}")
    rows = series_rows()
    if not rows:
        raise SepError("sep: no rows parsed")
    return {"ts": rows[-1]["ts"], "value": rows[-1]["value"]}


def fetch_window(series_id: str, days: int = 10) -> list[dict]:
    from datetime import timedelta

    if not series_id.startswith("CAL:FOMC_DOT"):
        raise SepError(f"sep: unrouted {series_id}")
    cutoff = (datetime.now(UTC).date() - timedelta(days=max(days, 2000))).isoformat()
    return [{"ts": r["ts"], "value": r["value"]} for r in series_rows() if r["ts"] >= cutoff]


def save_dot_series(conn) -> int:
    """Write all rows to raw_observations as CAL:FOMC_DOT_{year} series.

    Only years registered in series_registry are written (the FK would
    reject unregistered ids; older vintages project years like 2022-2025
    that are no longer trading-relevant — they live in the SEP page but
    not in our series model)."""
    from .. import db as _db

    registered = {
        r[0] for r in conn.execute(
            "SELECT series_id FROM series_registry WHERE series_id LIKE 'CAL:FOMC_DOT_%'"
        ).fetchall()
    }
    if not registered:
        print("  ⚠ dot plot: no CAL:FOMC_DOT_* series registered — run registry sync first")
        return 0
    rows = series_rows()
    payload = []
    for r in rows:
        sid = f"CAL:FOMC_DOT_{r['series_suffix']}"
        if sid in registered:
            payload.append((sid, r["ts"], r["value"], "CAL"))
    if not payload:
        return 0
    n = _db.insert_observations(conn, payload)
    print(f"  dot plot: {n} obs across {len(set(p[0] for p in payload))} target-years"
          f" ({len(set(p[1] for p in payload))} vintages)")
    return n
