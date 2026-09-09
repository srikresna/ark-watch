"""Centralized unit conversions verified against published figures.

Each test pins a conversion to a real number from an official publication,
so magnitude slips (e.g. a 1000x kg/koz error) cannot pass unnoticed."""

from __future__ import annotations

import pytest

from arkwatch.units import koz_to_tonnes, oz_to_tonnes, wan_oz_to_tonnes


def test_pboc_safe_publication():
    """SAFE reported ~2,366 tonnes: 7607 wan-oz → 2366.0; 7608.5 wan-oz → 2366.5."""
    assert wan_oz_to_tonnes(7607) == pytest.approx(2366.04, abs=0.05)
    assert wan_oz_to_tonnes(7608.5) == pytest.approx(2366.51, abs=0.05)


def test_lbma_vault_publication():
    """LBMA July 2026: 907,058.96 koz of silver → 28,212.7 tonnes."""
    assert koz_to_tonnes(907058.96) == pytest.approx(28212.7, abs=0.5)


def test_koz_magitude():
    """1 koz = 31.1 kg = 0.0311 tonnes — not 0.0311 kg (a 1000x magnitude error)."""
    assert 28.0 < koz_to_tonnes(1000) < 32.5  # 1000 koz ≈ 31.1 t


def test_gld_shares():
    """GLD: 0.091711 oz/share x 353M shares ≈ 1006 tonnes."""
    assert oz_to_tonnes(0.091711 * 353_000_000) == pytest.approx(1006.4, abs=1.0)
