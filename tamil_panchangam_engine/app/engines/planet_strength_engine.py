# app/engines/planet_strength_engine.py

"""
EPIC-2B
Planet strength computation engine.

Pure, deterministic, reusable.
NO interpretation.
NO scoring by life area.
NO UI assumptions.
"""

from typing import Dict


# -------------------------------------------------
# Canonical dignity weights (stable + auditable)
# -------------------------------------------------

DIGNITY_WEIGHTS = {
    "exalted": 1.0,
    "own": 0.85,
    "friendly": 0.7,
    "neutral": 0.5,
    "enemy": 0.3,
    "debilitated": 0.1,
}


# -------------------------------------------------
# Core strength computation
# -------------------------------------------------

def compute_planet_strength(
    *,
    planet: str,
    d1_dignity: str | None,
    d9_dignity: str | None,
) -> Dict:
    """
    Composite planet strength using D1 + D9 dignity.

    Returns:
    {
        "planet": "Jupiter",
        "d1_dignity": "own",
        "d9_dignity": "exalted",
        "strength": 0.92,
        "components": {
            "d1_weight": 0.85,
            "d9_weight": 1.0
        }
    }
    """

    d1_weight = DIGNITY_WEIGHTS.get(d1_dignity, 0.5)
    d9_weight = DIGNITY_WEIGHTS.get(d9_dignity, 0.5)

    # Navamsa has higher weight for dharma & outcomes
    strength = round((0.45 * d1_weight + 0.55 * d9_weight), 2)

    return {
        "planet": planet,
        "d1_dignity": d1_dignity,
        "d9_dignity": d9_dignity,
        "strength": strength,
        "components": {
            "d1_weight": d1_weight,
            "d9_weight": d9_weight,
        },
    }


def compute_all_planet_strengths(
    *,
    d1_dignities: Dict[str, str],
    d9_dignities: Dict[str, str],
) -> Dict[str, Dict]:
    """
    Compute strengths for all planets present in Dasha context.
    """

    out: Dict[str, Dict] = {}

    for planet in set(d1_dignities.keys()) | set(d9_dignities.keys()):
        out[planet] = compute_planet_strength(
            planet=planet,
            d1_dignity=d1_dignities.get(planet),
            d9_dignity=d9_dignities.get(planet),
        )

    return out
