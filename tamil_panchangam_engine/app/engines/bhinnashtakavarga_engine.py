"""
Bhinnashtakavarga Engine — Parashari Jyotisha (BPHS)

Computes per-planet Bhinnashtakavarga (BAV) tables.
Each planet's BAV sums contributions from 8 contributors
(7 planets + Lagna), using classical Parashari tables.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Classical Parashari BAV tables
# For each ASSESSED planet, for each CONTRIBUTOR, these are the
# houses (counted from the contributor's position) that receive
# a benefic bindu in that planet's BAV.
# ──────────────────────────────────────────────────────────────

BAV_TABLES: Dict[str, Dict[str, list]] = {
    "sun": {
        "sun":     [1, 2, 4, 7, 8, 9, 10, 11],
        "moon":    [3, 6, 10, 11],
        "mars":    [1, 2, 4, 7, 8, 10, 11],
        "mercury": [5, 6, 9, 11, 12],
        "jupiter": [5, 6, 9, 11],
        "venus":   [5, 8, 9, 10, 11],
        "saturn":  [1, 2, 4, 7, 8, 10, 11],
        "lagna":   [1, 2, 4, 7, 8, 9, 10, 11],
    },
    "moon": {
        "sun":     [3, 6, 7, 8, 10, 11],
        "moon":    [1, 3, 6, 7, 10, 11],
        "mars":    [2, 3, 5, 6, 9, 10, 11],
        "mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "jupiter": [1, 4, 7, 8, 10, 11],
        "venus":   [3, 4, 5, 7, 9, 10, 11],
        "saturn":  [3, 5, 6, 11],
        "lagna":   [3, 6, 10, 11],
    },
    "mars": {
        "sun":     [3, 5, 6, 10, 11],
        "moon":    [3, 6, 11],
        "mars":    [1, 2, 4, 7, 8, 10, 11],
        "mercury": [3, 5, 6, 11],
        "jupiter": [6, 10, 11, 12],
        "venus":   [6, 8, 11, 12],
        "saturn":  [1, 4, 7, 8, 9, 10, 11],
        "lagna":   [1, 2, 4, 7, 8, 10, 11],
    },
    "mercury": {
        "sun":     [5, 6, 9, 11, 12],
        "moon":    [2, 4, 6, 8, 10, 11],
        "mars":    [1, 2, 4, 7, 8, 9, 10, 11],
        "mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "jupiter": [6, 8, 11, 12],
        "venus":   [1, 2, 3, 4, 5, 8, 9, 11],
        "saturn":  [1, 2, 4, 7, 8, 9, 10, 11],
        "lagna":   [1, 2, 4, 7, 8, 10, 11],
    },
    "jupiter": {
        "sun":     [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "moon":    [2, 5, 7, 9, 11],
        "mars":    [1, 2, 4, 7, 8, 10, 11],
        "mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
        "venus":   [2, 5, 6, 9, 10, 11],
        "saturn":  [3, 5, 6, 11, 12],
        "lagna":   [1, 2, 4, 5, 6, 7, 9, 10, 11],
    },
    "venus": {
        "sun":     [8, 11, 12],
        "moon":    [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "mars":    [3, 4, 6, 9, 11, 12],
        "mercury": [3, 5, 6, 9, 11],
        "jupiter": [5, 8, 9, 10, 11],
        "venus":   [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "saturn":  [3, 4, 5, 8, 9, 10, 11],
        "lagna":   [1, 2, 3, 4, 5, 8, 9, 11],
    },
    "saturn": {
        "sun":     [1, 2, 4, 7, 8, 10, 11],
        "moon":    [3, 6, 11],
        "mars":    [3, 5, 6, 10, 11, 12],
        "mercury": [6, 8, 9, 10, 11, 12],
        "jupiter": [5, 6, 11, 12],
        "venus":   [6, 11, 12],
        "saturn":  [3, 5, 6, 11],
        "lagna":   [1, 3, 4, 6, 10, 11],
    },
}

PLANET_KEYS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]

# Map API planet names → BAV key names
PLANET_NAME_MAP = {
    "Sun": "sun", "Moon": "moon", "Mars": "mars",
    "Mercury": "mercury", "Jupiter": "jupiter",
    "Venus": "venus", "Saturn": "saturn",
    "Rahu": "rahu", "Ketu": "ketu",
}

SIGN_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_INDEX = {s: i for i, s in enumerate(SIGN_ORDER)}


def _longitude_to_sign_index(lon: float) -> int:
    """Convert ecliptic longitude (0-360) to 0-based sign index."""
    return int(lon % 360 / 30)


def _compute_planet_bav(
    assessed_planet: str,
    contributor_sign_indices: Dict[str, int],
) -> list:
    """
    Compute BAV bindus-per-sign (list of 12 ints) for one assessed planet.

    For each contributor, find which signs receive a bindu:
      contributor_sign + (benefic_house - 1)  mod 12
    """
    bindus = [0] * 12
    table = BAV_TABLES.get(assessed_planet, {})

    for contributor, benefic_houses in table.items():
        contrib_sign = contributor_sign_indices.get(contributor)
        if contrib_sign is None:
            continue  # missing contributor — skip
        for house in benefic_houses:
            target_sign = (contrib_sign + house - 1) % 12
            bindus[target_sign] += 1

    return bindus


def _combined_strength(bav_score: int) -> str:
    if bav_score >= 5:
        return "strong"
    elif bav_score >= 3:
        return "moderate"
    return "weak"


def compute_bhinnashtakavarga(ephemeris: dict) -> dict:
    """
    Compute per-planet Bhinnashtakavarga (BAV) tables using Parashari method.

    Returns:
    {
      "sun": {"bindus_per_sign": [int × 12], "total": int},
      "moon": {...}, "mars": {...}, "mercury": {...},
      "jupiter": {...}, "venus": {...}, "saturn": {...},
      "sarvashtakavarga": [int × 12],  # sum across all 7 planets
      "transit_scores": {
          "saturn": {"current_sign_index": int, "bav_score": int,
                     "sav_score": int, "combined_strength": str},
          "jupiter": {...},
          "rahu": {"current_sign_index": int, "sav_score": int, "strength": str}
      }
    }
    """
    try:
        planets_raw = ephemeris.get("planets", {})
        lagna_data = ephemeris.get("lagna", {})
        lagna_lon = lagna_data.get("longitude_deg", 0.0)

        # Build contributor sign index map
        contributor_sign_indices: Dict[str, int] = {
            "lagna": _longitude_to_sign_index(lagna_lon)
        }

        planet_sign_indices: Dict[str, int] = {}

        for api_name, bav_key in PLANET_NAME_MAP.items():
            pdata = planets_raw.get(api_name, {})
            if not pdata:
                continue
            lon = pdata.get("longitude_deg")
            if lon is None:
                rasi = pdata.get("rasi", "")
                if rasi in SIGN_INDEX:
                    idx = SIGN_INDEX[rasi]
                else:
                    continue
            else:
                idx = _longitude_to_sign_index(float(lon))

            planet_sign_indices[bav_key] = idx
            contributor_sign_indices[bav_key] = idx

        # Compute BAV for each of the 7 main planets
        result = {}
        sav = [0] * 12

        for planet_key in PLANET_KEYS:
            bindus = _compute_planet_bav(planet_key, contributor_sign_indices)
            total = sum(bindus)
            result[planet_key] = {
                "bindus_per_sign": bindus,
                "total": total,
            }
            for i in range(12):
                sav[i] += bindus[i]

        result["sarvashtakavarga"] = sav

        # Transit scores for Saturn, Jupiter, Rahu
        transit_scores = {}

        # Saturn
        saturn_idx = planet_sign_indices.get("saturn")
        if saturn_idx is not None:
            sat_bav = result["saturn"]["bindus_per_sign"][saturn_idx]
            sat_sav = sav[saturn_idx]
            transit_scores["saturn"] = {
                "current_sign_index": saturn_idx,
                "bav_score": sat_bav,
                "sav_score": sat_sav,
                "combined_strength": _combined_strength(sat_bav),
            }

        # Jupiter
        jupiter_idx = planet_sign_indices.get("jupiter")
        if jupiter_idx is not None:
            jup_bav = result["jupiter"]["bindus_per_sign"][jupiter_idx]
            jup_sav = sav[jupiter_idx]
            transit_scores["jupiter"] = {
                "current_sign_index": jupiter_idx,
                "bav_score": jup_bav,
                "sav_score": jup_sav,
                "combined_strength": _combined_strength(jup_bav),
            }

        # Rahu (no BAV of its own — only SAV)
        rahu_idx = planet_sign_indices.get("rahu")
        if rahu_idx is not None:
            rahu_sav = sav[rahu_idx]
            transit_scores["rahu"] = {
                "current_sign_index": rahu_idx,
                "sav_score": rahu_sav,
                "strength": _combined_strength(rahu_sav // 7 if rahu_sav else 0),
            }

        result["transit_scores"] = transit_scores
        return result

    except Exception as e:
        logger.warning(f"Bhinnashtakavarga computation failed: {e}", exc_info=True)
        return {"error": str(e)}
