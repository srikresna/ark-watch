# ark-watch

A personal US macro monitoring engine: automated daily data pipeline over 20+ free public sources → SQLite → Telegram morning brief + alert watcher.

## What it does

- **Collects** 100+ economic series daily (FRED, NY Fed Markets API incl. SOMA per-CUSIP holdings, CME settlements & per-strike options, Treasury/fiscaldata auctions, regional Fed models, Bybit crypto positioning)
- **Computes** signals: Fed net-liquidity decomposition, SOMA maturity walls, options put/call ratios & OI walls, primary-dealer positioning, auction demand percentiles (45 years of history), inflation risk premium, recession triangulation (curve model / SPF survey / Sahm rule)
- **Delivers** a morning brief via Telegram, with a 16-trigger alert watcher running every 60 seconds

## Quickstart

```bash
pip install -r requirements.lock
cp .env.example .env      # add your FRED / FMP / EODHD / Telegram keys
python -m arkwatch daemon # runs the daily schedule
```

Or run single jobs:

```bash
python -m arkwatch harvest   # fetch all series
python -m arkwatch brief     # render the daily brief
python -m arkwatch verify    # data truth gate
```

## Layout

```
arkwatch/    fetchers (data sources) · signals (computation) · qa (jobs) · senders · daemon
config/      series registry + signal thresholds (all YAML, provenance-commented)
tests/       362 offline tests — no network needed
fixtures/    captured API responses for parser tests
```

## Notes

- Keys go in `.env` only (see `.env.example`) — never commit them.
- Some sources are unofficial CDN endpoints; every source is degradable — one going down never breaks the brief.
- This is a personal research tool, **not** investment advice.

## License

[MIT](LICENSE)
