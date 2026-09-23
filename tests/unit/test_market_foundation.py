import gzip
import hashlib
import json
from datetime import UTC, datetime, timedelta

from arkwatch import db
from arkwatch.qa import market_news, market_timeline, okx_liquidations, okx_market


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
