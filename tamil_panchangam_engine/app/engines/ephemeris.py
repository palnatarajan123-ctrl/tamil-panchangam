"""
This module will compute:
- Sidereal planetary longitudes
- Moon longitude (critical for Nakshatra)
- Lagna
Using Swiss Ephemeris + Lahiri ayanamsa

"""

import swisseph as swe
from datetime import datetime
from typing import Dict

# -----------------------------
# CONSTANTS
# -----------------------------

NAKSHATRA_SPAN = 13 + 1/3  # 13°20'
PADA_SPAN = NAKSHATRA_SPAN / 4

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}

NODE_TYPES = {
    "true": swe.TRUE_NODE,
    "mean": swe.MEAN_NODE,
}

RASI_NAMES = [
    "Mesham", "Rishabam", "Mithunam", "Kadakam",
    "Simmam", "Kanni", "Thulam", "Vrischikam",
    "Dhanusu", "Makaram", "Kumbham", "Meenam"
]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha",
    "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashada",
    "Uttara Ashada", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
]

AYANAMSA_MODES = {
    "lahiri": swe.SIDM_LAHIRI,
    "kp": swe.SIDM_KRISHNAMURTI,
}

# -----------------------------
# INITIALIZE SWISS EPHEMERIS
# -----------------------------

swe.set_ephe_path('.')  # use built-in ephemeris

# -----------------------------
# CORE FUNCTIONS
# -----------------------------

def to_julian_day(dt_utc: datetime) -> float:
    """
    Convert UTC datetime to Julian Day.
    """
    return swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    )


def get_sidereal_longitude(jd: float, planet: int) -> float:
    """
    Returns sidereal longitude (0–360°) for a planet.
    """
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    longitude, _ = swe.calc_ut(jd, planet, flags)
    return longitude[0] % 360


def compute_lagna(jd: float, latitude: float, longitude: float) -> float:
    """
    Compute sidereal Lagna (Ascendant).
    """
    flags = swe.FLG_SIDEREAL
    houses, ascmc = swe.houses_ex(jd, latitude, longitude, b'P', flags)
    lagna = ascmc[0] % 360
    return lagna


def get_rasi(longitude: float) -> str:
    """
    Get rasi name from sidereal longitude.
    """
    index = int(longitude // 30)
    return RASI_NAMES[index]


def get_nakshatra(longitude: float) -> Dict:
    """
    Compute Nakshatra and Pada from Moon longitude.
    """
    nak_index = int(longitude // NAKSHATRA_SPAN)
    nak_start = nak_index * NAKSHATRA_SPAN
    pada = int((longitude - nak_start) // PADA_SPAN) + 1

    return {
        "name": NAKSHATRA_NAMES[nak_index],
        "index": nak_index,
        "pada": pada
    }


def compute_sidereal_positions(
    dt_utc: datetime,
    latitude: float,
    longitude: float,
    node_type: str = "mean",
    ayanamsa: str = "lahiri",
) -> Dict:
    """
    MASTER FUNCTION
    Computes:
    - Sidereal planetary positions
    - Moon rasi & nakshatra
    - Lagna

    Args:
        dt_utc: Birth datetime in UTC
        latitude: Birth location latitude
        longitude: Birth location longitude  
        node_type: "mean" (traditional Tamil) or "true" (astronomical)
                   Default is "mean" for traditional Tamil astrology compatibility.

    This output is AUTHORITATIVE.
    """
    swe.set_sid_mode(AYANAMSA_MODES.get(ayanamsa, swe.SIDM_LAHIRI))

    jd = to_julian_day(dt_utc)

    planets = {}
    for name, planet_id in PLANETS.items():
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        result, _ = swe.calc_ut(jd, planet_id, flags)
        lon = result[0] % 360
        speed = result[3]  # degrees per day, negative = retrograde

        # Get equatorial coords for declination
        eq_flags = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL
        eq_result, _ = swe.calc_ut(jd, planet_id, eq_flags)
        declination = eq_result[1]  # degrees, negative = south

        planets[name] = {
            "longitude_deg": lon,
            "rasi": get_rasi(lon),
            "speed_deg_per_day": speed,
            "is_retrograde": speed < 0,
            "declination": declination,
        }

    node_id = NODE_TYPES.get(node_type.lower(), swe.MEAN_NODE)
    rahu_flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    rahu_result, _ = swe.calc_ut(jd, node_id, rahu_flags)
    rahu_lon = rahu_result[0] % 360
    planets["Rahu"] = {
        "longitude_deg": rahu_lon,
        "rasi": get_rasi(rahu_lon),
        "speed_deg_per_day": rahu_result[3],
        "is_retrograde": True,  # Rahu always retrograde
        "declination": 0.0,
    }

    ketu_lon = (rahu_lon + 180) % 360
    planets["Ketu"] = {
        "longitude_deg": ketu_lon,
        "rasi": get_rasi(ketu_lon),
        "speed_deg_per_day": -rahu_result[3],
        "is_retrograde": True,  # Ketu always retrograde
        "declination": 0.0,
    }

    moon_lon = planets["Moon"]["longitude_deg"]

    return {
        "julian_day": jd,
        "node_type": node_type.lower(),
        "ayanamsa": ayanamsa.lower(),
        "lagna": {
            "longitude_deg": compute_lagna(jd, latitude, longitude),
            "rasi": get_rasi(compute_lagna(jd, latitude, longitude))
        },
        "moon": {
            "longitude_deg": moon_lon,
            "rasi": get_rasi(moon_lon),
            "nakshatra": get_nakshatra(moon_lon)
        },
        "planets": planets
    }
