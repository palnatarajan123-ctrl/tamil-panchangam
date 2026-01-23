from typing import Dict

POSITIVE_THRESHOLD = 30
NEGATIVE_THRESHOLD = -30

CONFIDENCE_EXPLANATION = (
    "Confidence reflects the strength and alignment of astrological signals "
    "contributing to this life area. Higher confidence indicates stronger "
    "agreement across timing, transits, and chart factors."
)


def _tone_from_score(score: float) -> str:
    if score >= POSITIVE_THRESHOLD:
        return "positive"
    if score <= NEGATIVE_THRESHOLD:
        return "caution"
    return "neutral"


def _area_lens(area: str) -> str:
    """
    Deterministic, non-astrological framing for each life area.
    """
    return {
        "career": "professional direction, responsibility, and role clarity",
        "finance": "income stability, spending discipline, and financial timing",
        "relationships": "communication, expectations, and emotional balance",
        "health": "physical vitality, mental resilience, and recovery",
        "personal_growth": "learning, self-awareness, and value alignment",
    }.get(area, "general life circumstances")


def _variant_summary(area: str, tone: str, style: str) -> str:
    lens = _area_lens(area)

    if style == "short":
        if tone == "positive":
            return (
                f"{area.capitalize()} matters are supported this month. "
                f"Conditions favor progress related to {lens}."
            )
        if tone == "caution":
            return (
                f"{area.capitalize()} requires patience this month. "
                f"Attention to {lens} helps reduce friction."
            )
        return (
            f"{area.capitalize()} remains stable this month. "
            f"Focus on maintaining balance around {lens}."
        )

    if style == "practical":
        if tone == "positive":
            return (
                f"Take practical steps in {area} related to {lens}. "
                "Effort is likely to produce tangible results."
            )
        if tone == "caution":
            return (
                f"Proceed conservatively in {area}. "
                f"Stability improves when managing {lens} carefully."
            )
        return (
            f"Maintain existing routines in {area}. "
            f"Consistency around {lens} is sufficient."
        )

    if style == "reflective":
        if tone == "positive":
            return (
                f"{area.capitalize()} offers growth opportunities. "
                f"Awareness around {lens} amplifies favorable conditions."
            )
        if tone == "caution":
            return (
                f"{area.capitalize()} invites reflection. "
                f"Slower pacing helps realign {lens}."
            )
        return (
            f"{area.capitalize()} is in a holding phase. "
            f"Observe patterns connected to {lens} before initiating change."
        )

    return (
        f"{area.capitalize()} is steady this month. "
        f"Maintain awareness around {lens}."
    )


def build_interpretation(
    synthesis: Dict,
    narrative_style: str = "short"
) -> Dict:
    """
    Deterministic interpretation builder.
    NO astrology logic.
    NO scoring.
    TEXT ONLY.
    """

    life_areas = synthesis.get("life_areas", {})
    interpretation = {}

    for area, data in life_areas.items():
        score = data.get("score", 0)
        confidence = data.get("confidence", 0.0)

        tone = _tone_from_score(score)
        summary = _variant_summary(area, tone, narrative_style)

        interpretation[area] = {
            "summary": summary,
            "tone": tone,
            "confidence": confidence,
            "confidence_explanation": CONFIDENCE_EXPLANATION,
        }

    return {
        "interpretation": interpretation,
        "narrative_style": narrative_style,
        "engine_version": "interpretation-builder-v3",
    }
