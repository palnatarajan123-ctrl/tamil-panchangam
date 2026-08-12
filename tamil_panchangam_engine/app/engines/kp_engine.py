"""
KP (Krishnamurti Paddhati) engine.

Computes KP star/sub lords for planets and all 12 Placidus house cusps,
plus cuspal significators for the six financial/relational houses (2,6,7,8,10,11).

KP for NEW charts only — no lazy backfill, no retrofit of existing charts.
"""

from app.engines.kp_sublords import get_star_lord, get_sub_lord, get_sub_sub_lord

# Rasi (sign) lords in zodiac order (Aries=0 … Pisces=11)
_SIGN_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
]

# Houses for which we compute cuspal significators
_KEY_HOUSES = [2, 6, 7, 8, 10, 11]


def _sign_lord(longitude: float) -> str:
    return _SIGN_LORDS[int(longitude // 30) % 12]


def _house_of(longitude: float, cusps: list) -> int:
    """Return 1-indexed house number for a given sidereal longitude."""
    for h in range(12):
        start = cusps[h]
        end = cusps[(h + 1) % 12]
        if start <= end:
            if start <= longitude < end:
                return h + 1
        else:  # straddles 360°/0°
            if longitude >= start or longitude < end:
                return h + 1
    return 1  # fallback


def _cuspal_significators(house_num: int, cusps: list, planets: dict) -> list:
    """
    KP significators for house_num, in order of strength:
    1. Occupants of the house
    2. Planets whose star lord is an occupant
    3. Sign lord of the house cusp
    4. Planets whose star lord is the sign lord of the cusp
    """
    planet_names = [n for n in planets if n != "Lagna"]

    occupants = {n for n in planet_names if planets[n]["house"] == house_num}
    star_of_occupants = {n for n in planet_names if planets[n]["star_lord"] in occupants}

    cusp_lord = _sign_lord(cusps[house_num - 1])
    star_of_cusp_lord = {n for n in planet_names if planets[n]["star_lord"] == cusp_lord}

    seen: set = set()
    result: list = []
    for group in [sorted(occupants), sorted(star_of_occupants), [cusp_lord], sorted(star_of_cusp_lord)]:
        for p in group:
            if p not in seen:
                seen.add(p)
                result.append(p)
    return result


def compute_kp(ephemeris: dict, cusps: list) -> dict:
    """
    Full KP computation for a birth chart.

    Args:
        ephemeris: output of compute_sidereal_positions()
        cusps: list of 12 sidereal Placidus cusp longitudes from compute_placidus_cusps()
               (0-indexed: cusps[0] = house 1 cusp, cusps[11] = house 12 cusp)

    Returns:
        {
          "planets":  {planet_name: {longitude, house, star_lord, sub_lord}},
          "house_cusps": {"1": {longitude, sign_lord, star_lord, sub_lord}, …},
          "cuspal_significators": {"2": [...], "6": [...], "7": [...], "8": [...], "10": [...], "11": [...]},
        }
    """
    # Build planet dict (planets + Moon + Lagna from ephemeris)
    all_planets: dict = dict(ephemeris.get("planets", {}))
    moon = ephemeris.get("moon", {})
    if moon:
        all_planets["Moon"] = moon
    lagna = ephemeris.get("lagna", {})
    if lagna:
        all_planets["Lagna"] = lagna

    planets: dict = {}
    for name, data in all_planets.items():
        lon = data.get("longitude_deg", 0.0)
        planets[name] = {
            "longitude": lon,
            "house": 1 if name == "Lagna" else _house_of(lon, cusps),
            "star_lord": get_star_lord(lon),
            "sub_lord": get_sub_lord(lon),
            "sub_sub_lord": get_sub_sub_lord(lon),
        }

    # House cusp sublords (all 12)
    house_cusps: dict = {}
    for i, cusp_lon in enumerate(cusps):
        h = i + 1
        house_cusps[str(h)] = {
            "longitude": cusp_lon,
            "sign_lord": _sign_lord(cusp_lon),
            "star_lord": get_star_lord(cusp_lon),
            "sub_lord": get_sub_lord(cusp_lon),
        }

    # Cuspal significators for key houses
    cuspal_significators: dict = {
        str(h): _cuspal_significators(h, cusps, planets)
        for h in _KEY_HOUSES
    }

    return {
        "planets": planets,
        "house_cusps": house_cusps,
        "cuspal_significators": cuspal_significators,
    }
