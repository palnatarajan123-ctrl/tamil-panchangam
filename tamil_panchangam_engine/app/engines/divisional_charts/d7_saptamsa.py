"""
D7 Saptamsa Chart - Creativity & Children
Parashara Method

Division: Each sign divided into 7 equal parts of 4°17'08.57" each.
- Odd signs: Count from same sign
- Even signs: Count from 7th sign

This chart reveals creative potential and progeny.
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

SAPTAMSA_SPAN = 30.0 / 7  # 4.285714... degrees per division


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


def compute_saptamsa_sign(rasi: str, degree_in_rasi: float) -> Dict[str, Any]:
    """
    Compute Saptamsa (D7) sign using Parashara method.
    
    Args:
        rasi: The D1 sign (Rasi)
        degree_in_rasi: Degree within the sign (0-30)
    
    Returns:
        Dict with saptamsa sign and part
    """
    canonical_rasi = _normalize_rasi(rasi)
    if canonical_rasi is None:
        raise ValueError(f"Unknown rasi sign: {rasi}")
    
    rasi_index = SIGN_INDEX[canonical_rasi]
    is_odd_sign = (rasi_index % 2 == 0)  # 0-indexed
    
    saptamsa_part = int(degree_in_rasi // SAPTAMSA_SPAN)  # 0-6
    saptamsa_part = min(saptamsa_part, 6)  # Clamp to 6 max
    
    if is_odd_sign:
        start_sign = rasi_index
    else:
        start_sign = (rasi_index + 6) % 12  # 7th sign (0-indexed = +6)
    
    saptamsa_index = (start_sign + saptamsa_part) % 12
    saptamsa_sign = SIGNS[saptamsa_index]
    
    logger.debug(f"D7 Saptamsa: {rasi} {degree_in_rasi:.4f}° -> {saptamsa_sign} (part {saptamsa_part + 1})")
    
    return {
        "sign": saptamsa_sign,
        "part": saptamsa_part + 1,
        "longitude": _longitude_to_dms(degree_in_rasi),
    }


def build_saptamsa_chart(ephemeris: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Saptamsa (D7) chart from birth ephemeris.
    
    Returns structured D7 chart data with arc-second precision.
    """
    saptamsa_chart: Dict[str, Any] = {
        "chart": "D7",
        "name": "Saptamsa",
        "purpose": "Creativity & Children",
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
            saptamsa_data = compute_saptamsa_sign(rasi, degree_in_rasi)
            saptamsa_chart["planets"][planet] = saptamsa_data
    
    lagna = ephemeris.get("lagna")
    if isinstance(lagna, dict):
        rasi = lagna.get("rasi")
        lon = _extract_longitude_deg(lagna)
        if rasi and lon is not None:
            degree_in_rasi = lon % 30.0
            saptamsa_data = compute_saptamsa_sign(rasi, degree_in_rasi)
            saptamsa_chart["planets"]["Lagna"] = saptamsa_data
    
    return saptamsa_chart
