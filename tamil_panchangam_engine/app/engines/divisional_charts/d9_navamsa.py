"""
D9 Navamsa Chart - Dharma & Maturity
Parashara Method

This is a wrapper around the existing navamsa_engine.py for consistency
with the divisional_charts module structure.

Division: Each sign divided into 9 equal parts of 3°20' each.
"""

from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}

RASI_NORMALIZATION = {
    "mesham": "Aries", "rishabam": "Taurus", "mithunam": "Gemini",
    "kadakam": "Cancer", "katakam": "Cancer",
    "simmam": "Leo", "simham": "Leo",
    "kanni": "Virgo", "thulam": "Libra",
    "vrischikam": "Scorpio", "vrischigam": "Scorpio",
    "viruchigam": "Scorpio", "viruchikam": "Scorpio",
    "dhanusu": "Sagittarius", "dhanus": "Sagittarius", "dhanush": "Sagittarius",
    "makaram": "Capricorn", "kumbham": "Aquarius", "meenam": "Pisces",
    "aries": "Aries", "taurus": "Taurus", "gemini": "Gemini",
    "cancer": "Cancer", "leo": "Leo", "virgo": "Virgo",
    "libra": "Libra", "scorpio": "Scorpio", "sagittarius": "Sagittarius",
    "capricorn": "Capricorn", "aquarius": "Aquarius", "pisces": "Pisces",
}

NAVAMSA_SPAN = 30.0 / 9  # 3.333... degrees per division

EXALTATION_SIGNS = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
    "Saturn": "Libra",
}

DEBILITATION_SIGNS = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
    "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
    "Saturn": "Aries",
}


def _normalize_rasi(rasi: Any) -> Optional[str]:
    if not rasi or not isinstance(rasi, str):
        return None
    key = rasi.strip().casefold()
    return RASI_NORMALIZATION.get(key)


def _extract_longitude_deg(data: Dict[str, Any]) -> Optional[float]:
    lon = data.get("longitude_deg")
    if isinstance(lon, (int, float)):
        return float(lon)
    deg = data.get("degree")
    if isinstance(deg, (int, float)):
        return float(deg)
    return None


def _longitude_to_dms(longitude: float) -> str:
    """Convert longitude to dd:mm:ss format."""
    degrees = int(longitude)
    remainder = (longitude - degrees) * 60
    minutes = int(remainder)
    seconds = int((remainder - minutes) * 60)
    return f"{degrees:02d}:{minutes:02d}:{seconds:02d}"


def _assess_dignity(planet: str, navamsa_sign: str) -> str:
    if EXALTATION_SIGNS.get(planet) == navamsa_sign:
        return "exalted"
    if DEBILITATION_SIGNS.get(planet) == navamsa_sign:
        return "debilitated"
    return "neutral"


def compute_navamsa_sign(rasi: str, degree_in_rasi: float) -> Dict[str, Any]:
    """
    Compute Navamsa (D9) sign using Parashara method.
    
    Args:
        rasi: The D1 sign (Rasi)
        degree_in_rasi: Degree within the sign (0-30)
    
    Returns:
        Dict with navamsa sign and part
    """
    canonical_rasi = _normalize_rasi(rasi)
    if canonical_rasi is None:
        raise ValueError(f"Unknown rasi sign: {rasi}")
    
    rasi_index = SIGN_INDEX[canonical_rasi]
    navamsa_part = int(degree_in_rasi // NAVAMSA_SPAN)  # 0-8
    navamsa_part = min(navamsa_part, 8)  # Clamp to 8 max
    
    navamsa_index = (rasi_index * 9 + navamsa_part) % 12
    navamsa_sign = SIGNS[navamsa_index]
    
    logger.debug(f"D9 Navamsa: {rasi} {degree_in_rasi:.4f}° -> {navamsa_sign} (part {navamsa_part + 1})")
    
    return {
        "sign": navamsa_sign,
        "part": navamsa_part + 1,
        "longitude": _longitude_to_dms(degree_in_rasi),
    }


def build_navamsa_chart(ephemeris: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Navamsa (D9) chart from birth ephemeris.
    
    Returns structured D9 chart data with arc-second precision.
    """
    navamsa_chart: Dict[str, Any] = {
        "chart": "D9",
        "name": "Navamsa",
        "purpose": "Dharma & Maturity",
        "division_method": "parashara",
        "precision": "arc-second",
        "planets": {}
    }
    
    planets = ephemeris.get("planets", {})
    if isinstance(planets, dict):
        for planet, data in planets.items():
            if not isinstance(data, dict):
                continue
            
            rasi = data.get("rasi")
            lon = _extract_longitude_deg(data)
            if not rasi or lon is None:
                continue
            
            degree_in_rasi = lon % 30.0
            navamsa_data = compute_navamsa_sign(rasi, degree_in_rasi)
            dignity = _assess_dignity(planet, navamsa_data["sign"])
            navamsa_data["dignity"] = dignity
            navamsa_chart["planets"][planet] = navamsa_data
    
    lagna = ephemeris.get("lagna")
    if isinstance(lagna, dict):
        rasi = lagna.get("rasi")
        lon = _extract_longitude_deg(lagna)
        if rasi and lon is not None:
            degree_in_rasi = lon % 30.0
            navamsa_data = compute_navamsa_sign(rasi, degree_in_rasi)
            navamsa_chart["planets"]["Lagna"] = navamsa_data
    
    return navamsa_chart
