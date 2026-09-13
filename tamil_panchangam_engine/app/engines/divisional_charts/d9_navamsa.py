"""
D9 Navamsa Chart - Dharma & Maturity
Parashara Method

THE canonical D9 implementation (2026-09-13 consolidation). A second,
independent implementation used to exist at app.engines.navamsa_engine
-- this file's own docstring used to (incorrectly) describe itself as
"a wrapper around" it, but never actually called it; both were fully
separate reimplementations with different output shapes
("navamsa_sign" here vs "sign" there), which caused
prediction_envelope.py's d9_context to silently read the wrong key
and made the classical Vargottama (same D1/D9 sign) strength bonus in
d9_strength_engine.py never fire, for any chart. The formula itself
was never wrong -- verified identical output across real charts, and
independently confirmed against Parashara's movable/fixed/dual-sign
Navamsa rule (Brihat Parashara Hora Sastra) before deleting the other
copy. See CLAUDE.md's 2026-09-13 entry.

Division: Each sign divided into 9 equal parts of 3°20' each.
"""

from typing import Any, Dict, Optional
import logging

from app.utils.rasi_utils import to_english_rasi

logger = logging.getLogger(__name__)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}

# Transliteration variants real chart data has never actually used
# (checked live production data 2026-09-13) but kept defensively, since
# this is the one thing the old duplicate copy of this table handled
# that app.utils.rasi_utils doesn't -- see _normalize_rasi().
_EXTRA_SPELLING_VARIANTS = {
    "katakam": "Cancer",
    "simham": "Leo",
    "vrischigam": "Scorpio", "viruchigam": "Scorpio", "viruchikam": "Scorpio",
    "dhanus": "Sagittarius", "dhanush": "Sagittarius",
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
    """
    Normalize a rasi name (Tamil, English, or a known transliteration
    variant) to canonical English. Delegates the canonical Tamil<->English
    mapping to app.utils.rasi_utils.to_english_rasi() -- the single
    source of truth for that conversion (see CLAUDE.md's 2026-09-12
    rasi-name bug fix) -- rather than maintaining a second copy of that
    table here. _EXTRA_SPELLING_VARIANTS covers only transliteration
    variants to_english_rasi() doesn't.
    """
    if not rasi or not isinstance(rasi, str):
        return None
    stripped = rasi.strip()
    english = to_english_rasi(stripped)
    if english in SIGN_INDEX:
        return english
    variant = _EXTRA_SPELLING_VARIANTS.get(stripped.casefold())
    if variant:
        return variant
    for sign in SIGNS:
        if stripped.casefold() == sign.casefold():
            return sign
    return None


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


def to_legacy_shape(navamsa_chart: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Convert this engine's native output (per-planet {"sign", "part",
    "longitude", "dignity"}) to the shape the old, now-deleted
    navamsa_engine.py used to produce ({"navamsa_sign", "dignity"}),
    for the one remaining consumer (data_loader.py's PDF generation,
    via base_chart.py's payload["charts"]["D9"]) that still expects it.

    Excludes "Lagna" -- navamsa_engine.py never computed a Lagna entry,
    and payload["charts"]["D9"] consumers were never built to expect
    one; keeping this conversion behaviorally identical to what that
    payload key used to contain, not silently adding a new field to it.
    """
    return {
        planet: {"navamsa_sign": data.get("sign", ""), "dignity": data.get("dignity", "neutral")}
        for planet, data in navamsa_chart.get("planets", {}).items()
        if planet != "Lagna"
    }
