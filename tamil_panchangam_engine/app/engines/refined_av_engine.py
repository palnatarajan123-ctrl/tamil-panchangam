"""
Refined Ashtakavarga Engine — Trikona Shodhana + Ekadhipatya Shodhana.

Applies classical purification to Bhinnashtakavarga scores for more accurate predictions.
"""

import logging
from typing import Any, Dict, List, Optional, Set

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


def _ekadhipatya_shodhana(bindus: List[float], occupied_signs: Set[int]) -> List[float]:
    """
    Classical Ekadhipatya (dual-lordship) Shodhana, keyed on whether a
    NATAL PLANET actually tenants each sign of the pair -- not on bindu
    count, which the pre-2026-09-14 version used as an occupancy proxy
    (bindu > 0). That proxy is wrong: e.g. an equal 5/5 bindu pair with
    neither sign actually occupied should both go to zero under "both
    unoccupied", but the old code treated bindu>0 as "occupied" and left
    them at (5, 0) instead -- confirmed by concrete counter-example
    during the 2026-09-14 investigation (2 of 3 real sub-cases wrong).

    Three sub-cases (both signs of a same-lord pair):
    1. Both occupied (by a natal planet) -> no reduction.
    2. Both unoccupied -> reduce the higher bindu count down to the
       lower (a no-op if already equal).
    3. Exactly one occupied -> the unoccupied sign's bindus go to 0;
       the occupied sign is untouched, regardless of which one has
       more bindus.
    """
    result = list(bindus)
    for i, j in _EKADHIPATYA_PAIRS:
        i_occupied = i in occupied_signs
        j_occupied = j in occupied_signs
        if i_occupied and j_occupied:
            continue
        elif not i_occupied and not j_occupied:
            a, b = result[i], result[j]
            if a > b:
                result[i] = b
            elif b > a:
                result[j] = a
        else:
            if not i_occupied:
                result[i] = 0.0
            else:
                result[j] = 0.0
    return result


def compute_refined_av(
    bhinnashtakavarga: Dict[str, Any],
    natal_planets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Apply Trikona + Ekadhipatya Shodhana to Bhinnashtakavarga scores.

    Args:
        bhinnashtakavarga: payload['bhinnashtakavarga'] dict.
            Expected: { "sun": {"bindus_per_sign": [12 ints]}, ... }
        natal_planets: payload['ephemeris']['planets'], keyed by
            capitalized planet name with a 'longitude_deg' field --
            used to determine real sign OCCUPANCY for Ekadhipatya
            Shodhana (see _ekadhipatya_shodhana()'s docstring). Deriving
            occupancy from longitude_deg // 30 rather than matching the
            natal 'rasi' string against this file's own RASI_NAMES list
            sidesteps a separate, independently-found spelling mismatch
            between this file's RASI_NAMES ("Midhunam", "Kadagam",
            "Simham") and ephemeris.py's ("Mithunam", "Kadakam",
            "Simmam") for Gemini/Cancer/Leo -- the same silent
            Tamil-name-mismatch bug class already fixed elsewhere in
            this codebase (see CLAUDE.md's rasi-name-mismatch entries),
            not yet fixed in this file's own constant. If omitted,
            Ekadhipatya Shodhana is skipped entirely (Trikona Shodhana
            still applies) rather than guessing occupancy -- a wrong
            sub-case reduction is worse than none at this stage. Only
            the 7 classical Bhinnashtakavarga contributors (_PLANETS)
            are considered for occupancy; Rahu/Ketu are not part of the
            Ashtakavarga contributor set this file works with.

    Returns:
        {
            "refined_scores": {"Sun": {"Mesham": 4.0, ...}, ...},
            "sarvashtakavarga_refined": {"Mesham": 28.0, ...}
        }
    """
    if not bhinnashtakavarga:
        return {"refined_scores": {}, "sarvashtakavarga_refined": {}}

    occupied_signs: Optional[Set[int]] = None
    if natal_planets:
        occupied_signs = set()
        for planet_key in _PLANETS:
            pdata = natal_planets.get(planet_key.capitalize(), {})
            lon = pdata.get("longitude_deg") if isinstance(pdata, dict) else None
            if lon is not None:
                occupied_signs.add(int(lon // 30) % 12)
    else:
        logger.warning("compute_refined_av called without natal_planets -- skipping Ekadhipatya Shodhana")

    refined_scores: Dict[str, Dict[str, float]] = {}
    sarva = [0.0] * 12

    for planet_key in _PLANETS:
        planet_data = bhinnashtakavarga.get(planet_key, {})
        raw = planet_data.get("bindus_per_sign", [])
        if not raw or len(raw) != 12:
            continue

        bindus = [float(b) for b in raw]
        bindus = _trikona_shodhana(bindus)
        if occupied_signs is not None:
            bindus = _ekadhipatya_shodhana(bindus, occupied_signs)

        planet_name = planet_key.capitalize()
        refined_scores[planet_name] = {RASI_NAMES[i]: round(bindus[i], 2) for i in range(12)}

        for i in range(12):
            sarva[i] += bindus[i]

    sarvashtakavarga = {RASI_NAMES[i]: round(sarva[i], 2) for i in range(12)}
    return {
        "refined_scores": refined_scores,
        "sarvashtakavarga_refined": sarvashtakavarga,
    }
