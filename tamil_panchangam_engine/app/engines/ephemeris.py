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
    "Rahu": swe.TRUE_NODE,
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

# -----------------------------
# INITIALIZE SWISS EPHEMERIS
# -----------------------------

swe.set_sid_mode(swe.SIDM_LAHIRI)
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
    longitude: float
) -> Dict:
    """
    MASTER FUNCTION
    Computes:
    - Sidereal planetary positions
    - Moon rasi & nakshatra
    - Lagna

    This output is AUTHORITATIVE.
    """
    # ✅ Ensure Lahiri ayanamsa is set before EVERY calculation
    # (protects against global state pollution from other modules)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    jd = to_julian_day(dt_utc)

    planets = {}
    for name, planet_id in PLANETS.items():
        lon = get_sidereal_longitude(jd, planet_id)
        planets[name] = {
            "longitude_deg": lon,
            "rasi": get_rasi(lon)
        }

    # Ketu = Rahu + 180°
    rahu_lon = planets["Rahu"]["longitude_deg"]
    ketu_lon = (rahu_lon + 180) % 360
    planets["Ketu"] = {
        "longitude_deg": ketu_lon,
        "rasi": get_rasi(ketu_lon)
    }

    moon_lon = planets["Moon"]["longitude_deg"]

    return {
        "julian_day": jd,
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
