# app/engines/synthesis_engine.py

from statistics import pstdev
from app.engines.life_area_scorer import LifeAreaScorer

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
    Deterministic synthesis layer.

    Emits:
    - base score
    - base confidence
    - normalized signals (NO interpretation)
    """

    # -------------------------------------------------
    # 🔥 ABSOLUTE PROOF THIS FUNCTION IS EXECUTING
    # -------------------------------------------------
    print("\n🔥🔥🔥 SYNTHESIS v4.1 EXECUTING 🔥🔥🔥")

    # -------------------------------------------------
    # BASIC ENVELOPE SANITY
    # -------------------------------------------------
    print("DEBUG: envelope keys =", list(envelope.keys()))
    print("DEBUG: has houses =", "houses" in envelope)
    print("DEBUG: has dasha_context =", "dasha_context" in envelope)

    dasha_context = envelope.get("dasha_context", {})
    active_lords = dasha_context.get("active_lords", [])

    print("DEBUG: active_lords =", active_lords)

    # -------------------------------------------------
    # BASELINE
    # -------------------------------------------------
    base_score = 67
    base_confidence = 0.90
    signals = []

    # -------------------------------------------------
    # BUILD PLANET → HOUSE MAP
    # -------------------------------------------------
    houses = envelope.get("houses", {})
    print("DEBUG: envelope.houses keys =", list(houses.keys()))

    house_lords = {}
    for house, hdata in houses.items():
        lord = hdata.get("lord")
        if lord:
            house_lords.setdefault(lord, []).append(int(house))

    print("DEBUG: house_lords =", house_lords)

    # -------------------------------------------------
    # NAVAMSA SIGNAL
    # -------------------------------------------------
    navamsa = envelope.get("navamsa", {})
    d9_dignity = navamsa.get("dignity", {})

    navamsa_bias = 0
    if navamsa.get("has_d9"):
        exalted = {p for p, d in d9_dignity.items() if d == "exalted"}
        debilitated = {p for p, d in d9_dignity.items() if d == "debilitated"}

        benefic_strength = len(exalted & BENEFIC_LORDS)
        benefic_weakness = len(debilitated & BENEFIC_LORDS)
        malefic_strength = len(exalted & MALEFIC_LORDS)
        malefic_weakness = len(debilitated & MALEFIC_LORDS)

        navamsa_bias = (
            (benefic_strength - benefic_weakness)
            - (malefic_strength - malefic_weakness)
        )
        navamsa_bias = max(min(navamsa_bias, 2), -2)

        signals.append({
            "key": "NAVAMSA_DIGNITY",
            "source": "derived",
            "kind": "score",
            "valence": (
                "pos" if navamsa_bias > 0
                else "neg" if navamsa_bias < 0
                else "mix"
            ),
            "strength": abs(navamsa_bias) / 2,
            "confidence": 0.75,
            "rationale": f"Navamsa dignity bias: {navamsa_bias}",
        })

    # -------------------------------------------------
    # ACTIVE DASHA LORD SIGNALS (HOUSE-AWARE)
    # -------------------------------------------------
    for lord in active_lords:
        owned_houses = house_lords.get(lord, [])
        print(f"DEBUG: {lord} owns houses {owned_houses}")

        for house in owned_houses:
            signals.append({
                "key": f"DASHA_{lord}_H{house}",
                "source": "dasha",
                "kind": "planet",
                "planet": lord,
                "house": house,
                "valence": "pos" if lord in BENEFIC_LORDS else "neg",
                "strength": 0.75,
                "confidence": 0.85,
                "rationale": f"{lord} dasha activating house {house}",
            })

    # -------------------------------------------------
    # FINAL SIGNAL AUDIT
    # -------------------------------------------------
    print("DEBUG: FINAL SIGNALS (count =", len(signals), ")")
    for s in signals:
        print("  ", s)

    # -------------------------------------------------
    # LIFE AREA SCORING
    # -------------------------------------------------
    scorer = LifeAreaScorer()

    life_areas = scorer.score_all(
        base_score_0_100=base_score,
        base_confidence_0_1=base_confidence,
        signals=signals,
    )

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
        "engine_version": "synthesis-v4.1-debug",
        "generated_at": envelope["reference"]["reference_date_utc"],
        "confidence": confidence_meta,
    }
