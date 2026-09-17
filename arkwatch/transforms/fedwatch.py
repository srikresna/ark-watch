"""fedwatch.py — FedWatch-DIY: per-meeting probabilities from ZQ settlements.

Math (vendored from the cme-fedwatch MIT package, with corrections):
  implied = 100 - settle
  pre_rate = implied of the previous month (EFFR fallback for the front month)
  post_rate = (implied*D - pre_rate*(d-1)) / (D-d+1)
    D = days in the contract month, d = FOMC meeting day
    if D-d+1 <= 3: use the NEXT month's implied (end-of-month trick)
  expected_moves = (post - pre) / 0.25
  probability = fraction of a 25bp move

Corrections vs the PyPI package:
  - Do NOT use get_history() (it applies today's EFFR to past dates)
  - Probabilities are normalized (Σ=1)
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

FOMC_SCHEDULE = [
    # Vendored from cme-fedwatch; verified against federalreserve.gov
    # 2026
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 9),
    # 2027 (tentative)
    date(2027, 1, 27),
    date(2027, 3, 17),
    date(2027, 4, 28),
    date(2027, 6, 16),
    date(2027, 7, 28),
    date(2027, 9, 15),
    date(2027, 10, 27),
    date(2027, 12, 8),
]


@dataclass
class MeetingProb:
    meeting_date: date
    implied_rate: float  # rate after the meeting
    prob_ease: float  # P(cut ≥25bp)
    prob_hold: float  # P(no change)
    prob_hike: float  # P(hike ≥25bp)
    expected_moves: float  # (post-pre)/0.25


def month_code(y: int, m: int) -> str:
    """CME month code: JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC."""
    names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    return f"{names[m - 1]} {str(y)[2:]}"


def compute(
    settlements: dict[str, float],
    effr: float,
    meetings: list[date] | None = None,
    anchor_date: date | None = None,
) -> list[MeetingProb]:
    """Per-meeting probabilities along the chronological path (running rate).

    settlements: {month_code: settle_price}, e.g. {"SEP 26": 96.35, "OCT 26": 96.14}
    effr: current effective fed funds rate (pct, e.g. 3.63)
    anchor_date: observation date of `effr` (production passes it — see the
        stale-anchor self-heal below)

    The pre-rate for meeting N is the rate in effect at the start of meeting
    N's month — i.e. the post-rate of meeting N-1 (running) — NOT the implied
    of month M-1: a ZQ implied is the MONTHLY AVERAGE of EFFR, so when month
    M-1 contains a meeting, its implied blends in pre-meeting days.
    Numerical example (Sep-26 cut fully priced, Oct priced as hold): correct
    pre 4.08 → hold 100%; wrong pre 4.205 → "cut 100%" for a meeting the
    market prices as a hold.

    Stale-anchor self-heal (2026-09-17 incident): DFF prints T+1, so between
    a rate change and the next print `effr` is still the OLD rate. The
    D/n_post extraction amplifies that anchor error by ~D/n_post (live:
    ×31/4 → Oct-26 "implied" 5.53% the morning after the Sep-16 hike to
    3.88). When anchor_date predates a just-held meeting, that meeting is
    re-run FIRST so the running rate bootstraps the new level from the strip
    itself (live: (3.7375·30 − 3.63·15)/15 = 3.845 = the post-hike level).
    The anchor counts as the PRE-rate through the decision day itself — a
    same-day DFF still prints the old rate because the new target takes
    effect the following day.
    """
    today = date.today()
    if meetings is None:
        loop = [m for m in FOMC_SCHEDULE if m >= today]
        if anchor_date is not None:
            loop = [m for m in FOMC_SCHEDULE if anchor_date <= m < today] + loop
        future_only = True
    else:
        loop = list(meetings)
        future_only = False
    meetings = sorted(loop)
    implied = {k.strip().upper(): 100.0 - v for k, v in settlements.items() if v is not None}

    running = effr  # rate currently in effect
    results = []
    for mtg in meetings:
        m, y = mtg.month, mtg.year
        D = calendar.monthrange(y, m)[1]
        d = mtg.day
        n_post = D - d + 1

        key_cur = month_code(y, m)
        key_next = month_code(y, m + 1) if m < 12 else month_code(y + 1, 1)

        if key_cur not in implied:
            continue  # no contract for this month

        rate_cur = implied[key_cur]
        pre_rate = running

        # post_rate
        if n_post <= 3:
            if key_next in implied:
                post_rate = implied[key_next]  # end-of-month trick
            else:
                # A divisor <= 3 without a next-month contract amplifies
                # settlement noise ~10x; skip rather than extract a
                # degenerate value.
                continue
        else:
            n_pre = d - 1
            post_rate = (rate_cur * D - pre_rate * n_pre) / n_post

        running = post_rate  # new rate in effect after this meeting

        # expected moves in 25bp units
        expected = (post_rate - pre_rate) / 0.25
        delta = post_rate - pre_rate

        # Probability as the fraction of a 25bp move (|delta|/0.25 capped to
        # 0-1) — more realistic than a linear split across a 25bp outcome grid.
        if abs(delta) < 0.01:  # <1bp = essentially no change
            prob_hold = 1.0
            prob_ease = prob_hike = 0.0
        elif delta > 0:  # hike
            prob_hike = min(1.0, delta / 0.25)
            prob_hold = max(0.0, 1.0 - prob_hike)
            prob_ease = 0.0
        else:  # cut
            prob_ease = min(1.0, abs(delta) / 0.25)
            prob_hold = max(0.0, 1.0 - prob_ease)
            prob_hike = 0.0

        results.append(
            MeetingProb(
                meeting_date=mtg,
                implied_rate=post_rate,
                prob_ease=round(prob_ease, 4),
                prob_hold=round(prob_hold, 4),
                prob_hike=round(prob_hike, 4),
                expected_moves=round(expected, 2),
            )
        )
    if future_only:
        # the bootstrap meetings are machinery — only future meetings are
        # a probability statement
        results = [r for r in results if r.meeting_date >= today]
        # Degenerate tripwire (production path only — explicit `meetings`
        # callers get the raw math): no FOMC meeting in history moved
        # >100bp, so a row beyond 4 moves is an artifact (stale anchor, bad
        # settle), never a probability. Drop it loudly so the brief degrades
        # to "ZQ data unavailable" instead of printing a 5.53% implied
        # (2026-09-17 class).
        sane = [r for r in results if abs(r.expected_moves) <= 4.0]
        for r in results:
            if abs(r.expected_moves) > 4.0:
                print(
                    f"  ⚠ fedwatch: degenerate row dropped {r.meeting_date} "
                    f"({r.expected_moves:+.1f} moves, implied {r.implied_rate:.2f})"
                )
        return sane
    return results


def format_brief(probs: list[MeetingProb], asof: str | None = None) -> str:
    """Format the brief line for the next FOMC meeting.

    asof = the snapshot's ZQ trade date (round-2: the line rendered the
    pre-FOMC-decision strip as CURRENT policy the morning after the hike —
    the reader cannot know the pricing vintage without the date)."""
    if not probs:
        has_future = any(d >= date.today() for d in FOMC_SCHEDULE)
        if has_future:
            return "FedWatch: ZQ data unavailable"
        return "FedWatch: vendored FOMC schedule exhausted — UPDATE FOMC_SCHEDULE"
    p = probs[0]
    if p.prob_ease > 0.5:
        action = f"cut {p.prob_ease:.0%}"
    elif p.prob_hike > 0.5:
        action = f"hike {p.prob_hike:.0%}"
    else:
        action = f"hold {p.prob_hold:.0%}"
    tail = f" (ZQ {asof[5:]})" if asof else ""
    if max(FOMC_SCHEDULE) < date.today() + timedelta(days=90):
        tail += " ⚠ vendored schedule <90 days"
    return f"{action} ({p.meeting_date.strftime('%b')} → {p.implied_rate:.2f}%){tail}"
