"""
This module will compute:
- Gochara (planetary transits)
- Transit effects based on natal Moon
- Ashtakavarga points for transits
- Major transit events (Saturn, Jupiter, Rahu-Ketu)

"""

from datetime import datetime
from typing import Dict

from app.engines.ephemeris import compute_sidereal_positions

RASI_ORDER = [
    "Mesham", "Rishabam", "Mithunam", "Kadakam",
    "Simmam", "Kanni", "Thulam", "Vrischikam",
    "Dhanusu", "Makaram", "Kumbham", "Meenam"
]

def rasi_distance(from_rasi: str, to_rasi: str) -> int:
    """
    Compute distance from one rasi to another (1 to 12).
    """
    from_idx = RASI_ORDER.index(from_rasi)
    to_idx = RASI_ORDER.index(to_rasi)
    return ((to_idx - from_idx) % 12) + 1


def classify_gochara(distance: int) -> str:
    """
    Simple classical classification (v1).
    """
    if distance in [1, 4, 7, 8, 12]:
        return "Challenging"
    elif distance in [2, 6, 10, 11]:
        return "Supportive"
    else:
        return "Neutral"


def compute_monthly_transits(
    reference_date_utc: datetime,
    latitude: float,
    longitude: float,
    natal_moon_rasi: str
) -> Dict:
    """
    Compute monthly transit snapshot and Moon-based Gochara.
    """

    transit_positions = compute_sidereal_positions(
        reference_date_utc,
        latitude,
        longitude
    )

    results = {}

    for planet in ["Saturn", "Jupiter", "Mars"]:
        transit_rasi = transit_positions["planets"][planet]["rasi"]
        distance = rasi_distance(natal_moon_rasi, transit_rasi)

        results[planet] = {
            "transit_rasi": transit_rasi,
            "from_moon_house": distance,
            "gochara_effect": classify_gochara(distance)
        }

    return {
        "reference_date": reference_date_utc.strftime("%Y-%m-%d"),
        "moon_gochara_reference": natal_moon_rasi,
        "major_transits": results
    }
