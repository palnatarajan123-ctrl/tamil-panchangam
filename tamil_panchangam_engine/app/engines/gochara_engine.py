"""
Gochara (Transit) Engine - EPIC Signal Expansion

Computes planetary transit effects from Moon sign (Chandra Rasi) and Lagna.
Evaluates Jupiter, Saturn, Rahu, Ketu transits with traditional classifications.
"""
import logging
from datetime import datetime
from typing import Dict, Optional
from app.utils.swisseph_utils import compute_planet_longitude

logger = logging.getLogger(__name__)

RASI_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

RASI_TO_INDEX = {rasi: i for i, rasi in enumerate(RASI_ORDER)}

JUPITER_EFFECTS = {
    1: "challenging",
    2: "favorable",
    3: "neutral",
    4: "neutral",
    5: "favorable",
    6: "challenging",
    7: "favorable",
    8: "challenging",
    9: "favorable",
    10: "neutral",
    11: "favorable",
    12: "challenging",
}

SATURN_PHASES = {
    1: ("janma_sani", "challenging"),
    2: ("neutral", "neutral"),
    3: ("neutral", "neutral"),
    4: ("ashtama_sani", "challenging"),
    5: ("neutral", "neutral"),
    6: ("neutral", "neutral"),
    7: ("kantaka_sani", "challenging"),
    8: ("ashtama_sani", "challenging"),
    9: ("neutral", "neutral"),
    10: ("neutral", "mixed"),
    11: ("favorable", "favorable"),
    12: ("neutral", "mixed"),
}

RAHU_KETU_AXIS_EFFECTS = {
    "1-7": "identity_partnerships",
    "2-8": "resources_transformation",
    "3-9": "skills_wisdom",
    "4-10": "home_career",
    "5-11": "creativity_gains",
    "6-12": "service_liberation",
}


def _longitude_to_rasi(longitude: float) -> str:
    """Convert longitude to rasi name."""
    rasi_index = int(longitude / 30) % 12
    return RASI_ORDER[rasi_index]


def _house_from_moon(transit_rasi: str, natal_moon_rasi: str) -> int:
    """Calculate house position from Moon sign."""
    moon_idx = RASI_TO_INDEX.get(natal_moon_rasi, 0)
    transit_idx = RASI_TO_INDEX.get(transit_rasi, 0)
    return ((transit_idx - moon_idx) % 12) + 1


def compute_gochara(
    reference_date_utc: datetime,
    latitude: float,
    longitude: float,
    natal_moon_rasi: str,
    natal_lagna_rasi: Optional[str] = None,
) -> Dict:
    """
    Compute Gochara (transit) effects for slow-moving planets.
    
    Returns structured transit data with effects classification.
    """
    logger.debug(f"DEBUG: Gochara engine computing for {reference_date_utc}")
    
    try:
        jup_long = compute_planet_longitude("Jupiter", reference_date_utc)
        sat_long = compute_planet_longitude("Saturn", reference_date_utc)
        rahu_long = compute_planet_longitude("Rahu", reference_date_utc)
        ketu_long = (rahu_long + 180) % 360
        
        jup_rasi = _longitude_to_rasi(jup_long)
        sat_rasi = _longitude_to_rasi(sat_long)
        rahu_rasi = _longitude_to_rasi(rahu_long)
        ketu_rasi = _longitude_to_rasi(ketu_long)
        
        jup_house_from_moon = _house_from_moon(jup_rasi, natal_moon_rasi)
        sat_house_from_moon = _house_from_moon(sat_rasi, natal_moon_rasi)
        rahu_house_from_moon = _house_from_moon(rahu_rasi, natal_moon_rasi)
        ketu_house_from_moon = _house_from_moon(ketu_rasi, natal_moon_rasi)
        
        jup_effect = JUPITER_EFFECTS.get(jup_house_from_moon, "neutral")
        sat_phase, sat_effect = SATURN_PHASES.get(sat_house_from_moon, ("neutral", "neutral"))
        
        rahu_axis_key = f"{min(rahu_house_from_moon, ketu_house_from_moon)}-{max(rahu_house_from_moon, ketu_house_from_moon)}"
        if rahu_axis_key not in RAHU_KETU_AXIS_EFFECTS:
            h1 = rahu_house_from_moon
            h2 = ketu_house_from_moon
            if h2 < h1:
                h1, h2 = h2, h1
            rahu_axis_key = f"{h1}-{h2}"
        
        rahu_ketu_theme = RAHU_KETU_AXIS_EFFECTS.get(rahu_axis_key, "general_karmic")
        
        rahu_ketu_effect = "neutral"
        if rahu_house_from_moon in [1, 4, 7, 10] or ketu_house_from_moon in [1, 4, 7, 10]:
            rahu_ketu_effect = "disruptive"
        elif rahu_house_from_moon in [3, 6, 11] or ketu_house_from_moon in [3, 6, 11]:
            rahu_ketu_effect = "favorable"
        
        gochara = {
            "jupiter": {
                "transit_rasi": jup_rasi,
                "from_moon_house": jup_house_from_moon,
                "effect": jup_effect,
                "longitude": round(jup_long, 2),
            },
            "saturn": {
                "transit_rasi": sat_rasi,
                "from_moon_house": sat_house_from_moon,
                "phase": sat_phase,
                "effect": sat_effect,
                "longitude": round(sat_long, 2),
            },
            "rahu_ketu": {
                "rahu_rasi": rahu_rasi,
                "ketu_rasi": ketu_rasi,
                "rahu_from_moon_house": rahu_house_from_moon,
                "ketu_from_moon_house": ketu_house_from_moon,
                "axis": rahu_axis_key,
                "theme": rahu_ketu_theme,
                "effect": rahu_ketu_effect,
            },
            "computed_at": reference_date_utc.isoformat(),
        }
        
        logger.debug(f"DEBUG: Gochara computed: Jupiter={jup_effect}, Saturn={sat_phase}/{sat_effect}, Rahu-Ketu={rahu_ketu_effect}")
        
        return gochara
        
    except Exception as e:
        logger.error(f"ERROR: Gochara computation failed: {e}")
        return {
            "jupiter": {"effect": "neutral", "error": str(e)},
            "saturn": {"phase": "unknown", "effect": "neutral", "error": str(e)},
            "rahu_ketu": {"effect": "neutral", "error": str(e)},
            "computed_at": reference_date_utc.isoformat(),
            "error": str(e),
        }
