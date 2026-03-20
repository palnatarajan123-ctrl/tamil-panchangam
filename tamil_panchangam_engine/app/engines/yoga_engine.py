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
KENDRA_HOUSES = [1, 4, 7, 10]
TRIKONA_HOUSES = [1, 5, 9]
DUSTHANA_HOUSES = [6, 8, 12]
DHANA_HOUSES = [2, 5, 9, 11]

PANCHA_PLANETS = {
    "Mars":    ("Ruchaka",   ["Courage, ambition, military success, strong physique"]),
    "Mercury": ("Bhadra",    ["Intelligence, communication, business acumen, wit"]),
    "Jupiter": ("Hamsa",     ["Wisdom, spirituality, prosperity, noble character"]),
    "Venus":   ("Malavya",   ["Luxury, beauty, artistic talent, marital happiness"]),
    "Saturn":  ("Shasha",    ["Discipline, longevity, service, judicial authority"]),
}

OWN_SIGNS = {
    "Sun":     [5],
    "Moon":    [4],
    "Mars":    [1, 8],
    "Mercury": [3, 6],
    "Jupiter": [9, 12],
    "Venus":   [2, 7],
    "Saturn":  [10, 11],
}

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


def check_raja_yoga(
    planets_data: Dict[str, Any],
    lagna_lon: float
) -> List[Dict[str, Any]]:
    """
    Raja Yoga: Lord of a Kendra (1,4,7,10) conjunct or mutually aspecting
    lord of a Trikona (1,5,9). House 1 counts for both.
    """
    yogas = []
    lagna_rasi = get_rasi_from_longitude(lagna_lon)

    kendra_lords = {}
    for house in KENDRA_HOUSES:
        target_rasi = ((lagna_rasi - 1 + house - 1) % 12) + 1
        lord = RASI_LORDS.get(target_rasi)
        if lord and lord not in ["Rahu", "Ketu"]:
            kendra_lords[house] = lord

    trikona_lords = {}
    for house in TRIKONA_HOUSES:
        target_rasi = ((lagna_rasi - 1 + house - 1) % 12) + 1
        lord = RASI_LORDS.get(target_rasi)
        if lord and lord not in ["Rahu", "Ketu"]:
            trikona_lords[house] = lord

    seen_pairs: set = set()
    for kh, klord in kendra_lords.items():
        for th, tlord in trikona_lords.items():
            if klord == tlord:
                continue
            pair_key = tuple(sorted([klord, tlord]))
            if pair_key in seen_pairs:
                continue
            if klord not in planets_data or tlord not in planets_data:
                continue

            klon = planets_data[klord].get("longitude_deg", 0)
            tlon = planets_data[tlord].get("longitude_deg", 0)
            khouse = get_house_from_lagna(klon, lagna_lon)
            thouse = get_house_from_lagna(tlon, lagna_lon)

            if khouse == thouse:
                seen_pairs.add(pair_key)
                yogas.append({
                    "name": "Raja Yoga",
                    "present": True,
                    "type": "conjunction",
                    "planets": [klord, tlord],
                    "houses_involved": [kh, th],
                    "strength": "strong",
                    "effects": [
                        "Authority and recognition",
                        "Career success and status",
                        "Leadership positions",
                        "Royal favour or institutional support"
                    ],
                    "rationale": (
                        f"Kendra lord {klord} (H{kh}) conjunct Trikona lord "
                        f"{tlord} (H{th}) in H{khouse}"
                    )
                })
            else:
                distance = abs(khouse - thouse)
                if distance == 6:
                    seen_pairs.add(pair_key)
                    yogas.append({
                        "name": "Raja Yoga",
                        "present": True,
                        "type": "mutual_aspect",
                        "planets": [klord, tlord],
                        "houses_involved": [kh, th],
                        "strength": "moderate",
                        "effects": [
                            "Professional elevation",
                            "Recognition through effort",
                            "Gradual rise in status"
                        ],
                        "rationale": (
                            f"Kendra lord {klord} (H{kh}) mutually aspecting "
                            f"Trikona lord {tlord} (H{th})"
                        )
                    })
    return yogas


def check_pancha_mahapurusha(
    planets_data: Dict[str, Any],
    lagna_lon: float
) -> List[Dict[str, Any]]:
    """
    Pancha Mahapurusha Yoga: Mars/Mercury/Jupiter/Venus/Saturn in own sign
    or exaltation AND placed in a Kendra (1,4,7,10) from Lagna.
    """
    yogas = []
    lagna_rasi = get_rasi_from_longitude(lagna_lon)

    for planet, (yoga_name, effects) in PANCHA_PLANETS.items():
        if planet not in planets_data:
            continue
        plon = planets_data[planet].get("longitude_deg", 0)
        prasi = get_rasi_from_longitude(plon)
        phouse = get_house_from_lagna(plon, lagna_lon)

        in_own    = prasi in OWN_SIGNS.get(planet, [])
        in_exalt  = prasi == EXALTATION_SIGNS.get(planet)
        in_kendra = phouse in KENDRA_HOUSES

        if (in_own or in_exalt) and in_kendra:
            strength = "very strong" if in_exalt else "strong"
            placement = "exaltation" if in_exalt else "own sign"
            yogas.append({
                "name": f"{yoga_name} Yoga",
                "category": "Pancha Mahapurusha",
                "present": True,
                "planet": planet,
                "placement": placement,
                "house": phouse,
                "strength": strength,
                "effects": effects,
                "rationale": (
                    f"{planet} in {placement} (sign {prasi}) "
                    f"placed in kendra H{phouse}"
                )
            })
    return yogas


def check_budhaditya_yoga(
    planets_data: Dict[str, Any],
    lagna_lon: float
) -> Optional[Dict[str, Any]]:
    """
    Budhaditya Yoga: Sun and Mercury in the same sign.
    """
    if "Sun" not in planets_data or "Mercury" not in planets_data:
        return None

    sun_lon  = planets_data["Sun"].get("longitude_deg", 0)
    merc_lon = planets_data["Mercury"].get("longitude_deg", 0)

    sun_rasi  = get_rasi_from_longitude(sun_lon)
    merc_rasi = get_rasi_from_longitude(merc_lon)

    if sun_rasi != merc_rasi:
        return None

    house = get_house_from_lagna(sun_lon, lagna_lon)
    orb   = abs(sun_lon - merc_lon) % 360
    if orb > 180:
        orb = 360 - orb

    combust = orb <= 14
    strength = "moderate" if combust else "strong"

    return {
        "name": "Budhaditya Yoga",
        "present": True,
        "planets": ["Sun", "Mercury"],
        "house": house,
        "combust_mercury": combust,
        "strength": strength,
        "effects": [
            "Sharp intellect and analytical mind",
            "Eloquence and communication skills",
            "Success in academics and writing",
            "Respected for intelligence"
        ],
        "rationale": (
            f"Sun and Mercury conjunct in sign {sun_rasi} (H{house})"
            + (" – Mercury combust, moderate strength" if combust else "")
        )
    }


def check_chandra_mangala_yoga(
    planets_data: Dict[str, Any],
    lagna_lon: float
) -> Optional[Dict[str, Any]]:
    """
    Chandra-Mangala Yoga: Moon and Mars in the same sign or mutual 7th aspect.
    """
    if "Moon" not in planets_data or "Mars" not in planets_data:
        return None

    moon_lon = planets_data["Moon"].get("longitude_deg", 0)
    mars_lon = planets_data["Mars"].get("longitude_deg", 0)

    moon_rasi = get_rasi_from_longitude(moon_lon)
    mars_rasi = get_rasi_from_longitude(mars_lon)
    moon_house = get_house_from_lagna(moon_lon, lagna_lon)
    mars_house = get_house_from_lagna(mars_lon, lagna_lon)

    if moon_rasi == mars_rasi:
        return {
            "name": "Chandra-Mangala Yoga",
            "present": True,
            "type": "conjunction",
            "planets": ["Moon", "Mars"],
            "house": moon_house,
            "strength": "strong",
            "effects": [
                "Wealth through enterprise and boldness",
                "Business acumen and drive",
                "Emotional courage",
                "Financial independence"
            ],
            "rationale": f"Moon and Mars conjunct in sign {moon_rasi} (H{moon_house})"
        }

    distance = abs(moon_house - mars_house)
    if distance == 6:
        return {
            "name": "Chandra-Mangala Yoga",
            "present": True,
            "type": "mutual_aspect",
            "planets": ["Moon", "Mars"],
            "houses": [moon_house, mars_house],
            "strength": "moderate",
            "effects": [
                "Ambitious emotional drive",
                "Wealth through persistence",
                "Competitive instinct"
            ],
            "rationale": f"Moon (H{moon_house}) and Mars (H{mars_house}) in mutual 7th aspect"
        }
    return None


def check_kemadruma_yoga(
    planets_data: Dict[str, Any],
    lagna_lon: float
) -> Optional[Dict[str, Any]]:
    """
    Kemadruma Yoga: Moon has no planets in the 2nd or 12th sign from it.
    Cancelled if Moon is in kendra from Lagna.
    """
    if "Moon" not in planets_data:
        return None

    moon_lon  = planets_data["Moon"].get("longitude_deg", 0)
    moon_rasi = get_rasi_from_longitude(moon_lon)
    moon_house = get_house_from_lagna(moon_lon, lagna_lon)

    second_from_moon  = (moon_rasi % 12) + 1
    twelfth_from_moon = ((moon_rasi - 2) % 12) + 1

    PHYSICAL_PLANETS = ["Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    flanking_occupied = False
    for planet in PHYSICAL_PLANETS:
        if planet not in planets_data:
            continue
        prasi = get_rasi_from_longitude(planets_data[planet].get("longitude_deg", 0))
        if prasi in [second_from_moon, twelfth_from_moon]:
            flanking_occupied = True
            break

    if flanking_occupied:
        return None

    if moon_house in KENDRA_HOUSES:
        return None  # Cancelled by kendra placement

    return {
        "name": "Kemadruma Yoga",
        "category": "Challenging Yoga",
        "present": True,
        "planet": "Moon",
        "moon_house": moon_house,
        "strength": "moderate",
        "effects": [
            "Emotional isolation or loneliness at times",
            "Need for inner resilience",
            "Self-reliance in emotional matters",
            "Periods of introspection"
        ],
        "rationale": (
            f"Moon in H{moon_house} with no planets flanking "
            f"(signs {twelfth_from_moon} and {second_from_moon} empty)"
        )
    }


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

        raja_yogas = check_raja_yoga(planets_data, lagna_lon)
        all_yogas.extend(raja_yogas)

        pancha_yogas = check_pancha_mahapurusha(planets_data, lagna_lon)
        all_yogas.extend(pancha_yogas)

        budhaditya = check_budhaditya_yoga(planets_data, lagna_lon)
        if budhaditya:
            all_yogas.append(budhaditya)

        chandra_mangala = check_chandra_mangala_yoga(planets_data, lagna_lon)
        if chandra_mangala:
            all_yogas.append(chandra_mangala)

        kemadruma = check_kemadruma_yoga(planets_data, lagna_lon)
        if kemadruma:
            all_yogas.append(kemadruma)

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
                "has_pancha_mahapurusha": any(
                    "Pancha Mahapurusha" in y.get("category", "") for y in present_yogas
                ),
                "has_budhaditya": any(y["name"] == "Budhaditya Yoga" for y in present_yogas),
                "has_kemadruma": any(y["name"] == "Kemadruma Yoga" for y in present_yogas),
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
                "has_pancha_mahapurusha": False,
                "has_budhaditya": False,
                "has_kemadruma": False,
                "yoga_names": [],
            },
            "error": str(e)
        }
