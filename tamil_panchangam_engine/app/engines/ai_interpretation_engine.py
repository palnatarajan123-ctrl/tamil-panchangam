# app/engines/ai_interpretation_engine.py
"""
AI Interpretation Engine v1.0

Generates intelligent, non-repetitive interpretations for prediction windows.
Runs after synthesis and before UI adaptation.

Three-level structure:
- Level 1: Window Summary (overall momentum, dominant forces)
- Level 2: Life Area Interpretations (signal interaction)
- Level 3: Astrological Attribution (planets, dasha, engines)

Contract: docs/contracts/ai_interpretation_v1.schema.json
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import random
import json
import os
from pathlib import Path

JSONSCHEMA_AVAILABLE = False
jsonschema = None
try:
    import jsonschema as _jsonschema
    jsonschema = _jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    print("WARNING: jsonschema not installed, schema validation disabled")

_SCHEMA_CACHE: Dict[str, Any] = {}

def _load_schema() -> Optional[Dict[str, Any]]:
    """Load the AI interpretation v1.0 schema."""
    if "v1" in _SCHEMA_CACHE:
        return _SCHEMA_CACHE["v1"]
    
    schema_paths = [
        Path(__file__).parent.parent.parent / "docs" / "contracts" / "ai_interpretation_v1.schema.json",
        Path("tamil_panchangam_engine/docs/contracts/ai_interpretation_v1.schema.json"),
        Path("docs/contracts/ai_interpretation_v1.schema.json"),
    ]
    
    for schema_path in schema_paths:
        if schema_path.exists():
            try:
                with open(schema_path, "r") as f:
                    schema = json.load(f)
                _SCHEMA_CACHE["v1"] = schema
                return schema
            except Exception as e:
                print(f"WARNING: Failed to load schema from {schema_path}: {e}")
    
    print("WARNING: Schema file not found, validation disabled")
    return None


def _validate_interpretation(interpretation: Dict[str, Any]) -> bool:
    """
    Validate interpretation against v1.0 schema.
    
    Returns True if valid, raises ValueError if invalid.
    """
    if not JSONSCHEMA_AVAILABLE:
        print("VALIDATION SKIPPED: jsonschema not available")
        return True
    
    schema = _load_schema()
    if schema is None:
        print("VALIDATION SKIPPED: schema not loaded")
        return True
    
    try:
        jsonschema.validate(instance=interpretation, schema=schema)
        print("✓ Schema validation passed")
        return True
    except jsonschema.ValidationError as e:
        error_path = " -> ".join(str(p) for p in e.absolute_path)
        error_msg = f"Schema validation failed at '{error_path}': {e.message}"
        print(f"✗ {error_msg}")
        raise ValueError(error_msg) from e

LIFE_AREAS = ["career", "finance", "relationships", "health", "personal_growth"]

MOMENTUM_TYPES = {
    "growth": ["expansion", "advancement", "rising trajectory", "progressive momentum"],
    "consolidation": ["stabilization", "grounding phase", "integration period", "steady maintenance"],
    "pressure": ["testing phase", "challenging dynamics", "intensity building", "karmic pressure"],
    "transition": ["shifting energies", "turning point", "phase change", "restructuring period"],
}

LIFE_AREA_VOCABULARY = {
    "career": {
        "positive": ["professional advancement", "leadership recognition", "authority strengthening", "visible accomplishments", "career momentum"],
        "negative": ["visibility delays", "professional obstacles", "authority challenges", "stalled progress", "workplace friction"],
        "neutral": ["steady efforts", "foundational work", "incremental progress", "professional stability", "consistent output"],
        "verbs": ["propels", "elevates", "anchors", "demands", "reveals", "tests"],
        "tone": "authority, effort, visibility",
    },
    "finance": {
        "positive": ["wealth inflow", "financial gains", "profitable ventures", "monetary stability", "investment returns"],
        "negative": ["financial pressure", "unexpected expenses", "resource strain", "monetary delays", "cash flow challenges"],
        "neutral": ["steady finances", "controlled spending", "balanced accounts", "measured growth", "stable resources"],
        "verbs": ["attracts", "compounds", "restricts", "channels", "multiplies", "preserves"],
        "tone": "inflow, retention, risk",
    },
    "relationships": {
        "positive": ["deepening bonds", "harmonious connections", "reciprocal warmth", "relationship growth", "emotional fulfillment"],
        "negative": ["relational strain", "communication gaps", "emotional distance", "trust challenges", "partnership friction"],
        "neutral": ["stable connections", "maintained bonds", "quiet understanding", "balanced dynamics", "steady rapport"],
        "verbs": ["nurtures", "bridges", "tests", "reveals", "deepens", "strains"],
        "tone": "warmth, strain, reciprocity",
    },
    "health": {
        "positive": ["vitality surge", "physical recovery", "energy renewal", "wellness momentum", "stamina building"],
        "negative": ["health vulnerabilities", "energy depletion", "recovery needs", "physical caution", "stamina challenges"],
        "neutral": ["stable health", "maintenance mode", "balanced energy", "steady vitality", "consistent wellness"],
        "verbs": ["restores", "challenges", "sustains", "depletes", "regenerates", "demands"],
        "tone": "stamina, vulnerability, recovery",
    },
    "personal_growth": {
        "positive": ["insight expansion", "spiritual advancement", "wisdom deepening", "consciousness elevation", "learning breakthroughs"],
        "negative": ["growth resistance", "inner conflicts", "stagnation risks", "blocked insights", "spiritual tests"],
        "neutral": ["steady learning", "gradual integration", "quiet reflection", "measured progress", "foundation building"],
        "verbs": ["illuminates", "transforms", "challenges", "integrates", "reveals", "tests"],
        "tone": "learning, resistance, insight",
    },
}

PLANET_DESCRIPTORS = {
    "Sun": {"nature": "authority", "themes": ["ego", "vitality", "leadership", "father figures"]},
    "Moon": {"nature": "emotion", "themes": ["mind", "mother", "public", "emotional wellbeing"]},
    "Mars": {"nature": "action", "themes": ["courage", "conflict", "energy", "competition"]},
    "Mercury": {"nature": "intellect", "themes": ["communication", "commerce", "learning", "siblings"]},
    "Jupiter": {"nature": "expansion", "themes": ["wisdom", "fortune", "teachers", "spirituality"]},
    "Venus": {"nature": "harmony", "themes": ["love", "luxury", "arts", "relationships"]},
    "Saturn": {"nature": "discipline", "themes": ["karma", "delays", "structure", "hard work"]},
    "Rahu": {"nature": "obsession", "themes": ["desires", "foreigners", "innovation", "unconventional"]},
    "Ketu": {"nature": "detachment", "themes": ["spirituality", "past karma", "isolation", "liberation"]},
}

HOUSE_THEMES = {
    1: "self, personality, physical body",
    2: "wealth, family, speech",
    3: "courage, siblings, communication",
    4: "home, mother, emotional peace",
    5: "children, creativity, intelligence",
    6: "enemies, health issues, service",
    7: "partnership, marriage, business",
    8: "transformation, longevity, occult",
    9: "fortune, higher learning, father",
    10: "career, status, authority",
    11: "gains, friends, aspirations",
    12: "losses, spirituality, foreign lands",
}


def _determine_momentum(signals: List[Dict], life_area_scores: Dict) -> str:
    """Determine overall momentum from signals."""
    pos_count = sum(1 for s in signals if s.get("valence") == "pos")
    neg_count = sum(1 for s in signals if s.get("valence") == "neg")
    
    avg_score = sum(la["score"] for la in life_area_scores.values()) / len(life_area_scores) if life_area_scores else 50
    
    if pos_count > neg_count + 2 and avg_score > 60:
        return "growth"
    elif neg_count > pos_count + 2 or avg_score < 45:
        return "pressure"
    elif abs(pos_count - neg_count) <= 1:
        return "consolidation"
    else:
        return "transition"


def _normalize_signals(raw_signals: List[Dict]) -> List[Dict]:
    """Normalize signals from synthesis top_signals format to standard format."""
    normalized = []
    for sig in raw_signals:
        key = sig.get("key", "")
        
        valence = sig.get("valence")
        if not valence and isinstance(sig.get("weights"), dict):
            valence = sig["weights"].get("valence")
        
        planet = sig.get("planet")
        source = sig.get("source")
        
        if not planet and "_" in key:
            parts = key.split("_")
            for part in parts[1:]:
                if part in ["Jupiter", "Saturn", "Mars", "Venus", "Mercury", "Sun", "Moon", "Rahu", "Ketu"]:
                    planet = part
                    break
        
        if not source:
            if key.startswith("GOCHARA"):
                source = "gochara"
            elif key.startswith("DRISHTI"):
                source = "drishti"
            elif key.startswith("HOUSE"):
                source = "house_strength"
            elif key.startswith("YOGA"):
                source = "yoga"
            elif key.startswith("DASHA"):
                source = "dasha"
            elif key.startswith("TARA"):
                source = "nakshatra"
            elif key.startswith("ASHTAKAVARGA"):
                source = "ashtakavarga"
        
        normalized.append({
            "key": key,
            "valence": valence or "mix",
            "planet": planet,
            "source": source,
            "strength": sig.get("strength") or sig.get("contrib") or 0.5,
            "rationale": sig.get("rationale", ""),
        })
    
    return normalized


def _get_dominant_forces(envelope: Dict, signals: List[Dict]) -> List[Dict]:
    """Extract top 2-3 dominant astrological forces."""
    forces = []
    
    dasha_context = envelope.get("dasha_context", {})
    maha = dasha_context.get("maha_lord") or dasha_context.get("maha")
    antar = dasha_context.get("antar_lord") or dasha_context.get("antar")
    
    if maha:
        forces.append({
            "type": "dasha",
            "planet": maha,
            "sub_planet": antar,
            "description": f"{maha} Mahadasha / {antar or 'Unknown'} Antardasha"
        })
    
    yogas = envelope.get("yogas", {}).get("yogas", [])
    for yoga in yogas[:2]:
        forces.append({
            "type": "yoga",
            "name": yoga.get("name"),
            "description": yoga.get("name", "Special combination active")
        })
    
    gochara = envelope.get("gochara", {})
    jup = gochara.get("jupiter", {})
    sat = gochara.get("saturn", {})
    
    if jup.get("effect") == "favorable":
        forces.append({
            "type": "transit",
            "planet": "Jupiter",
            "house": jup.get("from_moon_house"),
            "description": f"Jupiter transiting house {jup.get('from_moon_house')} from Moon (favorable)"
        })
    
    if sat.get("phase") in ["janma_sani", "ashtama_sani", "kantaka_sani"]:
        forces.append({
            "type": "transit",
            "planet": "Saturn",
            "phase": sat.get("phase"),
            "description": f"Saturn in {sat.get('phase').replace('_', ' ')} phase"
        })
    
    return forces[:3]


def _determine_outcome_mode(signals: List[Dict], momentum: str) -> str:
    """Determine how outcomes manifest: ease, effort, or delay."""
    saturn_signals = [s for s in signals if "Saturn" in s.get("key", "") or s.get("planet") == "Saturn"]
    jupiter_signals = [s for s in signals if "Jupiter" in s.get("key", "") or s.get("planet") == "Jupiter"]
    
    if momentum == "growth" and len(jupiter_signals) > len(saturn_signals):
        return "ease"
    elif momentum == "pressure" or len(saturn_signals) > 2:
        return "delay"
    else:
        return "effort"


def _generate_window_summary(
    envelope: Dict,
    synthesis: Dict,
    signals: List[Dict],
    year: int,
    month: int
) -> Dict[str, Any]:
    """Generate Level 1: Window Summary."""
    life_areas = synthesis.get("life_areas", {})
    
    momentum = _determine_momentum(signals, life_areas)
    dominant_forces = _get_dominant_forces(envelope, signals)
    outcome_mode = _determine_outcome_mode(signals, momentum)
    
    momentum_phrase = random.choice(MOMENTUM_TYPES.get(momentum, ["transitional period"]))
    
    force_descriptions = [f.get("description", "") for f in dominant_forces if f.get("description")]
    forces_text = " and ".join(force_descriptions[:2]) if force_descriptions else "mixed planetary influences"
    
    outcome_phrases = {
        "ease": "Results manifest with relative smoothness, requiring less effort than usual.",
        "effort": "Outcomes are achievable but require sustained focus and deliberate action.",
        "delay": "Progress may face obstacles; patience and persistence are essential."
    }
    
    event_windows = envelope.get("event_windows", {})
    timing_summary = event_windows.get("summary", {})
    timing_note = ""
    if timing_summary.get("supportive_periods", 0) > timing_summary.get("challenging_periods", 0):
        timing_note = "The early part of this period shows stronger support for initiatives."
    elif timing_summary.get("challenging_periods", 0) > timing_summary.get("supportive_periods", 0):
        timing_note = "Timing windows suggest caution in the middle portion of this period."
    
    overview = f"This period marks a {momentum_phrase}, shaped primarily by {forces_text}. {outcome_phrases.get(outcome_mode, '')} {timing_note}".strip()
    
    return {
        "momentum": momentum,
        "momentum_description": momentum_phrase,
        "dominant_forces": dominant_forces,
        "outcome_mode": outcome_mode,
        "overview": overview,
        "period": {"year": year, "month": month}
    }


def _get_relevant_signals_for_area(signals: List[Dict], area: str, score_data: Dict | None = None) -> List[Dict]:
    """Get signals most relevant to a specific life area."""
    if score_data and score_data.get("top_signals"):
        return _normalize_signals(score_data.get("top_signals", []))[:3]
    
    house_mappings = {
        "career": [1, 6, 10],
        "finance": [2, 5, 9, 11],
        "relationships": [4, 7, 5],
        "health": [1, 6, 8],
        "personal_growth": [5, 9, 12],
    }
    
    relevant_houses = house_mappings.get(area, [])
    relevant = []
    
    for signal in signals:
        house = signal.get("house")
        if house and house in relevant_houses:
            relevant.append(signal)
            continue
        
        source = signal.get("source", "")
        if source == "yoga" and area in ["career", "finance"]:
            relevant.append(signal)
        elif source == "gochara":
            relevant.append(signal)
        elif source == "dasha":
            relevant.append(signal)
    
    sorted_signals = sorted(relevant, key=lambda s: s.get("strength", 0), reverse=True)
    return sorted_signals[:3]


def _safe_get_planet(signal: Dict, fallback: str) -> str:
    """Safely get planet name, handling None values properly."""
    planet = signal.get("planet")
    if planet and planet != "None" and str(planet).strip():
        return str(planet)
    source = signal.get("source")
    if source and source != "None" and str(source).strip():
        return str(source)
    return fallback


def _generate_signal_interaction_text(signals: List[Dict], area: str) -> str:
    """Generate text explaining how signals interact."""
    if len(signals) < 2:
        if signals:
            s = signals[0]
            planet = _safe_get_planet(s, "planetary")
            rationale = s.get("rationale") or "chart activation"
            return f"The primary influence comes from {planet} energy through {rationale}."
        return ""
    
    vocab = LIFE_AREA_VOCABULARY.get(area, LIFE_AREA_VOCABULARY["career"])
    
    pos_signals = [s for s in signals if s.get("valence") == "pos"]
    neg_signals = [s for s in signals if s.get("valence") == "neg"]
    
    if pos_signals and neg_signals:
        pos = pos_signals[0]
        neg = neg_signals[0]
        pos_planet = _safe_get_planet(pos, "benefic forces")
        neg_planet = _safe_get_planet(neg, "challenging aspects")
        
        templates = [
            f"Although {pos_planet} supports {random.choice(vocab['positive'])}, {neg_planet}'s influence creates {random.choice(vocab['negative'])}.",
            f"The supportive energy of {pos_planet} is partially offset by {neg_planet}, requiring balanced effort.",
            f"While {pos.get('rationale') or 'positive aspects'} opens doors, {neg.get('rationale') or 'challenges'} demands careful navigation."
        ]
        return random.choice(templates)
    elif len(pos_signals) >= 2:
        p1 = _safe_get_planet(pos_signals[0], "benefic influences")
        p2 = _safe_get_planet(pos_signals[1], "supportive transits")
        return f"The combined influence of {p1} and {p2} creates a favorable environment for {random.choice(vocab['positive'])}."
    elif len(neg_signals) >= 2:
        n1 = _safe_get_planet(neg_signals[0], "challenging aspects")
        n2 = _safe_get_planet(neg_signals[1], "karmic pressure")
        return f"Both {n1} and {n2} bring intensity, requiring patience with {random.choice(vocab['negative'])}."
    else:
        return f"Mixed influences create a period of {random.choice(vocab['neutral'])}."


def _generate_life_area_interpretation(
    area: str,
    score_data: Dict,
    signals: List[Dict],
    envelope: Dict
) -> Dict[str, Any]:
    """Generate Level 2: Life Area Interpretation with Level 3 Attribution."""
    vocab = LIFE_AREA_VOCABULARY.get(area, LIFE_AREA_VOCABULARY["career"])
    score = score_data.get("score", 50)
    
    if score >= 65:
        valence = "positive"
        outlook = random.choice(vocab["positive"])
    elif score <= 40:
        valence = "negative"
        outlook = random.choice(vocab["negative"])
    else:
        valence = "neutral"
        outlook = random.choice(vocab["neutral"])
    
    relevant_signals = _get_relevant_signals_for_area(signals, area, score_data)
    
    verb = random.choice(vocab["verbs"])
    
    summary_templates = {
        "positive": [
            f"This period {verb} {outlook}, with planetary support aligning favorably.",
            f"Strong astrological backing creates momentum for {outlook}.",
            f"Favorable configurations actively support {outlook} throughout this window."
        ],
        "negative": [
            f"Planetary tensions may manifest as {outlook}, requiring mindful navigation.",
            f"Current configurations suggest {outlook}; strategic patience is advised.",
            f"Challenging aspects point toward {outlook}, though remedial measures can help."
        ],
        "neutral": [
            f"A period of {outlook} emerges from balanced planetary influences.",
            f"Mixed signals indicate {outlook} as the likely pattern.",
            f"Neither strongly supported nor opposed, expect {outlook}."
        ]
    }
    summary = random.choice(summary_templates.get(valence, summary_templates["neutral"]))
    
    interaction_text = _generate_signal_interaction_text(relevant_signals, area)
    
    # FIX 2: Get dasha_context for attribution only - do NOT add dasha_note to text
    # Dasha influence is explained ONCE in overview, not repeated per life area
    dasha_context = envelope.get("dasha_context", {})
    
    house_notes = []
    for sig in relevant_signals:
        house = sig.get("house")
        if house is not None:
            house_int = int(house)
            theme = HOUSE_THEMES.get(house_int, "")
            if theme:
                planet = _safe_get_planet(sig, "Planetary influence")
                house_notes.append(f"{planet}'s activation of the {house_int}th house ({theme}) shapes outcomes.")
    
    deeper_parts = [interaction_text]
    # FIX 2: No dasha_note added here - prevents repetition across life areas
    if house_notes:
        deeper_parts.append(house_notes[0])
    
    gochara = envelope.get("gochara", {})
    if area == "career" and gochara.get("saturn", {}).get("phase") in ["janma_sani", "ashtama_sani"]:
        deeper_parts.append("Saturn's current phase demands extra diligence in professional matters.")
    elif area == "finance" and gochara.get("jupiter", {}).get("effect") == "favorable":
        deeper_parts.append("Jupiter's favorable transit supports financial growth when action is taken.")
    
    deeper_explanation = " ".join(deeper_parts[:4])
    
    planets_involved = []
    engines_used = []
    
    for sig in relevant_signals:
        key = sig.get("key", "")
        planet = sig.get("planet")
        source = sig.get("source")
        
        if not planet and "_" in key:
            parts = key.split("_")
            for part in parts[1:]:
                if part in ["Jupiter", "Saturn", "Mars", "Venus", "Mercury", "Sun", "Moon", "Rahu", "Ketu"]:
                    planets_involved.append(part)
                    break
        elif planet:
            planets_involved.append(planet)
        
        if not source and key.startswith("GOCHARA"):
            engines_used.append("gochara")
        elif not source and key.startswith("DRISHTI"):
            engines_used.append("drishti")
        elif not source and key.startswith("HOUSE"):
            engines_used.append("house_strength")
        elif not source and key.startswith("YOGA"):
            engines_used.append("yoga")
        elif not source and key.startswith("DASHA"):
            engines_used.append("dasha")
        elif not source and key.startswith("TARA"):
            engines_used.append("nakshatra")
        elif not source and key.startswith("ASHTAKAVARGA"):
            engines_used.append("ashtakavarga")
        elif source:
            engines_used.append(source)
    
    planets_involved = list(set(planets_involved))[:3]
    engines_used = list(set(engines_used))
    
    engine_display_names = {
        "drishti": "Drishti (Aspects)",
        "house_strength": "House Strength",
        "functional_roles": "Functional Roles",
        "yoga": "Yoga Detection",
        "gochara": "Gochara (Transits)",
        "nakshatra": "Nakshatra/Tara Bala",
        "ashtakavarga": "Ashtakavarga",
        "chandra_gati": "Moon Rhythm",
        "dasha": "Dasha Analysis",
        "event_windows": "Event Windows",
    }
    
    signals_used = []
    for sig in relevant_signals:
        sig_valence = sig.get("valence")
        if not sig_valence and isinstance(sig.get("weights"), dict):
            sig_valence = sig["weights"].get("valence")
        
        sig_source = sig.get("source", "")
        sig_engine = engine_display_names.get(sig_source, sig_source) if sig_source else None
        
        sig_weight = sig.get("strength") or sig.get("contrib") or 0
        if isinstance(sig_weight, (int, float)):
            sig_weight = round(float(sig_weight), 2)
        
        signals_used.append({
            "engine": sig_engine,
            "weight": sig_weight,
            "valence": sig_valence or "neutral",
        })
    
    attribution = {
        "planets": planets_involved,
        "dasha": f"{dasha_context.get('maha_lord', dasha_context.get('maha', 'Unknown'))}/{dasha_context.get('antar_lord', dasha_context.get('antar', 'Unknown'))}",
        "engines": [engine_display_names.get(str(e), str(e)) for e in engines_used if e],
        "signals_used": signals_used
    }
    
    return {
        "score": score,
        "outlook": valence,  # This is the life area outlook from earlier
        "summary": summary,
        "deeper_explanation": deeper_explanation,
        "attribution": attribution,
        "word_count": len(summary.split()) + len(deeper_explanation.split())
    }


def generate_interpretation(
    envelope: Dict[str, Any],
    synthesis: Dict[str, Any],
    year: int,
    month: int,
    signals: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Main entry point for AI Interpretation Engine.
    
    Runs after synthesis to generate human-readable interpretations.
    
    Args:
        envelope: Full prediction envelope with all computed signals
        synthesis: Output from synthesis engine with life area scores
        year: Prediction year
        month: Prediction month
        signals: Optional pre-extracted signals (will extract from synthesis if not provided)
        
    Returns:
        Complete interpretation with window_summary and life_areas
    """
    print("\n🎯 AI INTERPRETATION ENGINE v1.0 EXECUTING")
    
    if signals is None:
        raw_signals = []
        life_areas = synthesis.get("life_areas", {})
        for area, data in life_areas.items():
            for sig in data.get("top_signals", []):
                raw_signals.append(sig)
            for sig in data.get("signals", []):
                raw_signals.append(sig)
        signals = _normalize_signals(raw_signals)
    
    print(f"DEBUG: Processing {len(signals)} normalized signals for interpretation")
    
    try:
        window_summary = _generate_window_summary(envelope, synthesis, signals, year, month)
        print(f"DEBUG: Window momentum = {window_summary.get('momentum')}")
    except Exception as e:
        print(f"ERROR in window_summary: {e}")
        window_summary = {
            "momentum": "transition",
            "overview": "A period of mixed influences with opportunities for growth.",
            "dominant_forces": [],
            "outcome_mode": "effort",
            "error": str(e)
        }
    
    life_area_interpretations = {}
    life_areas_data = synthesis.get("life_areas", {})
    
    for area in LIFE_AREAS:
        try:
            score_data = life_areas_data.get(area, {"score": 50})
            interpretation = _generate_life_area_interpretation(
                area, score_data, signals, envelope
            )
            life_area_interpretations[area] = interpretation
            print(f"DEBUG: {area} interpretation generated ({interpretation.get('word_count', 0)} words)")
        except Exception as e:
            print(f"ERROR in {area} interpretation: {e}")
            life_area_interpretations[area] = {
                "score": 50,
                "outlook": "neutral",
                "summary": f"Mixed influences affect {area} during this period.",
                "deeper_explanation": "Consult the signal data for detailed analysis.",
                "attribution": {"planets": [], "dasha": "Unknown", "engines": []},
                "error": str(e)
            }
    
    result = {
        "engine_version": "ai-interpretation-v1.0",
        "generated_at": datetime.utcnow().isoformat(),
        "window_summary": window_summary,
        "life_areas": life_area_interpretations
    }
    
    _validate_interpretation(result)
    
    print(f"DEBUG: Interpretation complete")
    return result
