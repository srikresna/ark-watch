"""playbook_tracker.py — Automated lifecycle state machine and outcome tracking for trading playbooks.

Tracks trading scenarios from generation through resolution:
  - PENDING_TRIGGER -> Waiting for price action to confirm trigger condition
  - ACTIVE -> Trigger condition verified; tracks real-time MFE (Max Favorable Excursion) and MAE (Max Adverse Excursion)
  - HIT_TARGET_WIN -> Price reached target profit
  - HIT_STOP_LOSS -> Price reached invalidation stop
  - CANCELLED_EXPIRED -> Session ended without trigger condition materializing
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from ..timezones import format_session_id, resolve_timezone


def record_playbook_scenarios(
    conn: sqlite3.Connection,
    playbook_payload: dict[str, Any],
    *,
    cfd_basis_offset: float = 0.0,
) -> list[str]:
    """Extract and persist all generated scenarios into playbook_scenarios table."""
    symbol = playbook_payload["symbol"]
    now_utc = playbook_payload.get("as_of", datetime.now(UTC).isoformat(timespec="seconds"))
    session_id = playbook_payload.get("reference_levels", {}).get(
        "active_session_current", now_utc[:10]
    )

    scenarios = playbook_payload.get("scenarios", [])
    recorded_uids = []

    for sc in scenarios:
        sc_id = sc["id"]
        horizon = sc.get("horizon", "INTRADAY").upper()
        direction = sc["direction"].upper()
        if direction not in ("LONG", "SHORT", "NEUTRAL_RANGE"):
            direction = "NEUTRAL_RANGE"

        target_p = float(sc["target_profit"]) + cfd_basis_offset
        inval_p = float(sc["invalidation_level"]) + cfd_basis_offset
        rr = float(sc.get("risk_reward_ratio", 1.0))
        trigger_cond = sc["trigger_condition"]
        trigger_price = (
            float(sc.get("trigger_price", playbook_payload.get("last_price", 0.0)))
            + cfd_basis_offset
        )

        scenario_uid = f"{symbol}-{session_id}-{horizon}-{sc_id}"

        payload_json = json.dumps(
            {
                "scenario": sc,
                "catalysts": playbook_payload.get("catalysts", {}),
                "multi_domain": playbook_payload.get("multi_domain", {}),
                "amt_context": playbook_payload.get("amt_context", {}),
                "decision_log": [
                    {
                        "ts_utc": now_utc,
                        "event": "CREATED_PENDING",
                        "details": f"Scenario created with trigger {trigger_price}, TP {target_p}, SL {inval_p}",
                    }
                ],
            }
        )

        try:
            conn.execute(
                """
                INSERT INTO playbook_scenarios (
                    scenario_uid, symbol, horizon, direction, scenario_id, title,
                    trigger_condition, trigger_price, target_profit, invalidation_level,
                    risk_reward_ratio, created_at_utc, session_id, state,
                    cfd_basis_offset, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_TRIGGER', ?, ?)
                ON CONFLICT(scenario_uid) DO UPDATE SET
                    target_profit=excluded.target_profit,
                    invalidation_level=excluded.invalidation_level,
                    payload_json=excluded.payload_json
                WHERE state = 'PENDING_TRIGGER'
                """,
                (
                    scenario_uid,
                    symbol,
                    horizon,
                    direction,
                    sc_id,
                    sc["title"],
                    trigger_cond,
                    trigger_price,
                    target_p,
                    inval_p,
                    rr,
                    now_utc,
                    session_id,
                    cfd_basis_offset,
                    payload_json,
                ),
            )
            recorded_uids.append(scenario_uid)
        except sqlite3.Error:
            pass

    conn.commit()
    return recorded_uids


def evaluate_active_playbooks(
    conn: sqlite3.Connection,
    *,
    as_of: datetime | str | None = None,
) -> dict[str, int]:
    """Advance the state machine for all open scenarios using subsequent 1m/5m bars."""
    if as_of is None:
        target_dt = datetime.now(UTC)
    elif isinstance(as_of, str):
        target_dt = datetime.fromisoformat(as_of).astimezone(UTC)
    else:
        target_dt = as_of.astimezone(UTC)

    target_ts = target_dt.isoformat(timespec="seconds")

    pending_or_active = conn.execute(
        """
        SELECT scenario_uid, symbol, horizon, direction, scenario_id,
               trigger_price, target_profit, invalidation_level, risk_reward_ratio,
               created_at_utc, state, entry_price, mfe_points, mae_points, session_id
        FROM playbook_scenarios
        WHERE state IN ('PENDING_TRIGGER', 'ACTIVE')
        """
    ).fetchall()

    if not pending_or_active:
        return {
            "evaluated": 0,
            "activated": 0,
            "resolved_wins": 0,
            "resolved_losses": 0,
            "resolved_breakeven": 0,
            "resolved_invalidated": 0,
        }

    stats = {
        "evaluated": len(pending_or_active),
        "activated": 0,
        "resolved_wins": 0,
        "resolved_losses": 0,
        "resolved_breakeven": 0,
        "resolved_invalidated": 0,
    }
    for row in pending_or_active:
        (
            uid,
            sym,
            horizon,
            direction,
            sc_id,
            trig_p,
            target_p,
            inval_p,
            rr,
            created_at,
            state,
            entry_p,
            mfe,
            mae,
            sc_sess_id,
        ) = row

        # Check fresh state from DB in case an earlier iteration in this batch cancelled it
        cur_db_state = conn.execute(
            "SELECT state, entry_price FROM playbook_scenarios WHERE scenario_uid = ?", (uid,)
        ).fetchone()
        if not cur_db_state or cur_db_state[0] not in ("PENDING_TRIGGER", "ACTIVE"):
            continue
        state = cur_db_state[0]
        if cur_db_state[1] is not None:
            entry_p = cur_db_state[1]

        # Fetch subsequent bars since creation
        bars = conn.execute(
            """
            SELECT bar_ts_utc, open, high, low, close, COALESCE(volume, 0.0)
            FROM intraday_bars
            WHERE symbol = ?
              AND bar_ts_utc >= ?
              AND bar_ts_utc <= ?
            ORDER BY bar_ts_utc ASC
            """,
            (sym, created_at, target_ts),
        ).fetchall()

        if not bars:
            continue

        if state == "PENDING_TRIGGER":
            activated = False
            invalidated = False
            activation_bar = None
            inval_bar = None
            for b in bars:
                b_high = b[2]
                b_low = b[3]
                b_close = b[4]
                if direction == "LONG":
                    if b_low <= inval_p:
                        invalidated = True
                        inval_bar = b
                        break
                    if b_close >= trig_p or b_high >= trig_p:
                        activated = True
                        activation_bar = b
                        break
                elif direction == "SHORT":
                    if b_high >= inval_p:
                        invalidated = True
                        inval_bar = b
                        break
                    if b_close <= trig_p or b_low <= trig_p:
                        activated = True
                        activation_bar = b
                        break

            if invalidated and inval_bar:
                inval_time = inval_bar[0]
                cur_payload_row = conn.execute(
                    "SELECT payload_json FROM playbook_scenarios WHERE scenario_uid = ?", (uid,)
                ).fetchone()
                try:
                    cur_p = json.loads(cur_payload_row[0]) if cur_payload_row else {}
                except Exception:
                    cur_p = {}
                cur_p.setdefault("decision_log", []).append(
                    {
                        "ts_utc": inval_time,
                        "event": "INVALIDATED_BEFORE_TRIGGER",
                        "details": f"Price breached invalidation level {inval_p} on bar {inval_time} before trigger {trig_p}",
                    }
                )
                conn.execute(
                    """
                    UPDATE playbook_scenarios
                    SET state = 'CANCELLED_EXPIRED', resolved_at_utc = ?, payload_json = ?
                    WHERE scenario_uid = ?
                    """,
                    (inval_time, json.dumps(cur_p), uid),
                )
                stats["resolved_invalidated"] += 1
                continue

            if activated and activation_bar:
                # Option 1: Trigger Fill at intended trigger price
                entry_price = trig_p if trig_p is not None else activation_bar[4]
                trig_time = activation_bar[0]
                target_already_passed = (direction == "LONG" and target_p <= entry_price) or (
                    direction == "SHORT" and target_p >= entry_price
                )
                if target_already_passed:
                    cur_payload_row = conn.execute(
                        "SELECT payload_json FROM playbook_scenarios WHERE scenario_uid = ?", (uid,)
                    ).fetchone()
                    try:
                        cur_p = json.loads(cur_payload_row[0]) if cur_payload_row else {}
                    except Exception:
                        cur_p = {}
                    cur_p.setdefault("decision_log", []).append(
                        {
                            "ts_utc": trig_time,
                            "event": "CANCELLED_EXPIRED",
                            "details": f"Target price {target_p} was already surpassed upon trigger at {entry_price} (missed fill/slippage)",
                        }
                    )
                    conn.execute(
                        """
                        UPDATE playbook_scenarios
                        SET state = 'CANCELLED_EXPIRED', resolved_at_utc = ?, payload_json = ?
                        WHERE scenario_uid = ?
                        """,
                        (trig_time, json.dumps(cur_p), uid),
                    )
                    stats["resolved_invalidated"] += 1
                    continue
                cur_payload_row = conn.execute(
                    "SELECT payload_json FROM playbook_scenarios WHERE scenario_uid = ?", (uid,)
                ).fetchone()
                try:
                    cur_p = json.loads(cur_payload_row[0]) if cur_payload_row else {}
                except Exception:
                    cur_p = {}
                cur_p.setdefault("decision_log", []).append(
                    {
                        "ts_utc": trig_time,
                        "event": "TRIGGERED_ACTIVE",
                        "details": f"Trigger met at price {entry_price} on bar {trig_time}",
                    }
                )

                conn.execute(
                    """
                    UPDATE playbook_scenarios
                    SET state = 'ACTIVE', triggered_at_utc = ?, entry_price = ?,
                        mfe_points = 0.0, mae_points = 0.0, payload_json = ?
                    WHERE scenario_uid = ?
                    """,
                    (trig_time, entry_price, json.dumps(cur_p), uid),
                )

                # 1. Close any existing ACTIVE opposing scenarios immediately (Reversal Exit Flip)
                active_opposing = conn.execute(
                    """
                    SELECT scenario_uid, direction, entry_price, invalidation_level, payload_json, mfe_points, mae_points
                    FROM playbook_scenarios
                    WHERE symbol = ? AND session_id = ? AND horizon = ?
                      AND state = 'ACTIVE' AND scenario_uid != ? AND direction != ?
                    """,
                    (sym, sc_sess_id, horizon, uid, direction),
                ).fetchall()
                for (
                    opp_uid,
                    opp_dir,
                    opp_entry,
                    opp_inval,
                    opp_payload_str,
                    _opp_mfe,
                    _opp_mae,
                ) in active_opposing:
                    try:
                        opp_p = json.loads(opp_payload_str) if opp_payload_str else {}
                    except Exception:
                        opp_p = {}
                    opp_exit = entry_price
                    opp_pnl = (
                        (opp_exit - opp_entry) if opp_dir == "LONG" else (opp_entry - opp_exit)
                    )
                    opp_risk = abs(opp_entry - opp_inval) or 1.0
                    opp_r = round(opp_pnl / opp_risk, 2)
                    opp_p.setdefault("decision_log", []).append(
                        {
                            "ts_utc": trig_time,
                            "event": "REVERSAL_EXIT_FLIP",
                            "details": f"Market structure reversed: closed early at {opp_exit} (PnL: {round(opp_pnl, 2)}, {opp_r}R) because opposing setup {uid} triggered ACTIVE",
                        }
                    )
                    conn.execute(
                        """
                        UPDATE playbook_scenarios
                        SET state = 'CANCELLED_EXPIRED', resolved_at_utc = ?, exit_price = ?,
                            pnl_points = ?, r_multiple = ?, payload_json = ?
                        WHERE scenario_uid = ?
                        """,
                        (trig_time, opp_exit, round(opp_pnl, 2), opp_r, json.dumps(opp_p), opp_uid),
                    )
                    stats["resolved_losses" if opp_pnl < 0 else "resolved_wins"] += 1

                # 2. Cancel opposing pending scenarios on same instrument, session & horizon
                opposing_rows = conn.execute(
                    """
                    SELECT scenario_uid, payload_json FROM playbook_scenarios
                    WHERE symbol = ? AND session_id = ? AND horizon = ?
                      AND state = 'PENDING_TRIGGER' AND scenario_uid != ?
                    """,
                    (sym, sc_sess_id, horizon, uid),
                ).fetchall()
                for opp_uid, opp_payload_str in opposing_rows:
                    try:
                        opp_p = json.loads(opp_payload_str) if opp_payload_str else {}
                    except Exception:
                        opp_p = {}
                    opp_p.setdefault("decision_log", []).append(
                        {
                            "ts_utc": trig_time,
                            "event": "CANCELLED_SUPERSEDED",
                            "details": f"Cancelled because scenario {uid} activated first",
                        }
                    )
                    conn.execute(
                        """
                        UPDATE playbook_scenarios
                        SET state = 'CANCELLED_EXPIRED', resolved_at_utc = ?, payload_json = ?
                        WHERE scenario_uid = ?
                        """,
                        (trig_time, json.dumps(opp_p), opp_uid),
                    )
                stats["activated"] += 1
                state = "ACTIVE"
                entry_p = entry_price
                bars = [b for b in bars if b[0] >= trig_time]
        if state == "ACTIVE" and entry_p:
            current_mfe = mfe or 0.0
            current_mae = mae or 0.0
            resolved_state = None
            exit_price = None
            resolved_time = None

            risk_dist = abs(entry_p - inval_p) or 1.0
            be_ratchet_active = False
            partial_tp_taken = False
            partial_pnl_pts = 0.0
            consecutive_vwap_losses = 0

            cum_pv = 0.0
            cum_vol = 0.0

            cur_payload_row = conn.execute(
                "SELECT payload_json FROM playbook_scenarios WHERE scenario_uid = ?", (uid,)
            ).fetchone()
            try:
                cur_p = json.loads(cur_payload_row[0]) if cur_payload_row else {}
            except Exception:
                cur_p = {}

            if any(log.get("event") == "PARTIAL_TP_50" for log in cur_p.get("decision_log", [])):
                partial_tp_taken = True
                be_ratchet_active = True
                partial_pnl_pts = round(0.5 * (1.0 * risk_dist), 2)

            # Multi-Domain Catalyst Defense
            try:
                from .sentiment import compute_intraday_catalyst_radar

                fast_cat = compute_intraday_catalyst_radar(
                    conn, sym, window_hours=2, as_of=target_ts
                )
                cat_score = fast_cat.get("net_stance_score", 0.0) if fast_cat else 0.0
            except Exception:
                cat_score = 0.0

            adverse_news_shock = (direction == "LONG" and cat_score <= -0.30) or (
                direction == "SHORT" and cat_score >= 0.30
            )
            if adverse_news_shock:
                if current_mfe > 0.0:
                    be_ratchet_active = True
                else:
                    inval_p = (
                        round(entry_p - (0.5 * risk_dist), 2)
                        if direction == "LONG"
                        else round(entry_p + (0.5 * risk_dist), 2)
                    )

            for b in bars:
                b_high = b[2]
                b_low = b[3]
                b_close = b[4]
                b_vol = max(1.0, float(b[5]) if len(b) > 5 and b[5] is not None else 1.0)

                typical = (b_high + b_low + b_close) / 3.0
                cum_pv += typical * b_vol
                cum_vol += b_vol
                session_vwap = cum_pv / cum_vol if cum_vol > 0 else b_close

                if direction == "LONG":
                    fav = b_high - entry_p
                    adv = entry_p - b_low
                    current_mfe = max(current_mfe, fav)
                    current_mae = max(current_mae, adv)

                    ratcheted_this_bar = False
                    # 1. Partial TP 50% at +1.0R Extension
                    if current_mfe >= 1.0 * risk_dist and not partial_tp_taken:
                        partial_tp_taken = True
                        be_ratchet_active = True
                        ratcheted_this_bar = True
                        partial_pnl_pts = round(0.5 * (1.0 * risk_dist), 2)
                        cur_p.setdefault("decision_log", []).append(
                            {
                                "ts_utc": b[0],
                                "event": "PARTIAL_TP_50",
                                "details": f"Hit +1.0R milestone (+{round(current_mfe, 2)} pts): scaled out 50% position (+0.50R / +{partial_pnl_pts} pts profit), moved remaining stop loss to Break-Even at {entry_p}",
                            }
                        )

                    # 2. Target Hit (Full Win)
                    if b_high >= target_p and target_p > entry_p:
                        resolved_state = "HIT_TARGET_WIN"
                        exit_price = target_p
                        resolved_time = b[0]
                        break

                    # 3. Early Full TP on Consecutive Session VWAP Loss (Structural Failure)
                    if partial_tp_taken and b_close < session_vwap:
                        consecutive_vwap_losses += 1
                        if consecutive_vwap_losses >= 2 and b_close > entry_p:
                            resolved_state = "EARLY_FULL_TP"
                            exit_price = b_close
                            resolved_time = b[0]
                            break
                    else:
                        consecutive_vwap_losses = 0

                    # 4. Stop Loss / Break-Even Hit
                    if be_ratchet_active and not ratcheted_this_bar and b_low <= entry_p:
                        resolved_state = "HIT_BREAKEVEN"
                        exit_price = entry_p
                        resolved_time = b[0]
                        break
                    if b_low <= inval_p:
                        resolved_state = "HIT_STOP_LOSS"
                        exit_price = inval_p
                        resolved_time = b[0]
                        break

                elif direction == "SHORT":
                    fav = entry_p - b_low
                    adv = b_high - entry_p
                    current_mfe = max(current_mfe, fav)
                    current_mae = max(current_mae, adv)

                    ratcheted_this_bar = False
                    # 1. Partial TP 50% at +1.0R Extension
                    if current_mfe >= 1.0 * risk_dist and not partial_tp_taken:
                        partial_tp_taken = True
                        be_ratchet_active = True
                        ratcheted_this_bar = True
                        partial_pnl_pts = round(0.5 * (1.0 * risk_dist), 2)
                        cur_p.setdefault("decision_log", []).append(
                            {
                                "ts_utc": b[0],
                                "event": "PARTIAL_TP_50",
                                "details": f"Hit +1.0R milestone (+{round(current_mfe, 2)} pts): scaled out 50% position (+0.50R / +{partial_pnl_pts} pts profit), moved remaining stop loss to Break-Even at {entry_p}",
                            }
                        )

                    # 2. Target Hit (Full Win)
                    if b_low <= target_p and target_p < entry_p:
                        resolved_state = "HIT_TARGET_WIN"
                        exit_price = target_p
                        resolved_time = b[0]
                        break

                    # 3. Early Full TP on Consecutive Session VWAP Loss (Structural Failure)
                    if partial_tp_taken and b_close > session_vwap:
                        consecutive_vwap_losses += 1
                        if consecutive_vwap_losses >= 2 and b_close < entry_p:
                            resolved_state = "EARLY_FULL_TP"
                            exit_price = b_close
                            resolved_time = b[0]
                            break
                    else:
                        consecutive_vwap_losses = 0

                    # 4. Stop Loss / Break-Even Hit
                    if be_ratchet_active and not ratcheted_this_bar and b_high >= entry_p:
                        resolved_state = "HIT_BREAKEVEN"
                        exit_price = entry_p
                        resolved_time = b[0]
                        break
                    if b_high >= inval_p:
                        resolved_state = "HIT_STOP_LOSS"
                        exit_price = inval_p
                        resolved_time = b[0]
                        break

            if resolved_state:
                raw_exit_pnl = (
                    (exit_price - entry_p) if direction == "LONG" else (entry_p - exit_price)
                )
                if partial_tp_taken:
                    total_pnl = partial_pnl_pts + (0.5 * raw_exit_pnl)
                else:
                    total_pnl = raw_exit_pnl

                risk_dist = abs(entry_p - inval_p) or 1.0
                r_mult = round(total_pnl / risk_dist, 2)

                if resolved_state == "HIT_TARGET_WIN" and total_pnl <= 0.0:
                    resolved_state = "CANCELLED_EXPIRED"

                cur_p.setdefault("decision_log", []).append(
                    {
                        "ts_utc": resolved_time,
                        "event": resolved_state,
                        "details": f"Exit reached at {exit_price}. Net PnL: {round(total_pnl, 2)} pts ({r_mult}R). MFE: +{round(current_mfe, 2)}, MAE: -{round(current_mae, 2)}",
                    }
                )

                db_state = (
                    "HIT_TARGET_WIN"
                    if (
                        resolved_state in ("HIT_TARGET_WIN", "EARLY_FULL_TP")
                        or (resolved_state == "HIT_BREAKEVEN" and total_pnl > 0)
                    )
                    else (
                        "HIT_STOP_LOSS"
                        if resolved_state == "HIT_STOP_LOSS"
                        else "CANCELLED_EXPIRED"
                    )
                )
                conn.execute(
                    """
                    UPDATE playbook_scenarios
                    SET state = ?, resolved_at_utc = ?, exit_price = ?,
                        mfe_points = ?, mae_points = ?, pnl_points = ?, r_multiple = ?,
                        payload_json = ?
                    WHERE scenario_uid = ?
                    """,
                    (
                        db_state,
                        resolved_time,
                        exit_price,
                        round(current_mfe, 2),
                        round(current_mae, 2),
                        round(total_pnl, 2),
                        r_mult,
                        json.dumps(cur_p),
                        uid,
                    ),
                )
                if db_state == "HIT_TARGET_WIN":
                    stats["resolved_wins"] += 1
                elif resolved_state == "HIT_BREAKEVEN":
                    stats["resolved_breakeven"] += 1
                else:
                    stats["resolved_losses"] += 1
            else:
                conn.execute(
                    """
                    UPDATE playbook_scenarios
                    SET mfe_points = ?, mae_points = ?, payload_json = ?
                    WHERE scenario_uid = ?
                    """,
                    (round(current_mfe, 2), round(current_mae, 2), json.dumps(cur_p), uid),
                )
    conn.commit()
    return stats


def get_playbook_performance_metrics(
    conn: sqlite3.Connection,
    symbol: str | None = None,
    horizon: str | None = None,
    outcome: str | None = None,
    detail: bool = False,
) -> dict[str, Any]:
    """Calculate institutional performance metrics: Win Rate, Profit Factor, MFE/MAE, and R-Multiple."""
    where_clauses = []
    params = []
    if symbol:
        where_clauses.append("symbol = ?")
        params.append(symbol.strip().upper())
    if horizon:
        where_clauses.append("horizon = ?")
        params.append(horizon.strip().upper())
    if outcome:
        out_u = outcome.strip().upper()
        if out_u in ("WIN", "WINS"):
            where_clauses.append("state = 'HIT_TARGET_WIN'")
        elif out_u in ("LOSS", "LOSE", "LOSSES"):
            where_clauses.append("state = 'HIT_STOP_LOSS'")
        elif out_u in ("BE", "BREAKEVEN"):
            where_clauses.append(
                "state = 'CANCELLED_EXPIRED' AND pnl_points = 0.0 AND mfe_points > 0"
            )
        elif out_u == "PENDING":
            where_clauses.append("state = 'PENDING_TRIGGER'")
        elif out_u == "ACTIVE":
            where_clauses.append("state = 'ACTIVE'")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = conn.execute(
        f"""
        SELECT state, pnl_points, r_multiple, mfe_points, mae_points
        FROM playbook_scenarios
        {where_sql}
        """,
        params,
    ).fetchall()

    if not rows:
        return {
            "total_scenarios": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "completed_trades": 0,
            "wins": 0,
            "losses": 0,
            "pending": 0,
            "active": 0,
            "avg_r_multiple": 0.0,
            "avg_mfe": 0.0,
            "avg_mae": 0.0,
        }
    wins = [r for r in rows if r[0] == "HIT_TARGET_WIN"]
    breakevens = [
        r for r in rows if r[0] == "CANCELLED_EXPIRED" and r[1] == 0.0 and r[3] and r[3] > 0
    ]
    losses = [r for r in rows if r[0] == "HIT_STOP_LOSS"]
    cancelled = [r for r in rows if r[0] == "CANCELLED_EXPIRED" and r not in breakevens]
    pending = sum(1 for r in rows if r[0] == "PENDING_TRIGGER")
    active = sum(1 for r in rows if r[0] == "ACTIVE")
    completed = len(wins) + len(losses) + len(breakevens)
    win_rate = round((len(wins) / completed * 100), 1) if completed > 0 else 0.0

    gross_profit = sum(r[1] for r in wins if r[1] and r[1] > 0)
    gross_loss = abs(sum(r[1] for r in losses if r[1] and r[1] < 0))
    profit_factor = (
        round(gross_profit / gross_loss, 2)
        if gross_loss > 0
        else (9.9 if gross_profit > 0 else 0.0)
    )

    completed_r = [r[2] for r in (wins + losses) if r[2] is not None]
    avg_r = round(sum(completed_r) / len(completed_r), 2) if completed_r else 0.0

    all_mfe = [r[3] for r in (wins + losses) if r[3] is not None]
    avg_mfe = round(sum(all_mfe) / len(all_mfe), 2) if all_mfe else 0.0

    all_mae = [r[4] for r in (wins + losses) if r[4] is not None]
    avg_mae = round(sum(all_mae) / len(all_mae), 2) if all_mae else 0.0

    res = {
        "total_scenarios": len(rows),
        "completed_trades": completed,
        "wins": len(wins),
        "breakevens": len(breakevens),
        "losses": len(losses),
        "invalidated": len(cancelled),
        "pending": pending,
        "active": active,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "avg_r_multiple": avg_r,
        "avg_mfe": avg_mfe,
        "avg_mae": avg_mae,
    }

    if detail:
        trade_rows = conn.execute(
            f"""
            SELECT rowid, scenario_uid, symbol, horizon, direction, scenario_id, title,
                   trigger_price, target_profit, invalidation_level, risk_reward_ratio,
                   state, entry_price, exit_price, pnl_points, r_multiple,
                   mfe_points, mae_points, created_at_utc, triggered_at_utc, resolved_at_utc, payload_json
            FROM playbook_scenarios
            {where_sql}
            ORDER BY rowid DESC
            """,
            params,
        ).fetchall()
        trades = []
        for t in trade_rows:
            try:
                p_data = json.loads(t[21]) if t[21] else {}
            except Exception:
                p_data = {}
            trades.append(
                {
                    "id": t[0],
                    "uid": t[1],
                    "symbol": t[2],
                    "horizon": t[3],
                    "direction": t[4],
                    "scenario_id": t[5],
                    "title": t[6],
                    "trigger_price": t[7],
                    "target_profit": t[8],
                    "invalidation_level": t[9],
                    "risk_reward_ratio": t[10],
                    "state": t[11],
                    "entry_price": t[12],
                    "exit_price": t[13],
                    "pnl_points": t[14],
                    "r_multiple": t[15],
                    "mfe_points": t[16],
                    "mae_points": t[17],
                    "created_at_utc": t[18],
                    "triggered_at_utc": t[19],
                    "resolved_at_utc": t[20],
                    "decision_log": p_data.get("decision_log", []),
                }
            )
        breakdowns = build_tracker_breakdowns(trades)
        res["breakdown_by_symbol"] = breakdowns["by_symbol"]
        res["breakdown_by_scenario"] = breakdowns["by_scenario"]
        res["trades"] = trades

    return res


def build_tracker_breakdowns(trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate granular breakdowns by asset symbol and by scenario pattern."""
    from collections import defaultdict

    by_sym = defaultdict(
        lambda: {
            "total": 0,
            "completed": 0,
            "wins": 0,
            "losses": 0,
            "breakevens": 0,
            "net_pnl": 0.0,
            "gross_win": 0.0,
            "gross_loss": 0.0,
            "r_list": [],
        }
    )
    by_sc = defaultdict(
        lambda: {
            "total": 0,
            "completed": 0,
            "wins": 0,
            "losses": 0,
            "breakevens": 0,
            "r_list": [],
        }
    )

    for t in trades:
        s = t.get("symbol", "UNKNOWN")
        st = t.get("state", "UNKNOWN")
        pnl = t.get("pnl_points") or 0.0
        r = t.get("r_multiple")
        sc = t.get("scenario_id", "UNKNOWN").replace("SCENARIO_", "")

        by_sym[s]["total"] += 1
        by_sc[sc]["total"] += 1

        if st == "HIT_TARGET_WIN":
            by_sym[s]["wins"] += 1
            by_sym[s]["completed"] += 1
            by_sc[sc]["wins"] += 1
            by_sc[sc]["completed"] += 1
            if pnl > 0:
                by_sym[s]["gross_win"] += pnl
        elif st == "HIT_STOP_LOSS":
            by_sym[s]["losses"] += 1
            by_sym[s]["completed"] += 1
            by_sc[sc]["losses"] += 1
            by_sc[sc]["completed"] += 1
            if pnl < 0:
                by_sym[s]["gross_loss"] += abs(pnl)
        elif pnl == 0.0 and (t.get("mfe_points") or 0.0) > 0:
            by_sym[s]["breakevens"] += 1
            by_sym[s]["completed"] += 1
            by_sc[sc]["breakevens"] += 1
            by_sc[sc]["completed"] += 1

        by_sym[s]["net_pnl"] += pnl
        if r is not None and st in ("HIT_TARGET_WIN", "HIT_STOP_LOSS"):
            by_sym[s]["r_list"].append(r)
            by_sc[sc]["r_list"].append(r)

    symbol_table = []
    for s, d in sorted(by_sym.items(), key=lambda x: x[1]["total"], reverse=True):
        comp = d["completed"]
        wr = round((d["wins"] / comp * 100), 1) if comp > 0 else 0.0
        avg_r = round(sum(d["r_list"]) / len(d["r_list"]), 2) if d["r_list"] else 0.0
        pf = (
            round(d["gross_win"] / d["gross_loss"], 2)
            if d["gross_loss"] > 0
            else (9.9 if d["gross_win"] > 0 else 0.0)
        )
        symbol_table.append(
            {
                "symbol": s,
                "total_scenarios": d["total"],
                "completed_trades": comp,
                "wins": d["wins"],
                "losses": d["losses"],
                "breakevens": d["breakevens"],
                "win_rate_pct": wr,
                "net_pnl_points": round(d["net_pnl"], 2),
                "profit_factor": pf,
                "avg_r_multiple": avg_r,
            }
        )

    scenario_table = []
    for sc, d in sorted(by_sc.items(), key=lambda x: x[1]["total"], reverse=True):
        comp = d["completed"]
        wr = round((d["wins"] / comp * 100), 1) if comp > 0 else 0.0
        avg_r = round(sum(d["r_list"]) / len(d["r_list"]), 2) if d["r_list"] else 0.0
        scenario_table.append(
            {
                "scenario": sc,
                "total_scenarios": d["total"],
                "completed_trades": comp,
                "wins": d["wins"],
                "losses": d["losses"],
                "breakevens": d["breakevens"],
                "win_rate_pct": wr,
                "avg_r_multiple": avg_r,
            }
        )

    return {"by_symbol": symbol_table, "by_scenario": scenario_table}


def get_trade_by_uid(conn: sqlite3.Connection, identifier: str | int) -> dict[str, Any] | None:
    """Fetch exact trade row and parsed decision log by short numeric ID or scenario UID."""
    raw_str = str(identifier).strip().lstrip("#")
    if raw_str.isdigit():
        row = conn.execute(
            """
            SELECT rowid, scenario_uid, symbol, horizon, direction, scenario_id, title,
                   trigger_price, target_profit, invalidation_level, risk_reward_ratio,
                   state, entry_price, exit_price, pnl_points, r_multiple,
                   mfe_points, mae_points, created_at_utc, triggered_at_utc, resolved_at_utc, payload_json
            FROM playbook_scenarios
            WHERE rowid = ?
            """,
            (int(raw_str),),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT rowid, scenario_uid, symbol, horizon, direction, scenario_id, title,
                   trigger_price, target_profit, invalidation_level, risk_reward_ratio,
                   state, entry_price, exit_price, pnl_points, r_multiple,
                   mfe_points, mae_points, created_at_utc, triggered_at_utc, resolved_at_utc, payload_json
            FROM playbook_scenarios
            WHERE scenario_uid = ? OR scenario_uid LIKE ?
            """,
            (raw_str, f"%{raw_str}%"),
        ).fetchone()
    if not row:
        return None
    try:
        p_data = json.loads(row[21]) if row[21] else {}
    except Exception:
        p_data = {}
    return {
        "id": row[0],
        "uid": row[1],
        "symbol": row[2],
        "horizon": row[3],
        "direction": row[4],
        "scenario_id": row[5],
        "title": row[6],
        "trigger_price": row[7],
        "target_profit": row[8],
        "invalidation_level": row[9],
        "risk_reward_ratio": row[10],
        "state": row[11],
        "entry_price": row[12],
        "exit_price": row[13],
        "pnl_points": row[14],
        "r_multiple": row[15],
        "mfe_points": row[16],
        "mae_points": row[17],
        "created_at_utc": row[18],
        "triggered_at_utc": row[19],
        "resolved_at_utc": row[20],
        "decision_log": p_data.get("decision_log", []),
    }


def format_tracker_detailed_report(
    res: dict[str, Any],
    display_tz: str | None = None,
    limit_trades: int = 15,
) -> str:
    """Format full tracker metrics, asset breakdown, setup breakdown, and journal into terminal dashboard."""
    _, tz_lbl = resolve_timezone(display_tz)

    lines = []
    lines.append("=" * 105)
    lines.append(
        f"                    ARK-WATCH PLAYBOOK PERFORMANCE TRACKER REPORT (TZ: {tz_lbl})"
    )
    lines.append("=" * 105)
    lines.append(
        f"  Total Skenario   : {res.get('total_scenarios', 0):<4}                    "
        f"Win Rate        : {res.get('win_rate_pct', 0.0)}% ({res.get('wins', 0)}W / {res.get('losses', 0)}L / {res.get('breakevens', 0)}BE)"
    )
    lines.append(
        f"  Completed Trades : {res.get('completed_trades', 0):<4}                    "
        f"Profit Factor   : {res.get('profit_factor', 0.0)}"
    )
    lines.append(
        f"  Pending Trigger  : {res.get('pending', 0):<4}                    "
        f"Avg R-Multiple  : {res.get('avg_r_multiple', 0.0):+.2f}R"
    )
    lines.append(
        f"  Active Running   : {res.get('active', 0):<4}                    "
        f"Avg MFE / MAE   : +{res.get('avg_mfe', 0.0)} pts / -{res.get('avg_mae', 0.0)} pts"
    )
    lines.append(f"  Invalidated/Exp  : {res.get('invalidated', 0):<4}")
    lines.append("-" * 105)

    # 1. Asset Breakdown
    by_sym = res.get("breakdown_by_symbol", [])
    if by_sym:
        lines.append("📈 PERFORMA PER INSTRUMEN (ASSET BREAKDOWN):")
        lines.append(
            f"  {'Simbol':<8} | {'Total':>5} | {'Done':>5} | {'Win':>4} | {'Loss':>4} | {'BE':>3} | {'WinRate':>7} | {'Net PnL':>11} | {'ProfitFac':>9} | {'Avg R':>7}"
        )
        lines.append("  " + "-" * 95)
        for d in by_sym:
            lines.append(
                f"  {d['symbol']:<8} | {d['total_scenarios']:>5} | {d['completed_trades']:>5} | {d['wins']:>4} | {d['losses']:>4} | {d['breakevens']:>3} | {d['win_rate_pct']:>6.1f}% | {d['net_pnl_points']:>11.2f} | {d['profit_factor']:>9.2f} | {d['avg_r_multiple']:>+6.2f}R"
            )
        lines.append("-" * 105)

    # 2. Setup Breakdown
    by_sc = res.get("breakdown_by_scenario", [])
    if by_sc:
        lines.append("🎯 PERFORMA PER TIPE SETUP / SKENARIO LELANG (SETUP BREAKDOWN):")
        lines.append(
            f"  {'Setup Pattern':<44} | {'Trades':>6} | {'Done':>5} | {'Win':>4} | {'Loss':>4} | {'BE':>3} | {'WinRate':>7} | {'Avg R':>7}"
        )
        lines.append("  " + "-" * 95)
        for d in by_sc:
            lines.append(
                f"  {d['scenario']:<44} | {d['total_scenarios']:>6} | {d['completed_trades']:>5} | {d['wins']:>4} | {d['losses']:>4} | {d['breakevens']:>3} | {d['win_rate_pct']:>6.1f}% | {d['avg_r_multiple']:>+6.2f}R"
            )
        lines.append("-" * 105)

    # 3. Recent Trades Journal
    trades = res.get("trades", [])
    if trades:
        lines.append(f"📜 JURNAL TRANSAKSI TERAKHIR (RECENT TRADES JOURNAL - Waktu: {tz_lbl}):")
        lines.append(
            f"  {'#ID':<5} | {'Waktu Selesai':<18} | {'Sym':<6} | {'Dir':<5} | {'Setup Name':<28} | {'Entry':>9} | {'Exit':>9} | {'PnL Pts':>8} | {'R-Mult':>6} | {'Status':<14}"
        )
        lines.append("  " + "-" * 120)
        for t in trades[:limit_trades]:
            t_id = f"#{t.get('id', '-')}"
            ts_res = t.get("resolved_at_utc")
            ts_str = format_session_id(ts_res, display_tz) if ts_res else "RUNNING"
            sym = t.get("symbol", "-")
            d = t.get("direction", "-")
            title = t.get("title", t.get("scenario_id", "-"))[:28]
            ent = f"{t['entry_price']:.2f}" if t.get("entry_price") is not None else "-"
            ex = f"{t['exit_price']:.2f}" if t.get("exit_price") is not None else "-"
            pnl = f"{t['pnl_points']:+.2f}" if t.get("pnl_points") is not None else "-"
            r = f"{t['r_multiple']:+.2f}R" if t.get("r_multiple") is not None else "-"
            st = t.get("state", "-").replace("HIT_TARGET_", "").replace("CANCELLED_", "")
            lines.append(
                f"  {t_id:<5} | {ts_str:<18} | {sym:<6} | {d:<5} | {title:<28} | {ent:>9} | {ex:>9} | {pnl:>8} | {r:>6} | {st:<14}"
            )
        lines.append("=" * 105)

    return "\n".join(lines)


def format_trade_decision_log(trade: dict[str, Any], display_tz: str | None = None) -> str:
    """Format comprehensive chronological decision log for a single trade scenario."""
    _, tz_lbl = resolve_timezone(display_tz)
    lines = []
    lines.append("=" * 95)
    lines.append(
        f"                    DETAIL AUDIT TRANSAKSI #{trade.get('id')}: {trade.get('uid')}"
    )
    lines.append(
        f"  Simbol    : {trade.get('symbol')} ({trade.get('horizon')})           "
        f"Arah       : {trade.get('direction')}"
    )
    lines.append(f"  Setup     : {trade.get('title')}")
    lines.append(
        f"  Status    : {trade.get('state')}                     "
        f"Risk/Reward: 1 : {trade.get('risk_reward_ratio')}"
    )
    lines.append(
        f"  Trigger   : {trade.get('trigger_price')}                  "
        f"Take Profit: {trade.get('target_profit')}  |  Stop Loss: {trade.get('invalidation_level')}"
    )
    ent = f"{trade['entry_price']:.2f}" if trade.get("entry_price") is not None else "-"
    ex = f"{trade['exit_price']:.2f}" if trade.get("exit_price") is not None else "-"
    pnl = f"{trade['pnl_points']:+.2f}" if trade.get("pnl_points") is not None else "-"
    r_val = f"{trade['r_multiple']:+.2f}R" if trade.get("r_multiple") is not None else "-"
    lines.append(f"  Eksekusi  : Entry {ent} -> Exit {ex} | PnL: {pnl} pts ({r_val})")
    lines.append(
        f"  Ekskursi  : MFE (Max Run-up) +{trade.get('mfe_points', 0)} pts  |  MAE (Max Drawdown) -{trade.get('mae_points', 0)} pts"
    )
    lines.append("-" * 95)
    lines.append(f"📜 KRONOLOGI DECISION LOG RIIL (Waktu: {tz_lbl}):")
    logs = trade.get("decision_log", [])
    if logs:
        for item in logs:
            ts_str = format_session_id(item.get("ts_utc", ""), display_tz)
            lines.append(f"  [{ts_str}] {item.get('event', ''):<20} -> {item.get('details', '')}")
    else:
        lines.append("  (Belum ada decision log tercatat)")
    lines.append("=" * 95)
    return "\n".join(lines)


def evaluate_counterfactual_outcomes(
    conn: sqlite3.Connection,
    *,
    as_of: datetime | str | None = None,
    forward_hours: int = 2,
) -> dict[str, int]:
    """Evaluate subsequent 2h-4h price behavior after exit to audit whether stop-loss/invalidation was justified."""
    if as_of is None:
        target_dt = datetime.now(UTC)
    elif isinstance(as_of, str):
        target_dt = datetime.fromisoformat(as_of).astimezone(UTC)
    else:
        target_dt = as_of.astimezone(UTC)

    target_ts = target_dt.isoformat(timespec="seconds")

    # Find resolved trades
    rows = conn.execute(
        """
        SELECT scenario_uid, symbol, direction, target_profit, invalidation_level,
               entry_price, exit_price, state, resolved_at_utc, payload_json
        FROM playbook_scenarios
        WHERE state IN ('HIT_TARGET_WIN', 'HIT_STOP_LOSS')
          AND resolved_at_utc IS NOT NULL
        """
    ).fetchall()

    stats = {
        "audited": 0,
        "good_stop_loss": 0,
        "whipsaw_stop": 0,
        "clean_win": 0,
        "runner_continuation": 0,
    }

    for r in rows:
        uid, sym, direction, target_p, inval_p, entry_p, exit_p, state, resolved_ts, payload_str = r
        try:
            payload = json.loads(payload_str)
        except Exception:
            payload = {}

        # Skip if already audited
        if "counterfactual_audit" in payload:
            continue

        # Fetch bars in forward window after resolution
        resolved_dt = datetime.fromisoformat(resolved_ts).astimezone(UTC)
        window_end_dt = resolved_dt + timedelta(hours=forward_hours)
        # Only audit if window has elapsed
        if target_dt < window_end_dt:
            continue

        cf_bars = conn.execute(
            """
            SELECT bar_ts_utc, open, high, low, close
            FROM intraday_bars
            WHERE symbol = ?
              AND bar_ts_utc >= ?
              AND bar_ts_utc <= ?
            ORDER BY bar_ts_utc ASC
            """,
            (sym, resolved_ts, window_end_dt.isoformat(timespec="seconds")),
        ).fetchall()

        if len(cf_bars) < 6:
            continue

        cf_high = max(b[2] for b in cf_bars)
        cf_low = min(b[3] for b in cf_bars)
        cf_close = cf_bars[-1][4]
        risk_dist = abs(entry_p - inval_p) if (entry_p and inval_p) else 10.0

        verdict = "NEUTRAL_CONSOLIDATION"
        reason = "Price hovered near exit level during post-trade window."

        if state == "HIT_STOP_LOSS":
            if direction == "LONG":
                # Did price drop further after stop loss?
                if cf_low < exit_p - (0.25 * risk_dist):
                    verdict = "GOOD_STOP_LOSS (Capital Saved)"
                    reason = f"Price continued to decline to {round(cf_low, 2)} after stop-loss. Cut-loss prevented deeper drawdown."
                    stats["good_stop_loss"] += 1
                # Did price reverse back and hit the original target?
                elif cf_high >= target_p:
                    verdict = "WHIPSAW_STOP (Bad Stop Placement)"
                    reason = f"Price reversed after stop-out and reached target profit ({target_p}). Stop loss was placed too tightly on a wick."
                    stats["whipsaw_stop"] += 1
            elif direction == "SHORT":
                if cf_high > exit_p + (0.25 * risk_dist):
                    verdict = "GOOD_STOP_LOSS (Capital Saved)"
                    reason = f"Price continued to rally to {round(cf_high, 2)} after stop-loss. Cut-loss prevented deeper drawdown."
                    stats["good_stop_loss"] += 1
                elif cf_low <= target_p:
                    verdict = "WHIPSAW_STOP (Bad Stop Placement)"
                    reason = f"Price reversed after stop-out and reached target profit ({target_p}). Stop loss was placed too tightly on a wick."
                    stats["whipsaw_stop"] += 1

        elif state == "HIT_TARGET_WIN":
            if direction == "LONG":
                if cf_high > target_p + (0.50 * risk_dist):
                    verdict = "RUNNER_CONTINUATION (Extended Win)"
                    reason = f"Price continued advancing to {round(cf_high, 2)} after target hit. Setup had additional continuation potential."
                    stats["runner_continuation"] += 1
                else:
                    verdict = "CLEAN_WIN (Optimal Exit)"
                    reason = (
                        "Target profit was hit at the auction extreme before price consolidated."
                    )
                    stats["clean_win"] += 1
            elif direction == "SHORT":
                if cf_low < target_p - (0.50 * risk_dist):
                    verdict = "RUNNER_CONTINUATION (Extended Win)"
                    reason = f"Price continued dropping to {round(cf_low, 2)} after target hit. Setup had additional continuation potential."
                    stats["runner_continuation"] += 1
                else:
                    verdict = "CLEAN_WIN (Optimal Exit)"
                    reason = (
                        "Target profit was hit at the auction extreme before price consolidated."
                    )
                    stats["clean_win"] += 1

        payload["counterfactual_audit"] = {
            "verdict": verdict,
            "reason": reason,
            "post_exit_high": round(cf_high, 4),
            "post_exit_low": round(cf_low, 4),
            "post_exit_close": round(cf_close, 4),
            "forward_bars_evaluated": len(cf_bars),
            "audited_at_utc": target_ts,
        }

        conn.execute(
            "UPDATE playbook_scenarios SET payload_json = ? WHERE scenario_uid = ?",
            (json.dumps(payload), uid),
        )
        stats["audited"] += 1

    conn.commit()
    return stats


def scan_market_opportunities(
    conn: sqlite3.Connection,
    *,
    symbols: list[str] | tuple[str, ...] | None = None,
    as_of: datetime | str | None = None,
    min_rr: float = 1.5,
) -> list[dict[str, Any]]:
    """Continuous Opportunity Scanner: Scans the tracked book and returns active/imminent trade opportunities."""
    from .playbook import generate_trading_playbook

    target_symbols = symbols or ("NQ1", "ES1", "YM1", "GC1", "CL1", "BTCUSD", "ETHUSD", "EURUSD")
    opportunities = []

    for sym in target_symbols:
        pb = generate_trading_playbook(conn, sym, as_of=as_of)
        if not pb:
            continue

        scenarios = pb.get("scenarios", [])
        last_price = pb.get("last_price", 0.0)
        confluence_status = pb.get("multi_domain", {}).get("confluence_status", {})
        alignment_state = confluence_status.get("alignment_state", "NEUTRAL_BALANCED")
        amt_ctx = pb.get("amt_context", {})

        # Filter out halt states
        if alignment_state == "EVENT_HALT_REQUIRED":
            continue

        for sc in scenarios:
            # Skip pure chop rotations unless explicitly high R:R
            if sc.get("direction") == "NEUTRAL_RANGE":
                continue

            rr = float(sc.get("risk_reward_ratio", 1.0))
            if rr < min_rr:
                continue

            opportunities.append(
                {
                    "symbol": sym,
                    "horizon": sc.get("horizon", "INTRADAY"),
                    "direction": sc.get("direction"),
                    "scenario_title": sc.get("title"),
                    "last_price": last_price,
                    "trigger_price": sc.get("trigger_price"),
                    "target_profit": sc.get("target_profit"),
                    "invalidation_level": sc.get("invalidation_level"),
                    "risk_reward_ratio": rr,
                    "open_type": amt_ctx.get("open_type"),
                    "alignment_state": alignment_state,
                    "catalyst_stance": pb.get("catalysts", {}).get("intraday_fast_stance"),
                }
            )

    # Sort opportunities by Risk-Reward ratio descending
    return sorted(opportunities, key=lambda x: x["risk_reward_ratio"], reverse=True)
