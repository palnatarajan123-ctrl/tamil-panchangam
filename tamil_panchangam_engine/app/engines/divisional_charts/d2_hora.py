"""
D2 Hora Chart - Wealth & Sustenance
Parashara Method

Division: Each sign divided into 2 equal parts of 15° each.
- Odd signs: First 15° = Sun (Leo), Second 15° = Moon (Cancer)
- Even signs: First 15° = Moon (Cancer), Second 15° = Sun (Leo)

This determines the source and nature of wealth.
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

HORA_LORDS = {
    "Sun": "Leo",
    "Moon": "Cancer"
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


def compute_hora_sign(rasi: str, degree_in_rasi: float) -> Dict[str, Any]:
    """
    Compute Hora (D2) sign using Parashara method.
    
    Args:
        rasi: The D1 sign (Rasi)
        degree_in_rasi: Degree within the sign (0-30)
    
    Returns:
        Dict with hora_sign and hora_lord
    """
    canonical_rasi = _normalize_rasi(rasi)
    if canonical_rasi is None:
        raise ValueError(f"Unknown rasi sign: {rasi}")
    
    rasi_index = SIGN_INDEX[canonical_rasi]
    is_odd_sign = (rasi_index % 2 == 0)  # 0-indexed: Aries(0)=odd, Taurus(1)=even
    
    hora_part = 0 if degree_in_rasi < 15.0 else 1  # 0=first half, 1=second half
    
    if is_odd_sign:
        hora_lord = "Sun" if hora_part == 0 else "Moon"
    else:
        hora_lord = "Moon" if hora_part == 0 else "Sun"
    
    hora_sign = HORA_LORDS[hora_lord]
    
    logger.debug(f"D2 Hora: {rasi} {degree_in_rasi:.4f}° -> {hora_sign} ({hora_lord})")
    
    return {
        "sign": hora_sign,
        "lord": hora_lord,
        "longitude": _longitude_to_dms(degree_in_rasi),
    }


def build_hora_chart(ephemeris: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Hora (D2) chart from birth ephemeris.
    
    Returns structured D2 chart data with arc-second precision.
    """
    hora_chart: Dict[str, Any] = {
        "chart": "D2",
        "name": "Hora",
        "purpose": "Wealth & Sustenance",
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
            hora_data = compute_hora_sign(rasi, degree_in_rasi)
            hora_chart["planets"][planet] = hora_data
    
    lagna = ephemeris.get("lagna")
    if isinstance(lagna, dict):
        rasi = lagna.get("rasi")
        lon = _extract_longitude_deg(lagna)
        if rasi and lon is not None:
            degree_in_rasi = lon % 30.0
            hora_data = compute_hora_sign(rasi, degree_in_rasi)
            hora_chart["planets"]["Lagna"] = hora_data
    
    return hora_chart
