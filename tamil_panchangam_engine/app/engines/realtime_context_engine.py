"""
Real-time Astrological Context Engine

Computes current-moment astrological context for a birth chart:
- Transit/Gochara positions (Jupiter, Saturn, Rahu-Ketu)
- Current Moon Nakshatra and Tara Bala
- Pancha Pakshi status
- Chandra Gati (Moon movement quality)

This engine is READ-ONLY and does not modify any stored data.
It's designed for on-the-fly display context, separate from prediction caching.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from app.engines.gochara_engine import compute_gochara
from app.engines.nakshatra_engine import compute_nakshatra_context
from app.engines.pancha_pakshi import get_birth_pakshi, get_daily_pakshi_guidance, PAKSHI_NATURE
from app.engines.moon_transit_engine import compute_chandra_gati

logger = logging.getLogger(__name__)


def compute_realtime_context(
    birth_moon_longitude: float,
    birth_moon_rasi: str,
    birth_nakshatra: str,
    birth_lagna_rasi: Optional[str] = None,
    latitude: float = 13.0827,
    longitude: float = 80.2707,
    reference_time_utc: Optional[datetime] = None,
) -> Dict:
    """
    Compute real-time astrological context for display.
    
    Args:
        birth_moon_longitude: Natal Moon longitude in degrees
        birth_moon_rasi: Natal Moon's Rasi (e.g., "Aries")
        birth_nakshatra: Natal Nakshatra name (e.g., "Ashwini")
        birth_lagna_rasi: Optional natal Lagna Rasi
        latitude: Location latitude for calculations
        longitude: Location longitude for calculations
        reference_time_utc: Override time (defaults to now)
    
    Returns:
        Dict with transit_context, nakshatra_timing_context, pakshi_context
    """
    now_utc = reference_time_utc or datetime.now(timezone.utc)
    
    logger.debug(f"Computing realtime context for {now_utc}")
    logger.debug(f"Inputs: moon_long={birth_moon_longitude}, moon_rasi={birth_moon_rasi}, nakshatra={birth_nakshatra}, lagna={birth_lagna_rasi}")
    
    result = {
        "computed_at": now_utc.isoformat(),
        "transit_context": {},
        "nakshatra_timing_context": {},
        "pakshi_context": {},
    }
    
    try:
        logger.debug(f"Calling gochara with natal_moon_rasi={birth_moon_rasi}, natal_lagna_rasi={birth_lagna_rasi}")
        gochara = compute_gochara(
            reference_date_utc=now_utc,
            latitude=latitude,
            longitude=longitude,
            natal_moon_rasi=birth_moon_rasi,
            natal_lagna_rasi=birth_lagna_rasi,
        )
        logger.debug(f"Gochara result: {gochara}")
        
        jupiter_transit = gochara.get("jupiter", {})
        saturn_transit = gochara.get("saturn", {})
        rahu_ketu = gochara.get("rahu_ketu", {})
        
        result["transit_context"] = {
            "jupiter_transit": _format_transit(jupiter_transit, "Jupiter"),
            "saturn_transit": _format_saturn_transit(saturn_transit),
            "rahu_ketu_axis": _format_rahu_ketu(rahu_ketu),
        }
        
    except Exception as e:
        logger.warning(f"Gochara computation failed: {e}", exc_info=True)
        result["transit_context"] = {
            "jupiter_transit": None,
            "saturn_transit": None,
            "rahu_ketu_axis": None,
        }
    
    try:
        nakshatra_ctx = compute_nakshatra_context(
            reference_date_utc=now_utc,
            birth_moon_longitude=birth_moon_longitude,
            latitude=latitude,
            longitude=longitude,
        )
        
        current_nak = nakshatra_ctx.get("current_nakshatra", "")
        tara_name = nakshatra_ctx.get("tara_name", "")
        quality = nakshatra_ctx.get("quality", "neutral")
        
        tara_bala_display = f"{tara_name}" if tara_name else None
        if tara_bala_display and quality:
            quality_label = {
                "favorable": "Favorable",
                "challenging": "Caution",
                "neutral": "Neutral",
            }.get(quality, "")
            if quality_label:
                tara_bala_display = f"{tara_name} ({quality_label})"
        
        favorable_window = None
        if quality == "favorable":
            favorable_window = "Yes - Auspicious period"
        elif quality == "challenging":
            favorable_window = "Caution advised"
        else:
            favorable_window = "Neutral"
        
        result["nakshatra_timing_context"] = {
            "current_moon_nakshatra": current_nak,
            "tara_bala": tara_bala_display,
            "chandra_gati": None,
            "favorable_window": favorable_window,
        }
        
    except Exception as e:
        logger.warning(f"Nakshatra computation failed: {e}")
        result["nakshatra_timing_context"] = {
            "current_moon_nakshatra": None,
            "tara_bala": None,
            "chandra_gati": None,
            "favorable_window": None,
        }
    
    try:
        chandra_gati = compute_chandra_gati(
            year=now_utc.year,
            month=now_utc.month,
            natal_moon_rasi=birth_moon_rasi,
            latitude=latitude,
            longitude=longitude,
        )
        dominant_moods = chandra_gati.get("dominant_moods", [])
        if dominant_moods:
            result["nakshatra_timing_context"]["chandra_gati"] = ", ".join(dominant_moods[:2]).capitalize() if len(dominant_moods) > 1 else dominant_moods[0].capitalize()
        
    except Exception as e:
        logger.warning(f"Chandra Gati computation failed: {e}")
    
    try:
        birth_pakshi_data = get_birth_pakshi(birth_nakshatra)
        pakshi_name = birth_pakshi_data.get("pakshi", "")
        
        daily_guidance = get_daily_pakshi_guidance(
            birth_pakshi=pakshi_name,
            date_local=now_utc,
        )
        
        pakshi_nature = PAKSHI_NATURE.get(pakshi_name, "")
        
        result["pakshi_context"] = {
            "dominant_pakshi": pakshi_name,
            "activity_phase": pakshi_nature,
        }
        
    except Exception as e:
        logger.warning(f"Pakshi computation failed: {e}")
        result["pakshi_context"] = {
            "dominant_pakshi": None,
            "activity_phase": None,
        }
    
    return result


def _format_transit(transit: Dict, planet: str) -> Optional[str]:
    """Format transit data for display."""
    if not transit:
        return None
    
    rasi = transit.get("transit_rasi", "") or transit.get("rasi", "")
    house = transit.get("from_moon_house", "") or transit.get("house_from_moon", "")
    effect = transit.get("effect", "neutral")
    
    if rasi and house:
        effect_label = {
            "favorable": "Favorable",
            "challenging": "Challenging",
            "neutral": "Neutral",
        }.get(effect, "Neutral")
        
        return f"{rasi} (H{house}) - {effect_label}"
    
    return None


def _format_saturn_transit(transit: Dict) -> Optional[str]:
    """Format Saturn transit with Sade Sati phase if applicable."""
    if not transit:
        return None
    
    rasi = transit.get("transit_rasi", "") or transit.get("rasi", "")
    house = transit.get("from_moon_house", "") or transit.get("house_from_moon", "")
    phase = transit.get("phase", "neutral")
    
    if rasi and house:
        special_phases = {
            "janma_sani": "Janma Sani",
            "ashtama_sani": "Ashtama Sani",
            "kantaka_sani": "Kantaka Sani",
        }
        
        if phase in special_phases:
            return f"{rasi} (H{house}) - {special_phases[phase]}"
        
        return f"{rasi} (H{house})"
    
    return None


def _format_rahu_ketu(axis: Dict) -> Optional[str]:
    """Format Rahu-Ketu axis for display."""
    if not axis:
        return None
    
    rahu_house = axis.get("rahu_from_moon_house", "") or axis.get("rahu_house", "")
    ketu_house = axis.get("ketu_from_moon_house", "") or axis.get("ketu_house", "")
    theme = axis.get("theme", "")
    
    if rahu_house and ketu_house:
        formatted = f"Rahu H{rahu_house} / Ketu H{ketu_house}"
        if theme:
            formatted += f" ({theme})"
        return formatted
    
    return None


def _format_tara_bala(tara: Dict) -> Optional[str]:
    """Format Tara Bala for display."""
    if not tara:
        return None
    
    name = tara.get("tara_name", "")
    quality = tara.get("quality", "neutral")
    
    if name:
        quality_emoji = {
            "favorable": "Favorable",
            "challenging": "Caution",
            "neutral": "Neutral",
        }.get(quality, "")
        
        return f"{name} ({quality_emoji})"
    
    return None


def _compute_favorable_window(tara: Dict) -> Optional[str]:
    """Determine if current window is favorable."""
    if not tara:
        return None
    
    quality = tara.get("quality", "neutral")
    
    if quality == "favorable":
        return "Yes - Auspicious period"
    elif quality == "challenging":
        return "Caution advised"
    else:
        return "Neutral"
