"""
Refined Ashtakavarga Engine — Trikona Shodhana + Ekadhipatya Shodhana.

Applies classical purification to Bhinnashtakavarga scores for more accurate predictions.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

RASI_NAMES = [
    "Mesham", "Rishabam", "Midhunam", "Kadagam", "Simham", "Kanni",
    "Thulam", "Vrischikam", "Dhanusu", "Makaram", "Kumbham", "Meenam",
]

# Trikona groups (0-indexed sign indices)
_TRIKONA_GROUPS: List[List[int]] = [
    [0, 4, 8],   # Mesham, Simham, Dhanusu
    [1, 5, 9],   # Rishabam, Kanni, Makaram
    [2, 6, 10],  # Midhunam, Thulam, Kumbham
    [3, 7, 11],  # Kadagam, Vrischikam, Meenam
]

# Ekadhipatya pairs — both signs owned by same planet (0-indexed)
_EKADHIPATYA_PAIRS: List[tuple] = [
    (2, 5),   # Mercury: Midhunam, Kanni
    (1, 6),   # Venus: Rishabam, Thulam
    (9, 10),  # Saturn: Makaram, Kumbham
]

# Bhinnashtakavarga planet keys as they appear in payload (lowercase)
_PLANETS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]


def _trikona_shodhana(bindus: List[float]) -> List[float]:
    """Subtract the minimum bindu from each sign in every trikona group."""
    result = list(bindus)
    for group in _TRIKONA_GROUPS:
        min_val = min(result[i] for i in group)
        for i in group:
            result[i] = max(0.0, result[i] - min_val)
    return result


def _ekadhipatya_shodhana(bindus: List[float]) -> List[float]:
    """
    For each dual-owned sign pair where both have bindus > 0:
    reduce the weaker sign to (stronger - weaker); stronger unchanged.
    """
    result = list(bindus)
    for i, j in _EKADHIPATYA_PAIRS:
        a, b = result[i], result[j]
        if a > 0 and b > 0:
            if a >= b:
                result[j] = a - b
            else:
                result[i] = b - a
    return result


def compute_refined_av(bhinnashtakavarga: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply Trikona + Ekadhipatya Shodhana to Bhinnashtakavarga scores.

    Args:
        bhinnashtakavarga: payload['bhinnashtakavarga'] dict.
            Expected: { "sun": {"bindus_per_sign": [12 ints]}, ... }

    Returns:
        {
            "refined_scores": {"Sun": {"Mesham": 4.0, ...}, ...},
            "sarvashtakavarga_refined": {"Mesham": 28.0, ...}
        }
    """
    if not bhinnashtakavarga:
        return {"refined_scores": {}, "sarvashtakavarga_refined": {}}

    refined_scores: Dict[str, Dict[str, float]] = {}
    sarva = [0.0] * 12

    for planet_key in _PLANETS:
        planet_data = bhinnashtakavarga.get(planet_key, {})
        raw = planet_data.get("bindus_per_sign", [])
        if not raw or len(raw) != 12:
            continue

        bindus = [float(b) for b in raw]
        bindus = _trikona_shodhana(bindus)
        bindus = _ekadhipatya_shodhana(bindus)

        planet_name = planet_key.capitalize()
        refined_scores[planet_name] = {RASI_NAMES[i]: round(bindus[i], 2) for i in range(12)}

        for i in range(12):
            sarva[i] += bindus[i]

    sarvashtakavarga = {RASI_NAMES[i]: round(sarva[i], 2) for i in range(12)}
    return {
        "refined_scores": refined_scores,
        "sarvashtakavarga_refined": sarvashtakavarga,
    }
