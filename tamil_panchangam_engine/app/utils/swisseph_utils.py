"""
Swiss Ephemeris utility functions for planetary calculations.
Wraps the core ephemeris module for use by signal engines.
"""
from datetime import datetime
import swisseph as swe

swe.set_sid_mode(swe.SIDM_LAHIRI)
swe.set_ephe_path('.')

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


def to_julian_day(dt_utc: datetime) -> float:
    """Convert UTC datetime to Julian Day."""
    return swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    )


def compute_planet_longitude_with_speed(planet_name: str, dt_utc: datetime):
    """
    Compute sidereal longitude and daily speed for a planet.

    Returns:
        (longitude: float, speed_deg_per_day: float)
        speed < 0 means retrograde motion.
    """
    jd = to_julian_day(dt_utc)

    if planet_name == "Ketu":
        rahu_id = PLANETS["Rahu"]
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        result, _ = swe.calc_ut(jd, rahu_id, flags)
        long = (result[0] + 180) % 360
        speed = -result[3]  # Ketu always moves opposite to Rahu
        return long, speed

    planet_id = PLANETS.get(planet_name)
    if planet_id is None:
        raise ValueError(f"Unknown planet: {planet_name}")

    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flags)
    return result[0] % 360, result[3]


def compute_planet_longitude(planet_name: str, dt_utc: datetime) -> float:
    """
    Compute sidereal longitude for a planet at a given UTC datetime.
    
    Args:
        planet_name: Name of planet (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu)
        dt_utc: UTC datetime
        
    Returns:
        Sidereal longitude in degrees (0-360)
    """
    jd = to_julian_day(dt_utc)
    
    if planet_name == "Ketu":
        rahu_id = PLANETS["Rahu"]
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        longitude, _ = swe.calc_ut(jd, rahu_id, flags)
        return (longitude[0] + 180) % 360
    
    planet_id = PLANETS.get(planet_name)
    if planet_id is None:
        raise ValueError(f"Unknown planet: {planet_name}")
    
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    longitude, _ = swe.calc_ut(jd, planet_id, flags)
    return longitude[0] % 360
