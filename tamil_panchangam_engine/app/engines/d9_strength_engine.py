# app/engines/d9_strength_engine.py

from typing import Dict


DIGNITY_WEIGHT = {
    "exalted": 1.25,
    "neutral": 1.0,
    "debilitated": 0.75,
}


def planet_strength(
    planet: str,
    d1: Dict,
    d9: Dict,
) -> float:
    """
    Compute planetary strength using Navāṁśa (D9).

    Rules:
    - Base strength = 1.0
    - Apply dignity multiplier
    - Optional same-sign reinforcement
    """

    strength = 1.0

    dignity = d9.get("dignity", {}).get(planet, "neutral")
    strength *= DIGNITY_WEIGHT.get(dignity, 1.0)

    # Optional reinforcement:
    # Same Rāsi in D1 and D9 (rare but powerful)
    try:
        d1_rasi = d1.get("planet_positions", {}).get(planet, {}).get("rasi")
        d9_rasi = d9.get("planet_signs", {}).get(planet)

        if d1_rasi and d9_rasi and d1_rasi == d9_rasi:
            strength *= 1.1
    except Exception:
        pass

    return round(strength, 2)
