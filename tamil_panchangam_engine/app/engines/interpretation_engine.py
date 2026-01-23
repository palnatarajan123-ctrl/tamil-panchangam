# app/engines/interpretation_engine.py

from app.engines.interpretation_builder import build_interpretation


def build_interpretation_from_synthesis(
    *,
    envelope: dict,
    synthesis: dict
) -> dict:
    """
    EPIC-4.3 + EPIC-3 (Corrected)

    Responsibilities:
    - Orchestrate deterministic interpretation
    - Attach confidence and scores
    - MUST NOT generate narrative prose
    """

    life_areas = synthesis.get("life_areas", {})

    # -------------------------------------------------
    # 🔧 SAFETY: if life areas only have score/confidence,
    # allow interpretation builder to proceed anyway
    # -------------------------------------------------
    minimal = True
    for v in life_areas.values():
        if isinstance(v, dict) and (
            "signals" in v or "contributors" in v
        ):
            minimal = False
            break

    if minimal:
        # Pass through minimal structure
        interpretation = {
            "interpretation": {
                area: {
                    "summary": None,  # builder will generate
                    "tone": None,
                    "confidence": data.get("confidence", 0.5),
                    "confidence_explanation": None,
                }
                for area, data in life_areas.items()
            },
            "narrative_style": "short",
            "engine_version": "interpretation-engine-fallback-v1",
        }
    else:
        interpretation = build_interpretation(
            synthesis=synthesis,
            narrative_style="short"
        )

    return {
        **interpretation,
        "note": (
            "This interpretation is derived from astrological factors. "
            "Use it as guidance, not as deterministic prediction."
        ),
    }
