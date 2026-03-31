# app/engines/family_prediction_engine.py
"""
Family Prediction Engine.
Assembles multi-member chart context, calls LLM once per group per year,
parses and returns structured family prediction. Caches in family_predictions.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.engines.budget_guard import log_llm_call
from app.engines.dasha_resolver import resolve_antar_dasha
from app.engines.sade_sati_engine import compute_sade_sati

logger = logging.getLogger(__name__)

# Model matches the rest of the codebase
FAMILY_PREDICTION_MODEL = "claude-sonnet-4-6"

# Load prompt once at module level
_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "family_prediction_prompt.txt"
try:
    FAMILY_PROMPT = _PROMPT_PATH.read_text()
except Exception as e:
    logger.error(f"Failed to load family prediction prompt: {e}")
    FAMILY_PROMPT = "You are Jyotishi. Return a valid JSON family prediction."


def _extract_nakshatra_name(moon: dict) -> str:
    """Extract nakshatra name from moon dict — handles dict or string."""
    nak_raw = moon.get("nakshatra", {})
    if isinstance(nak_raw, dict):
        return nak_raw.get("name", "")
    return str(nak_raw) if nak_raw else ""


def _build_family_context(group: dict, members_with_charts: list, year: int) -> str:
    """
    Assemble all member chart data into a single context string for the LLM.

    members_with_charts: list of dicts, each with:
      "member": family_members row dict (role, display_name, ...)
      "payload": parsed chart payload dict
    """
    now = datetime.now(timezone.utc)

    lines = [
        f"Family Group: {group['name']}",
        f"Prediction Year: {year}",
        f"Members: {len(members_with_charts)}",
        "",
    ]

    husband_present = any(i["member"]["role"] == "husband" for i in members_with_charts)
    wife_present = any(i["member"]["role"] == "wife" for i in members_with_charts)

    for item in members_with_charts:
        member = item["member"]
        payload = item["payload"]
        role = member.get("role", "other")
        birth = payload.get("birth_details", {}) if isinstance(payload, dict) else {}
        name = member.get("display_name") or birth.get("name", role)

        # Moon nakshatra + rasi
        ephemeris = payload.get("ephemeris", {}) if isinstance(payload, dict) else {}
        moon = ephemeris.get("moon", {}) if isinstance(ephemeris, dict) else {}
        nakshatra = _extract_nakshatra_name(moon)
        rasi = moon.get("rasi", "") if isinstance(moon, dict) else ""

        # Current Dasha — resolve_antar_dasha returns {"maha": {...}, "antar": {...}}
        maha_lord = "—"
        antar_lord = "—"
        antar_end = ""
        try:
            vimshottari = (
                payload.get("dashas", {}).get("vimshottari", {})
                if isinstance(payload, dict) else {}
            )
            resolved = resolve_antar_dasha(vimshottari=vimshottari, reference_date=now)
            if resolved:
                maha_lord = resolved["maha"]["lord"] or "—"
                antar_lord = resolved["antar"]["lord"] or "—"
                antar_end = resolved["antar"].get("end", "")
        except Exception as e:
            logger.warning(f"Dasha resolution failed for {name}: {e}")

        # Sade Sati
        ss_active = False
        ss_phase = ""
        try:
            ss_result = compute_sade_sati(payload)
            if isinstance(ss_result, dict):
                ss = ss_result.get("sade_sati", {})
                if isinstance(ss, dict) and ss.get("active"):
                    ss_active = True
                    ss_phase = ss.get("phase", "")
        except Exception as e:
            logger.warning(f"Sade Sati computation failed for {name}: {e}")

        lines += [
            f"--- {role.upper()}: {name} ---",
            f"Nakshatra: {nakshatra or 'unknown'}",
            f"Rasi: {rasi or 'unknown'}",
            f"Date of Birth: {birth.get('date_of_birth', 'unknown')}",
            f"Current Mahadasha: {maha_lord}",
            f"Current Antardasha: {antar_lord}",
            f"Antardasha ends: {antar_end[:10] if antar_end else 'unknown'}",
            f"Sade Sati: {'Active (' + ss_phase + ' phase)' if ss_active else 'Not active'}",
            "",
        ]

    if husband_present and wife_present:
        lines += [
            "--- PORUTHAM ---",
            "Note: Husband and wife charts are both present.",
            "Factor Kuta compatibility into financial and relationship caution analysis.",
            "",
        ]

    return "\n".join(lines)


def run_family_prediction(
    group: dict,
    members_with_charts: list,
    year: int,
    db,
) -> dict:
    """
    Main entry point. Checks cache first, runs LLM if cache miss.
    Returns parsed prediction dict. Caller is responsible for the db connection.
    """
    group_id = group["id"]

    # ── Cache check (same pattern as prediction_yearly.py) ───────────────────
    try:
        existing = db.execute("""
            SELECT id, executive_summary, financial_peaks, caution_windows,
                   child_milestones, raw_response
            FROM family_predictions
            WHERE group_id = ? AND year = ?
        """, [group_id, year]).fetchone()
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")
        existing = None

    if existing:
        try:
            raw = existing[5]
            raw_dict = (raw if isinstance(raw, dict) else json.loads(raw or "{}")) if raw else {}
            return {
                "cached": True,
                "group_id": group_id,
                "year": year,
                "executive_summary": existing[1] or "",
                "financial_peaks": _safe_json_list(existing[2]),
                "caution_windows": _safe_json_list(existing[3]),
                "child_milestones": _safe_json_list(existing[4]),
                "key_takeaways": raw_dict.get("key_takeaways", []),
            }
        except Exception as e:
            logger.warning(f"Failed to deserialise cached prediction: {e}")

    # ── Check LLM budget ─────────────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "LLM not configured — ANTHROPIC_API_KEY missing", "cached": False}

    try:
        budget_row = db.execute(
            "SELECT llm_enabled, paused_reason FROM llm_budget WHERE id = 1"
        ).fetchone()
        if budget_row and not budget_row[0]:
            return {
                "error": f"LLM paused: {budget_row[1] or 'budget'}",
                "cached": False,
            }
    except Exception as e:
        logger.warning(f"Budget check failed: {e}")

    # ── Build context ─────────────────────────────────────────────────────────
    context = _build_family_context(group, members_with_charts, year)
    user_message = (
        f"Here is the family chart data for analysis:\n\n{context}\n\n"
        f"Generate the family prediction JSON for {year} following the schema "
        f"in your instructions exactly. Return only valid JSON."
    )

    # ── LLM call (same pattern as anthropic_provider.py) ─────────────────────
    input_tokens = 0
    output_tokens = 0
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=FAMILY_PREDICTION_MODEL,
            max_tokens=4000,
            system=FAMILY_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        raw_text = response.content[0].text
    except Exception as e:
        logger.error(f"Family prediction LLM call failed: {e}")
        try:
            log_llm_call(
                db=db,
                chart_id=group_id,
                call_type="family_prediction",
                period=f"family_yearly/{year}",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                status="error",
                fallback_reason=str(e)[:100],
            )
        except Exception:
            pass
        return {"error": f"LLM call failed: {str(e)[:200]}", "cached": False}

    # ── Log success ───────────────────────────────────────────────────────────
    try:
        log_llm_call(
            db=db,
            chart_id=group_id,
            call_type="family_prediction",
            period=f"family_yearly/{year}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            status="success",
        )
    except Exception as e:
        logger.warning(f"log_llm_call failed: {e}")

    # ── Parse response (defensive markdown strip) ─────────────────────────────
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
        logger.error(f"JSON parse error for family prediction: {e}\nRaw: {clean[:200]}")
        try:
            log_llm_call(
                db=db,
                chart_id=group_id,
                call_type="family_prediction",
                period=f"family_yearly/{year}",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                status="error",
                fallback_reason="json_parse_error",
            )
        except Exception:
            pass
        return {"error": "Failed to parse LLM response", "cached": False}

    # ── Persist to cache (INSERT ... ON CONFLICT DO UPDATE — PostgreSQL) ──────
    prediction_id = str(uuid.uuid4())
    try:
        db.execute("""
            INSERT INTO family_predictions
                (id, group_id, year, raw_response, financial_peaks,
                 caution_windows, child_milestones, executive_summary,
                 llm_tokens_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (group_id, year) DO UPDATE SET
                id = EXCLUDED.id,
                raw_response = EXCLUDED.raw_response,
                financial_peaks = EXCLUDED.financial_peaks,
                caution_windows = EXCLUDED.caution_windows,
                child_milestones = EXCLUDED.child_milestones,
                executive_summary = EXCLUDED.executive_summary,
                llm_tokens_used = EXCLUDED.llm_tokens_used,
                created_at = CURRENT_TIMESTAMP
        """, [
            prediction_id,
            group_id,
            year,
            json.dumps(parsed),
            json.dumps(parsed.get("financial_peaks", [])),
            json.dumps(parsed.get("caution_windows", [])),
            json.dumps(parsed.get("child_milestones", [])),
            parsed.get("executive_summary", ""),
            input_tokens + output_tokens,
        ])
    except Exception as e:
        logger.error(f"Failed to persist family prediction: {e}")

    return {
        "cached": False,
        "group_id": group_id,
        "year": year,
        "executive_summary": parsed.get("executive_summary", ""),
        "financial_peaks": parsed.get("financial_peaks", []),
        "caution_windows": parsed.get("caution_windows", []),
        "child_milestones": parsed.get("child_milestones", []),
        "key_takeaways": parsed.get("key_takeaways", []),
    }


def _safe_json_list(val) -> list:
    """Safely parse a JSON list from a DB column (string or already a list)."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    try:
        result = json.loads(val)
        return result if isinstance(result, list) else []
    except Exception:
        return []
