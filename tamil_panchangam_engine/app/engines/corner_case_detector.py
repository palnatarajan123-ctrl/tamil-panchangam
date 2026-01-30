"""
Corner Case Detector - Calculation Confidence Assessment

Detects sensitive astrological configurations that may affect prediction certainty:
- Cusp placements (planets near sign boundaries)
- Fast-moving planet sensitivity
- Birth time uncertainty indicators
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

FAST_MOVING_PLANETS = {"Moon", "Mercury", "Venus"}
CUSP_THRESHOLD_DEGREES = 1.0  # Within 1° of sign boundary


def detect_cusp_placements(ephemeris: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Detect planets near sign boundaries (cusps).
    
    Returns list of planets with cusp sensitivity.
    """
    cusp_cases = []
    
    planets = ephemeris.get("planets", {})
    for planet, data in planets.items():
        if not isinstance(data, dict):
            continue
        
        longitude = data.get("longitude_deg", 0)
        degree_in_sign = longitude % 30.0
        
        near_start = degree_in_sign < CUSP_THRESHOLD_DEGREES
        near_end = degree_in_sign > (30.0 - CUSP_THRESHOLD_DEGREES)
        
        if near_start or near_end:
            cusp_cases.append({
                "planet": planet,
                "degree_in_sign": round(degree_in_sign, 4),
                "position": "start" if near_start else "end",
                "is_fast_moving": planet in FAST_MOVING_PLANETS,
            })
    
    lagna = ephemeris.get("lagna", {})
    if isinstance(lagna, dict):
        lagna_lon = lagna.get("longitude_deg", 0)
        lagna_degree = lagna_lon % 30.0
        
        if lagna_degree < CUSP_THRESHOLD_DEGREES or lagna_degree > (30.0 - CUSP_THRESHOLD_DEGREES):
            cusp_cases.append({
                "planet": "Lagna",
                "degree_in_sign": round(lagna_degree, 4),
                "position": "start" if lagna_degree < CUSP_THRESHOLD_DEGREES else "end",
                "is_fast_moving": True,  # Lagna moves ~1° every 4 minutes
            })
    
    return cusp_cases


def assess_calculation_confidence(
    ephemeris: Dict[str, Any],
    birth_time_precision: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Assess overall calculation confidence based on corner cases.
    
    Args:
        ephemeris: Birth chart ephemeris data
        birth_time_precision: Known precision of birth time (e.g., "minute", "hour")
    
    Returns:
        Calculation confidence assessment
    """
    cusp_cases = detect_cusp_placements(ephemeris)
    
    fast_moving_cusps = [c for c in cusp_cases if c.get("is_fast_moving")]
    lagna_cusp = any(c["planet"] == "Lagna" for c in cusp_cases)
    
    if lagna_cusp or len(fast_moving_cusps) >= 2:
        level = "sensitive"
        reason = "Multiple fast-moving planets or Lagna near sign boundaries"
    elif len(cusp_cases) >= 1:
        level = "medium"
        reason = f"{len(cusp_cases)} planet(s) near sign boundary"
    else:
        level = "high"
        reason = "All placements well within sign boundaries"
    
    if birth_time_precision == "hour":
        level = "sensitive"
        reason = "Birth time known only to the hour; Lagna may vary"
    
    return {
        "level": level,
        "reason": reason,
        "cusp_cases": cusp_cases,
        "lagna_sensitive": lagna_cusp,
        "fast_moving_cusps": len(fast_moving_cusps),
    }


def add_confidence_to_prediction(
    prediction: Dict[str, Any],
    ephemeris: Dict[str, Any],
    birth_time_precision: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Add calculation_confidence to prediction output.
    
    This is read-only and never affects scores.
    """
    confidence = assess_calculation_confidence(ephemeris, birth_time_precision)
    
    prediction["calculation_confidence"] = {
        "level": confidence["level"],
        "reason": confidence["reason"],
    }
    
    return prediction
