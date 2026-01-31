"""
Interpretive Hints Generator v1.0

Generates deterministic, linguistically-rich hints for signals.
These hints provide semantic material for LLM expansion without
recomputing any astrology logic.

Rules:
- Fully deterministic based on engine, polarity, strength
- No astrology calculations
- Cacheable and reproducible
"""

from typing import Optional


def generate_interpretive_hint(
    engine: str,
    polarity: str,
    strength: float,
    life_area: Optional[str] = None
) -> str:
    """
    Generate an interpretive hint for a signal.
    
    Args:
        engine: Signal source (e.g., 'gochara', 'drishti', 'ashtakavarga')
        polarity: 'pos', 'neg', 'mix', or 'positive', 'negative', 'mixed'
        strength: Signal strength (0.0 to 1.0)
        life_area: Optional life area context
        
    Returns:
        A plain-English interpretive hint string
    """
    engine_lower = engine.lower().replace("_", " ")
    is_positive = polarity in ("pos", "positive")
    is_negative = polarity in ("neg", "negative")
    is_strong = strength >= 0.6
    is_moderate = 0.4 <= strength < 0.6
    
    if "gochara" in engine_lower:
        if is_positive:
            if is_strong:
                return "supports progress through favorable timing and external circumstances aligning more easily"
            return "offers supportive timing that gently assists forward movement"
        elif is_negative:
            if is_strong:
                return "introduces delays or friction due to less supportive external conditions"
            return "creates minor timing challenges that require patience"
        else:
            return "brings mixed timing influences that may shift between supportive and challenging"
    
    if "drishti" in engine_lower:
        if is_positive:
            if is_strong:
                return "enhances focus and clarity through reinforcing influences"
            return "provides gentle support and protective oversight"
        elif is_negative:
            if is_strong:
                return "creates pressure points that require careful navigation and restraint"
            return "introduces subtle tensions that call for measured responses"
        else:
            return "brings dynamic attention that can be channeled constructively"
    
    if "ashtakavarga" in engine_lower:
        if is_positive:
            if is_strong:
                return "indicates strong underlying structural support that sustains outcomes over time"
            return "provides moderate foundational stability for this area"
        elif is_negative:
            if is_strong:
                return "signals reduced margin for error, making consistency more important"
            return "suggests the need for careful attention to maintain stability"
        else:
            return "offers variable foundational support depending on other factors"
    
    if "nakshatra" in engine_lower or "tara" in engine_lower:
        if is_positive:
            return "creates a supportive emotional and intuitive backdrop for decisions"
        elif is_negative:
            return "suggests heightened sensitivity requiring mindful navigation"
        else:
            return "brings nuanced emotional undertones that color the period"
    
    if "dasha" in engine_lower:
        if is_positive:
            return "activates themes of growth and opportunity through planetary period influences"
        elif is_negative:
            return "highlights areas needing attention and careful handling during this planetary period"
        else:
            return "brings transformative energies that can manifest in various ways"
    
    if "yoga" in engine_lower:
        if is_positive:
            return "strengthens potential for positive outcomes through combined planetary configurations"
        elif is_negative:
            return "indicates complexities that require awareness and strategic response"
        else:
            return "creates dynamic potential that depends on how energies are directed"
    
    if "house" in engine_lower:
        if is_positive:
            return "reinforces this life domain through inherent chart strength"
        elif is_negative:
            return "suggests this area requires extra attention due to natal chart patterns"
        else:
            return "brings variable emphasis to this life domain"
    
    if "divisional" in engine_lower or engine_lower.startswith("d"):
        if is_positive:
            return "refines and strengthens outcomes in specialized chart analysis"
        elif is_negative:
            return "adds nuance suggesting careful attention in detailed matters"
        else:
            return "provides additional perspective on how this area unfolds"
    
    if "navamsa" in engine_lower:
        if is_positive:
            return "deepens stability and spiritual foundation for lasting outcomes"
        elif is_negative:
            return "indicates areas where inner alignment benefits from reflection"
        else:
            return "adds depth and complexity to how matters develop"
    
    if "functional" in engine_lower or "maraka" in engine_lower:
        if is_positive:
            return "supports vitality and constructive action through planetary roles"
        elif is_negative:
            return "calls for awareness around energy management and self-care"
        else:
            return "brings nuanced planetary influences to consider"
    
    if "event" in engine_lower or "window" in engine_lower:
        if is_positive:
            return "opens favorable windows for action and initiative"
        elif is_negative:
            return "suggests caution and patience during challenging timing windows"
        else:
            return "creates periods that benefit from thoughtful timing"
    
    if is_strong:
        base = "adds notable influence that shapes how this area unfolds"
    elif is_moderate:
        base = "adds subtle influence that shapes how this area unfolds"
    else:
        base = "adds background influence to the overall picture"
    
    return base


def get_life_area_context(life_area: str) -> str:
    """
    Get contextual framing for a life area.
    
    Args:
        life_area: Name of the life area
        
    Returns:
        Contextual description string
    """
    contexts = {
        "career": "professional development and work responsibilities",
        "finance": "financial matters and material resources",
        "relationships": "interpersonal connections and emotional bonds",
        "health": "physical well-being and vitality",
        "personal_growth": "inner development and self-improvement"
    }
    return contexts.get(life_area.lower(), "this life area")
