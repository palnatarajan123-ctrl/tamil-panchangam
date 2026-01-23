"""
Drishti (Aspect) Engine - Parashara Aspects

Implements classical Vedic aspects:
- All planets aspect 7th house from their position
- Mars: Special aspects on 4th and 8th houses
- Jupiter: Special aspects on 5th and 9th houses
- Saturn: Special aspects on 3rd and 10th houses
- Rahu/Ketu: Special aspects on 5th and 9th houses
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

PARASHARA_SPECIAL_ASPECTS = {
    "Mars": [4, 8],
    "Jupiter": [5, 9],
    "Saturn": [3, 10],
    "Rahu": [5, 9],
    "Ketu": [5, 9],
}

PLANET_NATURE = {
    "Sun": "malefic",
    "Moon": "benefic",
    "Mars": "malefic",
    "Mercury": "neutral",
    "Jupiter": "benefic",
    "Venus": "benefic",
    "Saturn": "malefic",
    "Rahu": "malefic",
    "Ketu": "malefic",
}

HOUSE_SIGNIFICATIONS = {
    1: ["self", "health", "personality"],
    2: ["wealth", "family", "speech"],
    3: ["siblings", "courage", "communication"],
    4: ["mother", "home", "comfort"],
    5: ["children", "intelligence", "creativity"],
    6: ["enemies", "disease", "service"],
    7: ["marriage", "partnership", "business"],
    8: ["longevity", "transformation", "occult"],
    9: ["fortune", "dharma", "higher_learning"],
    10: ["career", "status", "karma"],
    11: ["gains", "friends", "aspirations"],
    12: ["losses", "liberation", "foreign"],
}


def get_house_from_longitude(longitude: float) -> int:
    """Convert longitude to house number (1-12)."""
    return int(longitude // 30) + 1


def compute_aspected_houses(planet_house: int, planet_name: str) -> List[int]:
    """
    Compute all houses aspected by a planet.
    All planets aspect 7th from their position.
    Special aspects based on Parashara rules.
    """
    aspects = []
    seventh_house = ((planet_house - 1 + 7 - 1) % 12) + 1
    aspects.append(seventh_house)
    
    if planet_name in PARASHARA_SPECIAL_ASPECTS:
        for offset in PARASHARA_SPECIAL_ASPECTS[planet_name]:
            special_house = ((planet_house - 1 + offset - 1) % 12) + 1
            if special_house not in aspects:
                aspects.append(special_house)
    
    return sorted(aspects)


def determine_aspect_effect(planet_name: str, aspected_house: int, house_occupants: Dict[int, List[str]]) -> str:
    """
    Determine the effect of an aspect.
    - Benefic planet aspecting: positive
    - Malefic planet aspecting: challenging
    - Neutral: depends on context
    """
    nature = PLANET_NATURE.get(planet_name, "neutral")
    
    if nature == "benefic":
        return "supportive"
    elif nature == "malefic":
        if aspected_house in [6, 8, 12]:
            return "protective"
        return "challenging"
    else:
        return "mixed"


def compute_drishti(
    ephemeris: Dict[str, Any],
    houses: Dict[int, Any],
    lagna_longitude: float = 0.0
) -> Dict[str, Any]:
    """
    Compute planetary aspects (drishti) for the natal chart.
    
    Args:
        ephemeris: Planetary positions from base chart
        houses: House data with occupants
        lagna_longitude: Lagna degree for house calculation
        
    Returns:
        Structured drishti data with aspects and effects
    """
    try:
        logger.debug("DEBUG: Computing Drishti (aspects)")
        
        planets_data = ephemeris.get("planets", {})
        aspects = []
        house_aspects_received = {h: [] for h in range(1, 13)}
        
        lagna_deg = lagna_longitude
        if ephemeris.get("lagna"):
            lagna_deg = ephemeris["lagna"].get("longitude_deg", 0.0)
        
        for planet_name, planet_data in planets_data.items():
            if planet_name in ["Ketu"]:
                continue
                
            planet_lon = planet_data.get("longitude_deg", 0.0)
            planet_house = ((int(planet_lon // 30) - int(lagna_deg // 30) + 12) % 12) + 1
            
            aspected_houses = compute_aspected_houses(planet_house, planet_name)
            
            for aspected_house in aspected_houses:
                effect = determine_aspect_effect(
                    planet_name,
                    aspected_house,
                    {h: houses.get(h, {}).get("occupants", []) for h in range(1, 13)}
                )
                
                aspect_data = {
                    "planet": planet_name,
                    "from_house": planet_house,
                    "aspected_house": aspected_house,
                    "aspect_type": "special" if aspected_house != ((planet_house - 1 + 7 - 1) % 12) + 1 else "seventh",
                    "effect": effect,
                    "significations": HOUSE_SIGNIFICATIONS.get(aspected_house, []),
                }
                aspects.append(aspect_data)
                house_aspects_received[aspected_house].append({
                    "planet": planet_name,
                    "effect": effect
                })
        
        significant_aspects = []
        for aspect in aspects:
            if aspect["planet"] in ["Jupiter", "Saturn", "Mars", "Rahu"]:
                if aspect["aspect_type"] == "special" or aspect["effect"] != "mixed":
                    significant_aspects.append(aspect)
        
        benefic_aspects = sum(1 for a in aspects if a["effect"] == "supportive")
        malefic_aspects = sum(1 for a in aspects if a["effect"] == "challenging")
        
        logger.debug(f"DEBUG: Drishti computed - {len(aspects)} total aspects, {benefic_aspects} benefic, {malefic_aspects} malefic")
        
        return {
            "aspects": aspects,
            "significant_aspects": significant_aspects,
            "house_aspects": house_aspects_received,
            "summary": {
                "total_aspects": len(aspects),
                "benefic_aspects": benefic_aspects,
                "malefic_aspects": malefic_aspects,
                "balance": "benefic_dominant" if benefic_aspects > malefic_aspects else (
                    "malefic_dominant" if malefic_aspects > benefic_aspects else "balanced"
                )
            },
            "error": None
        }
        
    except Exception as e:
        logger.error(f"DEBUG: Drishti computation error: {e}")
        return {
            "aspects": [],
            "significant_aspects": [],
            "house_aspects": {h: [] for h in range(1, 13)},
            "summary": {
                "total_aspects": 0,
                "benefic_aspects": 0,
                "malefic_aspects": 0,
                "balance": "unknown"
            },
            "error": str(e)
        }
