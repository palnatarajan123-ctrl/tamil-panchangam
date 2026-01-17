from datetime import datetime, timezone
from statistics import pstdev

LIFE_AREAS = [
    "career",
    "finance",
    "relationships",
    "health",
    "personal_growth",
]

BENEFIC_LORDS = {"Jupiter", "Venus", "Mercury"}
MALEFIC_LORDS = {"Saturn", "Mars", "Rahu", "Ketu"}


def synthesize_from_envelope(envelope: dict) -> dict:
    """
    EPIC-7
    Deterministic, explainable synthesis with real confidence computation
    """

    scores = {}
    raw_values = []

    transits = envelope["environment"]["transits"]
    pakshi = envelope["biological_rhythm"]["pancha_pakshi_daily"]
    dasha_context = envelope["dasha_context"]

    active_lords = dasha_context["active_lords"]
    lord_weights = dasha_context.get("lord_weights", {})

    for area in LIFE_AREAS:
        base = 0.5

        # Transit influence
        if "major_transits" in transits:
            supportive = sum(
                1 for t in transits["major_transits"].values()
                if t.get("gochara_effect") == "Supportive"
            )
            challenging = sum(
                1 for t in transits["major_transits"].values()
                if t.get("gochara_effect") == "Challenging"
            )
            base += 0.05 * supportive
            base -= 0.05 * challenging

        # Dasha influence (multi-lord aware)
        for lord in active_lords:
            weight = lord_weights.get(lord, 0.2)
            if lord in BENEFIC_LORDS:
                base += 0.1 * weight
            elif lord in MALEFIC_LORDS:
                base -= 0.1 * weight

        # Pakshi rhythm
        if pakshi.get("dominant_pakshi"):
            base += 0.05

        raw = max(0.0, min(1.0, base))
        raw_values.append(raw)

        scores[area] = {
            "raw_score": round(raw, 2),
            "score": int(raw * 100),
        }

    # -----------------------------
    # Confidence computation (REAL)
    # -----------------------------
    variance = pstdev(raw_values) if len(raw_values) > 1 else 0.0
    lord_factor = min(1.0, 0.5 + 0.25 * len(active_lords))
    stability_factor = round(1.0 - variance, 2)

    confidence = round(0.4 * lord_factor + 0.6 * stability_factor, 2)

    for area in scores:
        scores[area]["confidence"] = confidence

    return {
        "life_areas": scores,
        "engine_version": "synthesis-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "confidence": {
            "overall": confidence,
            "variance": round(variance, 3),
            "active_lords": active_lords,
        },
    }
