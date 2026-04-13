# app/engines/children_timing_engine.py
"""
Children Timing Engine.
Analyzes 5th house, Jupiter placement, and Dasha windows across
husband and wife charts to identify favorable periods for having children.
Cache: family_children_timing table, keyed by (group_id, year_from, year_to).
"""

import json
import logging
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from app.engines.budget_guard import log_llm_call
from app.engines.dasha_resolver import resolve_antar_dasha
from app.engines.porutham_engine import _rasi_index
from app.engines.sade_sati_engine import compute_sade_sati

logger = logging.getLogger(__name__)

CHILDREN_TIMING_MODEL = "claude-sonnet-4-6"

_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "children_timing_prompt.txt"
try:
    CHILDREN_TIMING_PROMPT = _PROMPT_PATH.read_text()
except Exception as e:
    logger.error(f"Failed to load children timing prompt: {e}")
    CHILDREN_TIMING_PROMPT = "You are Jyotishi. Return a valid JSON children timing prediction."

# Rasi lord mapping: 0=Aries...11=Pisces
RASI_LORDS = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon", 4: "Sun",
    5: "Mercury", 6: "Venus", 7: "Mars", 8: "Jupiter",
    9: "Saturn", 10: "Saturn", 11: "Jupiter",
}


def _get_5th_lord(rasi_index: int) -> str:
    fifth_sign = (rasi_index + 4) % 12
    return RASI_LORDS[fifth_sign]


def _find_planet_dashas(vimshottari, planet: str, year_from: int, year_to: int) -> list:
    """
    Find Dasha periods where planet is Maha or Antar lord, within year range.
    Returns list of {from, to, level, lord} dicts.

    vimshottari is a dict with "timeline" key. Each entry has:
      mahadasha, start, end, antar_dashas: [{antar_lord, start, end}]
    """
    results = []
    if not vimshottari or not isinstance(vimshottari, dict):
        return results
    range_start = date(year_from, 1, 1)
    range_end = date(year_to, 12, 31)

    timeline = vimshottari.get("timeline", [])
    for maha in timeline:
        if not isinstance(maha, dict):
            continue
        maha_lord = maha.get("mahadasha", "")
        maha_start_raw = maha.get("start", "")
        maha_end_raw = maha.get("end", "")
        try:
            maha_start = date.fromisoformat(str(maha_start_raw)[:10])
            maha_end = date.fromisoformat(str(maha_end_raw)[:10])
        except Exception:
            continue
        if maha_start > range_end or maha_end < range_start:
            continue
        if maha_lord == planet:
            results.append({
                "from": max(maha_start, range_start).isoformat(),
                "to": min(maha_end, range_end).isoformat(),
                "level": "mahadasha",
                "lord": maha_lord,
            })
        antar_dashas = maha.get("antar_dashas", [])
        for antar in (antar_dashas if isinstance(antar_dashas, list) else []):
            if not isinstance(antar, dict):
                continue
            antar_lord = antar.get("antar_lord", "")
            antar_start_raw = antar.get("start", "")
            antar_end_raw = antar.get("end", "")
            try:
                antar_start = date.fromisoformat(str(antar_start_raw)[:10])
                antar_end = date.fromisoformat(str(antar_end_raw)[:10])
            except Exception:
                continue
            if antar_start > range_end or antar_end < range_start:
                continue
            if antar_lord == planet:
                results.append({
                    "from": max(antar_start, range_start).isoformat(),
                    "to": min(antar_end, range_end).isoformat(),
                    "level": "antardasha",
                    "lord": antar_lord,
                })
    return results


def _build_children_timing_context(
    husband_payload: dict,
    wife_payload: dict,
    year_from: int,
    year_to: int,
) -> str:
    now = datetime.now(timezone.utc)
    lines = [f"Analysis Period: {year_from} to {year_to}", ""]

    for role, payload in [("husband", husband_payload), ("wife", wife_payload)]:
        birth = payload.get("birth_details", {}) if isinstance(payload, dict) else {}
        name = birth.get("name", role)
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

        fifth_lord = _get_5th_lord(rasi_index)
        fifth_lord_dashas = _find_planet_dashas(vimshottari, fifth_lord, year_from, year_to)
        jupiter_dashas = _find_planet_dashas(vimshottari, "Jupiter", year_from, year_to)

        try:
            ss_result = compute_sade_sati(payload)
            ss = ss_result.get("sade_sati", {}) if isinstance(ss_result, dict) else {}
            ss_active = ss.get("active", False) if isinstance(ss, dict) else False
            ss_phase = ss.get("phase_name", "") if isinstance(ss, dict) else ""
        except Exception:
            ss_active = False
            ss_phase = ""

        lines += [
            f"--- {role.upper()}: {name} ---",
            f"Nakshatra: {nakshatra or 'unknown'}, Rasi: {rasi or 'unknown'}",
            f"5th House Lord: {fifth_lord}",
            f"Current Mahadasha: {maha_lord}",
            f"Current Antardasha: {antar_lord}",
            f"Sade Sati: {'Active (' + str(ss_phase) + ')' if ss_active else 'Not active'}",
            f"5th Lord ({fifth_lord}) Dasha windows in {year_from}-{year_to}: {json.dumps(fifth_lord_dashas)}",
            f"Jupiter Dasha windows in {year_from}-{year_to}: {json.dumps(jupiter_dashas)}",
            "",
        ]
    return "\n".join(lines)


def run_children_timing(
    group_id: str,
    husband_payload: dict,
    wife_payload: dict,
    year_from: int,
    year_to: int,
    db,
) -> dict:
    """Cache check -> LLM -> persist -> return."""
    # Cache check (positional tuple access)
    try:
        existing = db.execute("""
            SELECT id, overall_outlook, combined_windows, jupiter_transits,
                   husband_5th_analysis, wife_5th_analysis, has_children_already, raw_response
            FROM family_children_timing
            WHERE group_id = ? AND year_from = ? AND year_to = ?
        """, [group_id, year_from, year_to]).fetchone()
    except Exception as e:
        logger.warning(f"Children timing cache check failed: {e}")
        existing = None

    if existing:
        try:
            raw = existing[7]
            raw_dict = (raw if isinstance(raw, dict) else json.loads(raw or "{}")) if raw else {}
            return {
                "cached": True,
                "group_id": group_id,
                "year_from": year_from,
                "year_to": year_to,
                "overall_outlook": existing[1] or "",
                "combined_windows": _safe_json_list(existing[2]),
                "jupiter_transits": _safe_json_list(existing[3]),
                "husband_5th_analysis": _safe_json_dict(existing[4]),
                "wife_5th_analysis": _safe_json_dict(existing[5]),
                "has_children_already": bool(existing[6]),
                "jupiter_insight": raw_dict.get("jupiter_insight", ""),
                "remedies": raw_dict.get("remedies", []),
            }
        except Exception as e:
            logger.warning(f"Failed to deserialise cached children timing: {e}")

    # Check if group already has child members
    has_children = False
    try:
        count_row = db.execute(
            "SELECT COUNT(*) FROM family_members WHERE group_id = ? AND role = 'child'",
            [group_id]
        ).fetchone()
        has_children = bool(count_row and count_row[0] > 0)
    except Exception:
        pass

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

    context = _build_children_timing_context(husband_payload, wife_payload, year_from, year_to)
    user_message = (
        f"Analyze this couple's Santana Bhagya for {year_from}-{year_to}:\n\n{context}\n\n"
        f"Return only valid JSON following the schema in your instructions."
    )

    input_tokens = output_tokens = 0
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=CHILDREN_TIMING_MODEL,
            max_tokens=2000,
            system=CHILDREN_TIMING_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        raw_text = response.content[0].text
    except Exception as e:
        logger.error(f"Children timing LLM call failed: {e}")
        try:
            log_llm_call(db=db, chart_id=group_id, call_type="children_timing",
                         period=f"children_timing/{year_from}-{year_to}",
                         input_tokens=input_tokens, output_tokens=output_tokens,
                         status="error", fallback_reason=str(e)[:100])
        except Exception:
            pass
        return {"error": f"LLM call failed: {str(e)[:200]}", "cached": False}

    try:
        log_llm_call(db=db, chart_id=group_id, call_type="children_timing",
                     period=f"children_timing/{year_from}-{year_to}",
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
        logger.error(f"JSON parse error for children timing: {e}")
        try:
            log_llm_call(db=db, chart_id=group_id, call_type="children_timing",
                         period=f"children_timing/{year_from}-{year_to}",
                         input_tokens=input_tokens, output_tokens=output_tokens,
                         status="error", fallback_reason="json_parse_error")
        except Exception:
            pass
        return {"error": "Failed to parse LLM response", "cached": False}

    prediction_id = str(uuid.uuid4())
    try:
        db.execute("""
            INSERT INTO family_children_timing
                (id, group_id, year_from, year_to, raw_response,
                 has_children_already, combined_windows, jupiter_transits,
                 overall_outlook, husband_5th_analysis, wife_5th_analysis,
                 llm_tokens_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (group_id, year_from, year_to) DO UPDATE SET
                raw_response = EXCLUDED.raw_response,
                combined_windows = EXCLUDED.combined_windows,
                jupiter_transits = EXCLUDED.jupiter_transits,
                overall_outlook = EXCLUDED.overall_outlook,
                husband_5th_analysis = EXCLUDED.husband_5th_analysis,
                wife_5th_analysis = EXCLUDED.wife_5th_analysis,
                llm_tokens_used = EXCLUDED.llm_tokens_used,
                created_at = CURRENT_TIMESTAMP
        """, [
            prediction_id, group_id, year_from, year_to,
            json.dumps(parsed), int(has_children),
            json.dumps(parsed.get("combined_windows", [])),
            json.dumps([]),
            parsed.get("overall_outlook", ""),
            json.dumps({}), json.dumps({}),
            input_tokens + output_tokens,
        ])
    except Exception as e:
        logger.error(f"Failed to persist children timing: {e}")

    return {
        "cached": False,
        "group_id": group_id,
        "year_from": year_from,
        "year_to": year_to,
        "has_children_already": has_children,
        "combined_windows": parsed.get("combined_windows", []),
        "jupiter_transits": [],
        "overall_outlook": parsed.get("overall_outlook", ""),
        "jupiter_insight": parsed.get("jupiter_insight", ""),
        "remedies": parsed.get("remedies", []),
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
