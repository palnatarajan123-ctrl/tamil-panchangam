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

from app.engines.nakshatra_names import canonical_nakshatra_list as _canonical_nakshatra_list
NAKSHATRA_NAMES = _canonical_nakshatra_list()


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
    longitude: float = 80.0,
    ayanamsa: str = "lahiri",
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
            moon_lon = compute_planet_longitude("Moon", check_date, ayanamsa=ayanamsa)
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
    longitude: float = 80.0,
    ayanamsa: str = "lahiri",
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
            longitude,
            ayanamsa=ayanamsa,
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


# ── Confluence Detector ───────────────────────────────────────────────────────

from datetime import date as _date
from typing import Any as _Any, Dict as _Dict, List as _List, Optional as _Optional

_BENEFIC_PLANETS = {"Jupiter", "Venus", "Moon", "Mercury"}
_MALEFIC_PLANETS = {"Saturn", "Rahu", "Ketu", "Mars", "Sun"}

# Positive/negative aspects for confluence scoring
_POSITIVE_ASPECTS = {"conjunction", "trine"}
_NEGATIVE_ASPECTS = {"opposition", "square"}

# Planet → life areas it naturally supports (positive signal)
_PLANET_POSITIVE_AREAS: _Dict[str, _List[str]] = {
    "Jupiter": ["career", "fortune", "wealth", "spirituality", "self"],
    "Venus":   ["relationships", "creativity", "wealth", "gains", "home"],
    "Mercury": ["communication", "gains", "wealth"],
    "Moon":    ["home", "self", "spirituality"],
    "Sun":     ["career", "self"],
    "Mars":    ["health", "self"],
    "Saturn":  ["career", "spirituality"],
    "Rahu":    ["gains", "transformation"],
    "Ketu":    ["spirituality", "transformation"],
}

_YOGA_AREA: _Dict[str, str] = {
    "dhana": "wealth",
    "raja": "career",
    "dharma": "fortune",
    "moksha": "spirituality",
    "general": "self",
    "conjunction": "self",
}

_CONFIDENCE = {3: "medium", 4: "high", 5: "very high"}

_ALL_LIFE_AREAS = [
    "self", "wealth", "communication", "home", "creativity", "health",
    "relationships", "transformation", "fortune", "career", "gains", "spirituality",
]


def _signal_label(transit_hit: _Dict[str, _Any]) -> str:
    tp = transit_hit["transit_planet"]
    np_ = transit_hit["natal_planet"]
    asp = transit_hit["aspect_type"]
    h = transit_hit["house"]
    return f"{tp} {asp} natal {np_} (house {h})"


def detect_confluence(
    pratyantar: _Dict[str, _Any],
    transit_hits: _List[_Dict[str, _Any]],
    active_yogas: _List[_Dict[str, _Any]],
    varshaphal: _Dict[str, _Any],
    refined_av: _Dict[str, _Any],
    reference_date: _Optional[_date] = None,
    num_months: int = 3,
) -> _List[_Dict[str, _Any]]:
    """
    Combine all predictive signal engines and surface windows with 3+ confluent signals.

    Args:
        pratyantar: output of compute_pratyantar.
        transit_hits: output of compute_transit_hits.
        active_yogas: output of compute_yoga_activation.
        varshaphal: output of compute_varshaphal.
        refined_av: output of compute_refined_av.
        reference_date: center date; defaults to today.
        num_months: half-range in months (total range = 2 × num_months months).

    Returns:
        List of confluence window dicts sorted by window_start.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()

    # Build 2-week windows across ± num_months (≈ ±90 days)
    window_days = num_months * 30
    start = reference_date - timedelta(days=window_days)
    results: _List[_Dict[str, _Any]] = []

    # Pre-index transit hits by date string for fast lookup
    hits_by_date: _Dict[str, _List[_Dict[str, _Any]]] = {}
    for hit in transit_hits:
        hits_by_date.setdefault(hit["hit_date"], []).append(hit)

    # PT lord quality (static across current AD)
    pt_lord = (pratyantar.get("pratyantar") or {}).get("lord")
    pt_is_benefic = pt_lord in _BENEFIC_PLANETS if pt_lord else False
    pt_is_malefic = pt_lord in _MALEFIC_PLANETS if pt_lord else False

    # Varshesha
    varshesha = varshaphal.get("varshesha", "")
    varshesha_benefic = varshesha in _BENEFIC_PLANETS
    varshesha_malefic = varshesha in _MALEFIC_PLANETS

    # Refined AV — flag signs with high scores (>= 5 in sarvashtakavarga)
    sarva = refined_av.get("sarvashtakavarga_refined", {})
    strong_signs = {rasi for rasi, score in sarva.items() if score >= 5}

    # Walk 2-week windows
    win_start = start
    while win_start <= reference_date + timedelta(days=window_days):
        win_end = win_start + timedelta(days=14)

        # Collect transit hits in this window
        window_hits = []
        d = win_start
        while d < win_end:
            window_hits.extend(hits_by_date.get(d.isoformat(), []))
            d += timedelta(days=1)

        # Score per life area
        pos_counts: _Dict[str, int] = {a: 0 for a in _ALL_LIFE_AREAS}
        neg_counts: _Dict[str, int] = {a: 0 for a in _ALL_LIFE_AREAS}
        pos_signals: _Dict[str, _List[str]] = {a: [] for a in _ALL_LIFE_AREAS}
        neg_signals: _Dict[str, _List[str]] = {a: [] for a in _ALL_LIFE_AREAS}

        # Signal 1: transit hits
        for hit in window_hits:
            tp = hit["transit_planet"]
            area = hit.get("life_area_hint", "self")
            label = _signal_label(hit)
            asp = hit["aspect_type"]
            if tp in _BENEFIC_PLANETS:
                pos_counts[area] += 1
                pos_signals[area].append(label)
            elif tp in _MALEFIC_PLANETS:
                if asp in _NEGATIVE_ASPECTS:
                    neg_counts[area] += 1
                    neg_signals[area].append(label)
                else:
                    # Malefic conjunction/trine — still challenging
                    neg_counts[area] += 1
                    neg_signals[area].append(label)

        # Signal 2: PT lord
        if pt_is_benefic and pt_lord:
            for area in _PLANET_POSITIVE_AREAS.get(pt_lord, []):
                pos_counts[area] += 1
                pos_signals[area].append(f"Pratyantar {pt_lord} active (benefic for {area})")
        elif pt_is_malefic and pt_lord:
            for area in _PLANET_POSITIVE_AREAS.get(pt_lord, []):
                neg_counts[area] += 1
                neg_signals[area].append(f"Pratyantar {pt_lord} active (malefic for {area})")

        # Signal 3: active yogas
        for yoga in active_yogas:
            y_area = _YOGA_AREA.get(yoga.get("type", "general"), "self")
            label = f"{yoga['name']} firing ({yoga['activation_level']})"
            pos_counts[y_area] += 1
            pos_signals[y_area].append(label)

        # Signal 4: varshaphal varshesha
        if varshesha_benefic:
            for area in _PLANET_POSITIVE_AREAS.get(varshesha, []):
                pos_counts[area] += 1
                pos_signals[area].append(f"Varshaphal: {varshesha} varshesha supports {area}")
        elif varshesha_malefic:
            for area in _PLANET_POSITIVE_AREAS.get(varshesha, []):
                neg_counts[area] += 1
                neg_signals[area].append(f"Varshaphal: {varshesha} varshesha challenges {area}")

        # Signal 5: refined AV — if transit planet's sign has high score
        for hit in window_hits:
            # Use the hit sign from transit degree
            transit_sign_idx = int(hit["transit_degree"] / 30.0) % 12
            transit_sign_names = [
                "Mesham", "Rishabam", "Midhunam", "Kadagam", "Simham", "Kanni",
                "Thulam", "Vrischikam", "Dhanusu", "Makaram", "Kumbham", "Meenam",
            ]
            transit_rasi = transit_sign_names[transit_sign_idx]
            if transit_rasi in strong_signs:
                area = hit.get("life_area_hint", "self")
                pos_counts[area] += 1
                pos_signals[area].append(f"Refined AV strong in {transit_rasi} (score ≥ 5)")

        # Emit windows where confluence >= 3
        for area in _ALL_LIFE_AREAS:
            pc = pos_counts[area]
            nc = neg_counts[area]
            if pc >= 3:
                results.append({
                    "type": f"{area}_peak",
                    "window_start": win_start.isoformat(),
                    "window_end": (win_end - timedelta(days=1)).isoformat(),
                    "confidence": _CONFIDENCE.get(min(pc, 5), "very high"),
                    "signal_count": pc,
                    "signals": pos_signals[area][:6],
                    "life_area": area,
                    "direction": "opportunity",
                })
            if nc >= 3:
                results.append({
                    "type": f"{area}_caution",
                    "window_start": win_start.isoformat(),
                    "window_end": (win_end - timedelta(days=1)).isoformat(),
                    "confidence": _CONFIDENCE.get(min(nc, 5), "very high"),
                    "signal_count": nc,
                    "signals": neg_signals[area][:6],
                    "life_area": area,
                    "direction": "caution",
                })

        win_start += timedelta(days=14)

    results.sort(key=lambda w: w["window_start"])
    return results
