# ark-watch — US Macro Engine

Personal US-macro monitoring system powering the owner's trading. Instruments: metals (XAUUSD/XAGUSD/XPTUSD/XCUUSD + EUR/GBP crosses), BTC/ETH, US100/US500/US30, FX majors, DXY. Swing timeframe, EOD-first.

**Communicate with the user in Bahasa Indonesia.** The owner is NOT from a finance background — explain terms from zero (`docs/explained/` is the teaching series written for them; match that register). They prefer to discuss before building, value verification over speed, and appreciate docs that invite challenge.

## Data sources
- **Paid** (keys in API.md): FMP premium (`fmp-api-docs.md`), EODHD all-bundle (`eodhd-api-redocs.json`) — positioned as cross-validation/failover + unique endpoints (calendars, sovereign CDS, CMDI, policy-rates, funding-stress spreads)
- **Free & verified**: FRED/ALFRED, CFTC Socrata, NY Fed Markets API, Treasury/fiscaldata, CBOE CDN, ECB, Cleveland/Atlanta/Philly Fed, NBER, Yahoo chart API (primary for prices), TwelveData, Bybit, DefiLlama, SAFE, LBMA CDN, SPDR XLSX
- **Gray-zone** (owner-approved for personal use; MUST be degradable — never sole source for a brief headline): CME backdoor endpoints, QuikStrike views, TradingView scanner/calendar (`tradingview-api-docs.json`), Farside, CNN stealth
- API.md lists every key; other listed providers there are unexplored backups

## Hard rules (full trap registry: BUILD-PLAN §0 + §6)
- Keys via env only — never hard-code; API.md must stay out of any git repo
- Server restarts MUST be verified: `systemctl is-active` lies across a failed restart (the old process stays active — two silent failures 2026-09-17). Use `scripts/deploy.sh` on the server; proof of restart = changed `ExecMainStartTimestamp` (see scripts/README.md)
- EODHD: param `api_token=` (not api_key), index suffix `.INDX`. FMP EOD: explicit `from/to` always (silent 2021-era data otherwise)
- cmegroup.com requires curl_cffi `impersonate='chrome'` from this local Windows box (plain PowerShell = 403; cloud IPs blocked). QuikStrike views additionally need a cmegroup.com `Referer` header
- NY Fed endpoints need explicit `.json` suffix; CME calendar `impact` must be `null`
- LME monthly stocks files publish at the START of month M+1 (the file for the CURRENT month never exists during its own month — do not treat that soft-404 as an outage)
- Timestamps stored UTC, displayed WIB (EDT/EST aware: +11/+12h)
- Raw append-only; derived recomputable; unit conversions centralized & unit-tested (case study: PBoC digit-transposition bug)
- BAML OAS series on FRED are truncated to 3 years (ICE license) — z-window 3y, CMDI for long credit history
- Any number reaching the daily brief must pass the calibration ladder (BUILD-PLAN §6.2)


## Working style in this repo
- Verification culture: live-test claims; adversarial-critic important designs; every result lands in the docs (they are the persistent memory of this project)
- Commits follow Conventional Commits: `feat:` / `fix:` / `chore:` / `docs:` / `refactor:` / `test:` / `perf:` prefix, lowercase imperative subject ≤72 chars, body wraps at 72 — e.g. `fix(qa/calendar): block dead CME stub families at ingest` (owner decision 2026-09-17; history before it is free-form — do not rewrite pushed history)
- Always consult context7 (MCP) for library/framework/API versions before writing code
- Always refer to software principles guidelines likes SOLID, DRY, clean code, clean architecture. Write the code don't overenginereed but still focus on the software principles guidelines
- Do research first before writing a code to make sure your code is up to date and best practices

