import gzip
import hashlib
import json
from datetime import UTC, datetime, timedelta

from arkwatch import db
from arkwatch.qa import market_news, market_timeline, okx_liquidations, okx_market


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = datetime(2026, 9, 22, 14, 0, tzinfo=UTC)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


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


def _bar(stamp: str) -> dict:
    return {"bar_ts_utc": stamp, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1}


def test_equity_freshness_tracks_active_session_close_weekend_and_holiday():
    fresh = market_timeline.assess_freshness(
        "SPY",
        [_bar("2026-09-22T13:55:00+00:00")],
        datetime.fromisoformat("2026-09-22T14:00:00+00:00"),
    )
    closed = market_timeline.assess_freshness(
        "SPY",
        [_bar("2026-09-22T23:55:00+00:00")],
        datetime.fromisoformat("2026-09-23T00:05:00+00:00"),
    )
    weekend = market_timeline.assess_freshness(
        "SPY",
        [_bar("2026-09-25T23:55:00+00:00")],
        datetime.fromisoformat("2026-09-26T14:00:00+00:00"),
    )
    thanksgiving = market_timeline.assess_freshness(
        "SPY",
        [_bar("2026-11-26T00:55:00+00:00")],
        datetime.fromisoformat("2026-11-26T17:00:00+00:00"),
    )
    assert (fresh.status, fresh.lag_minutes) == ("FRESH", 0)
    assert closed.status == weekend.status == thanksgiving.status == "CLOSED"


def test_futures_session_and_daily_maintenance_break():
    active = market_timeline.assess_freshness(
        "NQ1",
        [_bar("2026-09-22T14:00:00+00:00")],
        datetime.fromisoformat("2026-09-22T14:05:00+00:00"),
    )
    closed = market_timeline.assess_freshness(
        "NQ1",
        [_bar("2026-09-22T20:55:00+00:00")],
        datetime.fromisoformat("2026-09-22T21:30:00+00:00"),
    )
    assert active.status == "FRESH"
    assert closed.status == "CLOSED"


def test_cme_sunday_open_is_fresh():
    opening = market_timeline.assess_freshness(
        "NQ1",
        [_bar("2026-09-27T22:00:00+00:00")],
        datetime.fromisoformat("2026-09-27T22:05:00+00:00"),
    )
    assert opening.status == "FRESH"


def test_vix_global_and_regular_sessions_and_equity_open_warmup():
    gth = market_timeline.assess_freshness(
        "VIX",
        [_bar("2026-09-22T07:30:00+00:00")],
        datetime.fromisoformat("2026-09-22T07:35:00+00:00"),
    )
    warmup = market_timeline.assess_freshness(
        "SPY",
        [_bar("2026-09-21T19:55:00+00:00")],
        datetime.fromisoformat("2026-09-22T08:02:00+00:00"),
    )
    assert gth.status == "FRESH"
    assert warmup.status == "WAITING"


def test_equity_extended_hours_and_regular_only_breadth_window():
    premarket = market_timeline.assess_freshness(
        "SPY",
        [_bar("2026-09-22T08:00:00+00:00")],
        datetime.fromisoformat("2026-09-22T08:05:00+00:00"),
    )
    postmarket = market_timeline.assess_freshness(
        "SPY",
        [_bar("2026-09-22T23:55:00+00:00")],
        datetime.fromisoformat("2026-09-23T00:05:00+00:00"),
    )
    breadth = market_timeline.assess_freshness(
        "SPY",
        [_bar("2026-09-22T23:55:00+00:00")],
        datetime.fromisoformat("2026-09-23T00:05:00+00:00"),
        regular_only=True,
    )
    assert premarket.status == "FRESH"
    assert postmarket.status == "CLOSED"
    assert breadth.status == "OUT_OF_SESSION"


def test_brent_ice_hours_and_dxy_maintenance_break():
    brent_active = market_timeline.assess_freshness(
        "BZ1",
        [_bar("2026-09-22T08:55:00+00:00")],
        datetime.fromisoformat("2026-09-22T09:00:00+00:00"),
    )
    brent_closed = market_timeline.assess_freshness(
        "BZ1",
        [_bar("2026-09-22T21:55:00+00:00")],
        datetime.fromisoformat("2026-09-22T22:30:00+00:00"),
    )
    dxy_break = market_timeline.assess_freshness(
        "DXY",
        [_bar("2026-09-22T20:55:00+00:00")],
        datetime.fromisoformat("2026-09-22T22:30:00+00:00"),
    )
    brent_sunday = market_timeline.assess_freshness(
        "BZ1",
        [_bar("2026-09-25T21:55:00+00:00")],
        datetime.fromisoformat("2026-09-27T21:30:00+00:00"),
    )
    dxy_sunday = market_timeline.assess_freshness(
        "DXY",
        [_bar("2026-09-25T20:55:00+00:00")],
        datetime.fromisoformat("2026-09-27T21:00:00+00:00"),
    )
    brent_open = market_timeline.assess_freshness(
        "BZ1",
        [_bar("2026-09-27T22:00:00+00:00")],
        datetime.fromisoformat("2026-09-27T22:05:00+00:00"),
    )
    dxy_open = market_timeline.assess_freshness(
        "DXY",
        [_bar("2026-09-27T22:00:00+00:00")],
        datetime.fromisoformat("2026-09-27T22:05:00+00:00"),
    )
    assert brent_active.status == "FRESH"
    assert brent_closed.status == "CLOSED"
    assert dxy_break.status == "CLOSED"
    assert brent_sunday.status == dxy_sunday.status == "CLOSED"
    assert brent_open.status == dxy_open.status == "FRESH"


def test_early_close_is_respected_for_equities_and_vix():
    regular = market_timeline.assess_freshness(
        "SPY",
        [_bar("2026-11-27T17:55:00+00:00")],
        datetime.fromisoformat("2026-11-27T18:05:00+00:00"),
        regular_only=True,
    )
    extended = market_timeline.assess_freshness(
        "SPY",
        [_bar("2026-11-27T18:00:00+00:00")],
        datetime.fromisoformat("2026-11-27T18:05:00+00:00"),
    )
    vix = market_timeline.assess_freshness(
        "VIX",
        [_bar("2026-11-27T18:10:00+00:00")],
        datetime.fromisoformat("2026-11-27T18:20:00+00:00"),
    )
    assert regular.status == "CLOSED"
    assert extended.status == "FRESH"
    assert vix.status == "CLOSED"


def test_future_or_unzoned_bar_is_never_marked_fresh():
    future = market_timeline.assess_freshness(
        "BTCUSD",
        [_bar("2026-09-26T14:05:00+00:00")],
        datetime.fromisoformat("2026-09-26T14:00:00+00:00"),
    )
    unzoned = market_timeline.assess_freshness(
        "BTCUSD",
        [_bar("2026-09-26T13:55:00")],
        datetime.fromisoformat("2026-09-26T14:00:00+00:00"),
    )
    assert future.status == "FUTURE"
    assert unzoned.status == "UNKNOWN"


def test_crypto_is_continuous_on_weekends_and_stales_after_three_intervals():
    now = datetime.fromisoformat("2026-09-26T14:00:00+00:00")
    fresh = market_timeline.assess_freshness("BTCUSD", [_bar("2026-09-26T13:55:00+00:00")], now)
    boundary = market_timeline.assess_freshness(
        "BTCUSD", [_bar("2026-09-26T13:40:00+00:00")], now
    )
    stale = market_timeline.assess_freshness("BTCUSD", [_bar("2026-09-26T13:35:00+00:00")], now)
    assert fresh.status == boundary.status == "FRESH"
    assert stale.status == "STALE"


def test_stale_eodhd_is_skipped_for_fresher_fmp(monkeypatch):
    now = datetime.fromisoformat("2026-09-22T14:00:00+00:00")
    monkeypatch.setattr(
        market_timeline, "_eodhd_bars", lambda _symbol: [_bar("2026-09-22T13:30:00+00:00")]
    )
    monkeypatch.setattr(
        market_timeline, "_fmp_bars", lambda _symbol: [_bar("2026-09-22T13:55:00+00:00")]
    )
    selection = market_timeline._provider_bars("SPY", now)
    assert selection.source == "FMP"
    assert selection.freshness.status == "FRESH"
    assert selection.attempts[0].freshness.status == "STALE"


def test_stale_primary_and_fallback_are_logged_degraded_not_healthy(tmp_path, monkeypatch):
    stale = [_bar("2026-09-22T13:30:00+00:00")]
    monkeypatch.setattr(market_timeline, "datetime", _FixedDateTime)
    monkeypatch.setattr(market_timeline.yahoo, "fetch_intraday", lambda _ticker: stale)
    monkeypatch.setattr(market_timeline, "_eodhd_bars", lambda _symbol: [])
    monkeypatch.setattr(market_timeline, "_fmp_bars", lambda _symbol: stale)
    monkeypatch.setattr(market_timeline, "collect_okx_market", lambda _path: {})
    result = market_timeline.run(str(tmp_path / "freshness.db"), only="SPY")
    assert result["SPY"] == -1
    conn = db.get_conn(tmp_path / "freshness.db", allow_init=True)
    statuses = dict(conn.execute("SELECT target,status FROM fetch_log WHERE target LIKE 'SPY:%'"))
    sources = {
        row[0]
        for row in conn.execute("SELECT DISTINCT source FROM intraday_bars WHERE symbol='SPY'")
    }
    conn.close()
    assert statuses["SPY:YAHOO:5m"] == "DEGRADED"
    assert statuses["SPY:FMP:5m"] == "DEGRADED"
    assert sources == {"YAHOO", "FMP"}


def test_stale_eodhd_is_logged_and_fresher_fmp_is_selected(tmp_path, monkeypatch):
    stale = [_bar("2026-09-22T13:30:00+00:00")]
    fresh = [_bar("2026-09-22T13:55:00+00:00")]

    def fail_yahoo(_ticker):
        raise TimeoutError("synthetic outage")

    monkeypatch.setattr(market_timeline.yahoo, "fetch_intraday", fail_yahoo)
    monkeypatch.setattr(market_timeline, "_eodhd_bars", lambda _symbol: stale)
    monkeypatch.setattr(market_timeline, "_fmp_bars", lambda _symbol: fresh)
    monkeypatch.setattr(market_timeline, "collect_okx_market", lambda _path: {})
    monkeypatch.setattr(market_timeline, "datetime", _FixedDateTime)
    result = market_timeline.run(str(tmp_path / "fallback.db"), only="SPY")
    assert result["SPY"] > 0
    conn = db.get_conn(tmp_path / "fallback.db", allow_init=True)
    statuses = dict(conn.execute("SELECT target,status FROM fetch_log WHERE target LIKE 'SPY:%'"))
    sources = {
        row[0]
        for row in conn.execute("SELECT DISTINCT source FROM intraday_bars WHERE symbol='SPY'")
    }
    conn.close()
    assert statuses["SPY:EODHD:5m"] == "DEGRADED"
    assert statuses["SPY:FMP:5m"] == "OK"
    assert sources == {"EODHD", "FMP"}


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


def test_gdelt_mention_and_gkg_keep_all_provider_fields():
    mention = [str(index) for index in range(len(market_news.GDELT_MENTION_FIELDS))]
    parsed_mention = market_news._gdelt_mentions([mention])[0]
    assert parsed_mention[1] == "0"
    assert '"Extras":"15"' in parsed_mention[7]

    gkg = [str(index) for index in range(len(market_news.GDELT_GKG_FIELDS))]
    parsed_gkg = market_news._gdelt_gkg([gkg])[0]
    assert parsed_gkg[0] == "0"
    assert '"GCAM":"17"' in parsed_gkg[8]


def test_okx_contract_size_is_normalized_only_with_known_metadata():
    size_asset, notional = okx_market.normalize_contract_size(
        2, 100_000, {"ctVal": "0.01", "ctValCcy": "BTC", "ctMult": "1", "baseCcy": "BTC"}
    )
    assert size_asset == 0.02
    assert notional == 2_000
    assert okx_market.normalize_contract_size(2, 100, {}) == (None, None)


def test_okx_trade_and_book_streams_store_raw_and_normalized_values(tmp_path):
    conn = db.get_conn(tmp_path / "okx.db", allow_init=True)
    specs = {
        "BTC-USDT-SWAP": {
            "instId": "BTC-USDT-SWAP", "baseCcy": "BTC", "ctVal": "0.01",
            "ctValCcy": "BTC", "ctMult": "1",
        }
    }
    trades = {
        "arg": {"channel": "trades", "instId": "BTC-USDT-SWAP"},
        "data": [
            {"instId": "BTC-USDT-SWAP", "tradeId": "123", "px": "100000", "sz": "2", "side": "buy", "ts": "1790000000000"},
            {"instId": "BTC-USDT-SWAP", "tradeId": "124", "px": "100200", "sz": "3", "side": "sell", "ts": "1790000000001"},
        ],
    }
    books = {
        "arg": {"channel": "books5", "instId": "BTC-USDT-SWAP"},
        "data": [{"ts": "1790000000000", "bids": [["100000", "2", "0", "1"]], "asks": [["100100", "1", "0", "1"]], "seqId": 7}],
    }
    buffer = okx_liquidations.TradeFlowBuffer(conn, specs)
    concurrent_buffer = okx_liquidations.TradeFlowBuffer(conn, specs)
    assert okx_liquidations._trades(trades, buffer) == 2
    assert concurrent_buffer.add(trades["data"], source="OKX_REST", instrument="BTC-USDT-SWAP") == 2
    buffer.flush()
    assert concurrent_buffer.flush() == 0
    assert okx_liquidations._book(conn, books, specs, {}) == 1
    batch = conn.execute("SELECT payload_gzip FROM crypto_trade_raw_batches").fetchone()[0]
    payload = gzip.decompress(batch)
    raw_trades = json.loads(payload)
    assert [row["tradeId"] for row in raw_trades] == ["123", "124"]
    assert all("_sizeAsset" not in row for row in raw_trades)
    assert conn.execute("SELECT payload_sha256 FROM crypto_trade_raw_batches").fetchone()[0] == hashlib.sha256(payload).hexdigest()
    flow = conn.execute(
        "SELECT trade_count,buy_count,sell_count,buy_contracts,sell_contracts,buy_asset,sell_asset,buy_notional_usd,sell_notional_usd "
        "FROM crypto_trade_flow_1m"
    ).fetchone()
    assert flow == (2, 1, 1, 2.0, 3.0, 0.02, 0.03, 2000.0, 3006.0)
    assert conn.execute("SELECT COUNT(*) FROM crypto_trade_raw_batches").fetchone()[0] == 1
    book = conn.execute("SELECT bid_notional_usd_top5,ask_notional_usd_top5,imbalance_notional_usd_top5 FROM crypto_orderbook_snapshots").fetchone()
    assert book == (2000.0, 1001.0, (2000.0 - 1001.0) / (2000.0 + 1001.0))
    conn.close()


def test_okx_trade_flow_backfills_legacy_events_once(tmp_path):
    conn = db.get_conn(tmp_path / "okx-backfill.db", allow_init=True)
    conn.executemany(
        "INSERT INTO crypto_trade_events "
        "(event_uid,ts_utc,source,instrument,trade_id,aggressor_side,price,size_contracts,raw_json,fetched_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            ("a", "2026-09-23T15:01:01+00:00", "OKX", "BTC-USDT-SWAP", "100", "buy", 100000, 2, "{}", "2026-09-23T15:01:02+00:00"),
            ("b", "2026-09-23T15:01:30+00:00", "OKX", "BTC-USDT-SWAP", "101", "sell", 100100, 1, "{}", "2026-09-23T15:01:31+00:00"),
        ],
    )
    specs = {"BTC-USDT-SWAP": {"instId": "BTC-USDT-SWAP", "baseCcy": "BTC", "ctVal": "0.01", "ctValCcy": "BTC"}}
    okx_liquidations.TradeFlowBuffer(conn, specs)
    flow = conn.execute("SELECT trade_count,buy_count,sell_count,buy_notional_usd,sell_notional_usd FROM crypto_trade_flow_1m").fetchone()
    assert flow == (2, 1, 1, 2000.0, 1001.0)
    okx_liquidations.TradeFlowBuffer(conn, specs)
    assert conn.execute("SELECT trade_count FROM crypto_trade_flow_1m").fetchone()[0] == 2
    assert conn.execute("SELECT last_trade_id FROM crypto_trade_flow_state").fetchone()[0] == "101"
    conn.close()
