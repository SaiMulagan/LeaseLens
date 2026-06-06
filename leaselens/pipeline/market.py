"""A tiny rent gazetteer used by the reasoning stage.

Bands are monthly-rent ranges by city and bedroom count. In production this
would be a live comps feed; here it is a small fixed table so the market-band
check is deterministic and explainable on camera.
"""

from __future__ import annotations

# (low, high) plausible monthly rent by city -> bedrooms.
RENT_BANDS: dict[str, dict[int, tuple[int, int]]] = {
    "san francisco": {0: (1900, 3200), 1: (2600, 4200), 2: (3400, 6000), 3: (4500, 8500)},
    "austin": {0: (1100, 1900), 1: (1400, 2400), 2: (1800, 3200), 3: (2300, 4200)},
    "dallas": {0: (1000, 1700), 1: (1200, 2100), 2: (1600, 2900), 3: (2100, 3800)},
    "richardson": {0: (1000, 1700), 1: (1200, 2100), 2: (1600, 2900), 3: (2100, 3800)},
}

DEFAULT_BAND: dict[int, tuple[int, int]] = {0: (900, 2500), 1: (1100, 3000), 2: (1400, 4000), 3: (1900, 5500)}


def band_for(city: str | None, bedrooms: int | None) -> tuple[int, int] | None:
    if bedrooms is None:
        return None
    table = RENT_BANDS.get((city or "").strip().lower(), DEFAULT_BAND)
    return table.get(bedrooms, DEFAULT_BAND.get(bedrooms))
