"""
Transit Hits Engine — degree-level transits of slow planets over natal positions.

Checks Jupiter, Saturn, Rahu, Ketu, Mars for conjunction, opposition, trine, square
(nodes: conjunction and opposition only) within a configurable day window.
"""

import logging
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional

from app.utils.swisseph_utils import compute_planet_longitude

logger = logging.getLogger(__name__)

TRANSIT_PLANETS = ["Jupiter", "Saturn", "Rahu", "Ketu", "Mars"]

_FULL_ASPECTS = [
    ("conjunction", 0.0),
    ("opposition", 180.0),
    ("trine", 120.0),
    ("square", 90.0),
]
_NODE_ASPECTS = [
    ("conjunction", 0.0),
    ("opposition", 180.0),
]

_PLANET_ASPECTS = {
    "Jupiter": _FULL_ASPECTS,
    "Saturn": _FULL_ASPECTS,
    "Mars": _FULL_ASPECTS,
    "Rahu": _NODE_ASPECTS,
    "Ketu": _NODE_ASPECTS,
}

ORB = 2.0  # degrees

HOUSE_LIFE_AREA = {
    1: "self", 2: "wealth", 3: "communication", 4: "home",
    5: "creativity", 6: "health", 7: "relationships", 8: "transformation",
    9: "fortune", 10: "career", 11: "gains", 12: "spirituality",
}


def _angular_diff(transit_lon: float, natal_lon: float, aspect_angle: float) -> float:
    """Smallest angular distance between transit-natal and the target aspect."""
    raw = (transit_lon - natal_lon) % 360.0
    return min(abs(raw - aspect_angle), abs(raw - aspect_angle + 360.0), abs(raw - aspect_angle - 360.0))


def _house_of(natal_planet_lon: float, lagna_lon: float) -> int:
    return int((natal_planet_lon - lagna_lon) % 360.0 / 30.0) % 12 + 1


def compute_transit_hits(
    ephemeris: Dict[str, Any],
    reference_date: Optional[date] = None,
    ayanamsa: str = "lahiri",
    window_days: int = 45,
) -> List[Dict[str, Any]]:
    """
    Detect transit hits of slow planets over natal positions within
    [reference_date − window_days, reference_date + window_days].

    Args:
        ephemeris: payload['ephemeris']
        reference_date: center of window; defaults to today UTC.
        ayanamsa: ayanamsa name.
        window_days: half-window size (total window = 2 × window_days days).

    Returns:
        List of transit hit dicts sorted by hit_date.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()

    lagna_lon = ephemeris.get("lagna", {}).get("longitude_deg", 0.0)
    natal_planets = ephemeris.get("planets", {})
    if not natal_planets:
        return []

    start_day = reference_date - timedelta(days=window_days)
    end_day = reference_date + timedelta(days=window_days)

    # best_hit[key] = dict with minimum orb seen so far
    best_hit: Dict[tuple, Dict[str, Any]] = {}

    for transit_planet in TRANSIT_PLANETS:
        aspects = _PLANET_ASPECTS[transit_planet]
        day = start_day
        while day <= end_day:
            dt = datetime(day.year, day.month, day.day, 12, 0, tzinfo=timezone.utc)
            try:
                transit_lon = compute_planet_longitude(transit_planet, dt, ayanamsa)
            except Exception as e:
                logger.debug("Transit lon %s %s: %s", transit_planet, day, e)
                day += timedelta(days=1)
                continue

            for natal_name, natal_data in natal_planets.items():
                natal_lon = natal_data.get("longitude_deg")
                if natal_lon is None:
                    continue

                for aspect_name, aspect_angle in aspects:
                    orb = _angular_diff(transit_lon, natal_lon, aspect_angle)
                    if orb > ORB:
                        continue

                    key = (transit_planet, natal_name, aspect_name)
                    prev = best_hit.get(key)
                    if prev is None or orb < prev["orb"]:
                        house = _house_of(natal_lon, lagna_lon)
                        best_hit[key] = {
                            "transit_planet": transit_planet,
                            "natal_planet": natal_name,
                            "natal_degree": round(natal_lon, 2),
                            "transit_degree": round(transit_lon, 2),
                            "hit_date": day.isoformat(),
                            "aspect_type": aspect_name,
                            "orb": round(orb, 2),
                            "house": house,
                            "life_area_hint": HOUSE_LIFE_AREA.get(house, "unknown"),
                        }
            day += timedelta(days=1)

    hits = sorted(best_hit.values(), key=lambda h: h["hit_date"])
    return hits
