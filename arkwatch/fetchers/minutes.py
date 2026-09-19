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

import html as _html
import json
import os
import re

import requests

BASE = "https://www.federalreserve.gov/monetarypolicy/fomcminutes"
CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
# Anthropic-compatible endpoint (owner's Claude Code plan — same token,
# same billing pool as the interactive session)
ZAI_ENDPOINT = "https://api.z.ai/api/anthropic/v1/messages"

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


def _get_nlp_config() -> dict:
    """Resolve NLP provider from env — multi-provider by design.

    Supported providers (set NLP_PROVIDER):
      zai        — z.ai GLM via Anthropic Messages API (default)
      openai     — OpenAI GPT via chat completions (needs OPENAI_API_KEY)
      anthropic  — Anthropic Claude via Messages API (needs ANTHROPIC_API_KEY)
      custom     — any OpenAI-compatible endpoint (needs NLP_BASE_URL + NLP_API_KEY)

    Override-able per-call via env vars — swap providers without code changes.
    """
    provider = os.environ.get("NLP_PROVIDER", "zai").lower()
    model = os.environ.get("NLP_MODEL", "")
    base_url = os.environ.get("NLP_BASE_URL", "")
    api_key = os.environ.get("NLP_API_KEY", "")

    if provider == "zai":
        return {
            "endpoint": base_url or "https://api.z.ai/api/anthropic/v1/messages",
            "api_key": api_key or os.environ.get("ZAI_API_KEY") or os.environ.get("Z_AI_API_KEY", ""),
            "model": model or "glm-5.3",
            "format": "anthropic",  # Anthropic Messages API
        }
    if provider == "openai":
        return {
            "endpoint": base_url or "https://api.openai.com/v1/chat/completions",
            "api_key": api_key or os.environ.get("OPENAI_API_KEY", ""),
            "model": model or "gpt-4o",
            "format": "openai",
        }
    if provider == "anthropic":
        return {
            "endpoint": base_url or "https://api.anthropic.com/v1/messages",
            "api_key": api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
            "model": model or "claude-sonnet-5",
            "format": "anthropic",
        }
    if provider == "custom":
        if not base_url:
            raise MinutesError("NLP_PROVIDER=custom requires NLP_BASE_URL")
        return {
            "endpoint": base_url,
            "api_key": api_key,
            "model": model or "default",
            "format": os.environ.get("NLP_FORMAT", "openai"),  # openai | anthropic
        }
    raise MinutesError(f"unknown NLP_PROVIDER: {provider} (zai|openai|anthropic|custom)")


def _call_llm(cfg: dict, system: str, user: str) -> str:
    """Route to the correct API format and extract the text response."""
    if cfg["format"] == "anthropic":
        r = requests.post(
            cfg["endpoint"],
            headers={
                "Content-Type": "application/json",
                "x-api-key": cfg["api_key"],
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": cfg["model"],
                "max_tokens": 4096,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=(10, 180),
        )
        if r.status_code != 200:
            raise MinutesError(f"NLP: HTTP {r.status_code} — {r.text[:100]}")
        blocks = r.json().get("content", [])
        return next((b.get("text", "") for b in blocks if b.get("type") == "text"), "")

    # openai format (default for most providers)
    r = requests.post(
        cfg["endpoint"],
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
        json={
            "model": cfg["model"],
            "max_tokens": 4096,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=(10, 180),
    )
    if r.status_code != 200:
        raise MinutesError(f"NLP: HTTP {r.status_code} — {r.text[:100]}")
    return r.json()["choices"][0]["message"]["content"]


def nlp_sentiment(text: str, api_key: str | None = None) -> dict:
    """NLP sentiment — multi-provider (z.ai GLM / OpenAI / Anthropic / custom).

    Returns {"score": float, "summary": str, "key_concerns": [str]}.
    Score: −100 (max dovish) .. +100 (max hawkish).

    Provider selection via NLP_PROVIDER env (default: zai). Model, endpoint,
    and key all overridable — see _get_nlp_config(). The api_key parameter
    overrides the env-resolved key (backward-compat for direct calls).
    """
    cfg = _get_nlp_config()
    if api_key:
        cfg["api_key"] = api_key
    if not cfg["api_key"]:
        raise MinutesError(
            f"NLP_API_KEY not set for provider '{os.environ.get('NLP_PROVIDER', 'zai')}'"
        )

    discussion = text[:12000]
    prompt = f"""Analyze this FOMC minutes text for monetary policy tone.

Rate the overall tone on a scale from -100 (maximally dovish: rate cuts, easing concern) to +100 (maximally hawkish: inflation fighting, tightening bias).

Also identify the top 3 specific concerns discussed.

Respond in this exact JSON format:
{{"score": <number>, "summary": "<one sentence>", "key_concerns": ["<concern1>", "<concern2>", "<concern3>"]}}

FOMC MINUTES TEXT:
{discussion}"""

    content = _call_llm(
        cfg,
        system="You are a central bank policy analyst. Respond ONLY with valid JSON, no markdown.",
        user=prompt,
    )
    if not content:
        raise MinutesError("NLP: empty response")
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
