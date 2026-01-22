# app/engines/synthesis_engine.py

from datetime import datetime, timezone
from statistics import pstdev

# ============================================================
# CONSTANTS
# ============================================================

LIFE_AREAS = [
    "career",
    "finance",
    "relationships",
    "health",
    "personal_growth",
]

BENEFIC_LORDS = {"Jupiter", "Venus", "Mercury"}
MALEFIC_LORDS = {"Saturn", "Mars", "Rahu", "Ketu"}


# ============================================================
# SYNTHESIS ENGINE
# ============================================================

def synthesize_from_envelope(envelope: dict) -> dict:
    """
    EPIC-5 + EPIC-6 + EPIC-3 (2B + 3)

    Derive synthesis signals from FACT envelope.
    - Deterministic
    - No interpretation
    - No LLM
    """

    dasha_context = envelope.get("dasha_context", {})
    active_lords = dasha_context.get("active_lords", [])

    # -------------------------------------------------
    # BASELINE LIFE AREA SCORES (NEUTRAL)
    # -------------------------------------------------
    life_areas = {
        "career": {
            "raw_score": 0.67,
            "score": 67,
            "confidence": 0.9,
        },
        "finance": {
            "raw_score": 0.67,
            "score": 67,
            "confidence": 0.9,
        },
        "relationships": {
            "raw_score": 0.67,
            "score": 67,
            "confidence": 0.9,
        },
        "health": {
            "raw_score": 0.67,
            "score": 67,
            "confidence": 0.9,
        },
        "personal_growth": {
            "raw_score": 0.67,
            "score": 67,
            "confidence": 0.9,
        },
    }

    # -------------------------------------------------
    # EPIC-3 STEP 2B — NAVAMSA SIGNAL EXTRACTION
    # -------------------------------------------------
    navamsa = envelope.get("navamsa", {})
    d9_dignity = navamsa.get("dignity", {})

    if navamsa.get("has_d9"):
        exalted = {
            p for p, d in d9_dignity.items() if d == "exalted"
        }
        debilitated = {
            p for p, d in d9_dignity.items() if d == "debilitated"
        }

        benefic_strength = len(exalted & BENEFIC_LORDS)
        benefic_weakness = len(debilitated & BENEFIC_LORDS)
        malefic_strength = len(exalted & MALEFIC_LORDS)
        malefic_weakness = len(debilitated & MALEFIC_LORDS)

        # Net Navamsa signal (bounded)
        navamsa_bias = (
            (benefic_strength - benefic_weakness)
            - (malefic_strength - malefic_weakness)
        )

        # Clamp bias
        navamsa_bias = max(min(navamsa_bias, 2), -2)

    else:
        navamsa_bias = 0

    # -------------------------------------------------
    # EPIC-3 STEP 3 — APPLY SYNTHESIS ADJUSTMENTS
    # -------------------------------------------------
    for area in LIFE_AREAS:
        entry = life_areas[area]

        # Raw score adjustment (very small)
        delta = navamsa_bias * 0.01
        entry["raw_score"] = round(
            min(max(entry["raw_score"] + delta, 0.0), 1.0),
            3,
        )

        # Score adjustment (max ±5)
        entry["score"] = int(
            min(max(entry["score"] + navamsa_bias * 2, 0), 100)
        )

        # Confidence slight modifier
        if navamsa_bias > 0:
            entry["confidence"] = min(entry["confidence"] + 0.02, 1.0)
        elif navamsa_bias < 0:
            entry["confidence"] = max(entry["confidence"] - 0.02, 0.5)

    # -------------------------------------------------
    # META CONFIDENCE
    # -------------------------------------------------
    scores = [v["score"] for v in life_areas.values()]

    confidence_meta = {
        "overall": round(sum(scores) / (len(scores) * 100), 2),
        "variance": round(pstdev(scores), 2) if len(scores) > 1 else 0.0,
        "active_lords": active_lords,
        "navamsa_bias": navamsa_bias,
    }

    return {
        "life_areas": life_areas,
        "engine_version": "synthesis-v3",
        "generated_at": envelope["reference"]["reference_date_utc"],
        "confidence": confidence_meta,
    }
