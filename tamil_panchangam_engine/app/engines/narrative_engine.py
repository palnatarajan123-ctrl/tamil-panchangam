from typing import Dict, List, Optional, Any


def _normalize_list(value: Any) -> List[str]:
    """
    Safely normalize lists that may arrive as:
    - List[str]
    - Dict[str, List[str]]
    - None
    """
    if not value:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        out: List[str] = []
        for v in value.values():
            if isinstance(v, list):
                out.extend(v)
        return out

    return []


def build_narrative(
    *,
    period_label: str,
    maha_lord: str,
    antar_lord: Optional[str],
    antar_phase: Optional[str],
    themes: List[str],
    remedies: List[str],
    cautions: List[str],
    # -------------------------------------------------
    # EPIC-3 / EPIC-14 (optional, additive)
    # -------------------------------------------------
    navamsa_dignity: Optional[str] = None,
) -> Dict[str, Any]:
    """
    EPIC-14
    Human-readable narrative layer.

    NON-predictive.
    NON-authoritative.
    NON-scoring.

    This layer provides reflective framing only.
    """

    # ---- Normalize inputs (critical for stability) ----
    themes = _normalize_list(themes)
    remedies = _normalize_list(remedies)
    cautions = _normalize_list(cautions)

    # ---- Context framing ----
    antar_phrase = (
        f"the {antar_lord} sub-period operating within {maha_lord}"
        if antar_lord
        else f"the ongoing {maha_lord} period"
    )

    phase_hint = {
        "early": "This phase is still settling in.",
        "mid": "This phase is actively shaping daily experience.",
        "late": "This phase is moving toward closure and resolution.",
    }.get(antar_phase, "")

    overview = (
        f"This {period_label.lower()} reflects {antar_phrase}. "
        f"{phase_hint}".strip()
    )

    # ---- EPIC-3: Navamsa tone modifier (subtle, non-assertive) ----
    if navamsa_dignity == "exalted":
        overview += (
            " There may be an underlying sense of inner support or alignment."
        )
    elif navamsa_dignity == "debilitated":
        overview += (
            " Inner adjustments or recalibration may be required despite external activity."
        )

    # ---- Emotional tone ----
    emotional_tone = (
        f"The emotional tone may feel shaped by themes of "
        f"{', '.join(themes[:3])}."
        if themes
        else "The emotional tone may feel subtle but meaningful."
    )

    # ---- What to expect ----
    what_to_expect = (
        [f"You may notice increased focus on {t}." for t in themes[:4]]
        if themes
        else [
            "Experiences may unfold quietly but carry personal significance."
        ]
    )

    # ---- How to work with the period ----
    how_to_work = (
        [
            f"Leaning into {r.lower()} can help you stay aligned during this phase."
            for r in remedies[:3]
        ]
        if remedies
        else [
            "Maintaining balance and conscious pacing will be helpful during this time."
        ]
    )

    # ---- Cautions (if present) ----
    cautions_block = (
        [f"Be mindful of tendencies related to {c.lower()}." for c in cautions[:3]]
        if cautions
        else []
    )

    # ---- Closing reflection ----
    closing = (
        "Rather than forcing outcomes, this period supports steady awareness "
        "and conscious response to what unfolds."
    )

    return {
        "overview": overview,
        "emotional_tone": emotional_tone,
        "what_to_expect": what_to_expect,
        "how_to_work_with_this_period": how_to_work,
        "cautions": cautions_block,
        "closing_reflection": closing,
    }
