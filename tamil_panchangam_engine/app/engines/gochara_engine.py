"""
Gochara (Transit) Engine - EPIC Signal Expansion

Computes planetary transit effects from Moon sign (Chandra Rasi) and Lagna.
Evaluates Jupiter, Saturn, Rahu, Ketu transits with traditional classifications.
L3: Drishti (natal aspect) bonus adjusts transit signal strength.
"""
import logging
from datetime import datetime
from typing import Dict, Optional
from app.utils.swisseph_utils import compute_planet_longitude, compute_planet_longitude_with_speed

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


def _transit_phase(degree_in_sign: float) -> str:
    """Classify transit phase within a rasi."""
    if degree_in_sign < 5.0:
        return "entering"
    if degree_in_sign > 25.0:
        return "exiting"
    return "transiting"


def _days_in_sign(degree_in_sign: float, speed_deg_per_day: float) -> int:
    """Estimate days remaining in current sign based on current speed."""
    if abs(speed_deg_per_day) < 0.001:
        return 999  # stationary — unknown
    if speed_deg_per_day > 0:
        return max(0, int((30.0 - degree_in_sign) / speed_deg_per_day))
    else:
        # Retrograde — will re-enter previous sign
        return max(0, int(degree_in_sign / abs(speed_deg_per_day)))


def _house_from_moon(transit_rasi: str, natal_moon_rasi: str) -> int:
    """Calculate house position from Moon sign."""
    moon_idx = RASI_TO_INDEX.get(natal_moon_rasi, 0)
    transit_idx = RASI_TO_INDEX.get(transit_rasi, 0)
    return ((transit_idx - moon_idx) % 12) + 1


def _transit_natal_house(transit_rasi: str, natal_lagna_rasi: str) -> int:
    """Calculate house position of transit planet from natal Lagna."""
    lagna_idx = RASI_TO_INDEX.get(natal_lagna_rasi, 0)
    transit_idx = RASI_TO_INDEX.get(transit_rasi, 0)
    return ((transit_idx - lagna_idx) % 12) + 1


def _drishti_bonus_for_transit_house(transit_house: int, drishti_data: Dict) -> float:
    """
    Compute drishti aspect bonus for the natal house a transit planet occupies.

    Benefic natal aspects (Jupiter/Venus/Mercury effect='benefic') on that house
    add +0.1 each; malefic aspects subtract 0.08 each.
    Result clamped to [-0.25, +0.25].
    """
    house_aspects = drishti_data.get("house_aspects", {})
    # Keys may be strings (JSON round-trip) or ints — try both
    aspects_on_house = house_aspects.get(transit_house) or house_aspects.get(str(transit_house), [])
    bonus = 0.0
    for asp in aspects_on_house:
        effect = asp.get("effect", "")
        # Drishti engine uses "supportive" / "challenging" / "protective"
        if effect == "supportive":
            bonus += 0.10
        elif effect == "challenging":
            bonus -= 0.08
    logger.debug(
        f"DEBUG: Drishti bonus for house {transit_house}: aspects={aspects_on_house}, bonus={bonus:.3f}"
    )
    return round(max(-0.25, min(0.25, bonus)), 3)


def _conjunction_strength(transit_long: float, natal_long: float, orb: float = 6.0) -> float:
    """
    Compute angular proximity between a transit planet and a natal point.

    Returns a strength value 0.0–1.0:
      1.0 = exact conjunction (0° distance)
      0.0 = at or beyond the orb boundary
    """
    dist = abs((transit_long - natal_long + 180) % 360 - 180)
    return max(0.0, round(1.0 - dist / orb, 3))


def compute_gochara(
    reference_date_utc: datetime,
    latitude: float,
    longitude: float,
    natal_moon_rasi: str,
    natal_lagna_rasi: Optional[str] = None,
    natal_moon_longitude: Optional[float] = None,
    drishti_data: Optional[Dict] = None,
) -> Dict:
    """
    Compute Gochara (transit) effects for slow-moving planets.
    
    Returns structured transit data with effects classification.
    """
    logger.debug(f"DEBUG: Gochara engine computing for {reference_date_utc}")
    
    try:
        jup_long, jup_speed = compute_planet_longitude_with_speed("Jupiter", reference_date_utc)
        sat_long, sat_speed = compute_planet_longitude_with_speed("Saturn", reference_date_utc)
        rahu_long, rahu_speed = compute_planet_longitude_with_speed("Rahu", reference_date_utc)
        ketu_long = (rahu_long + 180) % 360

        jup_deg = jup_long % 30
        sat_deg = sat_long % 30
        rahu_deg = rahu_long % 30
        ketu_deg = ketu_long % 30

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
        
        # D-L2: conjunction strength vs natal Moon (0.0–1.0, orb = 6°)
        jup_cs = _conjunction_strength(jup_long, natal_moon_longitude) if natal_moon_longitude is not None else None
        sat_cs = _conjunction_strength(sat_long, natal_moon_longitude) if natal_moon_longitude is not None else None
        rahu_cs = _conjunction_strength(rahu_long, natal_moon_longitude) if natal_moon_longitude is not None else None
        ketu_cs = _conjunction_strength(ketu_long, natal_moon_longitude) if natal_moon_longitude is not None else None

        # L3: Drishti aspect bonus — natal aspects on the house occupied by transit planet
        if drishti_data and natal_lagna_rasi:
            jup_natal_house = _transit_natal_house(jup_rasi, natal_lagna_rasi)
            sat_natal_house = _transit_natal_house(sat_rasi, natal_lagna_rasi)
            rahu_natal_house = _transit_natal_house(rahu_rasi, natal_lagna_rasi)
            ketu_natal_house = _transit_natal_house(ketu_rasi, natal_lagna_rasi)
            jup_drishti_bonus = _drishti_bonus_for_transit_house(jup_natal_house, drishti_data)
            sat_drishti_bonus = _drishti_bonus_for_transit_house(sat_natal_house, drishti_data)
            rahu_drishti_bonus = _drishti_bonus_for_transit_house(rahu_natal_house, drishti_data)
            ketu_drishti_bonus = _drishti_bonus_for_transit_house(ketu_natal_house, drishti_data)
        else:
            jup_drishti_bonus = sat_drishti_bonus = rahu_drishti_bonus = ketu_drishti_bonus = None

        jup_entry = {
            "transit_rasi": jup_rasi,
            "from_moon_house": jup_house_from_moon,
            "effect": jup_effect,
            "longitude": round(jup_long, 2),
            "degree_in_sign": round(jup_deg, 2),
            "phase": _transit_phase(jup_deg),
            "is_retrograde": jup_speed < 0,
            "days_in_sign": _days_in_sign(jup_deg, jup_speed),
        }
        if jup_cs is not None:
            jup_entry["conjunction_strength"] = jup_cs
        if jup_drishti_bonus is not None:
            jup_entry["drishti_aspect_bonus"] = jup_drishti_bonus

        sat_entry = {
            "transit_rasi": sat_rasi,
            "from_moon_house": sat_house_from_moon,
            "phase": sat_phase,
            "effect": sat_effect,
            "longitude": round(sat_long, 2),
            "degree_in_sign": round(sat_deg, 2),
            "transit_phase": _transit_phase(sat_deg),
            "is_retrograde": sat_speed < 0,
            "days_in_sign": _days_in_sign(sat_deg, sat_speed),
        }
        if sat_cs is not None:
            sat_entry["conjunction_strength"] = sat_cs
        if sat_drishti_bonus is not None:
            sat_entry["drishti_aspect_bonus"] = sat_drishti_bonus

        rahu_ketu_entry = {
            "rahu_rasi": rahu_rasi,
            "ketu_rasi": ketu_rasi,
            "rahu_from_moon_house": rahu_house_from_moon,
            "ketu_from_moon_house": ketu_house_from_moon,
            "axis": rahu_axis_key,
            "theme": rahu_ketu_theme,
            "effect": rahu_ketu_effect,
            "rahu_degree_in_sign": round(rahu_deg, 2),
            "ketu_degree_in_sign": round(ketu_deg, 2),
            "rahu_phase": _transit_phase(rahu_deg),
            "ketu_phase": _transit_phase(ketu_deg),
            "is_retrograde": True,  # Rahu/Ketu always retrograde by convention
        }
        if rahu_cs is not None:
            rahu_ketu_entry["rahu_conjunction_strength"] = rahu_cs
        if ketu_cs is not None:
            rahu_ketu_entry["ketu_conjunction_strength"] = ketu_cs
        if rahu_drishti_bonus is not None:
            rahu_ketu_entry["rahu_drishti_bonus"] = rahu_drishti_bonus
        if ketu_drishti_bonus is not None:
            rahu_ketu_entry["ketu_drishti_bonus"] = ketu_drishti_bonus

        gochara = {
            "jupiter": jup_entry,
            "saturn": sat_entry,
            "rahu_ketu": rahu_ketu_entry,
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
