"""verify_sources.py — truth gate: correctness, not just coverage.

Four gates:
  1. ANCHOR   — value at anchor_date == golden_anchors.expected (±tolerance)
  2. SANITY   — latest value inside [sanity_min, sanity_max]
  3. DEPTH    — first observation (sort=asc, limit=1) ≤ expected_start + 90-day grace
  4. CROSSVAL — |primary − secondary| ≤ tolerance (FMP treasury for FRED:DGS2/10/30)
Duplicates are rejected by the PK (INSERT OR IGNORE rowcount) — part of acceptance, not a daily gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta

from ..config import load_anchors, load_registry
from ..fetchers import atl, cboe, cleve, ecb, eodhd, fiscal, fred, misc, nyfed, philly, treasury

# series_id → fetcher routing
ROUTES = {
    "FRED:": fred,
    "EODHD:": eodhd,
    "FISCAL:": fiscal,
    "CLEVE:": cleve,
    "TREASURY:": treasury,
    "CBOE:": cboe,
    "FMP:": misc,
    "PHILLY:": philly,
    "ATL:": atl,
    "NYFED:": nyfed,
    "ECB:": ecb,
}
# Fetchers exposing early history (depth gate); others show depth=· until backfilled
DEPTH_CAPABLE = ("FRED:", "FISCAL:", "CLEVE:", "CBOE:", "ECB:")
# Gate-4 crossval: FRED ↔ FMP treasury-rates pairs (FMP column)
CROSSVAL_MAP = {
    "FRED:DGS2": "year2",
    "FRED:DGS10": "year10",
    "FRED:DGS30": "year30",
}


def _crossval_fmp(series_id: str, fred_value: float, fred_ts: str, tolerance: float | None) -> str:
    """Gate 4 — |primary(FRED) − secondary(FMP treasury)| ≤ tolerance, on the SAME date."""
    import os

    import requests as _rq

    key = os.environ.get("FMP_API_KEY", "")
    if not key:
        return "·"
    col = CROSSVAL_MAP[series_id]
    try:
        from datetime import datetime
        from datetime import timedelta as _td

        today = datetime.utcnow().date()
        r = _rq.get(
            "https://financialmodelingprep.com/stable/treasury-rates",
            params={
                "from": str(today - _td(days=14)),
                "to": str(today + _td(days=1)),
                "apikey": key,
            },
            timeout=(10, 30),
        )
        rows = r.json()
        if not rows:
            return "✗ FMP response empty (14-day window)"
        by_date = {str(x["date"])[:10]: x for x in rows}
        row = by_date.get(str(fred_ts)[:10])
        if row is None:
            avail = sorted(by_date)[-1]
            return f"· FMP last date {avail} ≠ FRED {fred_ts}"
        diff = abs(float(row[col]) - fred_value)
        tol = tolerance if tolerance is not None else 0.05  # default 5bp
        return "✓" if diff <= tol else f"✗ Δ{diff:.3f} @{fred_ts}"
    except Exception as ex:
        return f"✗ {str(ex)[:60]}"


GRACE_DAYS = 90  # expected_start in the seed is approximate


@dataclass
class Row:
    series_id: str
    anchor: str = "·"
    sanity: str = "·"
    depth: str = "·"
    crossval: str = "·"
    note: str = ""


@dataclass
class Report:
    checked: int = 0
    rows: list[Row] = field(default_factory=list)

    @property
    def violations(self) -> list[Row]:
        return [r for r in self.rows if "✗" in (r.anchor + r.sanity + r.depth + r.crossval)]


def _fmt(v: float | None, fmt: str | None) -> str:
    if v is None:
        return "·"
    return f"{v:.4f}" if fmt == "fraction" else f"{v:,.4f}".rstrip("0").rstrip(".")


def verify(
    limit: int | None = None,
    block: str | None = None,
    registry: list[dict] | None = None,
    anchors: list[dict] | None = None,
) -> Report:
    reg = registry if registry is not None else load_registry()
    anc = anchors if anchors is not None else load_anchors()
    # Index anchors both ways (with & without the source prefix) so FRED:DGS10 ≡ DGS10
    anchor_map: dict[tuple[str, str], dict] = {}
    for a in anc:
        sid = str(a["series_id"])
        d = str(a["anchor_date"])
        anchor_map[(sid, d)] = a
        if ":" in sid:
            anchor_map.setdefault((sid.split(":", 1)[1], d), a)
        else:
            anchor_map.setdefault(("FRED:" + sid, d), a)

    targets = [e for e in reg if any(e["series_id"].startswith(p) for p in ROUTES)]
    if block:
        targets = [e for e in targets if e["block"] == block.upper()]
    if limit:
        targets = targets[:limit]

    rep = Report(checked=len(targets))
    for e in targets:
        prefix = next((p for p in ROUTES if e["series_id"].startswith(p)), None)
        if prefix is None:
            continue  # no fetcher for this prefix — skipped
        mod = ROUTES[prefix]
        # Fetch-id resolution: native_id > primary_source (mnemonic) > series_id
        fetch_ref = e.get("native_id") or e.get("primary_source") or e["series_id"]
        sid = fetch_ref.split(":", 1)[1] if ":" in fetch_ref else fetch_ref
        r = Row(series_id=e["series_id"])
        try:
            if prefix == "FRED:":
                latest = mod.fetch_observations(sid, sort="desc", limit=5)
                vals = [o for o in latest if o["value"] is not None]
                if not vals:
                    r.sanity = r.depth = "✗"
                    r.note = "all latest observations missing"
                    rep.rows.append(r)
                    continue
                cur = vals[0]
                cur_anchor_pool = vals
            else:
                # non-FRED: series_id is the direct key (their primary_source
                # is descriptive, not a mnemonic)
                cur = mod.fetch_latest(e["series_id"])
                # the latest obs itself is the anchor pool: a golden anchor
                # matches only when its anchor_date IS the latest ts (an
                # anchored day that has since rolled past = stale anchor,
                # surfaced as · and recalibrated — never silently compared)
                cur_anchor_pool = [cur]

            # GATE 2 — SANITY
            smin, smax = e.get("sanity_min"), e.get("sanity_max")
            if smin is not None and smax is not None:
                ok = smin <= cur["value"] <= smax
                r.sanity = "✓" if ok else f"✗ {_fmt(cur['value'], e.get('value_format'))}"
                if not ok:
                    r.note += f"sanity[{smin},{smax}] "

            # GATE 1 — ANCHOR
            a = anchor_map.get((e["series_id"], cur["ts"])) or _find_anchor(
                anchor_map, e["series_id"]
            )
            if a:
                obs = [o for o in cur_anchor_pool if o["ts"] == str(a["anchor_date"])]
                if not obs and prefix == "FRED:":
                    obs = [
                        o
                        for o in mod.fetch_observations(
                            sid, start=str(a["anchor_date"]), end=str(a["anchor_date"])
                        )
                        if o["value"] is not None
                    ]
                if obs:
                    diff = abs(obs[0]["value"] - float(a["expected"]))
                    r.anchor = (
                        "✓"
                        if diff <= float(a["tolerance"])
                        else f"✗ live={_fmt(obs[0]['value'], e.get('value_format'))} vs {a['expected']}"
                    )

            # GATE 3 — DEPTH (only fetchers with early history)
            es = e.get("expected_start")
            if es and prefix in DEPTH_CAPABLE:
                if prefix == "FRED:":
                    first_ts = mod.fetch_observations(sid, sort="asc", limit=1)[0]["ts"]
                else:
                    # pass the SERIES ID, not the fetch_ref: primary_source is
                    # descriptive for these fetchers and its ':'-split mangles
                    # the key (fiscal ignores the arg; cleve parses 'CLEVE:X'
                    # or bare 'X' — both are accepted)
                    first_ts = mod.fetch_first_ts(e["series_id"])
                limit_date = date.fromisoformat(str(es)[:10]) + timedelta(days=GRACE_DAYS)
                r.depth = (
                    "✓"
                    if date.fromisoformat(first_ts[:10]) <= limit_date
                    else f"✗ starts {first_ts[:10]} > {es}+grace"
                )

            # GATE 4 — CROSSVAL (FRED treasury ↔ FMP, same date)
            if e["series_id"] in CROSSVAL_MAP:
                r.crossval = _crossval_fmp(
                    e["series_id"], cur["value"], cur["ts"], e.get("tolerance")
                )
        except Exception as ex:  # a fetch error is recorded; it must not crash the gate
            r.anchor = r.sanity = r.depth = r.crossval = "✗"
            r.note = (r.note + str(ex))[:120]
        rep.rows.append(r)
    return rep


def _find_anchor(anchor_map, series_id: str):
    for (sid, _d), a in anchor_map.items():
        if sid == series_id:
            return a
    return None


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("FRED_API_KEY") is None:
        from dotenv import load_dotenv

        load_dotenv()

    p = argparse.ArgumentParser(prog="arkwatch verify")
    p.add_argument("--limit", type=int)
    p.add_argument("--block", help="filter category (policy/growth/inflation/etc)")
    p.add_argument("--json", action="store_true", help="JSON output (for CI)")
    args = p.parse_args(argv)

    rep = verify(limit=args.limit, block=args.block)
    ts = datetime.now(UTC).isoformat(timespec="seconds")
    if args.json:
        print(
            json.dumps(
                {
                    "ts": ts,
                    "checked": rep.checked,
                    "violations": [asdict(r) for r in rep.violations],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(
            f"=== verify-sources {ts} · checked={rep.checked} · violations={len(rep.violations)} ==="
        )
        for r in rep.rows:
            print(
                f"{r.series_id:<26} anchor={r.anchor:<18} sanity={r.sanity:<12} depth={r.depth:<10} "
                f"xval={r.crossval:<10} {r.note}"
            )
    return 1 if rep.violations else 0


if __name__ == "__main__":
    sys.exit(main())
