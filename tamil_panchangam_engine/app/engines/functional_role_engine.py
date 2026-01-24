"""
Functional Benefic/Malefic Engine

Determines the functional role of each planet based on:
- Lagna (Ascendant) sign
- Houses owned by each planet
- Kendradhipati dosha
- Maraka lordship
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

RASI_LORDS = {
    1: "Mars",     # Aries
    2: "Venus",    # Taurus
    3: "Mercury",  # Gemini
    4: "Moon",     # Cancer
    5: "Sun",      # Leo
    6: "Mercury",  # Virgo
    7: "Venus",    # Libra
    8: "Mars",     # Scorpio
    9: "Jupiter",  # Sagittarius
    10: "Saturn",  # Capricorn
    11: "Saturn",  # Aquarius
    12: "Jupiter", # Pisces
}

RASI_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", 
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

NATURAL_BENEFICS = ["Jupiter", "Venus", "Mercury", "Moon"]
NATURAL_MALEFICS = ["Saturn", "Mars", "Sun", "Rahu", "Ketu"]

TRIKONA_HOUSES = [1, 5, 9]
KENDRA_HOUSES = [1, 4, 7, 10]
DUSTHANA_HOUSES = [6, 8, 12]
MARAKA_HOUSES = [2, 7]


def get_houses_owned_by_planet(planet: str, lagna_rasi: int) -> List[int]:
    """
    Get houses owned by a planet for a given lagna.
    """
    houses = []
    for house_num in range(1, 13):
        rasi = ((lagna_rasi - 1 + house_num - 1) % 12) + 1
        if RASI_LORDS.get(rasi) == planet:
            houses.append(house_num)
    return houses


def determine_functional_role(
    planet: str,
    owned_houses: List[int],
    lagna_rasi: int
) -> Dict[str, Any]:
    """
    Determine functional benefic/malefic status.
    
    Rules:
    - Trikona lords (1, 5, 9) are benefic
    - Kendra lords can have kendradhipati dosha (natural benefics become neutral)
    - Dusthana lords (6, 8, 12) are malefic
    - Maraka lords (2, 7) are conditionally malefic
    """
    is_trikona_lord = any(h in TRIKONA_HOUSES for h in owned_houses)
    is_kendra_lord = any(h in KENDRA_HOUSES and h != 1 for h in owned_houses)
    is_dusthana_lord = any(h in DUSTHANA_HOUSES for h in owned_houses)
    is_maraka_lord = any(h in MARAKA_HOUSES for h in owned_houses)
    
    natural_nature = "benefic" if planet in NATURAL_BENEFICS else "malefic"
    
    reasons = []
    
    if is_trikona_lord and is_kendra_lord and not is_dusthana_lord:
        functional_role = "yogakaraka"
        strength = "very_strong"
        reasons.append("Yoga karaka - rules both trikona and kendra")
    
    elif is_trikona_lord and not is_dusthana_lord:
        functional_role = "benefic"
        strength = "strong" if 9 in owned_houses or 5 in owned_houses else "moderate"
        reasons.append(f"Trikona lord (houses {[h for h in owned_houses if h in TRIKONA_HOUSES]})")
    
    elif is_dusthana_lord:
        if is_trikona_lord:
            functional_role = "mixed"
            strength = "moderate"
            reasons.append("Rules both trikona and dusthana")
        else:
            functional_role = "malefic"
            strength = "moderate"
            reasons.append(f"Dusthana lord (houses {[h for h in owned_houses if h in DUSTHANA_HOUSES]})")
    
    elif is_kendra_lord and natural_nature == "benefic":
        functional_role = "neutral"
        strength = "moderate"
        reasons.append("Kendradhipati dosha - benefic owning kendra")
    
    elif is_kendra_lord and natural_nature == "malefic":
        functional_role = "neutral_positive"
        strength = "moderate"
        reasons.append("Natural malefic owning kendra - improved")
    
    elif is_maraka_lord:
        functional_role = "maraka"
        strength = "conditional"
        reasons.append(f"Maraka lord (houses {[h for h in owned_houses if h in MARAKA_HOUSES]})")
    
    else:
        functional_role = natural_nature
        strength = "moderate"
        reasons.append(f"Following natural nature: {natural_nature}")
    
    return {
        "planet": planet,
        "owned_houses": owned_houses,
        "natural_nature": natural_nature,
        "functional_role": functional_role,
        "strength": strength,
        "reasons": reasons,
        "is_yogakaraka": functional_role == "yogakaraka",
        "is_maraka": is_maraka_lord,
    }


def get_yogakaraka_for_lagna(lagna_rasi: int) -> List[str]:
    """
    Get yogakaraka planets for specific lagnas.
    Classical yogakarakas for each lagna.
    """
    yogakarakas = {
        1: ["Saturn"],      # Aries - Saturn rules 10 & 11
        2: ["Saturn"],      # Taurus - Saturn rules 9 & 10
        3: [],              # Gemini
        4: ["Mars"],        # Cancer - Mars rules 5 & 10
        5: ["Mars"],        # Leo - Mars rules 4 & 9
        6: [],              # Virgo
        7: ["Saturn"],      # Libra - Saturn rules 4 & 5
        8: [],              # Scorpio
        9: [],              # Sagittarius
        10: ["Venus"],      # Capricorn - Venus rules 5 & 10
        11: ["Venus"],      # Aquarius - Venus rules 4 & 9
        12: [],             # Pisces
    }
    return yogakarakas.get(lagna_rasi, [])


def compute_functional_roles(
    ephemeris: Dict[str, Any],
    houses: Dict[int, Any]
) -> Dict[str, Any]:
    """
    Compute functional benefic/malefic roles for all planets.
    
    Args:
        ephemeris: Planetary positions
        houses: House data
        
    Returns:
        Functional role analysis for each planet
    """
    try:
        logger.debug("DEBUG: Computing Functional Benefic/Malefic roles")
        
        lagna_data = ephemeris.get("lagna", {})
        lagna_lon = lagna_data.get("longitude_deg", 0.0)
        lagna_rasi = int(lagna_lon // 30) + 1
        lagna_name = RASI_NAMES[lagna_rasi - 1] if lagna_rasi <= 12 else "Unknown"
        
        planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        functional_roles = {}
        
        for planet in planets:
            owned_houses = get_houses_owned_by_planet(planet, lagna_rasi)
            role_data = determine_functional_role(planet, owned_houses, lagna_rasi)
            functional_roles[planet] = role_data
        
        functional_roles["Rahu"] = {
            "planet": "Rahu",
            "owned_houses": [],
            "natural_nature": "malefic",
            "functional_role": "shadow_malefic",
            "strength": "variable",
            "reasons": ["Shadow planet - takes on house lord's nature"],
            "is_yogakaraka": False,
            "is_maraka": False,
        }
        functional_roles["Ketu"] = {
            "planet": "Ketu",
            "owned_houses": [],
            "natural_nature": "malefic",
            "functional_role": "shadow_malefic",
            "strength": "variable",
            "reasons": ["Shadow planet - spiritual/detachment influence"],
            "is_yogakaraka": False,
            "is_maraka": False,
        }
        
        classical_yogakarakas = get_yogakaraka_for_lagna(lagna_rasi)
        
        benefics = [p for p, d in functional_roles.items() if d["functional_role"] in ["benefic", "yogakaraka"]]
        malefics = [p for p, d in functional_roles.items() if d["functional_role"] == "malefic"]
        neutrals = [p for p, d in functional_roles.items() if d["functional_role"] in ["neutral", "neutral_positive", "mixed"]]
        
        logger.debug(f"DEBUG: Functional roles computed for {lagna_name} lagna - {len(benefics)} benefics, {len(malefics)} malefics")
        
        return {
            "lagna": {
                "rasi": lagna_rasi,
                "name": lagna_name,
            },
            "planets": functional_roles,
            "summary": {
                "functional_benefics": benefics,
                "functional_malefics": malefics,
                "neutrals": neutrals,
                "yogakarakas": [p for p, d in functional_roles.items() if d["is_yogakaraka"]],
                "classical_yogakarakas": classical_yogakarakas,
                "marakas": [p for p, d in functional_roles.items() if d["is_maraka"]],
            },
            "error": None
        }
        
    except Exception as e:
        logger.error(f"DEBUG: Functional role computation error: {e}")
        return {
            "lagna": {"rasi": 1, "name": "Unknown"},
            "planets": {},
            "summary": {
                "functional_benefics": [],
                "functional_malefics": [],
                "neutrals": [],
                "yogakarakas": [],
                "classical_yogakarakas": [],
                "marakas": [],
            },
            "error": str(e)
        }
