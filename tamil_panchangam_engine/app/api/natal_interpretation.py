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

PROMPT_VERSION = "natal_v1.0"
FEATURE_NAME = "natal_interpretation"

NATAL_SYSTEM_PROMPT = """You are a classical Tamil Jyotish astrologer of the Siddhar tradition. \
Generate a profound natal chart interpretation for this person based on their birth chart data.

Return ONLY valid JSON — no markdown fences, no preamble, no explanation outside the JSON object."""

NATAL_USER_TEMPLATE = """Birth Chart Data:
{chart_context}

Generate a natal interpretation with this EXACT JSON schema:
{{
  "engine_version": "natal-v1.0",
  "life_theme": {{
    "title": "2-4 word poetic title for this life",
    "narrative": "3-4 sentences on the core karmic theme of this birth chart"
  }},
  "chart_highlights": {{
    "lagna_interpretation": "2-3 sentences on Lagna lord and ascendant sign meaning",
    "moon_interpretation": "2-3 sentences on Moon sign and nakshatra",
    "strongest_influence": "2-3 sentences on the strongest planet and its life impact",
    "key_yoga_impact": "2-3 sentences on the most significant yoga in the chart"
  }},
  "life_areas": {{
    "career": "2-3 sentences on career potential from D10 and 10th house",
    "wealth": "2-3 sentences on financial patterns from 2nd/11th house",
    "relationships": "2-3 sentences on relationship patterns from 7th house",
    "health": "2-3 sentences on health tendencies from Lagna and 6th house",
    "spirituality": "2-3 sentences on spiritual path from 9th/12th house and Ketu"
  }},
  "dasha_life_map": [
    {{
      "mahadasha": "planet name",
      "approximate_age": "age range e.g. 0-16",
      "theme": "1 sentence on what this Dasha period brings in this person's life"
    }}
  ],
  "closing_wisdom": "2-3 sentences of Siddhar-tradition closing wisdom for this soul's journey"
}}

Include ALL remaining Dashas from birth onward in dasha_life_map. Be specific to their chart, not generic. Return ONLY the JSON."""


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
        "engine_version": "natal-v1.0",
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
        max_tokens=2500,
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
    required_keys = ["life_theme", "chart_highlights", "life_areas", "dasha_life_map", "closing_wisdom"]
    for key in required_keys:
        if key not in llm_response:
            llm_response[key] = {} if key != "dasha_life_map" else []

    # 6. Cache and return
    _save_cache(
        base_chart_id, llm_response, provider, model,
        prompt_tokens, completion_tokens, total_tokens, None
    )

    return {"interpretation": llm_response, "cached": False}
