# app/api/natal_interpretation.py
"""
Natal Chart AI Interpretation Endpoint

Generates a once-off, lifelong natal chart reading using the Anthropic LLM.
Cached permanently — one LLM call per chart.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.limiter import limiter
from app.db.postgres import get_conn
from app.repositories.base_chart_repo import get_base_chart_by_id
from app.engines.llm_interpretation_orchestrator import is_llm_enabled
from app.llm.providers import anthropic_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chart", tags=["Natal Interpretation"])

PROMPT_VERSION = "natal_v2.0"
FEATURE_NAME = "natal_interpretation"

NATAL_SYSTEM_PROMPT = """You are a natal chart interpreter
combining Tamil Jyotisha tradition with plain-English
clarity.

Your output has TWO layers:

LAYER 1 — Plain English (new v2 sections):
who_you_are, where_you_shine, relationships_and_family,
current_chapter, life_by_decade

Rules for Layer 1:
- Write for an intelligent person with NO astrology background
- No Sanskrit terms, no house numbers, no jargon
- Every sentence answers: what does this mean in real life?
- Probabilistic language only: "tends to", "often", "may",
  "is likely to", "the chart suggests"
- Never deterministic: no "will", "definitely", "guaranteed"
- For marriage_windows and children_indication: give
  favorable WINDOWS and TENDENCIES only — never specific
  age predictions
- Tone: grounded, honest, warm — not threatening, not
  over-rosy
- Acknowledge challenges constructively, never fatalistic
- For very strong placements: highlight clearly and
  positively
- For challenging placements: honest but framed as growth

LAYER 2 — Classical Jyotisha (existing v1 sections):
chart_highlights, life_areas, dasha_life_map, closing_wisdom

Rules for Layer 2:
- Keep classical Siddhar tradition voice
- Name specific planets, houses, nakshatras
- Rich, chart-specific interpretation — no generic filler
- For KP charts: reference sub-lord significators explicitly
- Every sentence must name a planet, house, or nakshatra

GLOBAL RULES:
- Every sentence must be specific to THIS person's chart
- No repeated themes across sections
- Output ONLY valid JSON — no markdown, no text outside JSON
- Include ALL remaining dashas from birth in dasha_life_map
- Include ALL decades from birth to end of life in
  life_by_decade
- current_chapter must reflect the CURRENT dasha from
  the chart context provided"""

NATAL_USER_TEMPLATE = """Birth Chart Data:
{chart_context}

Generate a natal-v2.0 interpretation with this EXACT JSON.
Return ONLY the JSON — no markdown fences, no preamble.

{{
  "engine_version": "natal-v2.0",

  "who_you_are": {{
    "core_identity": "3 sentences plain English. Who is this person at their core? What drives them? How do others naturally experience them? Zero astrology terms.",
    "in_one_line": "One sentence. What a close friend who knows them well would say to describe them.",
    "core_strengths": [
      "Strength 1 — specific to this chart, plain English, 15 words max",
      "Strength 2 — specific to this chart, plain English, 15 words max",
      "Strength 3 — specific to this chart, plain English, 15 words max"
    ],
    "growth_edges": [
      "Growth area 1 — framed as opportunity not flaw, 15 words max",
      "Growth area 2 — framed as opportunity not flaw, 15 words max"
    ],
    "central_tension": "1-2 sentences. The core karmic push-pull of this life in plain English. What is this person's central paradox or challenge? What do they need to reconcile?"
  }},

  "where_you_shine": {{
    "natural_domains": [
      "Specific field or domain — e.g. medicine, teaching, finance, technology",
      "Specific field or domain",
      "Specific field or domain"
    ],
    "why": "1-2 sentences. Which specific planetary placements or yogas create this natural aptitude? Plain English — translate the astrology into capability.",
    "working_style": "1 sentence. How does this person naturally approach work, problems, and achievement?"
  }},

  "relationships_and_family": {{
    "partnership_nature": "2 sentences. What kind of partner is this person? What do they need and offer in close relationships? Plain English.",
    "marriage_windows": "2 sentences. When are the most favorable windows for committed partnership? Use probabilistic framing: 'the chart suggests favorable conditions during...', 'partnership tends to...' Never give a specific age as a prediction.",
    "children_indication": "1-2 sentences. What does the chart suggest about children? Frame probabilistically. Acknowledge uncertainty naturally.",
    "family_dynamics": "1-2 sentences. What patterns exist with parents or family of origin? What shaped this person early?"
  }},

  "current_chapter": {{
    "dasha_now": "Current Mahadasha / Antardasha — copy from the chart context",
    "what_this_means": "2-3 sentences. What does this specific dasha period mean for THIS person right now? What is being activated in their chart? What themes are dominant? Plain English, specific.",
    "focus_for_now": "1 sentence. The single most important focus or opportunity for this person in their current life phase."
  }},

  "life_by_decade": [
    {{
      "age_range": "0-10",
      "theme": "Plain English: what kind of period is this decade?",
      "key_focus": "What matters most or is being built in this window?",
      "dasha_context": "Which dasha is active and what specific life area does it activate for this chart?"
    }}
  ],

  "chart_highlights": {{
    "lagna_interpretation": "2-3 sentences. Name the Lagna sign and its lord, state the lord's current placement and dignity, explain the life impact specifically for this person.",
    "moon_interpretation": "2-3 sentences. Name the Moon sign, nakshatra, and pada. Explain emotional nature, mental patterns, and intuitive gifts specific to this placement.",
    "strongest_influence": "2-3 sentences. Name the strongest planet by Shadbala, its placement, and its dominant life impact for this chart.",
    "key_yoga_impact": "2-3 sentences. Name the most significant yoga present, explain its mechanism (which planets/houses form it), and state its practical life implication."
  }},

  "life_areas": {{
    "career": "2-3 sentences. Name the 10th house lord, its placement, any D10 signals if available, and one clear career implication specific to this chart.",
    "wealth": "2-3 sentences. Name the 2nd and 11th house lords, Jupiter's placement, and one specific wealth pattern or tendency.",
    "relationships": "2-3 sentences. Name the 7th house lord, Venus placement, and one specific relationship tendency or pattern.",
    "health": "2-3 sentences. Name the Lagna lord, 6th house condition, and one health consideration with practical guidance.",
    "spirituality": "2-3 sentences. Name Ketu's placement, 9th house lord, and the specific spiritual direction indicated."
  }},

  "dasha_life_map": [
    {{
      "mahadasha": "planet name",
      "approximate_age": "age range e.g. 0-16",
      "theme": "1 sentence naming the ruling planet's house(s) and the primary life theme it activates for this specific chart"
    }}
  ],

  "closing_wisdom": "2 sentences of Siddhar-tradition wisdom specific to this chart's most distinctive feature. Reference the actual chart — not generic wisdom."
}}

CRITICAL:
- Include ALL decades from 0 to end of life in life_by_decade
- Include ALL remaining dashas from birth in dasha_life_map
- current_chapter.dasha_now must match the current dasha
  in the chart context
- marriage_windows and children_indication must be
  probabilistic — never deterministic age predictions
- Return ONLY valid JSON"""


class NatalInterpretationRequest(BaseModel):
    base_chart_id: str


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_cached(base_chart_id: str) -> Optional[Dict[str, Any]]:
    try:
        with get_conn() as conn:
            row = conn.execute("""
                SELECT content_json FROM prediction_llm_interpretation
                WHERE base_chart_id = ?
                  AND period_type = 'natal'
                  AND period_key = 'natal'
                  AND feature_name = ?
                  AND prompt_version = ?
                ORDER BY created_at DESC LIMIT 1
            """, [base_chart_id, FEATURE_NAME, PROMPT_VERSION]).fetchone()
            if row and row[0]:
                data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                return data
    except Exception as e:
        logger.warning(f"Natal cache lookup failed: {e}")
    return None


def _save_cache(
    base_chart_id: str,
    content_json: Dict[str, Any],
    provider: Optional[str],
    model: Optional[str],
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    fallback_reason: Optional[str],
) -> None:
    try:
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO prediction_llm_interpretation (
                    id, base_chart_id, period_type, period_key, feature_name,
                    provider, model, prompt_version, prompt_tokens,
                    completion_tokens, total_tokens, content_json,
                    fallback_reason, reflection_text, created_at
                ) VALUES (?, ?, 'natal', 'natal', ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, CURRENT_TIMESTAMP)
            """, [
                str(uuid.uuid4()), base_chart_id, FEATURE_NAME,
                provider, model, PROMPT_VERSION,
                prompt_tokens, completion_tokens, total_tokens,
                json.dumps(content_json), fallback_reason,
            ])
            if total_tokens > 0 and not fallback_reason:
                conn.execute("""
                    INSERT INTO llm_token_usage (id, feature_name, prompt_version, total_tokens, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, [str(uuid.uuid4()), FEATURE_NAME, PROMPT_VERSION, total_tokens])
    except Exception as e:
        logger.error(f"Failed to save natal cache: {e}")


def _build_natal_context(payload: Dict[str, Any]) -> str:
    """Summarise the birth chart payload into a compact LLM-readable string."""
    eph = payload.get("ephemeris", {})
    birth = payload.get("birth_details", {})
    dashas = payload.get("dashas", {}).get("vimshottari", {})
    yogas_raw = payload.get("yogas", {})
    shadbala_raw = payload.get("shadbala", {})

    # Basic identity
    lagna = eph.get("lagna", {})
    moon = eph.get("moon", {})
    planets = eph.get("planets", {})

    lines: list[str] = []
    lines.append(f"Name: {birth.get('name', 'Unknown')}")
    lines.append(f"DOB: {birth.get('date_of_birth', '')} {birth.get('time_of_birth', '')} at {birth.get('place_of_birth', '')}")
    dob_str = birth.get('date_of_birth', '')
    if dob_str:
        try:
            from datetime import date
            birth_year = int(str(dob_str)[:4])
            age = date.today().year - birth_year
            lines.append(f"Approximate current age: {age}")
        except Exception:
            pass
    lines.append(f"Lagna (Ascendant): {lagna.get('rasi', '')} ({lagna.get('longitude_deg', 0):.1f}°)")
    lines.append(f"Moon: {moon.get('rasi', '')} nakshatra {moon.get('nakshatra', {}).get('name', '')} pada {moon.get('nakshatra', {}).get('pada', '')}")

    # Planet placements
    planet_lines = []
    for p, pdata in planets.items():
        if isinstance(pdata, dict):
            retro = " (R)" if pdata.get("is_retrograde") else ""
            planet_lines.append(f"{p}{retro}: {pdata.get('rasi', '')}")
    if planet_lines:
        lines.append("Planet placements: " + ", ".join(planet_lines))

    # Yogas
    if isinstance(yogas_raw, dict):
        present = [y["name"] for y in yogas_raw.get("present_yogas", []) if y.get("present")]
        if present:
            lines.append(f"Yogas present: {', '.join(present[:8])}")

    # Shadbala
    if isinstance(shadbala_raw, dict) and not shadbala_raw.get("error"):
        strongest = shadbala_raw.get("strongest_planet")
        weakest = shadbala_raw.get("weakest_planet")
        if strongest:
            lines.append(f"Strongest planet (Shadbala): {strongest}")
        if weakest:
            lines.append(f"Weakest planet (Shadbala): {weakest}")

    # KP Sub-lords (only for KP charts)
    ayanamsa = eph.get("ayanamsa", "lahiri")
    if ayanamsa == "kp":
        kp_sublords = payload.get("kp_sublords", {})
        if kp_sublords:
            lines.append("Ayanamsa: KP (Krishnamurti Paddhati)")
            kp_lines = []
            for planet in ["Lagna", "Sun", "Moon", "Mars", "Mercury",
                           "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
                if planet in kp_sublords:
                    e = kp_sublords[planet]
                    kp_lines.append(
                        f"{planet}: star={e.get('star_lord', '')} "
                        f"sub={e.get('sub_lord', '')} "
                        f"sub-sub={e.get('sub_sub_lord', '')}"
                    )
            if kp_lines:
                lines.append("KP Sub-lords: " + " | ".join(kp_lines))
    else:
        lines.append("Ayanamsa: Lahiri (Chitrapaksha)")

    # Current Dasha + full sequence
    if isinstance(dashas, dict):
        maha_seq = dashas.get("mahadasha_sequence", [])
        current_period = dashas.get("current_period", {})
        current_maha = current_period.get("mahadasha", {})
        if current_maha.get("lord"):
            lines.append(f"Current Mahadasha: {current_maha['lord']} (ends {current_maha.get('end_date', '')})")
        if maha_seq:
            seq_strs = []
            for m in maha_seq[:12]:
                if isinstance(m, dict):
                    seq_strs.append(f"{m.get('lord', '')} ({m.get('start_year', '')}-{m.get('end_year', '')})")
            if seq_strs:
                lines.append(f"Mahadasha sequence: {', '.join(seq_strs)}")

    return "\n".join(lines)


def _fallback_response() -> Dict[str, Any]:
    return {
        "engine_version": "natal-v2.0",
        "who_you_are": {
            "core_identity": "",
            "in_one_line": "",
            "core_strengths": [],
            "growth_edges": [],
            "central_tension": ""
        },
        "where_you_shine": {
            "natural_domains": [],
            "why": "",
            "working_style": ""
        },
        "relationships_and_family": {
            "partnership_nature": "",
            "marriage_windows": "",
            "children_indication": "",
            "family_dynamics": ""
        },
        "current_chapter": {
            "dasha_now": "",
            "what_this_means": "",
            "focus_for_now": ""
        },
        "life_by_decade": [],
        "life_theme": {
            "title": "Chart Under Analysis",
            "narrative": "Enable AI interpretation to receive your personalized natal reading."
        },
        "chart_highlights": {
            "lagna_interpretation": "",
            "moon_interpretation": "",
            "strongest_influence": "",
            "key_yoga_impact": ""
        },
        "life_areas": {
            "career": "",
            "wealth": "",
            "relationships": "",
            "health": "",
            "spirituality": ""
        },
        "dasha_life_map": [],
        "closing_wisdom": "",
        "llm_disabled": True,
    }


# ── Endpoint ─────────────────────────────────────────────────────────────────

@limiter.limit("3/hour")
@router.post("/natal-interpretation")
def get_natal_interpretation(request: Request, body: NatalInterpretationRequest):
    """
    Generate (or return cached) natal chart AI interpretation.
    One LLM call per chart — cached permanently afterward.
    """
    base_chart_id = body.base_chart_id

    # 1. Check cache first
    cached = _get_cached(base_chart_id)
    if cached:
        return {"interpretation": cached, "cached": True}

    # 2. LLM disabled?
    if not is_llm_enabled() or not anthropic_provider.is_available():
        return {"interpretation": _fallback_response(), "cached": False, "llm_disabled": True}

    # 3. Fetch base chart
    with get_conn() as conn:
        record = get_base_chart_by_id(conn, base_chart_id)
    if not record:
        raise HTTPException(status_code=404, detail="Base chart not found")

    raw_payload = record["payload"]
    if isinstance(raw_payload, str):
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Failed to parse chart payload")
    else:
        payload = raw_payload

    # 4. Build chart context and call LLM
    chart_context = _build_natal_context(payload)
    user_prompt = NATAL_USER_TEMPLATE.format(chart_context=chart_context)

    llm_response, usage_info, error = anthropic_provider.call_llm(
        system_prompt=NATAL_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=5000,
    )

    provider = usage_info.get("provider") if usage_info else None
    model = usage_info.get("model") if usage_info else None
    prompt_tokens = (usage_info or {}).get("prompt_tokens", 0)
    completion_tokens = (usage_info or {}).get("completion_tokens", 0)
    total_tokens = (usage_info or {}).get("total_tokens", 0)

    if error or llm_response is None:
        logger.warning(f"Natal LLM call failed: {error}, using fallback")
        fallback = _fallback_response()
        fallback["llm_error"] = error
        _save_cache(
            base_chart_id, fallback, provider, model,
            prompt_tokens, completion_tokens, total_tokens, error or "llm_failed"
        )
        return {"interpretation": fallback, "cached": False, "llm_error": error}

    # 5. Validate required keys
    required_keys = [
        "chart_highlights", "life_areas",
        "dasha_life_map", "closing_wisdom"
    ]
    for key in required_keys:
        if key not in llm_response:
            llm_response[key] = {} if key != "dasha_life_map" else []

    # 6. Cache and return
    _save_cache(
        base_chart_id, llm_response, provider, model,
        prompt_tokens, completion_tokens, total_tokens, None
    )

    return {"interpretation": llm_response, "cached": False}
