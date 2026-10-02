"""
Bhinnashtakavarga Engine — Parashari Jyotisha (BPHS)

Computes per-planet Bhinnashtakavarga (BAV) tables.
Each planet's BAV sums contributions from 8 contributors
(7 planets + Lagna), using classical Parashari tables.
"""

import logging
from typing import Dict

from app.utils.rasi_utils import to_english_rasi

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Classical Parashari BAV tables
# For each ASSESSED planet, for each CONTRIBUTOR, these are the
# houses (counted from the contributor's position) that receive
# a benefic bindu in that planet's BAV. Totals: Sun 48, Moon 49,
# Mars 39, Mercury 54, Jupiter 56, Venus 52, Saturn 39 (SAV 337).
#
# Corrected 2026-10-02 (10 rows were wrong across 6 planets; only
# Saturn's table was right). Source: B.V. Raman's tables (as given by
# vedastro.org "Mastering Ashtakavarga Part 2"), cross-checked against
# BPHS Ch. 66 vv. 43-60 (Santhanam tr.) and two published worked
# examples -- see tests/engines/test_bav_tables_classical.py. Where that
# BPHS translation differs (7 cells, e.g. Venus from Mars 3,4,... vs
# 3,5,...), Raman's reading is the one both worked examples reproduce.
# ──────────────────────────────────────────────────────────────

BAV_TABLES: Dict[str, Dict[str, list]] = {
    "sun": {
        "sun":     [1, 2, 4, 7, 8, 9, 10, 11],
        "moon":    [3, 6, 10, 11],
        "mars":    [1, 2, 4, 7, 8, 9, 10, 11],
        "mercury": [3, 5, 6, 9, 10, 11, 12],
        "jupiter": [5, 6, 9, 11],
        "venus":   [6, 7, 12],
        "saturn":  [1, 2, 4, 7, 8, 9, 10, 11],
        "lagna":   [3, 4, 6, 10, 11, 12],
    },
    "moon": {
        "sun":     [3, 6, 7, 8, 10, 11],
        "moon":    [1, 3, 6, 7, 10, 11],
        "mars":    [2, 3, 5, 6, 9, 10, 11],
        "mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "jupiter": [1, 4, 7, 8, 10, 11, 12],
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
        "lagna":   [1, 3, 6, 10, 11],
    },
    "mercury": {
        "sun":     [5, 6, 9, 11, 12],
        "moon":    [2, 4, 6, 8, 10, 11],
        "mars":    [1, 2, 4, 7, 8, 9, 10, 11],
        "mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "jupiter": [6, 8, 11, 12],
        "venus":   [1, 2, 3, 4, 5, 8, 9, 11],
        "saturn":  [1, 2, 4, 7, 8, 9, 10, 11],
        "lagna":   [1, 2, 4, 6, 8, 10, 11],
    },
    "jupiter": {
        "sun":     [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "moon":    [2, 5, 7, 9, 11],
        "mars":    [1, 2, 4, 7, 8, 10, 11],
        "mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
        "venus":   [2, 5, 6, 9, 10, 11],
        "saturn":  [3, 5, 6, 12],
        "lagna":   [1, 2, 4, 5, 6, 7, 9, 10, 11],
    },
    "venus": {
        "sun":     [8, 11, 12],
        "moon":    [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "mars":    [3, 5, 6, 9, 11, 12],
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


def compute_bav_transit_scores(bav: dict, transit_longitudes: Dict[str, float]) -> dict:
    """
    BAV/SAV support for the signs Saturn, Jupiter and Rahu are TRANSITING
    (transit_longitudes: sidereal longitude per lowercase planet name, e.g.
    from the envelope's gochara for the report's reference date), read from
    a chart's natal BAV tables.

    Returns {"saturn": {"transit_sign_index", "bav_score", "sav_score",
    "combined_strength"}, "jupiter": {...}, "rahu": {"transit_sign_index",
    "sav_score", "strength"}} for whichever planets have a longitude.
    Rahu has no BAV of its own -- SAV only.
    """
    if not bav or bav.get("error"):
        return {}
    sav = bav.get("sarvashtakavarga") or []
    out: Dict[str, dict] = {}
    for planet in ("saturn", "jupiter"):
        lon = transit_longitudes.get(planet)
        bindus = (bav.get(planet) or {}).get("bindus_per_sign") or []
        if lon is None or len(bindus) != 12 or len(sav) != 12:
            continue
        idx = _longitude_to_sign_index(float(lon))
        out[planet] = {
            "transit_sign_index": idx,
            "bav_score": bindus[idx],
            "sav_score": sav[idx],
            "combined_strength": _combined_strength(bindus[idx]),
        }
    lon = transit_longitudes.get("rahu")
    if lon is not None and len(sav) == 12:
        idx = _longitude_to_sign_index(float(lon))
        out["rahu"] = {
            "transit_sign_index": idx,
            "sav_score": sav[idx],
            "strength": _combined_strength(sav[idx] // 7 if sav[idx] else 0),
        }
    return out


def compute_bhinnashtakavarga(ephemeris: dict) -> dict:
    """
    Compute per-planet Bhinnashtakavarga (BAV) tables using Parashari method.

    Returns:
    {
      "sun": {"bindus_per_sign": [int × 12], "total": int},
      "moon": {...}, "mars": {...}, "mercury": {...},
      "jupiter": {...}, "venus": {...}, "saturn": {...},
      "sarvashtakavarga": [int × 12],  # sum across all 7 planets
    }

    Natal-only, stored at chart creation. Until 2026-10-02 this also
    returned "transit_scores", which actually scored each planet's NATAL
    sign; transit scores depend on the date, so they're computed where
    used: compute_bav_transit_scores().
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
                # Payload rasi is Tamil ("Kadakam"); SIGN_INDEX is English.
                # Without the conversion this fallback never matched and the
                # planet was silently dropped as a contributor.
                rasi = to_english_rasi(pdata.get("rasi", ""))
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

        return result

    except Exception as e:
        logger.warning(f"Bhinnashtakavarga computation failed: {e}", exc_info=True)
        return {"error": str(e)}
