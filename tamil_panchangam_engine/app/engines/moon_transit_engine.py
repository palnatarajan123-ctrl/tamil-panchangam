"""
Moon Transit Rhythm (Chandra Gati) Engine - EPIC Signal Expansion

Tracks Moon's movement through signs for the prediction window.
Summarizes emotional rhythm for the month.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from app.utils.swisseph_utils import compute_planet_longitude

logger = logging.getLogger(__name__)

RASI_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

RASI_TO_INDEX = {rasi: i for i, rasi in enumerate(RASI_ORDER)}

RASI_MOOD_QUALITIES = {
    "Aries": "energetic",
    "Taurus": "stable",
    "Gemini": "restless",
    "Cancer": "emotional",
    "Leo": "confident",
    "Virgo": "analytical",
    "Libra": "harmonious",
    "Scorpio": "intense",
    "Sagittarius": "optimistic",
    "Capricorn": "disciplined",
    "Aquarius": "detached",
    "Pisces": "reflective",
}

FAVORABLE_MOON_HOUSES = {2, 5, 7, 9, 10, 11}
CHALLENGING_MOON_HOUSES = {6, 8, 12}
SENSITIVE_MOON_HOUSES = {1, 4, 8}


def _longitude_to_rasi(longitude: float) -> str:
    """Convert longitude to rasi name."""
    rasi_index = int(longitude / 30) % 12
    return RASI_ORDER[rasi_index]


def _house_from_moon(transit_rasi: str, natal_moon_rasi: str) -> int:
    """Calculate house position from Moon sign."""
    moon_idx = RASI_TO_INDEX.get(natal_moon_rasi, 0)
    transit_idx = RASI_TO_INDEX.get(transit_rasi, 0)
    return ((transit_idx - moon_idx) % 12) + 1


def compute_chandra_gati(
    year: int,
    month: int,
    natal_moon_rasi: str,
    latitude: float = 13.0827,
    longitude: float = 80.2707,
) -> Dict:
    """
    Compute Moon transit rhythm (Chandra Gati) for the month.
    
    Samples Moon position at 3-day intervals and computes:
    - Dominant moods based on Moon transits
    - Supportive and sensitive days
    """
    logger.debug(f"DEBUG: Chandra Gati computing for {year}-{month}")
    
    try:
        from calendar import monthrange
        _, days_in_month = monthrange(year, month)
        
        sample_days = list(range(1, days_in_month + 1, 3))
        if days_in_month not in sample_days:
            sample_days.append(days_in_month)
        
        moon_positions = []
        mood_counts = {}
        supportive_days = []
        sensitive_days = []
        challenging_days = []
        
        for day in sample_days:
            try:
                sample_date = datetime(year, month, day, 12, 0, 0)
                moon_long = compute_planet_longitude("Moon", sample_date)
                moon_rasi = _longitude_to_rasi(moon_long)
                moon_house = _house_from_moon(moon_rasi, natal_moon_rasi)
                mood = RASI_MOOD_QUALITIES.get(moon_rasi, "neutral")
                
                moon_positions.append({
                    "day": day,
                    "rasi": moon_rasi,
                    "house_from_natal": moon_house,
                    "mood": mood,
                })
                
                mood_counts[mood] = mood_counts.get(mood, 0) + 1
                
                if moon_house in FAVORABLE_MOON_HOUSES:
                    supportive_days.append(day)
                elif moon_house in CHALLENGING_MOON_HOUSES:
                    challenging_days.append(day)
                
                if moon_house in SENSITIVE_MOON_HOUSES:
                    sensitive_days.append(day)
                    
            except Exception as e:
                logger.warning(f"WARN: Moon calculation failed for day {day}: {e}")
                continue
        
        sorted_moods = sorted(mood_counts.items(), key=lambda x: -x[1])
        dominant_moods = [m[0] for m in sorted_moods[:3]]
        
        chandra_gati = {
            "dominant_moods": dominant_moods,
            "supportive_days": supportive_days[:5],
            "sensitive_days": sensitive_days[:5],
            "challenging_days": challenging_days[:5],
            "moon_positions": moon_positions,
            "mood_distribution": mood_counts,
            "period": f"{year}-{month:02d}",
        }
        
        logger.debug(f"DEBUG: Chandra Gati computed: moods={dominant_moods}, supportive={len(supportive_days)}, sensitive={len(sensitive_days)}")
        
        return chandra_gati
        
    except Exception as e:
        logger.error(f"ERROR: Chandra Gati computation failed: {e}")
        return {
            "dominant_moods": ["neutral"],
            "supportive_days": [],
            "sensitive_days": [],
            "challenging_days": [],
            "period": f"{year}-{month:02d}",
            "error": str(e),
        }
