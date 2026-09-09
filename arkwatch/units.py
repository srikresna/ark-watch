"""units.py — centralized unit-conversion registry.

Constants: 1 troy tonne = 32,150.7466 oz (integer approximations such as
32,151 drift ~0.002% on large holdings); 1 koz = 31.1034768 kg; one 万盎司
(wan-ounce, the unit used in Chinese publications) = 10,000 oz.
Cross-check: 7607万oz * 10,000 / 32,150.7466 = 2,366.4 t, matching the
published SAFE figure.
"""

from __future__ import annotations

OZ_PER_TROY_TONNE = 32_150.7466
KG_PER_KOZ = 31.1034768
OZ_PER_WAN = 10_000  # 万盎司 (wan-ounce) = 10,000 oz


def wan_oz_to_tonnes(wan_oz: float) -> float:
    return wan_oz * OZ_PER_WAN / OZ_PER_TROY_TONNE


def koz_to_tonnes(koz: float) -> float:
    return koz * KG_PER_KOZ / 1000.0


def oz_to_tonnes(oz: float) -> float:
    return oz / OZ_PER_TROY_TONNE
