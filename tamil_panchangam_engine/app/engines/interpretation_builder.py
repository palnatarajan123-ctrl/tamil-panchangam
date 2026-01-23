"""
Dynamic interpretation builder using pre-generated fragments.
Assembles personalized predictions based on actual planetary signals.
"""
from typing import Dict, List, Optional

from app.engines.interpretation_fragments import (
    LIFE_AREA_OPENING,
    LIFE_AREA_CLOSING,
    HOUSE_LIFE_AREA_MAP,
    get_planet_house_fragment,
    get_dasha_context_fragment,
    PLANET_GENERAL,
)

AREA_DISPLAY_NAMES = {
    "career": "Career",
    "finance": "Finance",
    "relationships": "Relationships",
    "health": "Health",
    "personal_growth": "Personal Growth",
}


def _get_tone_from_score(score: float) -> str:
    if score >= 75:
        return "strong_positive"
    elif score >= 65:
        return "positive"
    elif score >= 45:
        return "mixed"
    else:
        return "challenging"


def _get_relevant_signals_for_area(
    area: str,
    top_signals: List[Dict],
) -> List[Dict]:
    """Filter signals relevant to this life area based on house mappings."""
    relevant = []
    for signal in top_signals:
        house = signal.get("house")
        if house is None:
            continue
        mapped_areas = HOUSE_LIFE_AREA_MAP.get(house, [])
        if area in mapped_areas:
            relevant.append(signal)
    return relevant[:3]


def _build_dynamic_summary(
    area: str,
    score: float,
    tone: str,
    top_signals: List[Dict],
    dasha_context: Optional[Dict] = None,
) -> str:
    """Build a dynamic summary using fragments based on actual signals."""
    parts = []

    opening = LIFE_AREA_OPENING.get(area, {}).get(tone, "This area shows mixed influences.")
    parts.append(opening)

    if dasha_context:
        maha_lord = dasha_context.get("maha_lord")
        antar_lord = dasha_context.get("antar_lord")
        if maha_lord:
            dasha_fragment = get_dasha_context_fragment(maha_lord, antar_lord)
            parts.append(dasha_fragment)

    relevant_signals = _get_relevant_signals_for_area(area, top_signals)
    
    if relevant_signals:
        for signal in relevant_signals[:2]:
            planet = signal.get("planet")
            house = signal.get("house")
            valence = signal.get("valence", "pos")
            weights = signal.get("weights", {})
            
            if planet and house:
                fragment = get_planet_house_fragment(planet, house, valence)
                parts.append(fragment)
    else:
        all_planets = set()
        for signal in top_signals[:3]:
            planet = signal.get("planet")
            if planet:
                all_planets.add(planet)
        
        if all_planets:
            planet_list = list(all_planets)[:2]
            if len(planet_list) == 1:
                quality = PLANET_GENERAL.get(planet_list[0], "planetary energy")
                parts.append(f"{planet_list[0]}'s themes of {quality} color this period.")
            else:
                parts.append(
                    f"The interplay of {planet_list[0]} and {planet_list[1]} "
                    f"shapes the overall direction."
                )

    closing = LIFE_AREA_CLOSING.get(area, {}).get(tone, "Maintain awareness and balance.")
    parts.append(closing)

    return " ".join(parts)


def build_interpretation(
    synthesis: Dict,
    narrative_style: str = "short",
    envelope: Optional[Dict] = None,
) -> Dict:
    """
    Dynamic interpretation builder.
    Uses actual signals and dasha context to create personalized descriptions.
    """
    life_areas = synthesis.get("life_areas", {})
    interpretation = {}

    dasha_context = None
    if envelope:
        dasha_context = envelope.get("dasha_context")

    all_signals = []
    for area_data in life_areas.values():
        signals = area_data.get("top_signals", [])
        all_signals.extend(signals)

    for area, data in life_areas.items():
        score = data.get("score", 50)
        confidence = data.get("confidence", 0.5)
        top_signals = data.get("top_signals", all_signals[:5])

        tone = _get_tone_from_score(score)
        summary = _build_dynamic_summary(
            area=area,
            score=score,
            tone=tone,
            top_signals=top_signals,
            dasha_context=dasha_context,
        )

        interpretation[area] = {
            "summary": summary,
            "tone": tone,
            "confidence": confidence,
            "confidence_explanation": None,
        }

    return {
        "interpretation": interpretation,
        "narrative_style": narrative_style,
        "engine_version": "interpretation-builder-v5-dynamic",
    }
