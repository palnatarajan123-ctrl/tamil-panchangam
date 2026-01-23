"""
Nakshatra + Tara Bala Engine - EPIC Signal Expansion

Computes:
- Birth Nakshatra
- Current Moon Nakshatra(s)
- Tara Bala classification (Janma, Sampat, Vipat, Kshemam, etc.)
"""
import logging
from datetime import datetime
from typing import Dict, Optional
from app.utils.swisseph_utils import compute_planet_longitude

logger = logging.getLogger(__name__)

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

TARA_BALA_CYCLE = [
    ("janma", "Janma Tara - Birth Star", "neutral", "Self-awareness heightened"),
    ("sampat", "Sampat Tara - Wealth", "favorable", "Financial opportunities present"),
    ("vipat", "Vipat Tara - Danger", "challenging", "Caution advised in commitments"),
    ("kshemam", "Kshemam Tara - Welfare", "favorable", "Well-being supported"),
    ("pratyak", "Pratyak Tara - Obstacles", "challenging", "Minor obstacles likely"),
    ("sadhana", "Sadhana Tara - Achievement", "favorable", "Efforts yield results"),
    ("naidhana", "Naidhana Tara - Death-like", "challenging", "Energy drain possible"),
    ("mitra", "Mitra Tara - Friend", "favorable", "Supportive connections active"),
    ("parama_mitra", "Parama Mitra - Great Friend", "favorable", "Highly auspicious period"),
]

NAKSHATRA_DEGREES = 360 / 27


def _longitude_to_nakshatra_index(longitude: float) -> int:
    """Convert longitude to nakshatra index (0-26)."""
    return int(longitude / NAKSHATRA_DEGREES) % 27


def _longitude_to_nakshatra(longitude: float) -> str:
    """Convert longitude to nakshatra name."""
    index = _longitude_to_nakshatra_index(longitude)
    return NAKSHATRA_NAMES[index]


def compute_tara_bala(birth_nakshatra_index: int, current_nakshatra_index: int) -> Dict:
    """
    Compute Tara Bala based on birth and current nakshatra.
    
    Tara Bala cycles through 9 categories based on distance from birth nakshatra.
    """
    distance = (current_nakshatra_index - birth_nakshatra_index) % 27
    
    tara_index = distance % 9
    
    tara_key, tara_name, quality, note = TARA_BALA_CYCLE[tara_index]
    
    return {
        "tara_bala": tara_key,
        "tara_name": tara_name,
        "quality": quality,
        "note": note,
        "distance": distance,
        "cycle_position": tara_index + 1,
    }


def compute_nakshatra_context(
    reference_date_utc: datetime,
    birth_moon_longitude: float,
    latitude: float = 13.0827,
    longitude: float = 80.2707,
) -> Dict:
    """
    Compute nakshatra context for predictions.
    
    Returns:
    - Birth nakshatra
    - Current Moon nakshatra
    - Tara Bala classification
    """
    logger.debug(f"DEBUG: Nakshatra engine computing for {reference_date_utc}")
    
    try:
        birth_nakshatra_index = _longitude_to_nakshatra_index(birth_moon_longitude)
        birth_nakshatra = NAKSHATRA_NAMES[birth_nakshatra_index]
        
        current_moon_long = compute_planet_longitude("Moon", reference_date_utc)
        current_nakshatra_index = _longitude_to_nakshatra_index(current_moon_long)
        current_nakshatra = NAKSHATRA_NAMES[current_nakshatra_index]
        
        tara_bala = compute_tara_bala(birth_nakshatra_index, current_nakshatra_index)
        
        birth_pada = int((birth_moon_longitude % NAKSHATRA_DEGREES) / (NAKSHATRA_DEGREES / 4)) + 1
        current_pada = int((current_moon_long % NAKSHATRA_DEGREES) / (NAKSHATRA_DEGREES / 4)) + 1
        
        nakshatra_context = {
            "birth_nakshatra": birth_nakshatra,
            "birth_nakshatra_index": birth_nakshatra_index,
            "birth_pada": birth_pada,
            "current_nakshatra": current_nakshatra,
            "current_nakshatra_index": current_nakshatra_index,
            "current_pada": current_pada,
            "tara_bala": tara_bala["tara_bala"],
            "tara_name": tara_bala["tara_name"],
            "quality": tara_bala["quality"],
            "note": tara_bala["note"],
            "computed_at": reference_date_utc.isoformat(),
        }
        
        logger.debug(f"DEBUG: Nakshatra computed: birth={birth_nakshatra}, current={current_nakshatra}, tara={tara_bala['tara_bala']}/{tara_bala['quality']}")
        
        return nakshatra_context
        
    except Exception as e:
        logger.error(f"ERROR: Nakshatra computation failed: {e}")
        return {
            "birth_nakshatra": "Unknown",
            "current_nakshatra": "Unknown",
            "tara_bala": "unknown",
            "quality": "neutral",
            "note": "Calculation unavailable",
            "computed_at": reference_date_utc.isoformat(),
            "error": str(e),
        }
