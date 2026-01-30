# app/llm/payload_builder.py
"""
LLM Payload Builder v1.0

Builds minimal "meaning-layer" payloads for LLM interpretation.
NEVER passes raw astrology, full envelope, or full synthesis.

Token Guardrails (HARD LIMITS - no exceptions):
- Weekly:  max 900 prompt tokens, 500 completion, 1500 total
- Monthly: max 1400 prompt tokens, 900 completion, 2500 total
- Yearly:  max 2200 prompt tokens, 1200 completion, 4500 total
"""

import json
import logging
from typing import Dict, Any, List, Literal

logger = logging.getLogger(__name__)

MAX_PROMPT_TOKENS = {
    "weekly": 600,
    "monthly": 900,
    "yearly": 1500
}

MAX_COMPLETION_TOKENS = {
    "weekly": 700,
    "monthly": 1000,
    "yearly": 1400
}

MAX_TOTAL_TOKENS = {
    "weekly": 1400,
    "monthly": 2100,
    "yearly": 3200
}

LIFE_AREA_LIMITS = {
    "weekly": {"max_areas": 4, "signals_per_area": 1},
    "monthly": {"max_areas": 5, "signals_per_area": 2},
    "yearly": {"max_areas": 7, "signals_per_area": 3}
}


def estimate_tokens(text: str) -> int:
    """Estimate tokens using chars/4 heuristic (conservative)."""
    return len(text) // 4


def _trim_signal(signal: Dict[str, Any]) -> Dict[str, str]:
    """Extract only summary and rationale from a signal."""
    key = signal.get("key", "")
    rationale = signal.get("rationale", "")
    
    summary = key.replace("_", " ").title()[:40]
    if len(rationale) > 80:
        rationale = rationale[:77] + "..."
    
    return {
        "summary": summary,
        "rationale": rationale
    }


def _score_to_strength(score: int) -> str:
    """Convert numeric score to strength label."""
    if score >= 65:
        return "supportive"
    elif score >= 45:
        return "neutral"
    else:
        return "watchful"


def build_llm_payload(
    *,
    period_type: Literal["weekly", "monthly", "yearly"],
    period_label: str,
    lagna: str,
    moon_nakshatra: str,
    active_dasha: Dict[str, str],
    life_area_scores: Dict[str, int],
    top_signals_by_life_area: Dict[str, List[Dict[str, Any]]],
    explainability_mode: str = "standard"
) -> Dict[str, Any]:
    """
    Build a minimal LLM payload with ONLY meaning-layer data.
    
    Args:
        period_type: "weekly" | "monthly" | "yearly"
        period_label: Human-readable period (e.g., "Week 5, 2026")
        lagna: Lagna rasi label (e.g., "Capricorn")
        moon_nakshatra: Moon's nakshatra (e.g., "Rohini")
        active_dasha: {"mahadasha": "Saturn", "antardasha": "Venus"}
        life_area_scores: {"career": 54, "finance": 56, ...}
        top_signals_by_life_area: {"career": [signal1, signal2], ...}
        explainability_mode: "minimal" | "standard" | "full"
        
    Returns:
        Trimmed payload dict ready for LLM
    """
    limits = LIFE_AREA_LIMITS.get(period_type, LIFE_AREA_LIMITS["monthly"])
    max_areas = limits["max_areas"]
    signals_per_area = limits["signals_per_area"]
    
    sorted_areas = sorted(
        life_area_scores.items(),
        key=lambda x: abs(x[1] - 50),
        reverse=True
    )[:max_areas]
    
    life_areas = []
    for area_name, score in sorted_areas:
        signals = top_signals_by_life_area.get(area_name, [])[:signals_per_area]
        trimmed_signals = [_trim_signal(s) for s in signals]
        
        life_areas.append({
            "name": area_name,
            "score": score,
            "strength": _score_to_strength(score),
            "signals": trimmed_signals
        })
    
    payload = {
        "context": {
            "period_type": period_type,
            "period_label": period_label,
            "lagna": lagna,
            "moon_nakshatra": moon_nakshatra,
            "active_dasha": {
                "mahadasha": active_dasha.get("mahadasha", "Unknown"),
                "antardasha": active_dasha.get("antardasha", "Unknown")
            },
            "explainability_mode": explainability_mode
        },
        "life_areas": life_areas
    }
    
    return payload


def validate_payload_size(
    payload: Dict[str, Any],
    period_type: str
) -> tuple[bool, str, int]:
    """
    Validate payload is within token limits.
    
    Returns:
        (is_valid, reason, estimated_tokens)
    """
    payload_json = json.dumps(payload)
    estimated_prompt = estimate_tokens(payload_json)
    
    max_prompt = MAX_PROMPT_TOKENS.get(period_type, 1400)
    max_completion = MAX_COMPLETION_TOKENS.get(period_type, 900)
    max_total = MAX_TOTAL_TOKENS.get(period_type, 2500)
    
    logger.info(
        f"LLM payload size: period_type={period_type}, "
        f"chars={len(payload_json)}, estimated_tokens={estimated_prompt}, "
        f"life_areas={len(payload.get('life_areas', []))}"
    )
    
    if estimated_prompt > max_prompt:
        return False, "prompt_too_large", estimated_prompt
    
    if estimated_prompt + max_completion > max_total:
        return False, "token_budget_exceeded", estimated_prompt
    
    return True, "ok", estimated_prompt


def extract_payload_inputs(
    envelope: Dict[str, Any],
    synthesis: Dict[str, Any],
    period_type: str,
    period_key: str
) -> Dict[str, Any]:
    """
    Extract the minimal inputs needed for build_llm_payload from envelope and synthesis.
    
    This is the ONLY place where we touch envelope/synthesis to extract labels.
    """
    lagna = envelope.get("lagna", {})
    nakshatra = envelope.get("nakshatra_context", {})
    dasha = envelope.get("dasha_context", {})
    
    lagna_label = lagna.get("label", lagna.get("rasi", "Unknown"))
    moon_nakshatra = nakshatra.get("janma_nakshatra", "Unknown")
    
    active_dasha = {
        "mahadasha": dasha.get("maha_lord", "Unknown"),
        "antardasha": dasha.get("antar_lord", "Unknown")
    }
    
    life_area_scores = {}
    top_signals_by_life_area = {}
    
    synthesis_life_areas = synthesis.get("life_areas", {})
    for area_name, area_data in synthesis_life_areas.items():
        if isinstance(area_data, dict):
            life_area_scores[area_name] = area_data.get("score", 50)
            top_signals_by_life_area[area_name] = area_data.get("top_signals", [])
    
    period_label = _format_period_label(period_type, period_key)
    
    return {
        "period_type": period_type,
        "period_label": period_label,
        "lagna": lagna_label,
        "moon_nakshatra": moon_nakshatra,
        "active_dasha": active_dasha,
        "life_area_scores": life_area_scores,
        "top_signals_by_life_area": top_signals_by_life_area
    }


def _format_period_label(period_type: str, period_key: str) -> str:
    """Format period key into human-readable label."""
    if period_type == "weekly" and "-W" in period_key:
        parts = period_key.split("-W")
        if len(parts) == 2:
            return f"Week {parts[1]}, {parts[0]}"
    elif period_type == "monthly" and "-" in period_key:
        parts = period_key.split("-")
        if len(parts) == 2:
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            month_idx = int(parts[1]) - 1
            if 0 <= month_idx < 12:
                return f"{months[month_idx]} {parts[0]}"
    elif period_type == "yearly":
        return period_key
    
    return period_key
