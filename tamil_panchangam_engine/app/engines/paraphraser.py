"""
Paraphraser Engine (Optional Layer)

Purpose:
- Rewrite interpretation text for tone & fluency
- NEVER change structure, scores, confidence, or meaning
- Safe to disable without affecting correctness

This module is intentionally isolated from:
- charts
- scores
- confidence math
"""

from typing import Dict, Callable
import os


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

ENABLE_PARAPHRASER = os.getenv("ENABLE_PARAPHRASER", "false").lower() == "true"


# -------------------------------------------------------------------
# Core API
# -------------------------------------------------------------------

def paraphrase_interpretation(
    interpretation: Dict,
    llm_fn: Callable[[str], str] | None = None
) -> Dict:
    """
    Paraphrase interpretation summaries using an LLM.

    Parameters:
    - interpretation: output from interpretation engine
    - llm_fn: function that takes text and returns rewritten text

    Returns:
    - Same structure as input
    """

    # --- Safety: if disabled or no LLM, return input unchanged ---
    if not ENABLE_PARAPHRASER or llm_fn is None:
        return interpretation

    rewritten = {}

    for life_area, payload in interpretation.get("life_areas", {}).items():
        rewritten[life_area] = payload.copy()

        summary = payload.get("summary")
        if not summary:
            continue

        rewritten_text = safe_rewrite(summary, llm_fn)
        rewritten[life_area]["summary"] = rewritten_text

    return {
        **interpretation,
        "life_areas": rewritten,
        "paraphrased": True
    }


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------

def safe_rewrite(text: str, llm_fn: Callable[[str], str]) -> str:
    """
    Guarded rewrite:
    - If LLM fails, return original text
    - Prevent hallucinations by strict prompting
    """

    try:
        prompt = build_prompt(text)
        rewritten = llm_fn(prompt)

        if not rewritten or len(rewritten.strip()) < 10:
            return text

        return rewritten.strip()

    except Exception:
        return text


def build_prompt(text: str) -> str:
    """
    Strict prompt that forbids interpretation changes
    """

    return f"""
Rewrite the following astrological guidance for clarity and warmth.

Rules:
- Do NOT add predictions
- Do NOT change meaning
- Do NOT add advice
- Do NOT mention astrology explicitly
- Preserve intent and tone
- Output only the rewritten paragraph

Text:
\"\"\"{text}\"\"\"
"""
