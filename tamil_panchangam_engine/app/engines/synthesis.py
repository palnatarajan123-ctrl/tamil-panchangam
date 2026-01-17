from typing import Dict
from app.engines.house_weights import compute_house_weight_multiplier


def normalize_score(value: float, max_abs: float = 5.0) -> float:
    """
    Normalize raw score into -100 to +100 range.
    """
    clipped = max(min(value, max_abs), -max_abs)
    return round((clipped / max_abs) * 100, 1)


def compute_confidence(
    contributors: dict
) -> float:
    """
    contributors example:
    {
        "dasha": +1.2,
        "transit": -0.4,
        "pakshi": +0.9,
        "house": +1.1
    }
    """

    signals = list(contributors.values())

    if not signals:
        return 0.0

    magnitude = sum(abs(s) for s in signals)
    directionality = abs(sum(signals))

    if magnitude == 0:
        return 0.0

    confidence = directionality / magnitude

    return round(min(confidence, 1.0), 2)


LIFE_AREAS = [
    "career",
    "finance",
    "relationships",
    "health",
    "learning",
    "spirituality"
]


DASHA_LIFE_AREA_WEIGHTS = {
    "Sun":        {"career": 2, "health": 1},
    "Moon":       {"relationships": 2, "health": 1},
    "Mars":       {"career": 1, "health": 2},
    "Mercury":    {"career": 1, "learning": 2},
    "Jupiter":    {"finance": 2, "learning": 1, "spirituality": 1},
    "Venus":      {"relationships": 2, "finance": 1},
    "Saturn":     {"career": 2, "health": -1},
    "Rahu":       {"career": 1, "finance": 1},
    "Ketu":       {"spirituality": 2, "learning": 1}
}


PAKSHI_EFFORT_MULTIPLIER = {
    "Vulture": 0.7,
    "Owl":     0.8,
    "Crow":    0.9,
    "Cock":    1.0,
    "Peacock": 1.2
}


def synthesize_monthly_guidance(
    dasha: Dict,
    transits: Dict,
    pakshi: Dict,
    natal_chart: Dict
) -> Dict:
    """
    Deterministic synthesis engine.
    Produces structured life-area guidance with confidence scoring.
    """

    # --- Initialize scores ---
    scores = {area: 0.0 for area in LIFE_AREAS}

    # ===============================
    # Part C: Confidence contributors
    # ===============================
    confidence_inputs = {
        area: {
            "dasha": 0.0,
            "transit": 0.0,
            "house": 0.0,
            "pakshi": 0.0
        }
        for area in LIFE_AREAS
    }

    # --- 1. Dasha influence ---
    dasha_lord = dasha.get("lord")
    if dasha_lord in DASHA_LIFE_AREA_WEIGHTS:
        for area, weight in DASHA_LIFE_AREA_WEIGHTS[dasha_lord].items():
            scores[area] += weight
            confidence_inputs[area]["dasha"] += weight

    # --- 2. Transit influence ---
    gochara = transits.get("gochara", {})
    for area in LIFE_AREAS:
        impact = gochara.get(area, "neutral")
        if impact == "favorable":
            scores[area] += 1
            confidence_inputs[area]["transit"] += 1
        elif impact == "challenging":
            scores[area] -= 1
            confidence_inputs[area]["transit"] -= 1

    # --- House-based weighting ---
    for planet, pdata in natal_chart.get("planets", {}).items():
        house = pdata.get("house")
        if not house:
            continue

        for area in scores:
            multiplier = compute_house_weight_multiplier(
                planet_name=planet,
                planet_house=house,
                life_area=area
            )
            delta = scores[area] * (multiplier - 1)
            scores[area] += delta
            confidence_inputs[area]["house"] += delta

    # --- House-based weighting (WHERE it manifests) ---
    for planet, pdata in natal_chart.get("planets", {}).items():
        planet_house = pdata.get("house")
        if not planet_house:
            continue

        for life_area in scores:
            multiplier = compute_house_weight_multiplier(
                planet_name=planet,
                planet_house=planet_house,
                life_area=life_area
            )
            delta = scores[life_area] * (multiplier - 1)
            scores[life_area] += delta
            confidence_inputs[life_area]["house"] += delta

    # --- 3. Pakshi modulation ---
    pakshi_name = pakshi.get("pakshi")
    effort_multiplier = PAKSHI_EFFORT_MULTIPLIER.get(pakshi_name, 1.0)

    adjusted_scores = {}
    for area, score in scores.items():
        delta = score * (effort_multiplier - 1)
        adjusted_scores[area] = round(score + delta, 2)
        confidence_inputs[area]["pakshi"] += delta

    # ===============================
    # Part D: Final normalization
    # ===============================
    life_area_output = {}

    for area in LIFE_AREAS:
        raw = adjusted_scores[area]
        life_area_output[area] = {
            "raw_score": raw,
            "score": normalize_score(raw),
            "confidence": compute_confidence(confidence_inputs[area]),
            "contributors": confidence_inputs[area]
        }

    # --- Global confidence (unchanged logic preserved) ---
    raw_signal_strength = sum(abs(v) for v in scores.values())
    normalized_confidence = min(1.0, raw_signal_strength / 10.0)

    if effort_multiplier < 0.9:
        normalized_confidence *= 0.85
    elif effort_multiplier > 1.1:
        normalized_confidence *= 1.05

    confidence = round(min(normalized_confidence, 1.0), 2)

    # --- 5. Output ---
    return {
        "life_area_scores": life_area_output,
        "effort_multiplier": effort_multiplier,
        "confidence": confidence,
        "confidence_label": (
            "high" if confidence >= 0.7 else
            "medium" if confidence >= 0.4 else
            "low"
        ),
        "engine_version": "synthesis-v1"
    }
