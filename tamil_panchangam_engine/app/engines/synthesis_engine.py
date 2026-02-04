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
    # DRISHTI (ASPECT) SIGNALS - Prompt 2
    # -------------------------------------------------
    drishti = envelope.get("drishti", {})
    significant_aspects = drishti.get("significant_aspects", [])
    drishti_summary = drishti.get("summary", {})
    
    for aspect in significant_aspects[:5]:
        planet = aspect.get("planet", "")
        aspected_house = aspect.get("aspected_house", 0)
        effect = aspect.get("effect", "mixed")
        
        signals.append({
            "key": f"DRISHTI_{planet}_H{aspected_house}",
            "source": "drishti",
            "kind": "aspect",
            "planet": planet,
            "house": aspected_house,
            "valence": "pos" if effect == "supportive" else ("neg" if effect == "challenging" else "mix"),
            "strength": 0.55,
            "confidence": 0.70,
            "rationale": f"{planet} aspects house {aspected_house} ({effect})",
        })
    
    if drishti_summary.get("balance") == "benefic_dominant":
        signals.append({
            "key": "DRISHTI_BALANCE_BENEFIC",
            "source": "drishti",
            "kind": "aspect_summary",
            "valence": "pos",
            "strength": 0.45,
            "confidence": 0.65,
            "rationale": "Benefic aspects dominate chart",
        })
    elif drishti_summary.get("balance") == "malefic_dominant":
        signals.append({
            "key": "DRISHTI_BALANCE_MALEFIC",
            "source": "drishti",
            "kind": "aspect_summary",
            "valence": "neg",
            "strength": 0.45,
            "confidence": 0.65,
            "rationale": "Malefic aspects dominate chart",
        })
    
    # -------------------------------------------------
    # HOUSE STRENGTH SIGNALS - Prompt 2
    # -------------------------------------------------
    house_strength_data = envelope.get("house_strength", {})
    hs_summary = house_strength_data.get("summary", {})
    
    for strong_house in hs_summary.get("strong_houses", []):
        signals.append({
            "key": f"HOUSE_STRENGTH_H{strong_house}",
            "source": "house_strength",
            "kind": "natal",
            "house": strong_house,
            "valence": "pos",
            "strength": 0.50,
            "confidence": 0.75,
            "rationale": f"House {strong_house} is natally strong",
        })
    
    for weak_house in hs_summary.get("weak_houses", []):
        signals.append({
            "key": f"HOUSE_WEAKNESS_H{weak_house}",
            "source": "house_strength",
            "kind": "natal",
            "house": weak_house,
            "valence": "neg",
            "strength": 0.45,
            "confidence": 0.70,
            "rationale": f"House {weak_house} is natally weak",
        })
    
    for afflicted_house in hs_summary.get("afflicted_houses", []):
        signals.append({
            "key": f"HOUSE_AFFLICTION_H{afflicted_house}",
            "source": "house_strength",
            "kind": "natal",
            "house": afflicted_house,
            "valence": "neg",
            "strength": 0.55,
            "confidence": 0.75,
            "rationale": f"House {afflicted_house} has affliction",
        })
    
    # -------------------------------------------------
    # FUNCTIONAL ROLE SIGNALS - Prompt 2
    # -------------------------------------------------
    functional_roles = envelope.get("functional_roles", {})
    fr_summary = functional_roles.get("summary", {})
    
    for yogakaraka in fr_summary.get("yogakarakas", []):
        if yogakaraka in active_lords:
            signals.append({
                "key": f"YOGAKARAKA_ACTIVE_{yogakaraka}",
                "source": "functional_roles",
                "kind": "natal",
                "planet": yogakaraka,
                "valence": "pos",
                "strength": 0.80,
                "confidence": 0.85,
                "rationale": f"{yogakaraka} is yogakaraka and currently active in dasha",
            })
    
    for maraka in fr_summary.get("marakas", []):
        if maraka in active_lords:
            signals.append({
                "key": f"MARAKA_ACTIVE_{maraka}",
                "source": "functional_roles",
                "kind": "natal",
                "planet": maraka,
                "valence": "neg",
                "strength": 0.60,
                "confidence": 0.70,
                "rationale": f"{maraka} is maraka lord and currently active",
            })
    
    # -------------------------------------------------
    # TIER-1 DIVISIONAL CHART SIGNALS
    # D10 → Career, D2 → Wealth, D7 → Family/Creativity, D9 → Direction
    # These REFINE but do not OVERRIDE D1 signals
    # -------------------------------------------------
    divisional_charts = envelope.get("divisional_charts", {})
    
    # D10 (Dasamsa) - Career emphasis
    d10 = divisional_charts.get("D10", {})
    d10_planets = d10.get("planets", {})
    if d10_planets and isinstance(d10_planets, dict):
        for planet in ["Sun", "Saturn", "Jupiter"]:
            planet_data = d10_planets.get(planet, {})
            if isinstance(planet_data, dict):
                d10_sign = planet_data.get("sign", "")
                if d10_sign:
                    signals.append({
                        "key": f"D10_{planet}",
                        "source": "divisional_d10",
                        "kind": "career_refinement",
                        "planet": planet,
                        "valence": "pos" if planet in BENEFIC_LORDS else "mix",
                        "strength": 0.35,
                        "confidence": 0.70,
                        "rationale": f"D10 {planet} in {d10_sign} refines career outlook",
                    })
    
    # D2 (Hora) - Wealth emphasis
    d2 = divisional_charts.get("D2", {})
    d2_planets = d2.get("planets", {})
    if d2_planets and isinstance(d2_planets, dict) and len(d2_planets) > 0:
        sun_data = d2_planets.get("Sun", {})
        moon_data = d2_planets.get("Moon", {})
        
        sun_sign = sun_data.get("sign", "") if isinstance(sun_data, dict) else ""
        moon_sign = moon_data.get("sign", "") if isinstance(moon_data, dict) else ""
        
        if sun_sign or moon_sign:
            signals.append({
                "key": "D2_WEALTH_PATTERN",
                "source": "divisional_d2",
                "kind": "wealth_refinement",
                "valence": "mix",
                "strength": 0.30,
                "confidence": 0.65,
                "rationale": f"D2 Hora pattern indicates wealth characteristics",
            })
    
    # D7 (Saptamsa) - Creativity/Children emphasis
    d7 = divisional_charts.get("D7", {})
    d7_planets = d7.get("planets", {})
    if d7_planets and isinstance(d7_planets, dict) and len(d7_planets) > 0:
        jupiter_data = d7_planets.get("Jupiter", {})
        venus_data = d7_planets.get("Venus", {})
        
        jupiter_sign = jupiter_data.get("sign", "") if isinstance(jupiter_data, dict) else ""
        venus_sign = venus_data.get("sign", "") if isinstance(venus_data, dict) else ""
        
        if jupiter_sign or venus_sign:
            signals.append({
                "key": "D7_CREATIVE_POTENTIAL",
                "source": "divisional_d7",
                "kind": "family_refinement",
                "valence": "pos",
                "strength": 0.30,
                "confidence": 0.65,
                "rationale": "D7 benefic placement supports creativity and family",
            })
    
    # -------------------------------------------------
    # YOGA SIGNALS - Prompt 2
    # -------------------------------------------------
    yogas = envelope.get("yogas", {})
    yoga_list = yogas.get("yogas", [])
    yoga_summary = yogas.get("summary", {})
    
    if yoga_summary.get("has_gaja_kesari"):
        signals.append({
            "key": "YOGA_GAJA_KESARI",
            "source": "yoga",
            "kind": "natal",
            "valence": "pos",
            "strength": 0.75,
            "confidence": 0.80,
            "rationale": "Gaja Kesari Yoga present - wisdom and leadership",
        })
    
    if yoga_summary.get("has_dhana_yoga"):
        signals.append({
            "key": "YOGA_DHANA",
            "source": "yoga",
            "kind": "natal",
            "valence": "pos",
            "strength": 0.70,
            "confidence": 0.75,
            "rationale": "Dhana Yoga present - wealth potential",
        })
    
    if yoga_summary.get("has_raja_yoga"):
        signals.append({
            "key": "YOGA_RAJA",
            "source": "yoga",
            "kind": "natal",
            "valence": "pos",
            "strength": 0.65,
            "confidence": 0.70,
            "rationale": "Raja Yoga present - power and success",
        })
    
    # -------------------------------------------------
    # EVENT WINDOW SIGNALS - Prompt 2
    # -------------------------------------------------
    event_windows = envelope.get("event_windows", {})
    ew_summary = event_windows.get("summary", {})
    overall_quality = ew_summary.get("overall_quality", "balanced")
    
    if overall_quality in ["favorable", "mildly_favorable"]:
        signals.append({
            "key": "EVENT_WINDOWS_FAVORABLE",
            "source": "event_windows",
            "kind": "timing",
            "valence": "pos",
            "strength": 0.55 if overall_quality == "favorable" else 0.40,
            "confidence": 0.70,
            "rationale": f"Monthly event windows are {overall_quality}",
        })
    elif overall_quality in ["challenging", "mildly_challenging"]:
        signals.append({
            "key": "EVENT_WINDOWS_CHALLENGING",
            "source": "event_windows",
            "kind": "timing",
            "valence": "neg",
            "strength": 0.50 if overall_quality == "challenging" else 0.35,
            "confidence": 0.70,
            "rationale": f"Monthly event windows are {overall_quality}",
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
    # ADD INTERPRETIVE HINTS TO ALL SIGNALS (v1.9: non-optional enforcement)
    # -------------------------------------------------
    from app.engines.interpretive_hints import generate_interpretive_hint
    
    for signal in signals:
        # v1.9: Use existing hint if present, otherwise generate
        signal["interpretive_hint"] = signal.get("interpretive_hint") or generate_interpretive_hint(
            engine=signal.get("source", ""),
            polarity=signal.get("valence", "mix"),
            strength=signal.get("strength", 0.5),
            life_area=None  # Will be contextualized per life area in payload
        )
    
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
