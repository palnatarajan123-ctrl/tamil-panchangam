# app/engines/child_prediction_engine.py
"""
Child Prediction Engine.
Generates per-child predictions: education, career aptitude,
marriage window, leaving home, health cautions.
Only valid for members with role='child'.
Cache: family_child_predictions table, keyed by (member_id, year).
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.engines.budget_guard import log_llm_call
from app.engines.dasha_resolver import resolve_antar_dasha
from app.engines.children_timing_engine import RASI_LORDS
from app.engines.porutham_engine import _rasi_index

logger = logging.getLogger(__name__)

CHILD_PREDICTION_MODEL = "claude-sonnet-4-6"

_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "child_prediction_prompt.txt"
try:
    CHILD_PREDICTION_PROMPT = _PROMPT_PATH.read_text()
except Exception as e:
    logger.error(f"Failed to load child prediction prompt: {e}")
    CHILD_PREDICTION_PROMPT = "You are Jyotishi. Return a valid JSON child prediction."


def _get_house_lord(moon_rasi_index: int, house_number: int) -> str:
    house_sign = (moon_rasi_index + house_number - 1) % 12
    return RASI_LORDS[house_sign]


def _build_child_context(payload: dict, year: int) -> str:
    now = datetime.now(timezone.utc)
    birth = payload.get("birth_details", {}) if isinstance(payload, dict) else {}
    ephemeris = payload.get("ephemeris", {}) if isinstance(payload, dict) else {}
    moon = ephemeris.get("moon", {}) if isinstance(ephemeris, dict) else {}
    nakshatra_raw = moon.get("nakshatra", {}) if isinstance(moon, dict) else {}
    nakshatra = nakshatra_raw.get("name", "") if isinstance(nakshatra_raw, dict) else str(nakshatra_raw)
    rasi = moon.get("rasi", "") if isinstance(moon, dict) else ""
    rasi_str = moon.get("rasi", "") if isinstance(moon, dict) else ""
    rasi_index = _rasi_index(rasi_str) or 0

    vimshottari = (
        payload.get("dashas", {}).get("vimshottari", {})
        if isinstance(payload, dict) else {}
    )
    try:
        resolved = resolve_antar_dasha(vimshottari=vimshottari, reference_date=now)
        maha_lord = resolved["maha"]["lord"] if resolved else "—"
        antar_lord = resolved["antar"]["lord"] if resolved else "—"
    except Exception:
        maha_lord = antar_lord = "—"

    houses = {
        "4th (Education)": _get_house_lord(rasi_index, 4),
        "5th (Intelligence)": _get_house_lord(rasi_index, 5),
        "10th (Career)": _get_house_lord(rasi_index, 10),
        "7th (Marriage)": _get_house_lord(rasi_index, 7),
        "12th (Leaving home)": _get_house_lord(rasi_index, 12),
    }

    lines = [
        f"Child Name: {birth.get('name', 'Child')}",
        f"Date of Birth: {birth.get('date_of_birth', 'unknown')}",
        f"Nakshatra: {nakshatra or 'unknown'}, Rasi: {rasi or 'unknown'}",
        f"Analysis Year: {year}",
        f"Current Mahadasha: {maha_lord}",
        f"Current Antardasha: {antar_lord}",
        "",
        "Key House Lords:",
    ]
    for house, lord in houses.items():
        lines.append(f"  {house}: {lord}")
    return "\n".join(lines)


def run_child_prediction(
    member_id: str,
    chart_payload: dict,
    year: int,
    db,
) -> dict:
    """Cache check -> LLM -> persist -> return."""
    # Cache check (positional tuple)
    try:
        existing = db.execute("""
            SELECT id, overall_narrative, education, career_aptitude,
                   marriage_window, leaving_home, health_cautions, key_takeaways, raw_response
            FROM family_child_predictions
            WHERE member_id = ? AND year = ?
        """, [member_id, year]).fetchone()
    except Exception as e:
        logger.warning(f"Child prediction cache check failed: {e}")
        existing = None

    if existing:
        try:
            return {
                "cached": True,
                "member_id": member_id,
                "year": year,
                "overall_narrative": existing[1] or "",
                "education": _safe_json_list(existing[2]),
                "career_aptitude": _safe_json_dict(existing[3]),
                "marriage_window": _safe_json_dict(existing[4]),
                "leaving_home": _safe_json_dict(existing[5]),
                "health_cautions": _safe_json_list(existing[6]),
                "key_takeaways": _safe_json_list(existing[7]),
            }
        except Exception as e:
            logger.warning(f"Failed to deserialise cached child prediction: {e}")

    # Budget check
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "LLM not configured — ANTHROPIC_API_KEY missing", "cached": False}
    try:
        budget_row = db.execute(
            "SELECT llm_enabled, paused_reason FROM llm_budget WHERE id = 1"
        ).fetchone()
        if budget_row and not budget_row[0]:
            return {"error": f"LLM paused: {budget_row[1] or 'budget'}", "cached": False}
    except Exception as e:
        logger.warning(f"Budget check failed: {e}")

    context = _build_child_context(chart_payload, year)
    user_message = (
        f"Analyze this child's chart for {year}:\n\n{context}\n\n"
        f"Return only valid JSON following the schema in your instructions."
    )

    input_tokens = output_tokens = 0
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=CHILD_PREDICTION_MODEL,
            max_tokens=3000,
            system=CHILD_PREDICTION_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        raw_text = response.content[0].text
    except Exception as e:
        logger.error(f"Child prediction LLM call failed: {e}")
        try:
            log_llm_call(db=db, chart_id=member_id, call_type="child_prediction",
                         period=f"child_yearly/{year}",
                         input_tokens=input_tokens, output_tokens=output_tokens,
                         status="error", fallback_reason=str(e)[:100])
        except Exception:
            pass
        return {"error": f"LLM call failed: {str(e)[:200]}", "cached": False}

    try:
        log_llm_call(db=db, chart_id=member_id, call_type="child_prediction",
                     period=f"child_yearly/{year}",
                     input_tokens=input_tokens, output_tokens=output_tokens,
                     status="success")
    except Exception as e:
        logger.warning(f"log_llm_call failed: {e}")

    clean = raw_text.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        if len(parts) >= 2:
            clean = parts[1]
            if clean.startswith("json"):
                clean = clean[4:]
    clean = clean.strip()

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error for child prediction: {e}")
        try:
            log_llm_call(db=db, chart_id=member_id, call_type="child_prediction",
                         period=f"child_yearly/{year}",
                         input_tokens=input_tokens, output_tokens=output_tokens,
                         status="error", fallback_reason="json_parse_error")
        except Exception:
            pass
        return {"error": "Failed to parse LLM response", "cached": False}

    pred_id = str(uuid.uuid4())
    try:
        db.execute("""
            INSERT INTO family_child_predictions
                (id, member_id, year, raw_response, education, career_aptitude,
                 marriage_window, leaving_home, health_cautions, key_takeaways,
                 overall_narrative, llm_tokens_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (member_id, year) DO UPDATE SET
                raw_response = EXCLUDED.raw_response,
                education = EXCLUDED.education,
                career_aptitude = EXCLUDED.career_aptitude,
                marriage_window = EXCLUDED.marriage_window,
                leaving_home = EXCLUDED.leaving_home,
                health_cautions = EXCLUDED.health_cautions,
                key_takeaways = EXCLUDED.key_takeaways,
                overall_narrative = EXCLUDED.overall_narrative,
                llm_tokens_used = EXCLUDED.llm_tokens_used,
                created_at = CURRENT_TIMESTAMP
        """, [
            pred_id, member_id, year,
            json.dumps(parsed),
            json.dumps(parsed.get("education", [])),
            json.dumps(parsed.get("career_aptitude", {})),
            json.dumps(parsed.get("marriage_window", {})),
            json.dumps(parsed.get("leaving_home", {})),
            json.dumps(parsed.get("health_cautions", [])),
            json.dumps(parsed.get("key_takeaways", [])),
            parsed.get("overall_narrative", ""),
            input_tokens + output_tokens,
        ])
    except Exception as e:
        logger.error(f"Failed to persist child prediction: {e}")

    return {
        "cached": False,
        "member_id": member_id,
        "year": year,
        "overall_narrative": parsed.get("overall_narrative", ""),
        "education": parsed.get("education", []),
        "career_aptitude": parsed.get("career_aptitude", {}),
        "marriage_window": parsed.get("marriage_window", {}),
        "leaving_home": parsed.get("leaving_home", {}),
        "health_cautions": parsed.get("health_cautions", []),
        "key_takeaways": parsed.get("key_takeaways", []),
    }


def _safe_json_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    try:
        r = json.loads(val)
        return r if isinstance(r, list) else []
    except Exception:
        return []


def _safe_json_dict(val) -> dict:
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    try:
        r = json.loads(val)
        return r if isinstance(r, dict) else {}
    except Exception:
        return {}
