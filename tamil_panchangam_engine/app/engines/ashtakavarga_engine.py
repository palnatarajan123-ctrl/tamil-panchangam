"""
Ashtaka Varga Validation Engine - EPIC Signal Expansion

Validates major transits (Saturn/Jupiter) against AV bindu strength.
Provides resistance vs support classification.

Note: This is a simplified implementation. Full AV requires detailed
calculations from all 7 planets + Lagna.
"""
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

RASI_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

RASI_TO_INDEX = {rasi: i for i, rasi in enumerate(RASI_ORDER)}

SATURN_AV_TEMPLATE = {
    "Aries": 3, "Taurus": 4, "Gemini": 5, "Cancer": 2,
    "Leo": 3, "Virgo": 4, "Libra": 5, "Scorpio": 3,
    "Sagittarius": 4, "Capricorn": 5, "Aquarius": 4, "Pisces": 3,
}

JUPITER_AV_TEMPLATE = {
    "Aries": 4, "Taurus": 5, "Gemini": 4, "Cancer": 6,
    "Leo": 4, "Virgo": 4, "Libra": 5, "Scorpio": 5,
    "Sagittarius": 6, "Capricorn": 4, "Aquarius": 4, "Pisces": 5,
}

def _classify_bindu_strength(bindu: int, planet: str) -> str:
    """
    Classify bindu strength.
    
    Average bindus per sign = 28/12 ≈ 2.33 for Saturn, higher for Jupiter
    """
    if planet == "Jupiter":
        if bindu >= 5:
            return "high_support"
        elif bindu >= 4:
            return "moderate_support"
        elif bindu >= 3:
            return "low_support"
        else:
            return "resistance"
    else:
        if bindu >= 4:
            return "high_support"
        elif bindu >= 3:
            return "moderate_support"
        elif bindu >= 2:
            return "low_support"
        else:
            return "resistance"


def compute_ashtakavarga_validation(
    saturn_transit_rasi: str,
    jupiter_transit_rasi: str,
    birth_moon_rasi: Optional[str] = None,
) -> Dict:
    """
    Validate Saturn and Jupiter transits against Ashtaka Varga bindus.
    
    This is a simplified template-based approach.
    Full implementation would require complete birth chart calculations.
    """
    logger.debug(f"DEBUG: Ashtakavarga validating Saturn={saturn_transit_rasi}, Jupiter={jupiter_transit_rasi}")
    
    try:
        saturn_bindu = SATURN_AV_TEMPLATE.get(saturn_transit_rasi, 3)
        jupiter_bindu = JUPITER_AV_TEMPLATE.get(jupiter_transit_rasi, 4)
        
        if birth_moon_rasi:
            moon_idx = RASI_TO_INDEX.get(birth_moon_rasi, 0)
            saturn_idx = RASI_TO_INDEX.get(saturn_transit_rasi, 0)
            jupiter_idx = RASI_TO_INDEX.get(jupiter_transit_rasi, 0)
            
            saturn_house = ((saturn_idx - moon_idx) % 12) + 1
            jupiter_house = ((jupiter_idx - moon_idx) % 12) + 1
            
            if saturn_house in [3, 6, 11]:
                saturn_bindu += 1
            elif saturn_house in [1, 4, 7, 8]:
                saturn_bindu -= 1
            
            if jupiter_house in [2, 5, 7, 9, 11]:
                jupiter_bindu += 1
            elif jupiter_house in [1, 6, 8, 12]:
                jupiter_bindu -= 1
        
        saturn_bindu = max(0, min(saturn_bindu, 8))
        jupiter_bindu = max(0, min(jupiter_bindu, 8))
        
        saturn_strength = _classify_bindu_strength(saturn_bindu, "Saturn")
        jupiter_strength = _classify_bindu_strength(jupiter_bindu, "Jupiter")
        
        overall_support = "balanced"
        if saturn_strength in ["high_support", "moderate_support"] and jupiter_strength in ["high_support", "moderate_support"]:
            overall_support = "strong_support"
        elif saturn_strength == "resistance" or jupiter_strength == "resistance":
            overall_support = "needs_remedies"
        elif saturn_strength in ["high_support", "moderate_support"] or jupiter_strength in ["high_support", "moderate_support"]:
            overall_support = "partial_support"
        
        ashtakavarga = {
            "saturn": {
                "transit_rasi": saturn_transit_rasi,
                "estimated_bindu": saturn_bindu,
                "strength": saturn_strength,
            },
            "jupiter": {
                "transit_rasi": jupiter_transit_rasi,
                "estimated_bindu": jupiter_bindu,
                "strength": jupiter_strength,
            },
            "overall_support": overall_support,
            "note": "Simplified AV estimation based on transit positions",
        }
        
        logger.debug(f"DEBUG: Ashtakavarga: Saturn={saturn_strength} (bindu={saturn_bindu}), Jupiter={jupiter_strength} (bindu={jupiter_bindu})")
        
        return ashtakavarga
        
    except Exception as e:
        logger.error(f"ERROR: Ashtakavarga computation failed: {e}")
        return {
            "saturn": {"strength": "unknown", "error": str(e)},
            "jupiter": {"strength": "unknown", "error": str(e)},
            "overall_support": "unknown",
            "error": str(e),
        }
