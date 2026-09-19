"""minutes.py — FOMC minutes parser + NLP sentiment harness (z.ai GLM).

Two layers:
  1. STRUCTURAL parse (pure regex — no AI needed): dissent count, voter
     lists, decision text, key-phrase frequencies, meeting metadata.
  2. NLP sentiment layer (z.ai GLM): hawkish/dovish tone score from the
     full Discussion section, calibrated to a −100..+100 scale.

URL pattern (live-verified): fomcminutes{YYYYMMDD}.htm where date = the
meeting's END date. Minutes publish ~3 weeks after the meeting.
"""
from __future__ import annotations

import json
import os
import re
import html as _html
from datetime import UTC, datetime

import requests

BASE = "https://www.federalreserve.gov/monetarypolicy/fomcminutes"
CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
ZAI_ENDPOINT = "https://api.z.ai/api/paas/v4/chat/completions"

# Hawkish/dovish keyword pairs for the structural tone score
_HAWKISH = (
    "raise", "hike", "increase the target", "tighten", "inflation remains elevated",
    "price stability", "upside risks to inflation", "restrictive",
    "resilient", "solid pace", "robust", "strong demand",
)
_DOVISH = (
    "lower", "cut", "reduce the target", "ease", "inflation is easing",
    "downside risks", "accommodative", "slowdown", "weakening",
    "softening", "labor market cooling",
)


class MinutesError(RuntimeError):
    pass


def _fetch(date_iso: str) -> str:
    r = requests.get(f"{BASE}{date_iso.replace('-', '')}.htm", timeout=(10, 60))
    if r.status_code != 200:
        raise MinutesError(f"minutes {date_iso}: HTTP {r.status_code}")
    return r.text


def _clean(html_text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_text)
    return re.sub(r"\s+", " ", _html.unescape(text))


def parse_minutes(date_iso: str) -> dict:
    """Structural parse: metadata + dissent + tone keywords + decision.

    Returns:
    {
        "meeting_date": str,
        "decision": str,             # the rate decision text
        "voters_for": [str],
        "voters_against": [str],
        "dissent_count": int,
        "dissent_direction": str,    # "hawkish" | "dovish" | ""
        "hawkish_count": int,
        "dovish_count": int,
        "tone_score": float,          # −100..+100 (structural, keyword-based)
        "full_text": str,            # cleaned text (for NLP layer)
    }
    """
    raw = _fetch(date_iso)
    text = _clean(raw)

    # --- decision ---
    di = text.find("members agreed")
    decision = text[di : di + 300] if di > 0 else ""

    # --- voting ---
    vi = text.find("Voting for this action:")
    voters_for, voters_against = [], []
    dissent_direction = ""
    if vi > 0:
        block = text[vi : vi + 800]
        fi = block.find("Voting against")
        if fi > 0:
            for_chunk = block[len("Voting for this action:") : fi]
            voters_for = [n.strip().rstrip(".") for n in for_chunk.split(",") if n.strip()]
            # dissent: stop at the first non-name token (Board/Consistent/effective)
            against_raw = block[fi + len("Voting against this action:") :]
            stop_kw = ("Consistent with", "the Board", "effective", "In addition")
            stop_at = len(against_raw)
            for kw in stop_kw:
                ki = against_raw.find(kw)
                if 0 < ki < stop_at:
                    stop_at = ki
            against_chunk = against_raw[:stop_at]
            if "preferred to raise" in against_raw:
                dissent_direction = "hawkish"
            elif "preferred to lower" in against_raw or "preferred a lower" in against_raw:
                dissent_direction = "dovish"
            # names only: split on comma, keep tokens that look like names
            # (title-case, 2+ words, no verbs/articles)
            for n in against_chunk.split(","):
                n = n.strip().rstrip(".")
                if n.lower().startswith("and "):
                    n = n[4:]
                words = n.split()
                if (
                    len(words) >= 2
                    and all(w[0].isupper() or w in ("van", "de", "der") for w in words if w)
                    and not any(v in n.lower() for v in ("board", "voted", "effective", "addition", "consistent", "who preferred"))
                ):
                    voters_against.append(n)

    # --- keyword tone score ---
    lower = text.lower()
    hawk = sum(lower.count(k) for k in _HAWKISH)
    dove = sum(lower.count(k) for k in _DOVISH)
    total_kw = hawk + dove
    tone = ((hawk - dove) / total_kw * 100) if total_kw else 0.0

    return {
        "meeting_date": date_iso,
        "decision": decision[:200],
        "voters_for": voters_for[:15],
        "voters_against": voters_against[:5],
        "dissent_count": len(voters_against),
        "dissent_direction": dissent_direction,
        "hawkish_count": hawk,
        "dovish_count": dove,
        "tone_score": round(tone, 1),
        "full_text": text,
    }


def nlp_sentiment(text: str, api_key: str | None = None) -> dict:
    """NLP sentiment via z.ai GLM — hawkish/dovish tone from full minutes.

    Returns {"score": float, "summary": str, "key_concerns": [str]}.
    Score: −100 (max dovish) .. +100 (max hawkish).
    """
    key = api_key or os.environ.get("ZAI_API_KEY") or os.environ.get("Z_AI_API_KEY")
    if not key:
        raise MinutesError("ZAI_API_KEY not set — NLP layer unavailable")

    # Truncate to ~12k chars (the Discussion section is the meat)
    discussion = text[:12000]
    prompt = f"""Analyze this FOMC minutes text for monetary policy tone.

Rate the overall tone on a scale from -100 (maximally dovish: rate cuts, easing concern) to +100 (maximally hawkish: inflation fighting, tightening bias).

Also identify the top 3 specific concerns discussed.

Respond in this exact JSON format:
{{"score": <number>, "summary": "<one sentence>", "key_concerns": ["<concern1>", "<concern2>", "<concern3>"]}}

FOMC MINUTES TEXT:
{discussion}"""

    r = requests.post(
        ZAI_ENDPOINT,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        json={
            "model": "glm-4.6",
            "messages": [{"role": "user", "content": prompt}],
            "thinking": {"type": "disabled"},
            "max_tokens": 500,
            "temperature": 0.3,
        },
        timeout=(10, 120),
    )
    if r.status_code != 200:
        raise MinutesError(f"z.ai: HTTP {r.status_code} — {r.text[:100]}")

    content = r.json()["choices"][0]["message"]["content"]
    # extract JSON from response (model may wrap in markdown)
    jm = re.search(r"\{.*\}", content, re.DOTALL)
    if not jm:
        raise MinutesError(f"z.ai: no JSON in response — {content[:100]}")
    try:
        return json.loads(jm.group())
    except json.JSONDecodeError:
        return {"score": 0.0, "summary": content[:200], "key_concerns": []}


def minutes_dates() -> list[str]:
    """All minutes release dates (meeting end-dates) from the calendar."""
    r = requests.get(CALENDAR_URL, timeout=(10, 60))
    if r.status_code != 200:
        raise MinutesError(f"FOMC calendar: HTTP {r.status_code}")
    dates = sorted(set(re.findall(r"fomcminutes(\d{8})\.htm", r.text)), reverse=True)
    return [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in dates]
