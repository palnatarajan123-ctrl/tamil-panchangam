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
    # GOCHARA (TRANSIT) SIGNALS - EPIC Signal Expansion
    # -------------------------------------------------
    gochara = envelope.get("gochara", {})
    print("DEBUG: gochara =", gochara.get("jupiter", {}).get("effect"), gochara.get("saturn", {}).get("phase"))
    
    # Jupiter Gochara Signal
    jup_gochara = gochara.get("jupiter", {})
    jup_effect = jup_gochara.get("effect", "neutral")
    jup_house = jup_gochara.get("from_moon_house", 0)
    if jup_effect != "neutral":
        signals.append({
            "key": "GOCHARA_JUPITER",
            "source": "gochara",
            "kind": "transit",
            "planet": "Jupiter",
            "house": jup_house,
            "valence": "pos" if jup_effect == "favorable" else "neg",
            "strength": 0.8 if jup_effect == "favorable" else 0.6,
            "confidence": 0.85,
            "rationale": f"Jupiter transiting house {jup_house} from Moon ({jup_effect})",
        })
    
    # Saturn Gochara Signal
    sat_gochara = gochara.get("saturn", {})
    sat_phase = sat_gochara.get("phase", "neutral")
    sat_effect = sat_gochara.get("effect", "neutral")
    sat_house = sat_gochara.get("from_moon_house", 0)
    if sat_phase != "neutral":
        signals.append({
            "key": f"GOCHARA_SATURN_{sat_phase.upper()}",
            "source": "gochara",
            "kind": "transit",
            "planet": "Saturn",
            "house": sat_house,
            "valence": "neg" if sat_effect == "challenging" else "pos",
            "strength": 0.9 if sat_phase in ["janma_sani", "ashtama_sani", "kantaka_sani"] else 0.5,
            "confidence": 0.90,
            "rationale": f"Saturn {sat_phase} phase, house {sat_house} from Moon",
        })
    
    # Rahu-Ketu Gochara Signal
    rahu_ketu = gochara.get("rahu_ketu", {})
    rahu_effect = rahu_ketu.get("effect", "neutral")
    if rahu_effect != "neutral":
        signals.append({
            "key": "GOCHARA_RAHU_KETU",
            "source": "gochara",
            "kind": "transit",
            "planet": "Rahu",
            "house": rahu_ketu.get("rahu_from_moon_house", 0),
            "valence": "neg" if rahu_effect == "disruptive" else "pos",
            "strength": 0.7,
            "confidence": 0.75,
            "rationale": f"Rahu-Ketu axis {rahu_ketu.get('axis', 'unknown')} ({rahu_effect})",
        })
    
    # -------------------------------------------------
    # NAKSHATRA + TARA BALA SIGNALS - EPIC Signal Expansion
    # -------------------------------------------------
    nakshatra_ctx = envelope.get("nakshatra_context", {})
    tara_quality = nakshatra_ctx.get("quality", "neutral")
    print("DEBUG: nakshatra =", nakshatra_ctx.get("tara_bala"), tara_quality)
    
    if tara_quality != "neutral":
        signals.append({
            "key": f"TARA_BALA_{nakshatra_ctx.get('tara_bala', 'unknown').upper()}",
            "source": "nakshatra",
            "kind": "quality",
            "valence": "pos" if tara_quality == "favorable" else "neg",
            "strength": 0.65,
            "confidence": 0.80,
            "rationale": f"Tara Bala: {nakshatra_ctx.get('tara_name', 'Unknown')}",
        })
    
    # -------------------------------------------------
    # ASHTAKAVARGA VALIDATION SIGNALS - EPIC Signal Expansion
    # -------------------------------------------------
    ashtakavarga = envelope.get("ashtakavarga", {})
    overall_support = ashtakavarga.get("overall_support", "balanced")
    print("DEBUG: ashtakavarga =", overall_support)
    
    if overall_support != "balanced":
        av_valence = "pos" if overall_support in ["strong_support", "partial_support"] else "neg"
        signals.append({
            "key": f"ASHTAKAVARGA_{overall_support.upper()}",
            "source": "ashtakavarga",
            "kind": "validation",
            "valence": av_valence,
            "strength": 0.6 if overall_support == "strong_support" else 0.4,
            "confidence": 0.70,
            "rationale": f"Ashtakavarga validation: {overall_support}",
        })
    
    # -------------------------------------------------
    # CHANDRA GATI (Moon Rhythm) SIGNALS - EPIC Signal Expansion
    # -------------------------------------------------
    chandra_gati = envelope.get("chandra_gati", {})
    dominant_moods = chandra_gati.get("dominant_moods", [])
    print("DEBUG: chandra_gati moods =", dominant_moods)
    
    positive_moods = {"stable", "harmonious", "optimistic", "confident"}
    negative_moods = {"restless", "intense", "detached", "emotional"}
    
    mood_balance = 0
    for mood in dominant_moods[:2]:
        if mood in positive_moods:
            mood_balance += 1
        elif mood in negative_moods:
            mood_balance -= 1
    
    if mood_balance != 0:
        signals.append({
            "key": "CHANDRA_GATI_RHYTHM",
            "source": "chandra_gati",
            "kind": "rhythm",
            "valence": "pos" if mood_balance > 0 else "neg",
            "strength": 0.5,
            "confidence": 0.65,
            "rationale": f"Moon emotional rhythm: {', '.join(dominant_moods[:2])}",
        })
    
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
