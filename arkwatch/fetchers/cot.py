"""cot.py — CFTC Commitments of Traders: all categories x 156 weeks of history.

Socrata datasets:
  Legacy 6dca-aqww · TFF gpe5-46if · Disaggregated 72hh-3qpy

Native field names per dataset (verified):
  Disagg: m_money_positions_*_all · prod_merc_positions_* · swap_positions_*_all
          other_rept_positions_* · nonrept_positions_*_all
  TFF:    lev_money_positions_*_all · asset_mgr_positions_*_all
          dealer_positions_*_all · other_rept_positions_*
  Legacy: noncomm_positions_*_all · comm_positions_*_all

Concentration: conc_gross_le_4_tdr_* and conc_gross_le_8_tdr_*
Traders: traders_*_long_all / traders_*_short_all
Changes: change_in_*_long_all / change_in_*_short_all
"""

from __future__ import annotations

import requests

BASE = "https://publicreporting.cftc.gov/resource"
DATASETS = {
    "legacy": "6dca-aqww",
    "tff": "gpe5-46if",
    "disagg": "72hh-3qpy",
    "disagg_c": "kh3c-gbw2",  # combined futures+options Disaggregated
    "tff_c": "yw9f-hn96",  # combined futures+options TFF
}

# Category key -> Socrata field prefix, per dataset.
CATEGORY_MAP = {
    "disagg": {
        "mm": "m_money",
        "prod": "prod_merc",
        "swap": "swap",
        "other": "other_rept",
        "nonrep": "nonrept",
    },
    "disagg_c": {  # same field names as disagg
        "mm": "m_money",
        "prod": "prod_merc",
        "swap": "swap",
        "other": "other_rept",
        "nonrep": "nonrept",
    },
    "tff": {
        "lev": "lev_money",
        "am": "asset_mgr",
        "dealer": "dealer",
        "other": "other_rept",
    },
    "tff_c": {  # combined futures+options TFF
        "lev": "lev_money",
        "am": "asset_mgr",
        "dealer": "dealer",
        "other": "other_rept",
    },
    "legacy": {
        "noncomm": "noncomm",
        "comm": "comm",
        # Legacy also reports nonreportable positions; without this entry
        # retail positioning would never be stored for legacy fetches.
        "nonrep": "nonrept",
    },
}


class CotError(RuntimeError):
    pass


def _i(v):
    if v in (None, "", "nan"):
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except (ValueError, TypeError):
        return None


def _f(v):
    if v in (None, "", "nan"):
        return None
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return None


def fetch_cot(dataset: str, contract_code: str, limit: int = 156) -> list[dict]:
    """Fetch full COT — all categories, all fields, `limit` weeks of history.

    Returns a list of {report_date, category, long, short, spread, oi, pct,
                       conc4_l, conc4_s, conc8_l, conc8_s,
                       traders_l, traders_s, chg_l, chg_s, name}
    — one dict PER CATEGORY PER WEEK.
    """
    ds = DATASETS.get(dataset)
    if not ds:
        raise CotError(f"unknown dataset: {dataset}")
    params = {
        "$where": f"cftc_contract_market_code='{contract_code}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": limit,
    }
    r = requests.get(f"{BASE}/{ds}.json", params=params, timeout=(10, 60))
    if r.status_code != 200:
        raise CotError(f"COT {dataset}/{contract_code}: HTTP {r.status_code}")
    rows = r.json()
    if not rows:
        return []

    cats = CATEGORY_MAP.get(dataset, {})
    out = []
    for row in rows:
        rd = str(row.get("report_date_as_yyyy_mm_dd", ""))[:10]
        if not rd:
            continue
        name = row.get("contract_market_name") or row.get("market_and_exchange_names", "")
        oi = _i(row.get("open_interest_all"))
        # concentration ratios exist in disagg/legacy but not in all TFF reports
        conc4l = _f(row.get("conc_gross_le_4_tdr_long"))
        conc4s = _f(row.get("conc_gross_le_4_tdr_short"))
        conc8l = _f(row.get("conc_gross_le_8_tdr_long"))
        conc8s = _f(row.get("conc_gross_le_8_tdr_short"))

        for cat_key, field_prefix in cats.items():
            # field names vary: some categories use the _all suffix, some do not
            long_key = f"{field_prefix}_positions_long_all"
            short_key = f"{field_prefix}_positions_short_all"
            spread_key = f"{field_prefix}_positions_spread"
            # fallback for fields without the _all suffix (prod_merc, other_rept)
            if row.get(long_key) is None:
                long_key = f"{field_prefix}_positions_long"
            if row.get(short_key) is None:
                short_key = f"{field_prefix}_positions_short"

            lng = _i(row.get(long_key))
            sht = _i(row.get(short_key))
            if lng is None and sht is None:
                continue

            # An `or` chain would turn legitimate 0 values into None
            # (pct=0/traders=0/change=0 would vanish); pick the first
            # non-None value explicitly.
            def _first(*vals):
                for v in vals:
                    if v is not None:
                        return v
                return None

            spr = _first(
                _i(row.get(spread_key)), _i(row.get(f"{field_prefix}_positions_spread_all"))
            )
            pct = _first(
                _f(row.get(f"pct_of_oi_{field_prefix}_long_all")),
                _f(row.get(f"pct_of_oi_{field_prefix}_long")),
            )
            # trader counts
            trl = _first(
                _i(row.get(f"traders_{field_prefix}_long_all")),
                _i(row.get(f"traders_{field_prefix}_long")),
            )
            trs = _first(
                _i(row.get(f"traders_{field_prefix}_short_all")),
                _i(row.get(f"traders_{field_prefix}_short")),
            )
            # weekly changes
            chl = _first(
                _i(row.get(f"change_in_{field_prefix}_long_all")),
                _i(row.get(f"change_in_{field_prefix}_long")),
            )
            chs = _first(
                _i(row.get(f"change_in_{field_prefix}_short_all")),
                _i(row.get(f"change_in_{field_prefix}_short")),
            )

            out.append(
                {
                    "report_date": rd,
                    "contract_code": contract_code,
                    "report_type": dataset,
                    "category": cat_key,
                    "name": name,
                    "long": lng,
                    "short": sht,
                    "spread": spr,
                    "open_interest_all": oi,
                    "pct_of_oi": pct,
                    "conc4_long": conc4l,
                    "conc4_short": conc4s,
                    "conc8_long": conc8l,
                    "conc8_short": conc8s,
                    "traders_long": trl,
                    "traders_short": trs,
                    "change_long": chl,
                    "change_short": chs,
                }
            )
    return out
