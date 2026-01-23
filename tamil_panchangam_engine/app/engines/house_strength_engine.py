"""
House Strength & Affliction Engine

Computes static natal chart house analysis:
- House strength based on occupants and lord placement
- House affliction based on malefic presence/aspects
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

NATURAL_BENEFICS = ["Jupiter", "Venus", "Moon", "Mercury"]
NATURAL_MALEFICS = ["Saturn", "Mars", "Rahu", "Ketu", "Sun"]

HOUSE_KENDRA = [1, 4, 7, 10]
HOUSE_TRIKONA = [1, 5, 9]
HOUSE_DUSTHANA = [6, 8, 12]
HOUSE_UPACHAYA = [3, 6, 10, 11]

PLANET_STRENGTH_FACTOR = {
    "Sun": 0.8,
    "Moon": 0.7,
    "Mars": 0.9,
    "Mercury": 0.6,
    "Jupiter": 1.0,
    "Venus": 0.85,
    "Saturn": 0.95,
    "Rahu": 0.7,
    "Ketu": 0.6,
}

RASI_LORDS = {
    1: "Mars",
    2: "Venus",
    3: "Mercury",
    4: "Moon",
    5: "Sun",
    6: "Mercury",
    7: "Venus",
    8: "Mars",
    9: "Jupiter",
    10: "Saturn",
    11: "Saturn",
    12: "Jupiter",
}


def get_lord_for_house(house_num: int, lagna_rasi: int) -> str:
    """Get the lord of a house based on lagna."""
    rasi = ((lagna_rasi - 1 + house_num - 1) % 12) + 1
    return RASI_LORDS.get(rasi, "Unknown")


def compute_house_strength(
    occupants: List[str],
    lord_position: int,
    house_num: int,
    aspects_received: List[Dict]
) -> Dict[str, Any]:
    """
    Compute strength score for a house.
    
    Factors:
    - Benefic occupants add strength
    - Lord in good position adds strength
    - Benefic aspects add strength
    """
    score = 50
    factors = []
    
    for occupant in occupants:
        if occupant in NATURAL_BENEFICS:
            score += 10
            factors.append(f"{occupant} (benefic) occupying")
        elif occupant in NATURAL_MALEFICS:
            if house_num in HOUSE_UPACHAYA:
                score += 5
                factors.append(f"{occupant} in upachaya (positive)")
            else:
                score -= 8
                factors.append(f"{occupant} (malefic) occupying")
    
    if lord_position in HOUSE_KENDRA:
        score += 12
        factors.append(f"Lord in kendra (H{lord_position})")
    elif lord_position in HOUSE_TRIKONA:
        score += 15
        factors.append(f"Lord in trikona (H{lord_position})")
    elif lord_position in HOUSE_DUSTHANA:
        score -= 10
        factors.append(f"Lord in dusthana (H{lord_position})")
    
    for aspect in aspects_received:
        if aspect.get("effect") == "supportive":
            score += 5
            factors.append(f"Benefic aspect from {aspect.get('planet')}")
        elif aspect.get("effect") == "challenging":
            score -= 5
            factors.append(f"Malefic aspect from {aspect.get('planet')}")
    
    score = max(0, min(100, score))
    
    if score >= 70:
        strength = "strong"
    elif score >= 50:
        strength = "moderate"
    elif score >= 30:
        strength = "weak"
    else:
        strength = "very_weak"
    
    return {
        "score": score,
        "strength": strength,
        "factors": factors
    }


def compute_house_affliction(
    occupants: List[str],
    aspects_received: List[Dict],
    house_num: int
) -> Dict[str, Any]:
    """
    Compute affliction level for a house.
    
    Affliction comes from:
    - Malefic occupants
    - Malefic aspects
    - Dusthana lords present
    """
    affliction_score = 0
    affliction_sources = []
    
    malefics_present = [p for p in occupants if p in NATURAL_MALEFICS]
    for mal in malefics_present:
        if mal in ["Saturn", "Rahu"]:
            affliction_score += 20
        elif mal in ["Mars", "Ketu"]:
            affliction_score += 15
        else:
            affliction_score += 10
        affliction_sources.append(f"{mal} present")
    
    for aspect in aspects_received:
        if aspect.get("effect") == "challenging":
            planet = aspect.get("planet", "")
            if planet in ["Saturn", "Rahu"]:
                affliction_score += 12
            elif planet == "Mars":
                affliction_score += 10
            else:
                affliction_score += 5
            affliction_sources.append(f"{planet} aspect")
    
    affliction_score = min(100, affliction_score)
    
    if affliction_score >= 40:
        level = "high"
    elif affliction_score >= 20:
        level = "moderate"
    elif affliction_score > 0:
        level = "mild"
    else:
        level = "none"
    
    return {
        "score": affliction_score,
        "level": level,
        "sources": affliction_sources
    }


def compute_all_house_strength(
    ephemeris: Dict[str, Any],
    houses: Dict[int, Any],
    drishti_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute strength and affliction for all 12 houses.
    
    Args:
        ephemeris: Planetary positions
        houses: House data with occupants
        drishti_data: Computed aspects data
        
    Returns:
        Complete house strength analysis
    """
    try:
        logger.debug("DEBUG: Computing House Strength & Affliction")
        
        lagna_data = ephemeris.get("lagna", {})
        lagna_lon = lagna_data.get("longitude_deg", 0.0)
        lagna_rasi = int(lagna_lon // 30) + 1
        
        planets_data = ephemeris.get("planets", {})
        planet_houses = {}
        for planet_name, planet_data in planets_data.items():
            p_lon = planet_data.get("longitude_deg", 0.0)
            p_house = ((int(p_lon // 30) - int(lagna_lon // 30) + 12) % 12) + 1
            planet_houses[planet_name] = p_house
        
        house_aspects = drishti_data.get("house_aspects", {h: [] for h in range(1, 13)})
        
        house_strength = {}
        house_affliction = {}
        
        for house_num in range(1, 13):
            house_data = houses.get(house_num, {})
            occupants = house_data.get("occupants", [])
            
            lord = get_lord_for_house(house_num, lagna_rasi)
            lord_position = planet_houses.get(lord, house_num)
            
            aspects_received = house_aspects.get(house_num, [])
            
            strength = compute_house_strength(
                occupants, lord_position, house_num, aspects_received
            )
            house_strength[house_num] = strength
            
            affliction = compute_house_affliction(
                occupants, aspects_received, house_num
            )
            house_affliction[house_num] = affliction
        
        strong_houses = [h for h, d in house_strength.items() if d["strength"] == "strong"]
        weak_houses = [h for h, d in house_strength.items() if d["strength"] in ["weak", "very_weak"]]
        afflicted_houses = [h for h, d in house_affliction.items() if d["level"] in ["high", "moderate"]]
        
        logger.debug(f"DEBUG: House analysis complete - {len(strong_houses)} strong, {len(weak_houses)} weak, {len(afflicted_houses)} afflicted")
        
        return {
            "strength": house_strength,
            "affliction": house_affliction,
            "summary": {
                "strong_houses": strong_houses,
                "weak_houses": weak_houses,
                "afflicted_houses": afflicted_houses,
                "kendra_strength": sum(house_strength.get(h, {}).get("score", 0) for h in HOUSE_KENDRA) / 4,
                "trikona_strength": sum(house_strength.get(h, {}).get("score", 0) for h in HOUSE_TRIKONA) / 3,
            },
            "error": None
        }
        
    except Exception as e:
        logger.error(f"DEBUG: House strength computation error: {e}")
        return {
            "strength": {},
            "affliction": {},
            "summary": {
                "strong_houses": [],
                "weak_houses": [],
                "afflicted_houses": [],
                "kendra_strength": 50,
                "trikona_strength": 50,
            },
            "error": str(e)
        }
