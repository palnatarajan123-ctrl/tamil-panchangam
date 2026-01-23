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

    # Always use the builder - pass envelope for dasha context
    interpretation = build_interpretation(
        synthesis=synthesis,
        narrative_style="short",
        envelope=envelope,
    )

    return {
        **interpretation,
        "note": (
            "This interpretation is derived from astrological factors. "
            "Use it as guidance, not as deterministic prediction."
        ),
    }
