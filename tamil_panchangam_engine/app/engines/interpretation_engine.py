# app/engines/interpretation_engine.py

def build_interpretation_from_synthesis(
    *,
    envelope: dict,
    synthesis: dict
) -> dict:
    """
    EPIC-4.3 + EPIC-3 (Step 2C)

    Build deterministic narrative interpretation from synthesis + envelope.

    Output:
    - Structured text by life area
    - Deterministic
    - No paraphrasing
    - No LLM
    """

    interpretations = {}

    life_areas = synthesis["life_areas"]

    dasha = envelope["time_ruler"]["vimshottari_dasha"]
    dasha_lord = dasha.get("lord")

    transits = envelope["environment"]["transits"]
    pakshi = envelope["biological_rhythm"]["pancha_pakshi_daily"]

    # -------------------------------------------------
    # EPIC-3 — Navamsa context (SAFE, OPTIONAL READ)
    # -------------------------------------------------
    navamsa = envelope.get("navamsa", {})
    navamsa_dignity = navamsa.get("dignity", {})
    has_d9 = navamsa.get("has_d9", False)

    for area, metrics in life_areas.items():
        score = metrics["score"]
        confidence = metrics["confidence"]

        # -------------------------------------------------
        # Tone selection (score-driven)
        # -------------------------------------------------
        if score >= 70:
            tone = "strongly favorable"
        elif score >= 55:
            tone = "moderately supportive"
        elif score >= 45:
            tone = "mixed"
        else:
            tone = "challenging"

        # -------------------------------------------------
        # Base confidence language
        # -------------------------------------------------
        if confidence >= 0.85:
            certainty = "with high confidence"
        elif confidence >= 0.7:
            certainty = "with reasonable confidence"
        else:
            certainty = "with caution"

        # -------------------------------------------------
        # EPIC-3 STEP 2C — Navamsa confidence overlay
        # (NO reinterpretation, only modifier)
        # -------------------------------------------------
        d9_note = ""
        if has_d9 and dasha_lord:
            dignity = navamsa_dignity.get(dasha_lord)

            if dignity == "exalted":
                certainty = "with reinforced confidence"
                d9_note = (
                    " The Navamsa chart strengthens the operating dasha lord."
                )

            elif dignity == "debilitated":
                certainty = "with reduced confidence"
                d9_note = (
                    " The Navamsa chart indicates inner strain despite external factors."
                )

        # -------------------------------------------------
        # Deterministic narrative construction
        # -------------------------------------------------
        text = (
            f"For {area.replace('_', ' ')}, this period appears {tone} "
            f"{certainty}. "
            f"The active {dasha_lord} dasha sets the overall theme, "
            f"while current planetary transits and Pancha Pakshi timing "
            f"shape day-to-day outcomes."
            f"{d9_note}"
        )

        interpretations[area] = {
            "text": text,
            "score": score,
            "confidence": confidence,
        }

    return {
        "by_life_area": interpretations,
        "note": (
            "This interpretation is derived from astrological factors. "
            "Use it as guidance, not as deterministic prediction."
        ),
    }
