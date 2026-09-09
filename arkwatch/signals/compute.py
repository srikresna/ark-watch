"""compute.py — compatibility shim re-exporting the signal modules.

  pillars.py     — pillars A-F, regime score, quadrant, dollar smile, identities
  cot_signals.py — 12 COT signals + z-scores + computed_signals persistence
  brief.py       — brief renderer + save/run
Legacy imports (`from .signals.compute import X`) keep working via re-exports.
"""

from __future__ import annotations

from .brief import generate_brief, run, save_brief
from .cot_signals import (
    _btc_smart_money,
    _cot_zscore,
    _cross_contract_aggregate,
    _fx_turning_point,
    _hedging_pressure,
    _price_oi_quadrant,
    _price_positioning_divergence,
    _regime_conditioned_cot,
    _silver_52wk_gate,
    _spread_share_filter,
    store_cot_signals,
)
from .pillars import (
    PILLAR_WEIGHTS,
    _identity_checks,
    _latest,
    _pct,
    _values,
    compute_dollar_smile,
    compute_pillars,
    compute_quadrant,
    compute_regime_score,
)

__all__ = [
    "generate_brief",
    "run",
    "save_brief",
    "store_cot_signals",
    "compute_pillars",
    "compute_regime_score",
    "compute_quadrant",
    "compute_dollar_smile",
    "_identity_checks",
    "_cot_zscore",
    "_btc_smart_money",
    "_price_oi_quadrant",
    "_hedging_pressure",
    "_cross_contract_aggregate",
    "_fx_turning_point",
    "_silver_52wk_gate",
    "_price_positioning_divergence",
    "_regime_conditioned_cot",
    "_spread_share_filter",
    "_values",
    "_latest",
    "_pct",
    "PILLAR_WEIGHTS",
]
