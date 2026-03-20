"""
Ashtaka Varga Engine - Full Classical Parashari Calculation

Computes Sarvashtakavarga (sum of all 8 Bhinnashtakavargas) for each sign
using 7 planets + Lagna as contributors.

Each contributor gives +1 bindu to signs at classical benefic house distances
from its own position. Total bindus in Sarvashtakavarga = 57.
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

RASI_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

RASI_TO_INDEX = {rasi: i for i, rasi in enumerate(RASI_ORDER)}

# Classical benefic house distances (1-indexed, counted from contributor's own sign)
# These are the contributor's own Sarvashtakavarga bindu positions (Parashara-based)
SUN_AV_BENEFIC_HOUSES = [1, 2, 4, 7, 8, 9, 10, 11]       # 8 bindus
MOON_AV_BENEFIC_HOUSES = [3, 6, 7, 8, 10, 11]             # 6 bindus
MARS_AV_BENEFIC_HOUSES = [1, 2, 4, 7, 8, 10, 11]          # 7 bindus
MERCURY_AV_BENEFIC_HOUSES = [1, 2, 4, 5, 6, 9, 10, 11]    # 8 bindus
JUPITER_AV_BENEFIC_HOUSES = [1, 2, 3, 4, 7, 8, 10, 11]    # 8 bindus
VENUS_AV_BENEFIC_HOUSES = [1, 2, 3, 4, 5, 8, 9, 11]       # 8 bindus
SATURN_AV_BENEFIC_HOUSES = [3, 5, 6, 11]                   # 4 bindus
LAGNA_AV_BENEFIC_HOUSES = [1, 2, 4, 7, 8, 9, 10, 11]      # 8 bindus
# Total: 8+6+7+8+8+8+4+8 = 57


def _rasi_index(longitude: float) -> int:
    return int(longitude / 30) % 12


def _compute_sarvashtakavarga(ephemeris: Dict, lagna_longitude: float) -> Dict[str, int]:
    """
    Compute Sarvashtakavarga bindu count for each of the 12 signs.

    Returns dict of rasi_name → bindu_count (total across chart = 57).
    """
    bindus = [0] * 12
    planets = ephemeris.get("planets", {})

    contributors = [
        (planets.get("Sun", ephemeris.get("sun", {})).get("longitude_deg", 0.0), SUN_AV_BENEFIC_HOUSES),
        (planets.get("Moon", ephemeris.get("moon", {})).get("longitude_deg", 0.0), MOON_AV_BENEFIC_HOUSES),
        (planets.get("Mars", {}).get("longitude_deg", 0.0), MARS_AV_BENEFIC_HOUSES),
        (planets.get("Mercury", {}).get("longitude_deg", 0.0), MERCURY_AV_BENEFIC_HOUSES),
        (planets.get("Jupiter", {}).get("longitude_deg", 0.0), JUPITER_AV_BENEFIC_HOUSES),
        (planets.get("Venus", {}).get("longitude_deg", 0.0), VENUS_AV_BENEFIC_HOUSES),
        (planets.get("Saturn", {}).get("longitude_deg", 0.0), SATURN_AV_BENEFIC_HOUSES),
        (lagna_longitude, LAGNA_AV_BENEFIC_HOUSES),
    ]

    for contrib_long, benefic_houses in contributors:
        contrib_rasi = _rasi_index(contrib_long)
        for house_dist in benefic_houses:
            target_sign = (contrib_rasi + house_dist - 1) % 12
            bindus[target_sign] += 1

    return {RASI_ORDER[i]: bindus[i] for i in range(12)}


def _classify_bindu_strength(bindu: int, planet: str) -> str:
    """Classify bindu strength relative to Sarvashtakavarga average (57/12 ≈ 4.75)."""
    if bindu >= 6:
        return "high_support"
    elif bindu >= 5:
        return "moderate_support"
    elif bindu >= 4:
        return "low_support"
    else:
        return "resistance"


def compute_ashtakavarga_validation(
    saturn_transit_rasi: str,
    jupiter_transit_rasi: str,
    birth_moon_rasi: Optional[str] = None,
    natal_positions: Optional[Dict] = None,
    lagna_longitude: Optional[float] = None,
) -> Dict:
    """
    Validate Saturn and Jupiter transits against Ashtaka Varga bindus.

    When natal_positions (ephemeris dict) and lagna_longitude are provided,
    computes full classical Sarvashtakavarga. Otherwise falls back to a
    simplified estimation.
    """
    logger.debug(f"DEBUG: Ashtakavarga validating Saturn={saturn_transit_rasi}, Jupiter={jupiter_transit_rasi}")

    try:
        if natal_positions is not None and lagna_longitude is not None:
            sarva = _compute_sarvashtakavarga(natal_positions, lagna_longitude)
            total = sum(sarva.values())
            logger.debug(f"DEBUG: Sarvashtakavarga total={total} (expected 57), distribution={sarva}")

            saturn_bindu = sarva.get(saturn_transit_rasi, 4)
            jupiter_bindu = sarva.get(jupiter_transit_rasi, 4)
            source = "classical"
        else:
            # Fallback: simplified estimation using birth moon position
            SATURN_AV_TEMPLATE = {
                "Aries": 3, "Taurus": 4, "Gemini": 5, "Cancer": 2,
                "Leo": 3, "Virgo": 4, "Libra": 5, "Scorpio": 3,
                "Sagittarius": 4, "Capricorn": 5, "Aquarius": 4, "Pisces": 3,
            }
            JUPITER_AV_TEMPLATE = {
                "Aries": 4, "Taurus": 5, "Gemini": 4, "Cancer": 6,
                "Leo": 4, "Virgo": 4, "Libra": 5, "Scorpio": 5,
                "Sagittarius": 6, "Capricorn": 4, "Aquarius": 4, "Pisces": 5,
            }
            saturn_bindu = SATURN_AV_TEMPLATE.get(saturn_transit_rasi, 3)
            jupiter_bindu = JUPITER_AV_TEMPLATE.get(jupiter_transit_rasi, 4)

            if birth_moon_rasi:
                moon_idx = RASI_TO_INDEX.get(birth_moon_rasi, 0)
                saturn_idx = RASI_TO_INDEX.get(saturn_transit_rasi, 0)
                jupiter_idx = RASI_TO_INDEX.get(jupiter_transit_rasi, 0)
                saturn_house = ((saturn_idx - moon_idx) % 12) + 1
                jupiter_house = ((jupiter_idx - moon_idx) % 12) + 1
                if saturn_house in [3, 6, 11]:
                    saturn_bindu += 1
                elif saturn_house in [1, 4, 7, 8]:
                    saturn_bindu -= 1
                if jupiter_house in [2, 5, 7, 9, 11]:
                    jupiter_bindu += 1
                elif jupiter_house in [1, 6, 8, 12]:
                    jupiter_bindu -= 1

            saturn_bindu = max(0, min(saturn_bindu, 8))
            jupiter_bindu = max(0, min(jupiter_bindu, 8))
            sarva = None
            source = "estimated"

        saturn_strength = _classify_bindu_strength(saturn_bindu, "Saturn")
        jupiter_strength = _classify_bindu_strength(jupiter_bindu, "Jupiter")

        overall_support = "balanced"
        if saturn_strength in ["high_support", "moderate_support"] and jupiter_strength in ["high_support", "moderate_support"]:
            overall_support = "strong_support"
        elif saturn_strength == "resistance" or jupiter_strength == "resistance":
            overall_support = "needs_remedies"
        elif saturn_strength in ["high_support", "moderate_support"] or jupiter_strength in ["high_support", "moderate_support"]:
            overall_support = "partial_support"

        result = {
            "saturn": {
                "transit_rasi": saturn_transit_rasi,
                "bindus": saturn_bindu,
                "strength": saturn_strength,
            },
            "jupiter": {
                "transit_rasi": jupiter_transit_rasi,
                "bindus": jupiter_bindu,
                "strength": jupiter_strength,
            },
            "overall_support": overall_support,
            "source": source,
        }

        if sarva is not None:
            result["sarvashtakavarga"] = sarva

        logger.debug(f"DEBUG: Ashtakavarga ({source}): Saturn={saturn_strength} (bindu={saturn_bindu}), Jupiter={jupiter_strength} (bindu={jupiter_bindu})")

        return result

    except Exception as e:
        logger.error(f"ERROR: Ashtakavarga computation failed: {e}")
        return {
            "saturn": {"strength": "unknown", "error": str(e)},
            "jupiter": {"strength": "unknown", "error": str(e)},
            "overall_support": "unknown",
            "error": str(e),
        }
