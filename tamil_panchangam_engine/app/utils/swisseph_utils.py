"""
Swiss Ephemeris utility functions for planetary calculations.
Wraps the core ephemeris module for use by signal engines.
"""
from datetime import datetime
import swisseph as swe

swe.set_ephe_path('.')

# Default string values for the many `ayanamsa: str = "lahiri"` /
# `node_type: str = "mean"` parameter defaults scattered across the
# engines -- exported so a call site can reference DEFAULT_AYANAMSA/
# DEFAULT_NODE_TYPE instead of re-typing the literal. Not retrofitted
# across every existing call site in one sweep (2026-09-13): the actual
# drift risk this project hit twice (once for AYANAMSA_MODES, once for
# NODE_TYPES) was in the swe-constant LOOKUP TABLES, not these default
# strings -- a stray "Lahiri"/"LAHIRI" typo in one file's default just
# falls through .get(ayanamsa, swe.SIDM_LAHIRI) to the same fallback
# every other file already uses, so it's a much lower-value target than
# the dict consolidation was. Use these for new code and when a file is
# touched for other reasons; not worth a dedicated 20+-file sweep on
# its own.
DEFAULT_AYANAMSA = "lahiri"
DEFAULT_NODE_TYPE = "mean"

AYANAMSA_MODES = {
    "lahiri": swe.SIDM_LAHIRI,
    "kp": swe.SIDM_KRISHNAMURTI,
}

# Mirrors app.engines.ephemeris.NODE_TYPES -- "mean" is the traditional
# Tamil astrology convention and the default there; kept as the default
# here too so a transit computed today doesn't silently drift ~1-3
# degrees (and near a sign boundary, days) from what the natal chart
# used. See CLAUDE.md's 2026-09-12 Rahu-Ketu peyarchi investigation --
# this used to be hardcoded to TRUE_NODE regardless of the chart's own
# node_type setting, which moved Rahu's Dec 2026 Capricorn ingress ~10
# days earlier than the mean-node date external sources report.
NODE_TYPES = {
    "true": swe.TRUE_NODE,
    "mean": swe.MEAN_NODE,
}

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}


def to_julian_day(dt_utc: datetime) -> float:
    """Convert UTC datetime to Julian Day."""
    return swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    )


def compute_planet_longitude_with_speed(
    planet_name: str, dt_utc: datetime, ayanamsa: str = "lahiri", node_type: str = "mean"
):
    """
    Compute sidereal longitude and daily speed for a planet.

    Args:
        node_type: "mean" (traditional Tamil astrology, default) or "true"
            (astronomical) -- only affects Rahu/Ketu. Pass the chart's own
            chart_metadata.node_type so a transit lines up with the same
            convention the natal chart was computed with.

    Returns:
        (longitude: float, speed_deg_per_day: float)
        speed < 0 means retrograde motion.
    """
    swe.set_sid_mode(AYANAMSA_MODES.get(ayanamsa, swe.SIDM_LAHIRI))
    jd = to_julian_day(dt_utc)

    if planet_name in ("Rahu", "Ketu"):
        node_id = NODE_TYPES.get(node_type.lower(), swe.MEAN_NODE)
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        result, _ = swe.calc_ut(jd, node_id, flags)
        if planet_name == "Ketu":
            long = (result[0] + 180) % 360
            speed = -result[3]  # Ketu always moves opposite to Rahu
            return long, speed
        return result[0] % 360, result[3]

    planet_id = PLANETS.get(planet_name)
    if planet_id is None:
        raise ValueError(f"Unknown planet: {planet_name}")

    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flags)
    return result[0] % 360, result[3]


def compute_planet_longitude_at_jd(
    planet_name: str, jd: float, ayanamsa: str = "lahiri", node_type: str = "mean"
) -> float:
    """
    Compute sidereal longitude for a planet at a given Julian Day.

    JD-native counterpart to compute_planet_longitude(), for callers
    that already work in JD-space (a sunrise-relative time, a
    binary-search refinement, etc.) rather than starting from a plain
    UTC datetime -- routing those through the datetime-based function
    would mean converting JD -> datetime -> JD on every call for no
    benefit. This is the one place swe.set_sid_mode()/swe.calc_ut() get
    called for a non-speed planet longitude; every caller that needs
    one should use this (or compute_planet_longitude(), for the
    datetime-native case) instead of calling swe directly, so an
    ayanamsa/node_type change only ever needs to happen here. See
    CLAUDE.md's 2026-09-13 entry.

    Args:
        planet_name: Name of planet (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu)
        jd: Julian Day (UT)
        ayanamsa: Ayanamsa system ("lahiri" or "kp")
        node_type: "mean" (traditional Tamil astrology, default) or "true"
            (astronomical) -- only affects Rahu/Ketu.

    Returns:
        Sidereal longitude in degrees (0-360)
    """
    swe.set_sid_mode(AYANAMSA_MODES.get(ayanamsa, swe.SIDM_LAHIRI))

    if planet_name in ("Rahu", "Ketu"):
        node_id = NODE_TYPES.get(node_type.lower(), swe.MEAN_NODE)
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        longitude, _ = swe.calc_ut(jd, node_id, flags)
        if planet_name == "Ketu":
            return (longitude[0] + 180) % 360
        return longitude[0] % 360

    planet_id = PLANETS.get(planet_name)
    if planet_id is None:
        raise ValueError(f"Unknown planet: {planet_name}")

    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    longitude, _ = swe.calc_ut(jd, planet_id, flags)
    return longitude[0] % 360


def compute_planet_longitude(
    planet_name: str, dt_utc: datetime, ayanamsa: str = "lahiri", node_type: str = "mean"
) -> float:
    """
    Compute sidereal longitude for a planet at a given UTC datetime.

    Args:
        planet_name: Name of planet (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu)
        dt_utc: UTC datetime
        ayanamsa: Ayanamsa system ("lahiri" or "kp")
        node_type: "mean" (traditional Tamil astrology, default) or "true"
            (astronomical) -- only affects Rahu/Ketu.

    Returns:
        Sidereal longitude in degrees (0-360)
    """
    return compute_planet_longitude_at_jd(planet_name, to_julian_day(dt_utc), ayanamsa, node_type)
