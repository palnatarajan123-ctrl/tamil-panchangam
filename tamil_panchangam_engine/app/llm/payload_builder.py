# app/llm/payload_builder.py
"""
LLM Payload Builder v3.0 — Siddhar-Tradition Synthesizer

Builds enriched "meaning-layer" payloads for LLM interpretation.
NEVER passes raw astrology, full envelope, or full synthesis.

v3.0 additions:
- Birth year for age-aware tone
- Lagnadipathi (Ascendant Lord) status with placement and dignity
- Saturn phase (Sade Sati / Ashtama Sani / Kantaka Sani)
- Rahu-Ketu axis and karmic theme
- Detected Yogas (Gaja Kesari, Dhana, etc.)
- Chandrashtama (challenging Moon transit) periods

Token Guardrails (HARD LIMITS):
- Weekly:  max 1400 prompt tokens, 2000 completion, 3500 total
- Monthly: max 2000 prompt tokens, 4000 completion, 7000 total
- Yearly:  max 2500 prompt tokens, 5000 completion, 9000 total
"""

import json
import logging
from datetime import date
from typing import Dict, Any, List, Literal, Optional

logger = logging.getLogger(__name__)

MAX_PROMPT_TOKENS = {
    "weekly": 1400,
    "monthly": 2000,
    "yearly": 2500
}

MAX_COMPLETION_TOKENS = {
    "weekly": 3000,
    "monthly": 6000,
    "yearly": 8000
}

MAX_TOTAL_TOKENS = {
    "weekly": 5500,
    "monthly": 10000,
    "yearly": 13000
}

RASI_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"
}

PLANET_TAMIL = {
    "Sun": "Surya", "Moon": "Chandra", "Mars": "Sevvai/Mangal",
    "Mercury": "Budha", "Jupiter": "Guru", "Venus": "Sukra",
    "Saturn": "Sani", "Rahu": "Rahu", "Ketu": "Ketu"
}

DIGNITY_SIGNS = {
    "Sun": {"exalted": "Aries", "debilitated": "Libra"},
    "Moon": {"exalted": "Taurus", "debilitated": "Scorpio"},
    "Mars": {"exalted": "Capricorn", "debilitated": "Cancer"},
    "Mercury": {"exalted": "Virgo", "debilitated": "Pisces"},
    "Jupiter": {"exalted": "Cancer", "debilitated": "Capricorn"},
    "Venus": {"exalted": "Pisces", "debilitated": "Virgo"},
    "Saturn": {"exalted": "Libra", "debilitated": "Aries"},
}

LIFE_AREA_LIMITS = {
    "weekly": {"max_areas": 4, "signals_per_area": 2},
    "monthly": {"max_areas": 5, "signals_per_area": 3},
    "yearly": {"max_areas": 7, "signals_per_area": 3}
}

HOUSE_THEMES = {
    1: "Self & Personality (Thanu Bhava)",
    2: "Wealth & Speech (Dhana Bhava)",
    3: "Courage & Siblings (Sahaja Bhava)",
    4: "Home & Happiness (Sukha Bhava)",
    5: "Children & Intelligence (Putra Bhava)",
    6: "Health & Enemies (Shatru Bhava)",
    7: "Partnerships & Marriage (Kalatra Bhava)",
    8: "Transformation & Longevity (Ayur Bhava)",
    9: "Fortune & Dharma (Bhagya Bhava)",
    10: "Career & Authority (Karma Bhava)",
    11: "Gains & Aspirations (Labha Bhava)",
    12: "Liberation & Loss (Vyaya Bhava)",
}

RASI_TAMIL = {
    "Aries": "Mesham", "Taurus": "Rishabam", "Gemini": "Mithunam",
    "Cancer": "Kadagam", "Leo": "Simmam", "Virgo": "Kanni",
    "Libra": "Thulam", "Scorpio": "Viruchigam", "Sagittarius": "Dhanusu",
    "Capricorn": "Makaram", "Aquarius": "Kumbam", "Pisces": "Meenam"
}


def estimate_tokens(text: str) -> int:
    """Estimate tokens using chars/4 heuristic (conservative)."""
    return len(text) // 4


def sanitize_signals(signals: list) -> list:
    """
    Sanitize signals before payload construction.
    Remove null, empty, or invalid signals that would leak "None" text.
    """
    return [
        s for s in signals
        if s
        and s.get("summary")
        and s.get("rationale")
        and str(s.get("summary", "")).lower() != "none"
        and str(s.get("rationale", "")).lower() != "none"
    ]


def _trim_signal(signal: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Extract signal data for LLM, including astrological context for richer interpretations.
    
    v2.0: Now includes planet, house, and source fields so the LLM can reference
    specific planetary positions and house activations in its narratives.
    """
    key = signal.get("key", "")
    rationale = signal.get("rationale", "")
    interpretive_hint = signal.get("interpretive_hint", "")
    
    if not key or not rationale:
        return None
    
    summary = key.replace("_", " ").title()[:40]
    if len(rationale) > 120:
        rationale = rationale[:117] + "..."
    
    if summary.lower() == "none" or rationale.lower() == "none":
        return None
    
    result: Dict[str, Any] = {
        "summary": summary,
        "rationale": rationale
    }
    
    if interpretive_hint and str(interpretive_hint).lower() != "none":
        result["interpretive_hint"] = interpretive_hint
    
    # v2.0: Include astrological context for richer LLM narratives
    planet = signal.get("planet") or signal.get("source_planet")
    if not planet and "_" in key:
        parts = key.split("_")
        for part in parts:
            if part in ("Jupiter", "Saturn", "Mars", "Venus", "Mercury", "Sun", "Moon", "Rahu", "Ketu"):
                planet = part
                break
    if planet and str(planet).lower() != "none":
        result["planet"] = str(planet)
    
    house = signal.get("house")
    if house is not None and str(house).lower() != "none":
        result["house"] = int(house)
    
    valence = signal.get("valence")
    if valence and str(valence).lower() != "none":
        result["valence"] = str(valence)
    
    return result


def _score_to_strength(score: int) -> str:
    """Convert numeric score to strength label."""
    if score >= 65:
        return "supportive"
    elif score >= 45:
        return "neutral"
    else:
        return "watchful"


def build_llm_payload(
    *,
    period_type: Literal["weekly", "monthly", "yearly"],
    period_label: str,
    lagna: str,
    moon_nakshatra: str,
    active_dasha: Dict[str, str],
    life_area_scores: Dict[str, int],
    top_signals_by_life_area: Dict[str, List[Dict[str, Any]]],
    explainability_mode: str = "standard",
    transit_context: Optional[Dict[str, Any]] = None,
    dasha_timing: Optional[Dict[str, str]] = None,
    moon_rasi: Optional[str] = None,
    birth_year: Optional[int] = None,
    lagnadipathi_status: Optional[Dict[str, Any]] = None,
    saturn_phase: Optional[str] = None,
    rahu_ketu_axis: Optional[Dict[str, Any]] = None,
    yogas: Optional[List[Dict[str, Any]]] = None,
    chandrashtama_periods: Optional[List[Dict[str, Any]]] = None,
    nakshatra_pada: Optional[int] = None
) -> Dict[str, Any]:
    """
    Build enriched LLM payload v3.0 — Siddhar-Tradition Synthesizer.
    
    v3.0: Adds birth year, lagnadipathi, Saturn phase, yogas, Rahu-Ketu axis,
    Chandrashtama periods for deeply personal, strategic life-map predictions.
    """
    limits = LIFE_AREA_LIMITS.get(period_type, LIFE_AREA_LIMITS["monthly"])
    max_areas = limits["max_areas"]
    signals_per_area = limits["signals_per_area"]
    
    sorted_areas = sorted(
        life_area_scores.items(),
        key=lambda x: abs(x[1] - 50),
        reverse=True
    )[:max_areas]
    
    life_areas = []
    for area_name, score in sorted_areas:
        signals = top_signals_by_life_area.get(area_name, [])[:signals_per_area]
        trimmed_signals = [_trim_signal(s) for s in signals]
        trimmed_signals = [s for s in trimmed_signals if s is not None]
        trimmed_signals = sanitize_signals(trimmed_signals)
        
        life_areas.append({
            "name": area_name,
            "score": score,
            "strength": _score_to_strength(score),
            "signals": trimmed_signals
        })
    
    lagna_tamil = RASI_TAMIL.get(lagna, "")
    lagna_display = f"{lagna} ({lagna_tamil})" if lagna_tamil else lagna
    
    moon_rasi_tamil = RASI_TAMIL.get(moon_rasi, "") if moon_rasi else ""
    moon_display = f"{moon_rasi} ({moon_rasi_tamil})" if moon_rasi and moon_rasi_tamil else (moon_rasi or "Unknown")
    
    nakshatra_display = moon_nakshatra
    if nakshatra_pada:
        nakshatra_display = f"{moon_nakshatra} (Pada {nakshatra_pada})"
    
    overall_context: Dict[str, Any] = {
        "period_type": period_type,
        "period_label": period_label,
        "lagna": lagna_display,
        "moon_rasi": moon_display,
        "moon_nakshatra": nakshatra_display,
        "nakshatra_pada": nakshatra_pada,
        "active_dasha": {
            "mahadasha": active_dasha.get("mahadasha", "Unknown"),
            "antardasha": active_dasha.get("antardasha", "Unknown"),
            "nature": active_dasha.get("nature", "")
        },
        "explainability_mode": explainability_mode
    }
    if not overall_context["active_dasha"]["nature"]:
        del overall_context["active_dasha"]["nature"]
    
    if birth_year:
        current_year = date.today().year
        age = current_year - birth_year
        overall_context["birth_year"] = birth_year
        overall_context["approximate_age"] = age
        if age >= 50:
            overall_context["life_stage"] = "senior — focus on legacy, health preservation, long-term financial security"
        elif age >= 35:
            overall_context["life_stage"] = "established — focus on career consolidation, family stability, wealth building"
        elif age >= 22:
            overall_context["life_stage"] = "emerging — focus on career foundation, relationships, skill acquisition"
        else:
            overall_context["life_stage"] = "formative — focus on education, self-discovery, foundational choices"
    
    if lagnadipathi_status:
        lord_name = lagnadipathi_status.get("lord", "")
        tamil_name = PLANET_TAMIL.get(lord_name, "")
        lagnadipathi = {
            "lord": f"{lord_name} ({tamil_name})" if tamil_name else lord_name,
            "placed_in_house": lagnadipathi_status.get("house"),
        }
        if lagnadipathi_status.get("house_theme"):
            lagnadipathi["house_theme"] = lagnadipathi_status["house_theme"]
        if lagnadipathi_status.get("dignity"):
            lagnadipathi["dignity"] = lagnadipathi_status["dignity"]
        overall_context["lagnadipathi_status"] = lagnadipathi
    
    if dasha_timing:
        overall_context["dasha_timing"] = dasha_timing
    
    if transit_context:
        transits = {}
        for planet_name, transit_data in transit_context.items():
            if isinstance(transit_data, dict):
                rasi = transit_data.get("rasi", "")
                house = transit_data.get("house_from_moon")
                rasi_tamil = RASI_TAMIL.get(rasi, "")
                transit_entry: Dict[str, Any] = {
                    "sign": f"{rasi} ({rasi_tamil})" if rasi_tamil else rasi
                }
                if house is not None:
                    transit_entry["house_from_moon"] = house
                    house_theme = HOUSE_THEMES.get(house, "")
                    if house_theme:
                        transit_entry["house_theme"] = house_theme
                effect = transit_data.get("effect", "")
                if effect:
                    transit_entry["effect"] = effect
                phase = transit_data.get("phase", "")
                if phase and phase != "neutral":
                    transit_entry["phase"] = phase
                transits[planet_name] = transit_entry
        if transits:
            overall_context["current_transits"] = transits
    
    if saturn_phase and saturn_phase not in ("neutral", "unknown"):
        phase_labels = {
            "janma_sani": "Janma Sani (Saturn over natal Moon — karmic testing period)",
            "ashtama_sani": "Ashtama Sani (Saturn in 8th from Moon — transformation and endurance)",
            "kantaka_sani": "Kantaka Sani (Saturn in 4th/7th from Moon — domestic and partnership pressure)",
        }
        overall_context["saturn_phase"] = phase_labels.get(saturn_phase, saturn_phase)
    
    if rahu_ketu_axis:
        axis_entry: Dict[str, Any] = {}
        if rahu_ketu_axis.get("rahu_house"):
            axis_entry["rahu_house"] = rahu_ketu_axis["rahu_house"]
        if rahu_ketu_axis.get("ketu_house"):
            axis_entry["ketu_house"] = rahu_ketu_axis["ketu_house"]
        if rahu_ketu_axis.get("theme"):
            axis_entry["karmic_theme"] = rahu_ketu_axis["theme"]
        if axis_entry:
            overall_context["rahu_ketu_axis"] = axis_entry
    
    if yogas:
        yoga_summaries = []
        for y in yogas[:4]:
            name = y.get("name", "")
            if name:
                entry: Dict[str, Any] = {"name": name}
                if y.get("effects"):
                    effects = y["effects"]
                    if isinstance(effects, list):
                        entry["effects"] = ", ".join(effects[:3])
                    elif isinstance(effects, str):
                        entry["effects"] = effects[:100]
                yoga_summaries.append(entry)
        if yoga_summaries:
            overall_context["yogas"] = yoga_summaries
    
    if chandrashtama_periods:
        overall_context["chandrashtama_periods"] = chandrashtama_periods[:6]
    
    payload = {
        "overall_context": overall_context,
        "synthesis_instruction": (
            "SYNTHESIZE, DON'T LIST: Do not repeat the data. Instead, explain the RESULT and IMPACT on life. "
            "The engine provides the 'What' — you provide the 'So What?' "
            "Use the individual's age/life_stage to tailor advice tone."
        ),
        "life_areas": life_areas
    }
    
    # Safety assertion: ensure no dasha leaked into life-area payloads
    assert all(
        "active_dasha" not in area for area in payload["life_areas"]
    ), "Dasha leaked into life-area payload"
    
    # PART 1: Fail-fast assertion - ensure interpretive hints are present
    # Skip LLM if hints are missing, fall back to deterministic interpretation
    missing_hints = []
    for area in payload["life_areas"]:
        for signal in area.get("signals", []):
            if "interpretive_hint" not in signal or not signal.get("interpretive_hint"):
                missing_hints.append({
                    "area": area.get("name"),
                    "signal": signal.get("summary", "unknown")
                })
    
    if missing_hints:
        # PART 2: Fail-fast - raise RuntimeError to skip LLM and use deterministic fallback
        raise RuntimeError(
            f"LLM blocked: missing interpretive_hint in {len(missing_hints)} signal(s): "
            f"{missing_hints[:3]}{'...' if len(missing_hints) > 3 else ''}"
        )
    
    # DEBUG LOG (v1.8): Confirm interpretive_hint is present in payload
    if payload.get("life_areas") and payload["life_areas"][0].get("signals"):
        logger.info(
            "DEBUG interpretive_hint sample: %s",
            payload["life_areas"][0]["signals"][:2]
        )
    
    return payload


def validate_payload_size(
    payload: Dict[str, Any],
    period_type: str
) -> tuple[bool, str, int]:
    """
    Validate payload is within token limits.
    
    Returns:
        (is_valid, reason, estimated_tokens)
    """
    payload_json = json.dumps(payload)
    estimated_prompt = estimate_tokens(payload_json)
    
    max_prompt = MAX_PROMPT_TOKENS.get(period_type, 1400)
    max_completion = MAX_COMPLETION_TOKENS.get(period_type, 900)
    max_total = MAX_TOTAL_TOKENS.get(period_type, 2500)
    
    logger.info(
        f"LLM payload size: period_type={period_type}, "
        f"chars={len(payload_json)}, estimated_tokens={estimated_prompt}, "
        f"life_areas={len(payload.get('life_areas', []))}"
    )
    
    if estimated_prompt > max_prompt:
        return False, "prompt_too_large", estimated_prompt
    
    if estimated_prompt + max_completion > max_total:
        return False, "token_budget_exceeded", estimated_prompt
    
    return True, "ok", estimated_prompt


def _derive_lagnadipathi(lagna_rasi: str, ephemeris: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Derive Ascendant Lord status from lagna rasi and ephemeris data."""
    lord = RASI_LORDS.get(lagna_rasi)
    if not lord:
        return None
    
    planets = ephemeris.get("planets", {})
    planet_data = planets.get(lord, {})
    if not planet_data:
        return None
    
    planet_rasi = planet_data.get("rasi", "")
    planet_house = planet_data.get("house")
    
    dignity = None
    dig_info = DIGNITY_SIGNS.get(lord, {})
    if planet_rasi == dig_info.get("exalted"):
        dignity = "exalted"
    elif planet_rasi == dig_info.get("debilitated"):
        dignity = "debilitated"
    elif planet_rasi == lagna_rasi:
        dignity = "own_sign"
    
    result: Dict[str, Any] = {"lord": lord}
    if planet_house is not None:
        result["house"] = planet_house
        house_theme = HOUSE_THEMES.get(planet_house, "")
        if house_theme:
            result["house_theme"] = house_theme
    if dignity:
        result["dignity"] = dignity
    
    return result


def _extract_chandrashtama(chandra_gati: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract Chandrashtama (8th house Moon transit) periods from Chandra Gati data."""
    periods = []
    positions = chandra_gati.get("moon_positions", [])
    for pos in positions:
        house = pos.get("house_from_natal_moon") or pos.get("house_from_moon")
        if house == 8:
            entry: Dict[str, Any] = {}
            if pos.get("date"):
                entry["date"] = str(pos["date"])[:10]
            if pos.get("rasi"):
                entry["moon_in"] = pos["rasi"]
            entry["warning"] = "Chandrashtama — emotionally sensitive period, avoid major decisions"
            periods.append(entry)
    
    sensitive_days = chandra_gati.get("sensitive_days", [])
    if not periods and sensitive_days:
        for day_info in sensitive_days[:6]:
            if isinstance(day_info, dict):
                entry = {}
                if day_info.get("date"):
                    entry["date"] = str(day_info["date"])[:10]
                entry["warning"] = "Sensitive Moon transit — exercise caution"
                periods.append(entry)
            elif isinstance(day_info, (int, str)):
                periods.append({"day": str(day_info), "warning": "Sensitive Moon transit"})
    
    return periods


def extract_payload_inputs(
    envelope: Dict[str, Any],
    synthesis: Dict[str, Any],
    period_type: str,
    period_key: str,
    base_chart_payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract enriched inputs from envelope and synthesis for LLM payload.
    
    v3.0: Now includes lagnadipathi, Saturn phase, yogas, Rahu-Ketu axis,
    birth year, Chandrashtama, and nakshatra pada for Siddhar-tradition interpretations.
    """
    lagna = envelope.get("lagna", {})
    nakshatra = envelope.get("nakshatra_context", {})
    dasha = envelope.get("dasha_context", {})
    gochara = envelope.get("gochara", {})
    
    lagna_label = lagna.get("label", lagna.get("rasi", "Unknown"))
    moon_nakshatra = nakshatra.get("janma_nakshatra", "Unknown")
    moon_rasi = envelope.get("moon_rasi") or nakshatra.get("janma_rasi", "")
    nakshatra_pada = nakshatra.get("janma_pada")
    
    antar_lord = dasha.get("antar_lord", "Unknown")
    antar_houses = dasha.get("antar_houses", [])
    dasha_nature = ""
    if antar_houses:
        house_refs = [str(h) for h in antar_houses[:2]]
        dasha_nature = f"{antar_lord} rules houses {', '.join(house_refs)}"
    
    active_dasha: Dict[str, Any] = {
        "mahadasha": dasha.get("maha_lord", "Unknown"),
        "antardasha": antar_lord,
    }
    if dasha_nature:
        active_dasha["nature"] = dasha_nature
    
    dasha_timing: Dict[str, Any] = {}
    antar = dasha.get("antar") or {}
    if antar.get("start"):
        dasha_timing["antardasha_start"] = str(antar["start"])[:10]
    if antar.get("end"):
        dasha_timing["antardasha_end"] = str(antar["end"])[:10]
    maha_balance = dasha.get("balance_years")
    if maha_balance:
        dasha_timing["mahadasha_balance"] = f"{maha_balance} years"
    
    transit_context: Dict[str, Any] = {}
    saturn_phase = None
    rahu_ketu_axis = None
    
    jupiter_data = gochara.get("jupiter", {})
    if isinstance(jupiter_data, dict) and jupiter_data.get("transit_rasi"):
        transit_context["Jupiter"] = {
            "rasi": jupiter_data["transit_rasi"],
            "house_from_moon": jupiter_data.get("from_moon_house"),
            "effect": jupiter_data.get("effect", "")
        }
    
    saturn_data = gochara.get("saturn", {})
    if isinstance(saturn_data, dict) and saturn_data.get("transit_rasi"):
        transit_context["Saturn"] = {
            "rasi": saturn_data["transit_rasi"],
            "house_from_moon": saturn_data.get("from_moon_house"),
            "effect": saturn_data.get("effect", ""),
            "phase": saturn_data.get("phase", "")
        }
        saturn_phase = saturn_data.get("phase")
    
    rahu_ketu_data = gochara.get("rahu_ketu", {})
    if isinstance(rahu_ketu_data, dict):
        if rahu_ketu_data.get("rahu_rasi"):
            transit_context["Rahu"] = {
                "rasi": rahu_ketu_data["rahu_rasi"],
                "house_from_moon": rahu_ketu_data.get("rahu_from_moon_house"),
                "effect": rahu_ketu_data.get("effect", "")
            }
        if rahu_ketu_data.get("ketu_rasi"):
            transit_context["Ketu"] = {
                "rasi": rahu_ketu_data["ketu_rasi"],
                "house_from_moon": rahu_ketu_data.get("ketu_from_moon_house"),
                "effect": rahu_ketu_data.get("effect", "")
            }
        rahu_ketu_axis = {
            "rahu_house": rahu_ketu_data.get("rahu_from_moon_house"),
            "ketu_house": rahu_ketu_data.get("ketu_from_moon_house"),
            "axis": rahu_ketu_data.get("axis", ""),
            "theme": rahu_ketu_data.get("theme", "")
        }
    
    envelope_yogas = envelope.get("yogas", {})
    yoga_list = []
    if isinstance(envelope_yogas, dict):
        present = envelope_yogas.get("present_yogas", [])
        if isinstance(present, list):
            yoga_list = [y for y in present if isinstance(y, dict) and y.get("present")]
    elif isinstance(envelope_yogas, list):
        yoga_list = [y for y in envelope_yogas if isinstance(y, dict) and y.get("present")]
    
    chandra_gati = envelope.get("chandra_gati", {})
    chandrashtama_periods = _extract_chandrashtama(chandra_gati) if chandra_gati else []
    
    birth_year = None
    lagnadipathi_status = None
    if base_chart_payload:
        birth_details = base_chart_payload.get("birth_details", {})
        dob = birth_details.get("date_of_birth", "")
        if dob:
            try:
                if isinstance(dob, str) and len(dob) >= 4:
                    birth_year = int(dob[:4])
                elif isinstance(dob, date):
                    birth_year = dob.year
            except (ValueError, TypeError):
                pass
        
        ephemeris = base_chart_payload.get("ephemeris", {})
        lagna_rasi_for_lord = ephemeris.get("lagna", {}).get("rasi", "")
        if lagna_rasi_for_lord:
            lagnadipathi_status = _derive_lagnadipathi(lagna_rasi_for_lord, ephemeris)
    
    life_area_scores = {}
    top_signals_by_life_area = {}
    
    synthesis_life_areas = synthesis.get("life_areas", {})
    for area_name, area_data in synthesis_life_areas.items():
        if isinstance(area_data, dict):
            life_area_scores[area_name] = area_data.get("score", 50)
            top_signals_by_life_area[area_name] = area_data.get("top_signals", [])
    
    period_label = _format_period_label(period_type, period_key)
    
    return {
        "period_type": period_type,
        "period_label": period_label,
        "lagna": lagna_label,
        "moon_nakshatra": moon_nakshatra,
        "moon_rasi": moon_rasi,
        "active_dasha": active_dasha,
        "life_area_scores": life_area_scores,
        "top_signals_by_life_area": top_signals_by_life_area,
        "transit_context": transit_context if transit_context else None,
        "dasha_timing": dasha_timing if dasha_timing else None,
        "birth_year": birth_year,
        "lagnadipathi_status": lagnadipathi_status,
        "saturn_phase": saturn_phase,
        "rahu_ketu_axis": rahu_ketu_axis,
        "yogas": yoga_list if yoga_list else None,
        "chandrashtama_periods": chandrashtama_periods if chandrashtama_periods else None,
        "nakshatra_pada": nakshatra_pada,
    }


def _format_period_label(period_type: str, period_key: str) -> str:
    """Format period key into human-readable label."""
    if period_type == "weekly" and "-W" in period_key:
        parts = period_key.split("-W")
        if len(parts) == 2:
            return f"Week {parts[1]}, {parts[0]}"
    elif period_type == "monthly" and "-" in period_key:
        parts = period_key.split("-")
        if len(parts) == 2:
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            month_idx = int(parts[1]) - 1
            if 0 <= month_idx < 12:
                return f"{months[month_idx]} {parts[0]}"
    elif period_type == "yearly":
        return period_key
    
    return period_key
