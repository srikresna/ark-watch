from datetime import UTC, datetime, timedelta

from arkwatch.qa import market_news, market_timeline, okx_liquidations


def test_fallback_rows_are_utc_completed_and_bounded():
    now = datetime.now(UTC)
    payload = [
        {"timestamp": int((now - timedelta(minutes=10)).timestamp()), "close": 1},
        {"timestamp": int((now - timedelta(days=3)).timestamp()), "close": 2},
        {"timestamp": int((now + timedelta(minutes=5)).timestamp()), "close": 3},
    ]
    rows = market_timeline._normalized_rows(payload, source="EODHD", ticker="NQ.COMM")
    assert len(rows) == 1
    assert rows[0]["bar_ts_utc"].endswith("+00:00")


def test_fmp_naive_equity_timestamp_uses_new_york():
    stamp = market_timeline._utc_stamp("2026-09-22 09:30:00", source="FMP", ticker="SPY")
    assert stamp == "2026-09-22T13:30:00+00:00"


def test_news_canonical_url_and_gdelt_timestamp():
    assert market_news._canonical_url("HTTPS://Example.com/a/?utm_source=x&b=2") == "https://example.com/a?b=2"
    assert market_news._time("20260922T120000Z") == "2026-09-22T12:00:00+00:00"


def test_okx_liquidation_event_parser():
    message = {"data": [{"instId": "BTC-USDT-SWAP", "details": [{"ts": "1790000000000", "bkPx": "100", "sz": "2", "posSide": "long"}]}]}
    events = okx_liquidations._events(message)
    assert len(events) == 1
    assert events[0]["notional"] is None
    assert events[0]["side"] == "long"


def test_news_cluster_reuses_similar_recent_headline(tmp_path):
    import sqlite3

    conn = sqlite3.connect(tmp_path / "news.db")
    conn.execute("CREATE TABLE market_news(title TEXT,cluster_id TEXT,published_at_utc TEXT)")
    conn.execute("INSERT INTO market_news VALUES (?,?,datetime('now'))", ("Oil falls after Middle East ceasefire agreement", "existing",))
    cluster, novelty = market_news._cluster(conn, "Oil falls after Middle East ceasefire deal")
    assert cluster == "existing"
    assert novelty == 0.5
