"""
Explainability Filter v1.1

Post-processing filter to control interpretation verbosity.
Does NOT regenerate interpretation - only controls visibility via flags.

Modes:
- minimal: summary only (full content retained, visibility flags added)
- standard: summary + explanation (full content retained)
- full: complete schema-compliant output (no changes)

The filter adds visibility metadata without modifying content to maintain
schema validity (minLength, required fields, etc. remain satisfied).
"""

from typing import Dict, Any, Literal
from copy import deepcopy


ExplainabilityLevel = Literal["minimal", "standard", "full"]


def apply_explainability(
    interpretation: Dict[str, Any],
    level: ExplainabilityLevel = "full"
) -> Dict[str, Any]:
    """
    Apply explainability filter to AI interpretation output.
    
    This is a post-processing filter that controls how much detail
    should be visible in the interpretation via visibility flags.
    It does NOT modify or delete content to maintain schema validity.
    
    Args:
        interpretation: Complete AI interpretation output (schema-valid)
        level: Explainability level
            - "minimal": summary only (visibility flags hide details)
            - "standard": summary + explanation (hide attribution)
            - "full": complete output (no changes)
            
    Returns:
        Interpretation with _visibility metadata (still schema-valid)
    """
    if level == "full":
        result = deepcopy(interpretation)
        result["_visibility"] = {
            "level": "full",
            "show_dominant_forces": True,
            "show_timing_guidance": True,
            "show_deeper_explanation": True,
            "show_attribution": True,
            "show_signals_used": True
        }
        return result
    
    result = deepcopy(interpretation)
    
    if level == "minimal":
        result["_visibility"] = {
            "level": "minimal",
            "show_dominant_forces": False,
            "show_timing_guidance": False,
            "show_deeper_explanation": False,
            "show_attribution": False,
            "show_signals_used": False
        }
    elif level == "standard":
        result["_visibility"] = {
            "level": "standard",
            "show_dominant_forces": True,
            "show_timing_guidance": True,
            "show_deeper_explanation": True,
            "show_attribution": False,  # Hide attribution for standard (per docstring)
            "show_signals_used": False
        }
    
    return result


def get_visible_content(
    interpretation: Dict[str, Any],
    level: ExplainabilityLevel = "full"
) -> Dict[str, Any]:
    """
    Get a view of interpretation with only visible content for the given level.
    
    Unlike apply_explainability which adds flags, this returns a filtered view
    suitable for display. Note: This view may not pass schema validation.
    
    Use this for UI rendering, not for storage or transmission.
    
    Args:
        interpretation: Complete AI interpretation output
        level: Explainability level
        
    Returns:
        Filtered view for display (may not be schema-valid)
    """
    result = deepcopy(interpretation)
    
    if level == "full":
        return result
    
    window = result.get("window_summary", {})
    
    if level == "minimal":
        result["window_summary"] = {
            "momentum": window.get("momentum", "transition"),
            "momentum_description": window.get("momentum_description", ""),
            "overview": window.get("overview", ""),
            "dominant_forces": [],
            "outcome_mode": window.get("outcome_mode", "effort"),
        }
        
        for area, data in result.get("life_areas", {}).items():
            result["life_areas"][area] = {
                "score": data.get("score", 50),
                "outlook": data.get("outlook", "neutral"),
                "summary": data.get("summary", ""),
                "deeper_explanation": data.get("deeper_explanation", ""),
                "attribution": {
                    "planets": [],
                    "dasha": "",
                    "engines": [],
                    "signals_used": []
                },
                "word_count": data.get("word_count", 0)
            }
            result["life_areas"][area]["_hidden"] = ["deeper_explanation", "attribution"]
    
    elif level == "standard":
        for area, data in result.get("life_areas", {}).items():
            attr = data.get("attribution", {})
            result["life_areas"][area]["attribution"] = {
                "planets": attr.get("planets", []),
                "dasha": attr.get("dasha", ""),
                "engines": attr.get("engines", []),
                "signals_used": []
            }
            result["life_areas"][area]["_hidden"] = ["signals_used"]
    
    return result


def get_explainability_levels() -> Dict[str, str]:
    """Return available explainability levels with descriptions."""
    return {
        "minimal": "Summary only - brief overview without technical details",
        "standard": "Summary + explanation - readable interpretation without signal attribution",
        "full": "Complete output - full interpretation with astrological attribution"
    }
