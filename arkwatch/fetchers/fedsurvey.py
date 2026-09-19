"""fedsurvey.py — Federal Reserve qualitative surveys + reports fetcher.

Sources handled (all from federalreserve.gov):
  SLOOS  — Senior Loan Officer Opinion Survey (quarterly, narrative HTML)
  Beige Book — Regional economic conditions (8x/year, HTML summary + PDF)
  SCOOS  — Senior Credit Officer Opinion Survey (quarterly, narrative HTML)
  FSR    — Financial Stability Report (semi-annual, PDF)
  SHED   — Survey of Household Economics (annual, HTML)
  MPR    — Monetary Policy Report (semi-annual, PDF)

Each source returns {'text': str, 'ts': str, 'meta': dict} that plugs
directly into the NLP analysis layer (nlp.py analyze_tone/extract_data).
"""
from __future__ import annotations

import re
import html as _html

import requests

BASE = "https://www.federalreserve.gov"


class FedSurveyError(RuntimeError):
    pass


def _clean(html_text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_text)
    return re.sub(r"\s+", " ", _html.unescape(text)).strip()


def _fetch(url: str) -> str:
    r = requests.get(url, timeout=(10, 60))
    if r.status_code != 200:
        raise FedSurveyError(f"HTTP {r.status_code}: {url[-60:]}")
    return r.text


# --- SLOOS ----------------------------------------------------------------------


def sloos_urls() -> list[str]:
    """All SLOOS survey report URLs (newest first)."""
    html = _fetch(f"{BASE}/data/sloos.htm")
    dates = sorted(set(re.findall(r"sloos-(\d{6})\.htm", html)), reverse=True)
    return [f"{BASE}/data/sloos/sloos-{d}.htm" for d in dates]


def fetch_sloos(yyyymm: str | None = None) -> dict:
    """SLOOS survey → {'text': str, 'ts': str, 'source': 'sloos'}.

    yyyymm: e.g. '202607' (July 2026). None = latest.
    """
    if yyyymm is None:
        urls = sloos_urls()
        if not urls:
            raise FedSurveyError("SLOOS: no surveys found")
        url = urls[0]
        yyyymm = re.search(r"sloos-(\d{6})", url).group(1)
    else:
        url = f"{BASE}/data/sloos/sloos-{yyyymm}.htm"

    text = _clean(_fetch(url))
    if len(text) < 500:
        raise FedSurveyError(f"SLOOS {yyyymm}: too short ({len(text)} chars)")
    return {
        "text": text,
        "ts": f"{yyyymm[:4]}-{yyyymm[4:]}-01",
        "source": "sloos",
        "url": url,
    }


def sloos_tone_metrics(text: str) -> dict:
    """Extract tightening/easing counts from SLOOS narrative (structural).

    Returns {'tightened': int, 'eased': int, 'stronger_demand': int,
             'weaker_demand': int, 'net_bias': str}.
    """
    lower = text.lower()
    tightened = lower.count("tightened")
    eased = lower.count("eased")
    stronger = lower.count("stronger") + lower.count("increased somewhat")
    weaker = lower.count("weaker") + lower.count("decreased somewhat")
    net = "tightening" if tightened > eased else ("easing" if eased > tightened else "unchanged")
    return {
        "tightened": tightened,
        "eased": eased,
        "stronger_demand": stronger,
        "weaker_demand": weaker,
        "net_bias": net,
    }


# --- Beige Book ------------------------------------------------------------------


def beige_book_urls() -> list[str]:
    """All Beige Book summary page URLs (newest first)."""
    html = _fetch(f"{BASE}/monetarypolicy/publications/beige-book-default.htm")
    dates = sorted(set(re.findall(r"beigebook(\d{6})-summary\.htm", html)), reverse=True)
    return [f"{BASE}/monetarypolicy/beigebook{d}-summary.htm" for d in dates]


def fetch_beige_book(yyyymm: str | None = None) -> dict:
    """Beige Book summary → {'text': str, 'ts': str, 'source': 'beige_book'}.

    yyyymm: e.g. '202608' (August 2026). None = latest.
    """
    if yyyymm is None:
        urls = beige_book_urls()
        if not urls:
            raise FedSurveyError("Beige Book: no reports found")
        url = urls[0]
        yyyymm = re.search(r"beigebook(\d{6})", url).group(1)
    else:
        url = f"{BASE}/monetarypolicy/beigebook{yyyymm}-summary.htm"

    text = _clean(_fetch(url))
    # strip navigation boilerplate (first ~800 chars is usually nav)
    if len(text) > 2000:
        # find the start of actual content
        for marker in ("Summary", "Economic activity", "Reports from"):
            i = text.find(marker)
            if 500 < i < 3000:
                text = text[i:]
                break
    if len(text) < 500:
        raise FedSurveyError(f"Beige Book {yyyymm}: too short ({len(text)} chars)")
    return {
        "text": text,
        "ts": f"{yyyymm[:4]}-{yyyymm[4:]}-01",
        "source": "beige_book",
        "url": url,
    }


# --- SCOOS -----------------------------------------------------------------------


def scoos_urls() -> list[str]:
    """All SCOOS report URLs."""
    html = _fetch(f"{BASE}/data/scoos.htm")
    dates = sorted(set(re.findall(r"scoos-(\d{6})\.htm", html)), reverse=True)
    return [f"{BASE}/data/scoos/scoos-{d}.htm" for d in dates]


def fetch_scoos(yyyymm: str | None = None) -> dict:
    """SCOOS → {'text': str, 'ts': str, 'source': 'scoos'}."""
    if yyyymm is None:
        urls = scoos_urls()
        if not urls:
            raise FedSurveyError("SCOOS: no surveys found")
        url = urls[0]
        yyyymm = re.search(r"scoos-(\d{6})", url).group(1)
    else:
        url = f"{BASE}/data/scoos/scoos-{yyyymm}.htm"
    text = _clean(_fetch(url))
    return {"text": text, "ts": f"{yyyymm[:4]}-{yyyymm[4:]}-01", "source": "scoos", "url": url}


# --- Financial Stability Report -----------------------------------------------------


def fetch_fsr() -> dict:
    """Financial Stability Report → PDF text extraction + metadata.

    Semi-annual (Apr + Nov). Returns {'text': str, 'ts': str, 'source': 'fsr'}.
    """
    html = _fetch(f"{BASE}/publications/financial-stability-report.htm")
    pdfs = re.findall(r'href="(/publications/files/financial-stability-report-(\d{8})\.pdf)"', html)
    if not pdfs:
        raise FedSurveyError("FSR: no PDF links found")
    pdf_path, date = sorted(pdfs, key=lambda x: x[1], reverse=True)[0]

    r = requests.get(f"{BASE}{pdf_path}", timeout=(10, 120))
    if r.status_code != 200 or r.content[:4] != b"%PDF":
        raise FedSurveyError(f"FSR: PDF fetch failed ({r.status_code})")

    import pymupdf

    doc = pymupdf.open(stream=r.content, filetype="pdf")
    text = " ".join(page.get_text() for page in doc)
    doc.close()
    text = re.sub(r"\s+", " ", text).strip()

    return {
        "text": text[:50000],  # cap for NLP context limits
        "ts": f"{date[:4]}-{date[4:6]}-{date[6:]}",
        "source": "fsr",
        "url": f"{BASE}{pdf_path}",
    }


# --- Charge-off & Delinquency ------------------------------------------------------


def fetch_chargeoff() -> list[dict]:
    """Charge-off & delinquency rates → [{series, ts, value, unit}].

    Quarterly SDMX XML (CHGDEL_data.xml inside a zip). Returns the key
    consumer credit series: charge-off + delinquency rates for credit card,
    auto, real estate, and all loans (ALL banks, NSA).
    """
    import io
    import zipfile
    from defusedxml.ElementTree import fromstring as parse_xml

    url = f"{BASE}/releases/chargeoff/data/FRB_CHGDEL_xml.zip"
    r = requests.get(url, timeout=(10, 120))
    if r.status_code != 200:
        raise FedSurveyError(f"Charge-off: HTTP {r.status_code}")

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    # the DATA file is CHGDEL_data.xml (first file is the XSD schema)
    data_xml = next(n for n in zf.namelist() if "data" in n.lower())
    root = parse_xml(zf.read(data_xml))

    # SDMX namespace — actual codes (live-verified from the XML):
    #   LOANTYPE: CONCC=credit card, CONALL=consumer, REALL=real estate,
    #             RERES=residential RE, CI=C&I, TOTAL=all, LEASE, AG, ...
    #   COMPONENT: RATIO=percentage rate (what we want), NUM=$, DEN=denominator
    #   CHGDEL: CHG=charge-off, DEL=delinquency
    #   SA: SA=seasonally adjusted, NSA=not
    _LOAN_LABELS = {
        "CONCC": "credit_card",
        "CONALL": "consumer",
        "REALL": "real_estate",
        "RERES": "residential_re",
        "CI": "commercial_industrial",
        "TOTAL": "all_loans",
    }
    out: list[dict] = []
    for series_elem in root.iter():
        if not series_elem.tag.endswith("Series"):
            continue
        attrs = series_elem.attrib
        # only RATIO (percentage), ALL banks, SA
        if attrs.get("COMPONENT") != "RATIO":
            continue
        if attrs.get("SIZE") != "ALL":
            continue
        if attrs.get("SA") != "SA":
            continue
        loan_type = attrs.get("LOANTYPE", "")
        metric = attrs.get("CHGDEL", "")
        if loan_type not in _LOAN_LABELS:
            continue
        label = f"chgoff_{metric.lower()}_{_LOAN_LABELS[loan_type]}"

        for obs in series_elem:
            ts = obs.get("TIME_PERIOD", "")
            val = obs.get("OBS_VALUE", "")
            if ts and val:
                try:
                    out.append({
                        "series": label,
                        "ts": ts,
                        "value": float(val),
                        "unit": "pct",
                    })
                except (ValueError, TypeError):
                    pass
    return out


# --- Convenience: analyze any survey with NLP ----------------------------------------


def analyze_survey(source: str, yyyymm: str | None = None) -> dict:
    """Fetch + NLP-analyze any Federal Reserve survey/report.

    source: 'sloos' | 'beige_book' | 'scoos' | 'fsr'
    Returns {'text': ..., 'tone': {...}, 'metrics': {...}}.
    """
    fetchers = {
        "sloos": fetch_sloos,
        "beige_book": fetch_beige_book,
        "scoos": fetch_scoos,
        "fsr": fetch_fsr,
    }
    if source not in fetchers:
        raise FedSurveyError(f"unknown source: {source} (sloos|beige_book|scoos|fsr)")

    data = fetchers[source](yyyymm) if source != "fsr" else fetch_fsr()

    # structural metrics (SLOOS-specific)
    metrics = sloos_tone_metrics(data["text"]) if source == "sloos" else {}

    # NLP tone analysis
    from .nlp import analyze_tone

    try:
        tone = analyze_tone(data["text"], source_type=source.replace("_", " "))
    except Exception as ex:
        tone = {"error": str(ex)[:100]}

    return {**data, "tone": tone, "metrics": metrics}
