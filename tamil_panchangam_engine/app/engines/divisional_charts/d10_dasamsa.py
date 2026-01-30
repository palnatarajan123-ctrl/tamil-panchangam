"""
D10 Dasamsa Chart - Career & Authority
Parashara Method

Division: Each sign divided into 10 equal parts of 3° each.
- Odd signs: Count from same sign
- Even signs: Count from 9th sign

This chart reveals career, profession, and public standing.
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

DASAMSA_SPAN = 3.0  # 3 degrees per division


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


def compute_dasamsa_sign(rasi: str, degree_in_rasi: float) -> Dict[str, Any]:
    """
    Compute Dasamsa (D10) sign using Parashara method.
    
    Args:
        rasi: The D1 sign (Rasi)
        degree_in_rasi: Degree within the sign (0-30)
    
    Returns:
        Dict with dasamsa sign and part
    """
    canonical_rasi = _normalize_rasi(rasi)
    if canonical_rasi is None:
        raise ValueError(f"Unknown rasi sign: {rasi}")
    
    rasi_index = SIGN_INDEX[canonical_rasi]
    is_odd_sign = (rasi_index % 2 == 0)  # 0-indexed
    
    dasamsa_part = int(degree_in_rasi // DASAMSA_SPAN)  # 0-9
    dasamsa_part = min(dasamsa_part, 9)  # Clamp to 9 max
    
    if is_odd_sign:
        start_sign = rasi_index
    else:
        start_sign = (rasi_index + 8) % 12  # 9th sign (0-indexed = +8)
    
    dasamsa_index = (start_sign + dasamsa_part) % 12
    dasamsa_sign = SIGNS[dasamsa_index]
    
    logger.debug(f"D10 Dasamsa: {rasi} {degree_in_rasi:.4f}° -> {dasamsa_sign} (part {dasamsa_part + 1})")
    
    return {
        "sign": dasamsa_sign,
        "part": dasamsa_part + 1,
        "longitude": _longitude_to_dms(degree_in_rasi),
    }


def build_dasamsa_chart(ephemeris: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Dasamsa (D10) chart from birth ephemeris.
    
    Returns structured D10 chart data with arc-second precision.
    """
    dasamsa_chart: Dict[str, Any] = {
        "chart": "D10",
        "name": "Dasamsa",
        "purpose": "Career & Authority",
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
            dasamsa_data = compute_dasamsa_sign(rasi, degree_in_rasi)
            dasamsa_chart["planets"][planet] = dasamsa_data
    
    lagna = ephemeris.get("lagna")
    if isinstance(lagna, dict):
        rasi = lagna.get("rasi")
        lon = _extract_longitude_deg(lagna)
        if rasi and lon is not None:
            degree_in_rasi = lon % 30.0
            dasamsa_data = compute_dasamsa_sign(rasi, degree_in_rasi)
            dasamsa_chart["planets"]["Lagna"] = dasamsa_data
    
    return dasamsa_chart
