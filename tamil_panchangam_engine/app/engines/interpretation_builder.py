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


def _base_summary(area: str, tone: str) -> str:
    if tone == "positive":
        return (
            f"{area.capitalize()} matters are supported this month. "
            "Conditions favor progress when effort is applied consistently."
        )
    if tone == "caution":
        return (
            f"{area.capitalize()} requires patience this month. "
            "Avoid forcing outcomes; steady handling reduces friction."
        )
    return (
        f"{area.capitalize()} remains stable this month. "
        "Neither major acceleration nor obstruction is indicated."
    )


def _variant_summary(area: str, tone: str, style: str) -> str:
    """
    style: short | practical | reflective
    """
    if style == "short":
        return _base_summary(area, tone)

    if style == "practical":
        if tone == "positive":
            return (
                f"Focus on concrete actions in {area}. "
                "This is a month where effort produces visible results."
            )
        if tone == "caution":
            return (
                f"Proceed carefully in {area}. "
                "Minimize risk and prioritize stability."
            )
        return (
            f"Maintain current momentum in {area}. "
            "Routine actions are sufficient."
        )

    if style == "reflective":
        if tone == "positive":
            return (
                f"{area.capitalize()} presents growth opportunities. "
                "Awareness and intention amplify favorable conditions."
            )
        if tone == "caution":
            return (
                f"{area.capitalize()} invites reflection. "
                "Slower pacing helps align with underlying rhythms."
            )
        return (
            f"{area.capitalize()} offers equilibrium. "
            "Observe patterns before initiating change."
        )

    return _base_summary(area, tone)


def build_interpretation(
    synthesis: Dict,
    narrative_style: str = "short"
) -> Dict:
    """
    Step 13B + 13C
    Deterministic interpretation builder with narrative variants.
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
            "confidence_explanation": CONFIDENCE_EXPLANATION
        }

    return {
        "interpretation": interpretation,
        "narrative_style": narrative_style,
        "engine_version": "interpretation-builder-v2"
    }
