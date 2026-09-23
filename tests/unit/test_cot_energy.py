from arkwatch.signals.cot_signals import COT_Z_CONTRACTS


def test_wti_is_in_cot_zscore_universe():
    assert "067651" in COT_Z_CONTRACTS
