"""
Event Window Engine

Computes monthly event windows based on:
- Moon transit through signs
- Tara Bala quality
- Planetary transits

Outputs time windows for:
- Supportive periods (good for initiatives)
- Sensitive periods (need caution)
- Challenging periods (avoid major decisions)
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from ..utils.swisseph_utils import compute_planet_longitude

logger = logging.getLogger(__name__)

MOON_TRANSIT_TIME_DAYS = 2.25

TARA_SEQUENCE = [
    "janma", "sampat", "vipat", "kshemam", "pratyak",
    "sadhana", "naidhana", "mitra", "parama_mitra"
]

TARA_QUALITY = {
    "janma": "sensitive",
    "sampat": "supportive",
    "vipat": "challenging",
    "kshemam": "supportive",
    "pratyak": "sensitive",
    "sadhana": "supportive",
    "naidhana": "challenging",
    "mitra": "supportive",
    "parama_mitra": "supportive",
}

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha",
    "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
]


def get_nakshatra_index(longitude: float) -> int:
    """Get nakshatra index (0-26) from longitude."""
    nakshatra_span = 360 / 27
    return int(longitude / nakshatra_span) % 27


def get_tara_bala(birth_nakshatra_idx: int, transit_nakshatra_idx: int) -> str:
    """
    Calculate Tara Bala from birth nakshatra to transit nakshatra.
    """
    distance = (transit_nakshatra_idx - birth_nakshatra_idx + 27) % 27
    tara_index = distance % 9
    return TARA_SEQUENCE[tara_index]


def compute_moon_windows(
    birth_moon_longitude: float,
    start_date: datetime,
    days: int = 30,
    latitude: float = 13.0,
    longitude: float = 80.0
) -> List[Dict[str, Any]]:
    """
    Compute Moon transit windows for a period.
    
    Args:
        birth_moon_longitude: Birth Moon longitude
        start_date: Start of period
        days: Number of days to analyze
        latitude: Location latitude
        longitude: Location longitude
        
    Returns:
        List of time windows with quality
    """
    windows = []
    birth_nakshatra_idx = get_nakshatra_index(birth_moon_longitude)
    
    current_date = start_date
    current_window = None
    
    for day_offset in range(0, days, 2):
        check_date = current_date + timedelta(days=day_offset)
        
        try:
            moon_lon = compute_planet_longitude("Moon", check_date)
            transit_nakshatra_idx = get_nakshatra_index(moon_lon)
            tara = get_tara_bala(birth_nakshatra_idx, transit_nakshatra_idx)
            quality = TARA_QUALITY.get(tara, "neutral")
            
            if current_window is None or current_window["quality"] != quality:
                if current_window:
                    windows.append(current_window)
                current_window = {
                    "start_day": day_offset + 1,
                    "end_day": day_offset + 2,
                    "quality": quality,
                    "tara": tara,
                    "nakshatra": NAKSHATRA_NAMES[transit_nakshatra_idx]
                }
            else:
                current_window["end_day"] = day_offset + 2
                
        except Exception as e:
            logger.debug(f"DEBUG: Error computing moon position for day {day_offset}: {e}")
            continue
    
    if current_window:
        windows.append(current_window)
    
    return windows


def aggregate_windows(windows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Aggregate windows by quality type.
    """
    supportive = []
    sensitive = []
    challenging = []
    
    for window in windows:
        quality = window.get("quality", "neutral")
        window_data = {
            "days": f"{window['start_day']}-{window['end_day']}",
            "tara": window.get("tara"),
            "nakshatra": window.get("nakshatra")
        }
        
        if quality == "supportive":
            supportive.append(window_data)
        elif quality == "sensitive":
            sensitive.append(window_data)
        elif quality == "challenging":
            challenging.append(window_data)
    
    return {
        "supportive": supportive,
        "sensitive": sensitive,
        "challenging": challenging
    }


def compute_event_windows(
    birth_moon_longitude: float,
    reference_date: datetime,
    gochara_data: Dict[str, Any] | None = None,
    latitude: float = 13.0,
    longitude: float = 80.0
) -> Dict[str, Any]:
    """
    Compute monthly event windows.
    
    Args:
        birth_moon_longitude: Birth Moon longitude
        reference_date: Reference date for the month
        gochara_data: Optional gochara data for enhanced analysis
        latitude: Location latitude
        longitude: Location longitude
        
    Returns:
        Event window analysis
    """
    try:
        logger.debug("DEBUG: Computing Event Windows")
        
        start_of_month = reference_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if reference_date.month == 12:
            next_month = start_of_month.replace(year=reference_date.year + 1, month=1)
        else:
            next_month = start_of_month.replace(month=reference_date.month + 1)
        
        days_in_month = (next_month - start_of_month).days
        
        moon_windows = compute_moon_windows(
            birth_moon_longitude,
            start_of_month,
            days_in_month,
            latitude,
            longitude
        )
        
        aggregated = aggregate_windows(moon_windows)
        
        overall_quality = "balanced"
        supportive_count = len(aggregated["supportive"])
        challenging_count = len(aggregated["challenging"])
        
        if supportive_count > challenging_count * 2:
            overall_quality = "favorable"
        elif challenging_count > supportive_count * 2:
            overall_quality = "challenging"
        elif supportive_count > challenging_count:
            overall_quality = "mildly_favorable"
        elif challenging_count > supportive_count:
            overall_quality = "mildly_challenging"
        
        recommendations = []
        
        if aggregated["supportive"]:
            best_window = aggregated["supportive"][0]
            recommendations.append(f"Best days for new initiatives: {best_window['days']}")
        
        if aggregated["challenging"]:
            caution_window = aggregated["challenging"][0]
            recommendations.append(f"Exercise caution around days {caution_window['days']}")
        
        if gochara_data:
            saturn_effect = gochara_data.get("saturn", {}).get("effect", "neutral")
            if saturn_effect == "challenging":
                recommendations.append("Saturn transit requires patience and careful planning")
            
            jupiter_effect = gochara_data.get("jupiter", {}).get("effect", "neutral")
            if jupiter_effect == "favorable":
                recommendations.append("Jupiter transit supports growth and expansion")
        
        logger.debug(f"DEBUG: Event windows computed - {len(moon_windows)} windows, overall: {overall_quality}")
        
        return {
            "windows": aggregated,
            "detailed_windows": moon_windows,
            "summary": {
                "overall_quality": overall_quality,
                "supportive_periods": supportive_count,
                "sensitive_periods": len(aggregated["sensitive"]),
                "challenging_periods": challenging_count,
            },
            "recommendations": recommendations,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"DEBUG: Event window computation error: {e}")
        return {
            "windows": {
                "supportive": [],
                "sensitive": [],
                "challenging": []
            },
            "detailed_windows": [],
            "summary": {
                "overall_quality": "unknown",
                "supportive_periods": 0,
                "sensitive_periods": 0,
                "challenging_periods": 0,
            },
            "recommendations": [],
            "error": str(e)
        }
