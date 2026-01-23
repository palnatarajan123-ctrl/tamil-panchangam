from typing import Dict, Callable
import os

# -------------------------------------------------
# Module-level config (single source of truth)
# -------------------------------------------------
ENABLE_PARAPHRASER = os.getenv("ENABLE_PARAPHRASER", "false").lower() == "true"


def paraphrase_interpretation(
    interpretation: Dict,
    llm_fn: Callable[[str], str] | None = None,
) -> Dict:
    """
    EPIC-8 Paraphrasing Engine

    - Optional stylistic smoothing
    - NO astrology logic
    - NO meaning changes
    - Controlled via ENABLE_PARAPHRASER env var
    """

    if not ENABLE_PARAPHRASER or llm_fn is None:
        return interpretation

    paraphrased = {}

    for key, text in interpretation.items():
        try:
            paraphrased[key] = llm_fn(text)
        except Exception:
            paraphrased[key] = text  # fail-safe: never block prediction

    return paraphrased
