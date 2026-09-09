"""f2_harvest.py — COT + Bybit + DefiLlama + FedWatch-DIY harvest job."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from .. import db
from ..config import load_cot_contracts
from ..fetchers import bybit, cot, spdr
from ..transforms import xccy

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "arkwatch.db"


def harvest_cot(conn, weeks: int = 156) -> dict[str, int]:
    """Fetch ALL categories × `weeks` weeks × futures + combined (for metals)."""
    contracts = load_cot_contracts()
    out: dict[str, int] = {}
    for c in contracts:
        code = str(c.get("code", ""))
        name = c.get("name", code)
        report_type = str(c.get("report_type", "tff"))
        # Disagg reports use the canonical `code`; legacy historical depth
        # (e.g. copper 085691) is fetched separately via legacy_code.
        actual_code = code

        # Fetch futures-only (primary)
        try:
            rows = cot.fetch_cot(report_type, actual_code, limit=weeks)
            n = _save_cot(conn, rows)
            out[f"{name}|{report_type}"] = n
        except Exception as ex:
            out[f"{name}|{report_type}"] = -1
            print(f"  ✗ {name} {report_type}: {str(ex)[:80]}")

        # Fetch combined futures+options (metals)
        if report_type == "disagg":
            combined_type = "disagg_c"
            try:
                rows_c = cot.fetch_cot(combined_type, actual_code, limit=weeks)
                n_c = _save_cot(conn, rows_c)
                out[f"{name}|{combined_type}"] = n_c
            except Exception:
                out[f"{name}|{combined_type}"] = -1
                # Combined is not available for every contract — not fatal
        elif report_type == "tff":
            combined_type = "tff_c"
            try:
                rows_c = cot.fetch_cot(combined_type, actual_code, limit=weeks)
                n_c = _save_cot(conn, rows_c)
                out[f"{name}|{combined_type}"] = n_c
            except Exception:
                out[f"{name}|{combined_type}"] = -1

        # Optional legacy historical depth when defined in config
        if c.get("legacy_code") and c.get("legacy_dataset"):
            try:
                rows_l = cot.fetch_cot("legacy", str(c["legacy_code"]), limit=weeks)
                out[f"{name}|legacy"] = _save_cot(conn, rows_l)
            except Exception:
                out[f"{name}|legacy"] = -1
    return out


def _save_cot(conn, rows: list[dict]) -> int:
    """Store ALL categories per row — each category is one cot_raw row."""
    from datetime import date, timedelta

    now = datetime.now(UTC).isoformat(timespec="seconds")
    payload = []
    for r in rows:
        rd = r.get("report_date", "")
        if not rd:
            continue
        release = (date.fromisoformat(rd) + timedelta(days=3)).isoformat()
        payload.append(
            (
                rd,
                r.get("contract_code", ""),
                r.get("report_type", ""),
                release,
                r.get("category", ""),
                r.get("long"),
                r.get("short"),
                r.get("spread"),
                r.get("open_interest_all"),
                r.get("pct_of_oi"),
                r.get("conc4_long"),
                r.get("conc4_short"),
                r.get("conc8_long"),
                r.get("conc8_short"),
                r.get("traders_long"),
                r.get("traders_short"),
                r.get("change_long"),
                r.get("change_short"),
                f"CFTC/{r.get('report_type', '')}",
                now,
            )
        )
    if not payload:
        return 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.executemany(
            "INSERT OR REPLACE INTO cot_raw("
            "report_date,contract_code,report_type,release_ts,category,"
            "long,short,spread,open_interest_all,pct_of_oi,"
            "conc_top4_long,conc_top4_short,conc_top8_long,conc_top8_short,"
            "traders_long,traders_short,change_long,change_short,"
            "source,fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            payload,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return cur.rowcount


def harvest_flows(conn) -> dict[str, float | None]:
    """Funding EOD = average of today's 8-hour funding points; NULL on failure.

    A fetch failure must produce NULL, not a sentinel: a sentinel −1 fraction
    scaled by 10000 becomes −10000bps in flows_daily, passes the watcher's bps
    filter, and fires a false extreme-funding alert. Legitimate negative
    funding rates are unaffected.
    """
    out: dict[str, float | None] = {}

    def _funding_eod_bps(symbol: str) -> float | None:
        """Average of the last UTC day's three 8-hour points = EOD."""
        try:
            hist = bybit.fetch_funding_history(symbol, limit=9)
            if not hist:
                return None
            last_day = max(h["ts"] for h in hist)[:10]
            rates = [h["rate"] for h in hist if h["ts"].startswith(last_day)]
            if not rates:
                return None
            return sum(rates) / len(rates) * 10_000
        except Exception:
            return None

    for sym, key in (("BTCUSDT", "btc"), ("ETHUSDT", "eth")):
        try:
            t = bybit.fetch_ticker(sym)
            out[f"oi_{key}"] = t["open_interest"]
        except Exception as ex:
            out[f"oi_{key}"] = None
            print(f"  ⚠ Bybit {sym}: {str(ex)[:70]}")
        fed = _funding_eod_bps(sym)
        if fed is None:  # Fallback: instantaneous point (degradable)
            try:
                fed = bybit.fetch_ticker(sym)["funding_rate"] * 10_000
            except Exception:
                fed = None
        out[f"funding_{key}"] = fed
    # DefiLlama stablecoins
    try:
        s = bybit.fetch_stablecoin_total()
        out["stablecoin_usd"] = s["total_usd"]
    except Exception:
        out["stablecoin_usd"] = None
    # Write ONLY these columns of flows_daily (not a full-row REPLACE): a
    # REPLACE would NULL out columns already filled by other jobs when this
    # job retries
    today = datetime.now(UTC).date().isoformat()
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        "INSERT INTO flows_daily(date,funding_bps,oi_btc,oi_eth,stablecoin_usd)"
        " VALUES (?,?,?,?,?)"
        " ON CONFLICT(date) DO UPDATE SET funding_bps=excluded.funding_bps,"
        " oi_btc=excluded.oi_btc, oi_eth=excluded.oi_eth,"
        " stablecoin_usd=excluded.stablecoin_usd",
        (
            today,
            out.get("funding_btc"),
            out.get("oi_btc"),
            out.get("oi_eth"),
            out.get("stablecoin_usd"),
        ),
    )
    conn.execute("COMMIT")

    _harvest_positioning(conn)
    return out


def _harvest_positioning(conn) -> int:
    """Bybit positioning extras → bybit_positioning (migration v12).

    Each leg is independently optional: a Bybit outage window stores the
    legs that answered and leaves the rest NULL for that day (the funding
    NULL convention — never a sentinel). Pulls the trailing ~30d each run;
    upsert per (symbol, date), so gaps from dead days self-heal on the next
    reachable window.
    """
    n = 0
    for sym in ("BTCUSDT", "ETHUSDT"):
        legs: dict[str, dict[str, float]] = {}
        for key, fn in (
            ("ls", bybit.fetch_account_ratio),
            ("tk", bybit.fetch_taker_volume),
            ("oi", bybit.fetch_open_interest_history),
        ):
            try:
                rows = fn(sym, limit=30)
            except Exception as ex:
                rows = []
                print(f"  ⚠ Bybit {key} {sym}: {str(ex)[:70]}")
            for r in rows:
                legs.setdefault(r["ts"], {})[key] = r.get(
                    "ls_ratio", r.get("buy_ratio", r.get("oi"))
                )
        if not legs:
            continue
        payload = [
            (sym, d, v.get("ls"), v.get("tk"), v.get("oi")) for d, v in sorted(legs.items())
        ]
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.executemany(
                "INSERT INTO bybit_positioning(symbol,date,ls_ratio,taker_buy_ratio,oi)"
                " VALUES (?,?,?,?,?)"
                " ON CONFLICT(symbol,date) DO UPDATE SET"
                " ls_ratio=COALESCE(excluded.ls_ratio, ls_ratio),"
                " taker_buy_ratio=COALESCE(excluded.taker_buy_ratio, taker_buy_ratio),"
                " oi=COALESCE(excluded.oi, oi)",
                payload,
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        n += len(payload)
    if n:
        print(f"  bybit_positioning: {n} rows upserted")
    # fetch_log row so health checks can join on it (the LME:CA_STOCKS
    # convention). n=0 during a Bybit outage window is NOT an error —
    # log_collection writes status EMPTY (invisible to the OK/ERROR ratio,
    # the funding-NULL convention).
    from .fetch_log import log_collection

    log_collection(conn, "bybit", "BYBIT:POSITIONING", None, n)
    return n


def compute_fedwatch(conn) -> list[dict]:
    """Read ZQ settlements from the DB → compute probabilities → save fedwatch_snapshots."""
    from ..transforms import fedwatch as fw

    # Latest ZQ settlements (product_id=305)
    rows = conn.execute(
        "SELECT month, settle FROM cme_settlements "
        "WHERE product_id=305 ORDER BY trade_date DESC, month LIMIT 50"
    ).fetchall()
    if not rows:
        return []
    # Keep only the latest trade_date
    latest_td = conn.execute(
        "SELECT MAX(trade_date) FROM cme_settlements WHERE product_id=305"
    ).fetchone()[0]
    rows = conn.execute(
        "SELECT month, settle FROM cme_settlements "
        "WHERE product_id=305 AND trade_date=? ORDER BY month",
        (latest_td,),
    ).fetchall()
    settlements = {m: s for m, s in rows if s is not None}

    # EFFR anchor: without DFF the implied probabilities are meaningless, so a
    # missing anchor skips writing the snapshot (degradable) instead of
    # freezing on a hardcoded rate. latest_observation guarantees the realtime
    # filter — an old vintage row would shift the anchor by a few bp, which
    # maps to a large probability error.
    from ..queries import latest_observation

    effr_row = latest_observation(conn, "FRED:DFF")
    if not effr_row or effr_row[1] is None:
        print("  ⚠ FedWatch-DIY skipped: FRED:DFF empty (without an EFFR anchor the probabilities are misleading)")
        return []
    effr = effr_row[1]

    probs = fw.compute(settlements, effr)

    conn.execute("BEGIN IMMEDIATE")
    for p in probs:
        conn.execute(
            "INSERT OR REPLACE INTO fedwatch_snapshots"
            "(date,meeting_date,source,prob_ease,prob_hold,prob_hike,implied_rate)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                latest_td,
                p.meeting_date.isoformat(),
                "diy",
                p.prob_ease,
                p.prob_hold,
                p.prob_hike,
                p.implied_rate,
            ),
        )

    # Official cross-check (gray-zone → degradable: a fetch failure is silent,
    # DIY remains primary). Flow: GET TreasuryWatch + a menu POST to the form
    # action carrying insid/qsid; the view shows the nearest meeting plus the
    # target-rate distribution.
    official_rows = []
    try:
        from ..fetchers.quikstrike import fetch_fedwatch_official

        official = fetch_fedwatch_official()
        for o in official or []:
            md = datetime.strptime(o["meeting_date"], "%d %b %Y").date().isoformat()
            implied = None
            if "mid" in o and o["mid"]:
                implied = 100 - o["mid"]  # implied = 100 − price (ZQ contract)
            conn.execute(
                "INSERT OR REPLACE INTO fedwatch_snapshots"
                "(date,meeting_date,source,prob_ease,prob_hold,prob_hike,implied_rate)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    latest_td,
                    md,
                    "official",
                    # Official parser reports percent 0-100; the table
                    # convention is a 0-1 fraction (matching DIY)
                    o.get("ease") / 100 if o.get("ease") is not None else None,
                    o.get("hold") / 100 if o.get("hold") is not None else None,
                    o.get("hike") / 100 if o.get("hike") is not None else None,
                    implied,
                ),
            )
            official_rows.append(o)
    except Exception:
        pass  # degradable by design

    # DIY vs official calibration gate ≤3pp
    if official_rows:
        try:
            from ..fetchers.quikstrike import compare_diy_vs_official

            diy_fmt = [
                {"meeting": p.meeting_date.strftime("%b %y"), "hike": p.prob_hike} for p in probs
            ]
            cmp_ = compare_diy_vs_official(diy_fmt, official_rows)
            for c in cmp_:
                status = "OK" if c["pass"] else "⚠ GATE>3pp"
                print(
                    f"  FedWatch gate {c['meeting']}: diy {c['diy_hike_pct']:.0f}% vs "
                    f"official {c['official_hike_pct']:.0f}% (Δ{c['delta_hike_pp']:.1f}pp) {status}"
                )
        except Exception as ex:
            print(f"  ⚠ FedWatch gate: {str(ex)[:70]}")
    conn.execute("COMMIT")
    return [
        {
            "meeting": p.meeting_date.isoformat(),
            "ease": p.prob_ease,
            "hold": p.prob_hold,
            "hike": p.prob_hike,
            "implied": p.implied_rate,
        }
        for p in probs
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch f2")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--skip-cot", action="store_true")
    p.add_argument("--skip-flows", action="store_true")
    p.add_argument(
        "--lme-years",
        type=int,
        default=0,
        metavar="N",
        help="backfill LME copper stocks N years (one-shot run)",
    )
    a = p.parse_args(argv)
    try:
        from dotenv import load_dotenv

        load_dotenv()  # direct-module invocation needs env (FMP for SLV/GLD shares)
    except ImportError:
        pass
    conn = db.get_conn(a.db, allow_init=True)

    if not a.skip_cot:
        print("=== COT (13 contracts × 2 reports) ===")
        cot_result = harvest_cot(conn)
        ok = sum(1 for v in cot_result.values() if v > 0)
        print(f"  {ok}/{len(cot_result)} contract-reports populated")

    if not a.skip_flows:
        print("=== Flows (Bybit + DefiLlama) ===")
        flows = harvest_flows(conn)
        for k, v in flows.items():
            print(f"  {k}: {v}")

    print("=== FedWatch-DIY (from ZQ settlements in DB) ===")
    probs = compute_fedwatch(conn)
    for p in probs:
        print(
            f"  {p['meeting']}: ease={p['ease']:.1%} hold={p['hold']:.1%} "
            f"hike={p['hike']:.1%} implied={p['implied']:.2f}%"
        )

    print("=== XCCY Basis (CIP from SR3+ESR+6E) ===")
    try:
        xccy_rows = xccy.compute_xccy(conn)
        for r in xccy_rows[:4]:
            print(
                f"  {r.contract}: {r.basis_bps:+.2f}bp "
                f"(F={r.f_actual:.4f} CIP={r.f_cip:.4f} τ={r.tau:.3f})"
            )
    except Exception as ex:
        print(f"  ⚠ {ex}")

    # CNN Fear & Greed — daily snapshot (degradable)
    try:
        from ..fetchers.cnn import fetch_fear_greed

        fg = fetch_fear_greed()
        today_fg = datetime.now(UTC).date().isoformat()
        conn.execute(
            "INSERT INTO flows_periodic(period,kind,value_raw,unit_raw,factor,value)"
            " VALUES (?,'cnn_fg',?, 'score',1,?)"
            " ON CONFLICT(period,kind) DO UPDATE SET value_raw=excluded.value_raw,"
            " value=excluded.value",
            (today_fg, fg["score"], fg["score"]),
        )
        conn.commit()
        print(f"Fear&Greed: {fg['score']} ({fg['label']})")
    except Exception as ex:
        print(f"  ⚠ CNN F&G: {str(ex)[:70]}")

    print("=== GLD / SLV Flows ===")
    try:
        gld = spdr.fetch_gld_tonnes()
        approx_mark = " (approx)" if gld.get("approx") else ""
        print(
            f"  GLD: {gld['oz_per_share']:.6f} oz/share → ~{gld['tonnes_approx']}t "
            f"{approx_mark} ({gld['ts']}, shares≈{gld['shares_assumed_m']:.0f}M)"
        )
        today = datetime.now(UTC).date().isoformat()
        conn.execute(
            "INSERT INTO flows_periodic(period,kind,value_raw,unit_raw,factor,value)"
            " VALUES (?,'gld_shares_approx','flag',1,1,?)"
            " ON CONFLICT(period,kind) DO UPDATE SET value=excluded.value",
            (today, 1.0 if gld.get("approx") else 0.0),
        )
        conn.execute(
            "INSERT INTO flows_daily(date,gld_tonnes) VALUES (?,?) "
            "ON CONFLICT(date) DO UPDATE SET gld_tonnes=excluded.gld_tonnes",
            (today, gld["tonnes_approx"]),
        )
        conn.commit()
    except Exception as ex:
        print(f"  ⚠ GLD: {str(ex)[:90]}")
    try:
        slv = spdr.fetch_slv_shares()
        print(f"  SLV: {slv['shares']:,} shares ({slv['ts']})")
        # Upsert the target column: a bare UPDATE is a silent no-op when the
        # row for that date does not exist yet
        conn.execute(
            "INSERT INTO flows_daily(date,slv_shares) VALUES (?,?) "
            "ON CONFLICT(date) DO UPDATE SET slv_shares=excluded.slv_shares",
            (slv["ts"], slv["shares"]),
        )
        conn.commit()
    except Exception as ex:
        print(f"  ⚠ SLV: {str(ex)[:90]}")

    # Farside ETF + PBoC + LBMA + TIC
    print("=== Flows Extra (Farside ETF + PBoC + LBMA + TIC) ===")
    from ..fetchers import flows_extra

    for path, col, label in (
        ("btc", "btc_etf_musd", "BTC-ETF"),
        ("eth", "eth_etf_musd", "ETH-ETF"),
    ):
        try:
            r = (
                flows_extra.fetch_farside_btc()
                if path == "btc"
                else flows_extra.fetch_farside_eth()
            )
            d = r.get("date_iso") or r["ts"]
            conn.execute(
                f"INSERT INTO flows_daily(date, {col}) VALUES(?,?) "
                f"ON CONFLICT(date) DO UPDATE SET {col}=excluded.{col}",
                (d, r["net_flow_musd"]),
            )
            conn.commit()
            print(f"  {label}: {r['net_flow_musd']:+.1f}M$ ({d})")
        except Exception as ex:
            print(f"  ⚠ {label}: {str(ex)[:80]}")

    def _periodic(ts, kind, value_raw, unit_raw, factor, value, meta):
        conn.execute(
            "INSERT OR REPLACE INTO flows_periodic"
            "(period, kind, value_raw, unit_raw, factor, value, meta_json)"
            " VALUES (?,?,?,?,?,?,?)",
            (ts, kind, value_raw, unit_raw, factor, value, json.dumps(meta)),
        )
        conn.commit()
        print(f"  {kind}: {value:,.1f} ({ts})")

    try:
        r = flows_extra.fetch_pboc_gold()
        from ..units import wan_oz_to_tonnes

        _periodic(
            r["ts"],
            "pboc_gold",
            r["wan_oz"],
            "万盎司",
            wan_oz_to_tonnes(1.0),
            r["tonnes"],
            {"source": "SAFE official reserve assets", "unit_out": "tonne"},
        )
    except Exception as ex:
        print(f"  ⚠ PBoC: {str(ex)[:80]}")
    try:
        r = flows_extra.fetch_lbma_silver()
        from ..units import koz_to_tonnes

        _periodic(
            r["ts"],
            "lbma_silver",
            r["koz"],
            "k_oz_troy",
            koz_to_tonnes(1.0),
            r["tonnes"],
            {"source": "LBMA london vault data", "unit_out": "tonne"},
        )
    except Exception as ex:
        print(f"  ⚠ LBMA: {str(ex)[:80]}")
    try:
        r = flows_extra.fetch_tic_china()
        _periodic(
            r["ts"],
            "tic_china",
            r["china_usd_b"],
            "usd_billion",
            1.0,
            r["china_usd_b"],
            {"source": "treasury ticdata mfh.txt"},
        )
    except Exception as ex:
        print(f"  ⚠ TIC: {str(ex)[:80]}")

    # LME copper stocks (daily; squeeze-watch trigger) — current month +
    # previous month (append-only; duplicates skipped by insert_observations)
    print("=== LME Copper Stocks ===")
    lme_err: str | None = None
    from .. import db as _db

    now_d = datetime.now(UTC).date()
    prev_y, prev_m = (now_d.year, now_d.month - 1) if now_d.month > 1 else (now_d.year - 1, 12)
    total_new = 0
    from curl_cffi import requests as _creq

    _lme_sess = _creq.Session(impersonate="chrome")  # one shared session for all months
    for y, m in ((now_d.year, now_d.month), (prev_y, prev_m)):
        try:
            rows = flows_extra.fetch_lme_stocks(y, m, session=_lme_sess)
            if rows:
                payload = [
                    ("LME:CA_STOCKS", r2["ts"], r2["copper_tonnes"], "LME:XLSX") for r2 in rows
                ]
                n_new = _db.insert_observations(conn, payload)
                total_new += n_new
                print(
                    f"  {y}-{m:02d}: {len(rows)} rows ({n_new} new) — "
                    f"latest {rows[-1]['ts']} = {rows[-1]['copper_tonnes']:,.0f}t"
                )
            else:
                print(f"  {y}-{m:02d}: (no file yet)")
        except Exception as ex:
            lme_err = str(ex)[:140]
            print(f"  ⚠ LME {y}-{m:02d}: {str(ex)[:70]}")

    if a.lme_years:
        print(f"=== LME backfill {a.lme_years} years ===")
        import time as _time

        start = now_d.year - a.lme_years
        n_files = n_empty = n_fail = 0
        for y in range(start, now_d.year + 1):
            for m in range(1, 13):
                if (y, m) > (now_d.year, now_d.month):
                    continue
                try:
                    rows = flows_extra.fetch_lme_stocks(y, m, session=_lme_sess)
                    if rows:
                        n_files += 1
                        n_new = _db.insert_observations(
                            conn,
                            [
                                ("LME:CA_STOCKS", r2["ts"], r2["copper_tonnes"], "LME:XLSX")
                                for r2 in rows
                            ],
                        )
                        total_new += n_new
                    else:
                        n_empty += 1
                except Exception:
                    n_fail += 1  # rate-limit block or missing month — counted, not hidden
                _time.sleep(0.6)  # pacing: request bursts trigger HTML bot challenges
            print(
                f"  {y}: {n_files} files · {n_empty} empty · {n_fail} failed "
                f"(new cumulative: {total_new})"
            )
        print(f"  total new backfill rows: {total_new}")

    # fetch_log for the f2 collections. The target is the series_id (so
    # health checks can join on it); the LME counter reports new rows;
    # flows-extra is idempotent by design and reports OK-0.
    from .fetch_log import log_collection

    log_collection(conn, "f2", "LME:CA_STOCKS", None, total_new, err=lme_err)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
