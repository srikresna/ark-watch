"""Cross-source market news collection with deterministic clustering."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .. import db as _db
from .fetch_log import log_collection

SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(total=1, connect=1, read=1, status=1, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",), respect_retry_after_header=True)))
TOPICS = ("fed", "inflation", "oil", "bitcoin", "ethereum", "war", "tariff", "yield", "treasury", "jobs", "china")
GDELT_EVENT_FIELDS = (
    "GlobalEventID", "SQLDATE", "MonthYear", "Year", "FractionDate",
    "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode",
    "Actor1EthnicCode", "Actor1Religion1Code", "Actor1Religion2Code",
    "Actor1Type1Code", "Actor1Type2Code", "Actor1Type3Code", "Actor2Code",
    "Actor2Name", "Actor2CountryCode", "Actor2KnownGroupCode",
    "Actor2EthnicCode", "Actor2Religion1Code", "Actor2Religion2Code",
    "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code", "IsRootEvent",
    "EventCode", "EventBaseCode", "EventRootCode", "QuadClass", "GoldsteinScale",
    "NumMentions", "NumSources", "NumArticles", "AvgTone", "Actor1Geo_Type",
    "Actor1Geo_FullName", "Actor1Geo_CountryCode", "Actor1Geo_ADM1Code",
    "Actor1Geo_ADM2Code", "Actor1Geo_Lat", "Actor1Geo_Long",
    "Actor1Geo_FeatureID", "Actor2Geo_Type", "Actor2Geo_FullName",
    "Actor2Geo_CountryCode", "Actor2Geo_ADM1Code", "Actor2Geo_ADM2Code",
    "Actor2Geo_Lat", "Actor2Geo_Long", "Actor2Geo_FeatureID", "ActionGeo_Type",
    "ActionGeo_FullName", "ActionGeo_CountryCode", "ActionGeo_ADM1Code",
    "ActionGeo_ADM2Code", "ActionGeo_Lat", "ActionGeo_Long",
    "ActionGeo_FeatureID", "DATEADDED", "SOURCEURL",
)
GDELT_MENTION_FIELDS = (
    "GlobalEventID", "EventTimeDate", "MentionTimeDate", "MentionType",
    "MentionSourceName", "MentionIdentifier", "SentenceID", "Actor1CharOffset",
    "Actor2CharOffset", "ActionCharOffset", "InRawText", "Confidence",
    "MentionDocLen", "MentionDocTone", "MentionDocTranslationInfo", "Extras",
)
GDELT_GKG_FIELDS = (
    "GKGRECORDID", "DATE", "SourceCollectionIdentifier", "SourceCommonName",
    "DocumentIdentifier", "Counts", "V2Counts", "Themes", "V2Themes",
    "Locations", "V2Locations", "Persons", "V2Persons", "Organizations",
    "V2Organizations", "V2Tone", "Dates", "GCAM", "SharingImage",
    "RelatedImages", "SocialImageEmbeds", "SocialVideoEmbeds", "Quotations",
    "AllNames", "Amounts", "TranslationInfo", "Extras",
)


def _time(value: str | None) -> str:
    raw = value or ""
    try:
        if re.fullmatch(r"\d{8}T\d{6}Z", raw):
            dt = datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        else:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.replace(tzinfo=dt.tzinfo or UTC).astimezone(UTC).isoformat(timespec="seconds")
    except ValueError as ex:
        raise ValueError(f"invalid news timestamp: {raw[:40]}") from ex


def _tokens(title: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", title.lower())) - {"the", "and", "for", "with", "from", "after", "says"}


def _canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def _cluster(conn, title: str) -> tuple[str, float]:
    tokens = _tokens(title)
    best = None
    best_score = 0.0
    for old_title, cluster_id in conn.execute("SELECT title,cluster_id FROM market_news WHERE published_at_utc >= datetime('now','-48 hours') ORDER BY published_at_utc DESC LIMIT 1000"):
        other = _tokens(old_title)
        score = len(tokens & other) / max(1, len(tokens | other))
        if score > best_score:
            best, best_score = cluster_id, score
    cluster_id = best if best_score >= 0.70 else hashlib.sha256(" ".join(sorted(tokens)).encode()).hexdigest()[:20]
    count = conn.execute("SELECT COUNT(*) FROM market_news WHERE cluster_id=?", (cluster_id,)).fetchone()[0]
    return cluster_id, 1.0 / (count + 1)


def _fmp() -> list[dict]:
    key = os.environ.get("FMP_API_KEY", "")
    if not key:
        return []
    r = SESSION.get("https://financialmodelingprep.com/stable/news/general-latest", params={"apikey": key}, timeout=(10, 45))
    r.raise_for_status()
    return [{"source": "FMP", "title": x.get("title", ""), "url": x.get("url"), "summary": x.get("text", ""), "published": x.get("publishedDate"), "symbols": str(x.get("symbol") or "").split(","), "provider_payload": x} for x in r.json() if x.get("title")]


def _eodhd() -> list[dict]:
    key = os.environ.get("EODHD_API_TOKEN", "")
    if not key:
        return []
    def fetch(ticker: str) -> list[dict] | None:
        try:
            r = SESSION.get("https://eodhd.com/api/news", params={"api_token": key, "s": ticker, "fmt": "json", "limit": 50}, timeout=(5, 20))
            r.raise_for_status()
        except requests.RequestException:
            return None
        return [{"source": "EODHD", "title": x.get("title", ""), "url": x.get("link"), "summary": x.get("content", ""), "published": x.get("date"), "symbols": [ticker], "provider_payload": x} for x in r.json() if x.get("title")]

    out = []
    succeeded = 0
    tickers = ("BTC-USD.CC", "ETH-USD.CC", "SPY.US", "NDX.INDX", "CL.COMM", "XAUUSD.FOREX")
    with ThreadPoolExecutor(max_workers=len(tickers)) as pool:
        futures = [pool.submit(fetch, ticker) for ticker in tickers]
        for future in as_completed(futures):
            rows = future.result()
            if rows is not None:
                succeeded += 1
                out.extend(rows)
    if not succeeded:
        raise RuntimeError("all EODHD news targets failed")
    return out


def _number(value: str, kind=float):
    try:
        return kind(value)
    except (TypeError, ValueError):
        return None


def _gdelt_feed(feed: str) -> list[list[str]]:
    update = SESSION.get("https://data.gdeltproject.org/gdeltv2/lastupdate.txt", timeout=(10, 45))
    update.raise_for_status()
    suffix = f".{feed}.CSV.zip" if feed == "mentions" else f".{feed}.csv.zip"
    url = next(line.split()[-1] for line in update.text.splitlines() if line.split()[-1].lower().endswith(suffix.lower()))
    match = re.search(r"(\d{14})(?=" + re.escape(suffix) + r"$)", url, re.IGNORECASE)
    if not match:
        raise RuntimeError(f"GDELT lastupdate returned an unrecognized {feed} URL")
    stamp = datetime.strptime(match.group(1), "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    response = None
    for offset in range(9):
        candidate_stamp = (stamp - timedelta(minutes=15 * offset)).strftime("%Y%m%d%H%M%S")
        candidate_url = url[:match.start(1)] + candidate_stamp + url[match.end(1):]
        candidate = SESSION.get(candidate_url.replace("http://", "https://", 1), timeout=(10, 120))
        if candidate.status_code == 404:
            continue
        candidate.raise_for_status()
        if not candidate.content.startswith(b"PK"):
            raise RuntimeError(f"GDELT {feed} response is not a ZIP archive")
        if offset > 2:
            raise RuntimeError(f"GDELT {feed} latest available file is more than 30 minutes behind")
        response = candidate
        break
    if response is None:
        raise RuntimeError(f"no available GDELT {feed} file in the latest two-hour window")
    out: list[list[str]] = []
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        name = archive.namelist()[0]
        with archive.open(name) as raw:
            rows = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", errors="replace"), delimiter="\t")
            for row in rows:
                if row:
                    out.append(row)
    return out


def _gdelt_fields(row: list[str], names: tuple[str, ...]) -> dict:
    result = dict(zip(names, row[:len(names)], strict=False))
    if len(row) > len(names):
        result["_extra_columns"] = row[len(names):]
    return result


def _gdelt_events(rows: list[list[str]]) -> list[tuple]:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    out = []
    for row in rows:
        if len(row) < 61:
            continue
        added = datetime.strptime(row[59], "%Y%m%d%H%M%S").replace(tzinfo=UTC).isoformat(timespec="seconds")
        raw = _gdelt_fields(row, GDELT_EVENT_FIELDS)
        out.append((row[0], row[1], added, row[6] or None, row[16] or None, row[26] or None, _number(row[29], int), _number(row[30]), _number(row[31], int), _number(row[32], int), _number(row[33], int), _number(row[34]), row[53] or None, _number(row[56]), _number(row[57]), row[60] or None, now, json.dumps(raw, ensure_ascii=False, separators=(",", ":"))))
    return out


def _gdelt_mentions(rows: list[list[str]]) -> list[tuple]:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    out = []
    for row in rows:
        if len(row) < len(GDELT_MENTION_FIELDS):
            continue
        raw = _gdelt_fields(row, GDELT_MENTION_FIELDS)
        raw_json = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
        uid = hashlib.sha256(raw_json.encode()).hexdigest()
        out.append((uid, row[0] or None, row[1] or None, row[2] or None, row[3] or None, row[4] or None, row[5] or None, raw_json, now))
    return out


def _gdelt_gkg(rows: list[list[str]]) -> list[tuple]:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    out = []
    for row in rows:
        if len(row) < len(GDELT_GKG_FIELDS):
            continue
        raw = _gdelt_fields(row, GDELT_GKG_FIELDS)
        raw_json = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
        uid = row[0] or hashlib.sha256(raw_json.encode()).hexdigest()
        themes = [part for part in row[8].split(";") if part]
        entities = {"persons": [part for part in row[12].split(";") if part], "organizations": [part for part in row[14].split(";") if part]}
        locations = [part for part in row[10].split(";") if part]
        out.append((uid, row[1], row[3] or None, row[4] or None, json.dumps(themes, ensure_ascii=False), json.dumps(entities, ensure_ascii=False), json.dumps(locations, ensure_ascii=False), json.dumps(row[15].split(",")), raw_json, now))
    return out


def _insert_batch(conn, sql: str, values: list[tuple]) -> int:
    if not values:
        return 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        cursor = conn.executemany(sql, values)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return cursor.rowcount


def run(db_path: str) -> dict[str, int]:
    conn = _db.get_conn(db_path, allow_init=True)
    out = {}
    for name, fetch in (("FMP", _fmp), ("EODHD", _eodhd)):
        try:
            rows = fetch()
            now = datetime.now(UTC).isoformat(timespec="seconds")
            values = []
            payloads = []
            for row in rows:
                title = str(row["title"]).strip()
                url = _canonical_url(row.get("url"))
                cluster, novelty = _cluster(conn, title)
                uid = hashlib.sha256(f"{row['source']}|{url}|{title}".encode()).hexdigest()
                relevance = min(1.0, 0.2 + 0.1 * sum(w in title.lower() for w in ("fed", "inflation", "oil", "bitcoin", "war", "tariff", "yield")))
                values.append((uid, _time(row.get("published")), row["source"], title, url, str(row.get("summary") or "")[:4000], json.dumps(row.get("symbols") or []), cluster, relevance, novelty, now))
                payload_json = json.dumps(row.get("provider_payload") or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                observation_id = hashlib.sha256(f"{uid}|{payload_json}".encode()).hexdigest()
                payloads.append((observation_id, uid, row["source"], now, payload_json))
            conn.executemany("INSERT OR IGNORE INTO market_news VALUES (?,?,?,?,?,?,?,?,?,?,?)", values)
            conn.executemany("INSERT OR IGNORE INTO market_news_payloads VALUES (?,?,?,?,?)", payloads)
            out[name] = len(values)
            log_collection(conn, "market_news", name, rows[0] if rows else None, len(values), status="OK")
        except Exception as ex:
            out[name] = -1
            print(f"{name}: {type(ex).__name__}: {str(ex)[:160]}")
            log_collection(conn, "market_news", name, None, 0, err=str(ex))
    gdelt_feeds = (
        ("GDELT", "export", _gdelt_events, "INSERT OR IGNORE INTO gdelt_events (event_id,event_date,added_at_utc,actor1,actor2,event_code,quad_class,goldstein_scale,mentions,sources,articles,avg_tone,action_country,action_lat,action_lon,source_url,fetched_at,raw_record_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", "GDELT:EVENTS"),
        ("GDELT_MENTIONS", "mentions", _gdelt_mentions, "INSERT OR IGNORE INTO gdelt_mentions VALUES (?,?,?,?,?,?,?,?,?)", "GDELT:MENTIONS"),
        ("GDELT_GKG", "gkg", _gdelt_gkg, "INSERT OR IGNORE INTO gdelt_gkg VALUES (?,?,?,?,?,?,?,?,?,?)", "GDELT:GKG"),
    )
    for name, feed, transform, sql, log_name in gdelt_feeds:
        try:
            rows = transform(_gdelt_feed(feed))
            _insert_batch(conn, sql, rows)
            out[name] = len(rows)
            log_collection(conn, "market_news", log_name, None, len(rows))
        except Exception as ex:
            out[name] = -1
            print(f"{name}: {type(ex).__name__}: {str(ex)[:160]}")
            log_collection(conn, "market_news", log_name, None, 0, err=str(ex))
    conn.close()
    return out


def main(argv=None):
    from dotenv import load_dotenv

    load_dotenv()
    p = argparse.ArgumentParser(prog="arkwatch market-news")
    p.add_argument("--db", default="data/arkwatch.db")
    result = run(p.parse_args(argv).db)
    print(result)
    return 1 if all(v <= 0 for v in result.values()) else 0
