"""
Selective Yoga Engine

Detects only the most significant yogas:
1. Gaja Kesari Yoga - Jupiter in kendra from Moon
2. Dhana Yoga - Lords of wealth houses in mutual aspect/conjunction
3. Viparita Raja Yoga - Dusthana lords in dusthana
4. Neecha Bhanga Raja Yoga - Cancellation of debilitation
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

KENDRA_FROM_POSITIONS = [1, 4, 7, 10]
DUSTHANA_HOUSES = [6, 8, 12]
DHANA_HOUSES = [2, 5, 9, 11]

EXALTATION_SIGNS = {
    "Sun": 1,       # Aries
    "Moon": 2,      # Taurus
    "Mars": 10,     # Capricorn
    "Mercury": 6,   # Virgo
    "Jupiter": 4,   # Cancer
    "Venus": 12,    # Pisces
    "Saturn": 7,    # Libra
}

DEBILITATION_SIGNS = {
    "Sun": 7,       # Libra
    "Moon": 8,      # Scorpio
    "Mars": 4,      # Cancer
    "Mercury": 12,  # Pisces
    "Jupiter": 10,  # Capricorn
    "Venus": 6,     # Virgo
    "Saturn": 1,    # Aries
}

RASI_LORDS = {
    1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon",
    5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars",
    9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter",
}


def get_rasi_from_longitude(longitude: float) -> int:
    """Get rasi (1-12) from longitude."""
    return int(longitude // 30) + 1


def get_house_from_lagna(planet_lon: float, lagna_lon: float) -> int:
    """Get house number from lagna."""
    planet_rasi = get_rasi_from_longitude(planet_lon)
    lagna_rasi = get_rasi_from_longitude(lagna_lon)
    return ((planet_rasi - lagna_rasi + 12) % 12) + 1


def check_gaja_kesari(
    jupiter_lon: float,
    moon_lon: float
) -> Optional[Dict[str, Any]]:
    """
    Check for Gaja Kesari Yoga.
    Jupiter must be in kendra (1, 4, 7, 10) from Moon.
    """
    moon_rasi = get_rasi_from_longitude(moon_lon)
    jupiter_rasi = get_rasi_from_longitude(jupiter_lon)
    
    distance = ((jupiter_rasi - moon_rasi + 12) % 12) + 1
    
    if distance in KENDRA_FROM_POSITIONS:
        strength = "strong" if distance in [1, 7] else "moderate"
        return {
            "name": "Gaja Kesari Yoga",
            "present": True,
            "strength": strength,
            "jupiter_house_from_moon": distance,
            "effects": [
                "Leadership and authority",
                "Wisdom and good reputation",
                "Success in endeavors",
                "Prosperity and respect"
            ],
            "rationale": f"Jupiter in {distance}th from Moon (kendra position)"
        }
    return None


def check_dhana_yoga(
    planets_data: Dict[str, Any],
    lagna_lon: float
) -> List[Dict[str, Any]]:
    """
    Check for Dhana Yogas.
    Lords of 2, 5, 9, 11 in mutual aspect or conjunction.
    """
    yogas = []
    lagna_rasi = get_rasi_from_longitude(lagna_lon)
    
    dhana_lords = {}
    for house in DHANA_HOUSES:
        target_rasi = ((lagna_rasi - 1 + house - 1) % 12) + 1
        lord = RASI_LORDS.get(target_rasi)
        if lord and lord not in ["Rahu", "Ketu"]:
            dhana_lords[house] = lord
    
    lord_positions = {}
    for house, lord in dhana_lords.items():
        if lord in planets_data:
            lord_lon = planets_data[lord].get("longitude_deg", 0)
            lord_house = get_house_from_lagna(lord_lon, lagna_lon)
            lord_positions[lord] = {
                "house": lord_house,
                "longitude": lord_lon,
                "owns": house
            }
    
    lords = list(lord_positions.keys())
    for i, lord1 in enumerate(lords):
        for lord2 in lords[i+1:]:
            pos1 = lord_positions[lord1]
            pos2 = lord_positions[lord2]
            
            if pos1["house"] == pos2["house"]:
                yogas.append({
                    "name": "Dhana Yoga",
                    "present": True,
                    "type": "conjunction",
                    "planets": [lord1, lord2],
                    "houses_involved": [pos1["owns"], pos2["owns"]],
                    "strength": "strong",
                    "effects": [
                        "Wealth accumulation",
                        "Financial prosperity",
                        "Material success"
                    ],
                    "rationale": f"{lord1} (H{pos1['owns']} lord) conjunct {lord2} (H{pos2['owns']} lord) in H{pos1['house']}"
                })
            
            distance = abs(pos1["house"] - pos2["house"])
            if distance in [6, 0]:
                if distance == 0:
                    continue
                yogas.append({
                    "name": "Dhana Yoga",
                    "present": True,
                    "type": "mutual_aspect",
                    "planets": [lord1, lord2],
                    "houses_involved": [pos1["owns"], pos2["owns"]],
                    "strength": "moderate",
                    "effects": [
                        "Financial stability",
                        "Gradual wealth growth"
                    ],
                    "rationale": f"{lord1} and {lord2} in mutual 7th aspect"
                })
    
    return yogas


def check_viparita_raja_yoga(
    planets_data: Dict[str, Any],
    lagna_lon: float
) -> List[Dict[str, Any]]:
    """
    Check for Viparita Raja Yoga.
    Lord of 6, 8, or 12 placed in another dusthana.
    """
    yogas = []
    lagna_rasi = get_rasi_from_longitude(lagna_lon)
    
    dusthana_lords = {}
    for house in DUSTHANA_HOUSES:
        target_rasi = ((lagna_rasi - 1 + house - 1) % 12) + 1
        lord = RASI_LORDS.get(target_rasi)
        if lord and lord not in ["Rahu", "Ketu"]:
            dusthana_lords[house] = lord
    
    for house, lord in dusthana_lords.items():
        if lord in planets_data:
            lord_lon = planets_data[lord].get("longitude_deg", 0)
            lord_house = get_house_from_lagna(lord_lon, lagna_lon)
            
            if lord_house in DUSTHANA_HOUSES and lord_house != house:
                yoga_name = {
                    6: "Harsha Yoga",
                    8: "Sarala Yoga",
                    12: "Vimala Yoga"
                }.get(house, "Viparita Raja Yoga")
                
                yogas.append({
                    "name": yoga_name,
                    "category": "Viparita Raja Yoga",
                    "present": True,
                    "planet": lord,
                    "owns_house": house,
                    "placed_in": lord_house,
                    "strength": "moderate",
                    "effects": [
                        "Rise through unconventional means",
                        "Overcoming obstacles",
                        "Victory over enemies"
                    ],
                    "rationale": f"H{house} lord {lord} placed in H{lord_house} (dusthana in dusthana)"
                })
    
    return yogas


def check_neecha_bhanga(
    planets_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Check for Neecha Bhanga Raja Yoga.
    Cancellation of debilitation when:
    - Lord of debilitation sign is in kendra from Moon or Lagna
    - Debilitated planet is aspected by its exaltation sign lord
    """
    yogas = []
    
    for planet, deb_sign in DEBILITATION_SIGNS.items():
        if planet not in planets_data:
            continue
            
        planet_lon = planets_data[planet].get("longitude_deg", 0)
        planet_rasi = get_rasi_from_longitude(planet_lon)
        
        if planet_rasi == deb_sign:
            deb_lord = RASI_LORDS.get(deb_sign)
            
            if deb_lord and deb_lord in planets_data:
                deb_lord_lon = planets_data[deb_lord].get("longitude_deg", 0)
                deb_lord_rasi = get_rasi_from_longitude(deb_lord_lon)
                
                moon_lon = planets_data.get("Moon", {}).get("longitude_deg", 0)
                moon_rasi = get_rasi_from_longitude(moon_lon)
                
                distance_from_moon = ((deb_lord_rasi - moon_rasi + 12) % 12) + 1
                
                if distance_from_moon in KENDRA_FROM_POSITIONS:
                    yogas.append({
                        "name": "Neecha Bhanga Raja Yoga",
                        "present": True,
                        "debilitated_planet": planet,
                        "cancellation_by": deb_lord,
                        "mechanism": f"{deb_lord} (lord of debilitation sign) in kendra from Moon",
                        "strength": "moderate",
                        "effects": [
                            "Rise from humble beginnings",
                            "Overcoming initial difficulties",
                            "Ultimate success despite challenges"
                        ],
                        "rationale": f"{planet} debilitated but cancelled by {deb_lord} in kendra from Moon"
                    })
    
    return yogas


def compute_yogas(
    ephemeris: Dict[str, Any],
    houses: Dict[int, Any]
) -> Dict[str, Any]:
    """
    Compute all selective yogas for the chart.
    
    Args:
        ephemeris: Planetary positions
        houses: House data
        
    Returns:
        Detected yogas with details
    """
    try:
        logger.debug("DEBUG: Computing Yogas")
        
        planets_data = ephemeris.get("planets", {})
        lagna_data = ephemeris.get("lagna", {})
        lagna_lon = lagna_data.get("longitude_deg", 0.0)
        moon_data = ephemeris.get("moon", {})
        moon_lon = moon_data.get("longitude_deg", planets_data.get("Moon", {}).get("longitude_deg", 0.0))
        
        jupiter_lon = planets_data.get("Jupiter", {}).get("longitude_deg", 0.0)
        
        all_yogas = []
        
        gaja_kesari = check_gaja_kesari(jupiter_lon, moon_lon)
        if gaja_kesari:
            all_yogas.append(gaja_kesari)
        
        dhana_yogas = check_dhana_yoga(planets_data, lagna_lon)
        all_yogas.extend(dhana_yogas)
        
        viparita_yogas = check_viparita_raja_yoga(planets_data, lagna_lon)
        all_yogas.extend(viparita_yogas)
        
        neecha_bhanga = check_neecha_bhanga(planets_data)
        all_yogas.extend(neecha_bhanga)
        
        present_yogas = [y for y in all_yogas if y.get("present")]
        
        has_gaja_kesari = any(y["name"] == "Gaja Kesari Yoga" for y in present_yogas)
        has_dhana = any(y["name"] == "Dhana Yoga" for y in present_yogas)
        has_raja = any("Raja" in y.get("name", "") or "Raja" in y.get("category", "") for y in present_yogas)
        
        logger.debug(f"DEBUG: Yogas computed - {len(present_yogas)} yogas found")
        
        return {
            "yogas": present_yogas,
            "summary": {
                "total_yogas": len(present_yogas),
                "has_gaja_kesari": has_gaja_kesari,
                "has_dhana_yoga": has_dhana,
                "has_raja_yoga": has_raja,
                "yoga_names": list(set(y["name"] for y in present_yogas)),
            },
            "error": None
        }
        
    except Exception as e:
        logger.error(f"DEBUG: Yoga computation error: {e}")
        return {
            "yogas": [],
            "summary": {
                "total_yogas": 0,
                "has_gaja_kesari": False,
                "has_dhana_yoga": False,
                "has_raja_yoga": False,
                "yoga_names": [],
            },
            "error": str(e)
        }
