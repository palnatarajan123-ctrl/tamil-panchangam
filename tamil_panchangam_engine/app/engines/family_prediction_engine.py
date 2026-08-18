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
from app.engines.porutham_engine import compute_porutham
from app.llm.payload_builder import _build_upagraha_context, _extract_nak_rasi

logger = logging.getLogger(__name__)

# Model matches the rest of the codebase
FAMILY_PREDICTION_MODEL = "claude-sonnet-4-6"

# family_predictions has no version-gating mechanism before this -- caching
# was keyed solely on (group_id, year), with no way to distinguish "cached
# under the current prompt/context" from "cached under an older one" (found
# during today's audit; documented explicitly in the commit that added
# yogas/upagraha/KP/predictive_signals context, since that content change
# would otherwise have silently done nothing for any group with an existing
# cached row for the current year). "family_v1.0" is the implicit,
# never-labeled state before that change; "family_v2.0" marks the addition
# of per-member yogas/upagraha/KP/predictive_signals context -- same
# significance bump as v5->v6 in the individual weekly/monthly/yearly
# prompts when upagraha context was added there.
PROMPT_VERSION = "family_v2.0"

# Load prompt once at module level
_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "family_prediction_prompt.txt"
try:
    FAMILY_PROMPT = _PROMPT_PATH.read_text()
except Exception as e:
    logger.error(f"Failed to load family prediction prompt: {e}")
    FAMILY_PROMPT = "You are Jyotishi. Return a valid JSON family prediction."


def _get_or_compute_porutham(
    db, group_id: str,
    husband_id: Optional[str], husband_name: str, husband_nak: str, husband_rasi: str,
    wife_id: Optional[str], wife_name: str, wife_nak: str, wife_rasi: str,
) -> Optional[dict]:
    """
    Cache-first Porutham lookup -- reuses family_porutham_cache, the same
    table and order-independent (group_id, member_id_1, member_id_2) key
    the dedicated GET /groups/{group_id}/porutham endpoint uses, so this
    never recomputes (or diverges from) what that endpoint would return
    for the same pair. On a cache miss, computes and writes back in the
    EXACT shape the endpoint itself writes (husband/wife dicts each with
    name+nakshatra+rasi, not just nakshatra+rasi) -- the cache is genuinely
    shared both ways, so writing a narrower shape here would silently break
    the endpoint's own read path (its response includes "name", and
    PoruthTab renders husband?.name || "Husband": found this exact bug
    live while testing this function against a cache-miss group, where a
    name-less write here caused a subsequent /porutham call to render the
    fallback "Husband"/"Wife" labels instead of the real names).

    Returns just the "porutham" breakdown dict (total_score/grade/points/...),
    or None if nak/rasi data or member ids are missing.
    """
    if not husband_id or not wife_id or not husband_nak or not husband_rasi \
            or not wife_nak or not wife_rasi:
        return None

    try:
        cached_row = db.execute("""
            SELECT result_json FROM family_porutham_cache
            WHERE group_id = ?
              AND ((member_id_1 = ? AND member_id_2 = ?)
                OR (member_id_1 = ? AND member_id_2 = ?))
            LIMIT 1
        """, [group_id, husband_id, wife_id, wife_id, husband_id]).fetchone()
        if cached_row:
            cached = cached_row[0] if isinstance(cached_row[0], dict) else json.loads(cached_row[0])
            return cached.get("porutham")
    except Exception as e:
        logger.warning(f"Porutham cache check failed: {e}")

    try:
        porutham_result = compute_porutham(
            boy_nakshatra=husband_nak, boy_rasi=husband_rasi,
            girl_nakshatra=wife_nak, girl_rasi=wife_rasi,
        )
        full_result = {
            "husband": {"name": husband_name, "nakshatra": husband_nak, "rasi": husband_rasi},
            "wife": {"name": wife_name, "nakshatra": wife_nak, "rasi": wife_rasi},
            "porutham": porutham_result,
        }
        db.execute("""
            INSERT INTO family_porutham_cache (group_id, member_id_1, member_id_2, result_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (group_id, member_id_1, member_id_2) DO UPDATE
            SET result_json = EXCLUDED.result_json, computed_at = NOW()
        """, [group_id, husband_id, wife_id, json.dumps(full_result)])
        return porutham_result
    except Exception as e:
        logger.warning(f"Porutham compute/cache-write failed: {e}")
        return None


def _build_family_context(group: dict, members_with_charts: list, year: int, db) -> str:
    """
    Assemble all member chart data into a single context string for the LLM.

    members_with_charts: list of dicts, each with:
      "member": family_members row dict (role, display_name, id, ...)
      "payload": parsed chart payload dict
    db: connection for the Porutham cache lookup (see PORUTHAM section below)
        -- reuses family_porutham_cache, same table/key shape as the
        dedicated /porutham endpoint, so this never diverges from what
        that endpoint would return for the same pair.
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
    husband_item = next((i for i in members_with_charts if i["member"]["role"] == "husband"), None)
    wife_item = next((i for i in members_with_charts if i["member"]["role"] == "wife"), None)

    for item in members_with_charts:
        member = item["member"]
        payload = item["payload"]
        role = member.get("role", "other")
        birth = payload.get("birth_details", {}) if isinstance(payload, dict) else {}
        name = member.get("display_name") or birth.get("name", role)

        # Moon nakshatra + rasi -- shared extraction with family.py's
        # /porutham endpoint and the PORUTHAM section below, so a couple's
        # nak/rasi can never silently diverge between what this prediction
        # sees and what a direct Porutham check would compute.
        nakshatra, rasi = _extract_nak_rasi(payload if isinstance(payload, dict) else {})

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
                    ss_phase = ss.get("phase_name", "")
        except Exception as e:
            logger.warning(f"Sade Sati computation failed for {name}: {e}")

        # Yogas — present/active yoga names, pre-filtered and stored by yoga_engine
        yoga_names = []
        try:
            yogas_data = payload.get("yogas", {}) if isinstance(payload, dict) else {}
            if isinstance(yogas_data, dict) and not yogas_data.get("error"):
                yoga_names = yogas_data.get("summary", {}).get("yoga_names", []) or []
        except Exception as e:
            logger.warning(f"Yoga extraction failed for {name}: {e}")

        # Upagraha (Gulika/Mandi) — reuse the same extraction used by chat/natal
        gulika_rasi = ""
        gulika_lord = ""
        try:
            upagraha_ctx = _build_upagraha_context(payload.get("upagrahas", {}) if isinstance(payload, dict) else {})
            gulika_rasi = upagraha_ctx.get("gulika_rasi", "")
            gulika_lord = upagraha_ctx.get("gulika_lord", "")
        except Exception as e:
            logger.warning(f"Upagraha extraction failed for {name}: {e}")

        # KP sub-lords — natal-only, optional (most charts won't have it)
        kp_note = ""
        try:
            kp_sublords = payload.get("kp_sublords") if isinstance(payload, dict) else None
            if kp_sublords:
                cuspal = kp_sublords.get("cuspal_significators", {})
                wealth_sigs = cuspal.get("2", []) or cuspal.get("11", [])
                if wealth_sigs:
                    kp_note = f"KP wealth-house significators: {', '.join(wealth_sigs[:4])}"
        except Exception as e:
            logger.warning(f"KP extraction failed for {name}: {e}")

        # Predictive signals — active yogas + event windows relevant to THIS
        # prediction year only (v7 monthly-signal data, not year-scoped by
        # default, so filter defensively rather than dumping everything)
        active_yoga_names = []
        year_event_windows = []
        try:
            ps = payload.get("predictive_signals", {}) if isinstance(payload, dict) else {}
            if isinstance(ps, dict):
                active_yoga_names = [
                    y.get("name", "") for y in ps.get("active_yogas", [])
                    if isinstance(y, dict) and y.get("currently_active") and y.get("name")
                ]
                for w in ps.get("event_windows", []):
                    if not isinstance(w, dict):
                        continue
                    if w.get("confidence") not in ("high", "very high"):
                        continue
                    w_start = str(w.get("window_start", ""))
                    if w_start.startswith(str(year)):
                        year_event_windows.append(w)
        except Exception as e:
            logger.warning(f"Predictive signals extraction failed for {name}: {e}")

        lines += [
            f"--- {role.upper()}: {name} ---",
            f"Nakshatra: {nakshatra or 'unknown'}",
            f"Rasi: {rasi or 'unknown'}",
            f"Date of Birth: {birth.get('date_of_birth', 'unknown')}",
            f"Current Mahadasha: {maha_lord}",
            f"Current Antardasha: {antar_lord}",
            f"Antardasha ends: {antar_end[:10] if antar_end else 'unknown'}",
            f"Sade Sati: {'Active – ' + ss_phase if ss_active else 'Not active'}",
        ]
        if yoga_names:
            lines.append(f"Present Yogas: {', '.join(yoga_names)}")
        if gulika_rasi:
            lines.append(
                "Gulika (karmic shadow point): " + gulika_rasi
                + (f", ruled by {gulika_lord}" if gulika_lord else "")
            )
        if kp_note:
            lines.append(kp_note)
        if active_yoga_names:
            lines.append(f"Currently Active Yogas ({year}): {', '.join(active_yoga_names[:5])}")
        if year_event_windows:
            window_parts = []
            for w in year_event_windows[:3]:
                label = f"{w.get('window_start', '')} to {w.get('window_end', '')}"
                area = str(w.get("life_area", "")).replace("_", " ")
                direction = w.get("direction", "")
                window_parts.append(f"{label} ({area}, {direction})")
            lines.append(f"High-Confidence Windows ({year}): " + " | ".join(window_parts))
        lines.append("")

    if husband_present and wife_present and husband_item and wife_item:
        porutham = None
        try:
            husband_member = husband_item["member"]
            wife_member = wife_item["member"]
            husband_id = husband_member.get("id")
            wife_id = wife_member.get("id")
            husband_payload = husband_item["payload"] if isinstance(husband_item["payload"], dict) else {}
            wife_payload = wife_item["payload"] if isinstance(wife_item["payload"], dict) else {}
            husband_name = husband_member.get("display_name") or husband_payload.get("birth_details", {}).get("name", "husband")
            wife_name = wife_member.get("display_name") or wife_payload.get("birth_details", {}).get("name", "wife")
            husband_nak, husband_rasi = _extract_nak_rasi(husband_payload)
            wife_nak, wife_rasi = _extract_nak_rasi(wife_payload)
            porutham = _get_or_compute_porutham(
                db, group["id"], husband_id, husband_name, husband_nak, husband_rasi,
                wife_id, wife_name, wife_nak, wife_rasi,
            )
        except Exception as e:
            logger.warning(f"Porutham lookup failed: {e}")

        # No result -> no section at all. Not falling back to a generic
        # "factor compatibility" note: that's exactly the ungrounded text
        # this replaces, and re-adding it here would make the LLM's output
        # LOOK grounded in real compatibility data when it isn't.
        if porutham and not porutham.get("error"):
            mandatory_fails = [
                p["name"] for p in porutham.get("points", [])
                if p.get("mandatory") and not p.get("pass")
            ]
            category_parts = []
            for p in porutham.get("points", []):
                if p.get("max", 0) > 0:
                    category_parts.append(f"{p['name']} {p['score']}/{p['max']}")
                else:
                    category_parts.append(f"{p['name']} {'pass' if p.get('pass') else 'FAIL'}")
            lines += [
                "--- PORUTHAM (Husband x Wife compatibility, 10-point Tamil Kuta system) ---",
                f"Score: {porutham.get('total_score')}/{porutham.get('max_score')} "
                f"({porutham.get('percent')}%) — {porutham.get('grade')}",
                "Mandatory categories: " + (
                    "all passed" if not mandatory_fails
                    else "FAILED: " + ", ".join(mandatory_fails)
                ),
                "Category breakdown: " + ", ".join(category_parts),
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
    # Filters on prompt_version so a row cached under an older prompt/context
    # version is correctly treated as a cache miss and regenerated, rather
    # than silently served stale -- same mechanism as natal_v2.2's fix.
    try:
        existing = db.execute("""
            SELECT id, executive_summary, financial_peaks, caution_windows,
                   child_milestones, raw_response
            FROM family_predictions
            WHERE group_id = ? AND year = ? AND prompt_version = ?
        """, [group_id, year, PROMPT_VERSION]).fetchone()
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
    context = _build_family_context(group, members_with_charts, year, db)
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
    # UNIQUE constraint stays (group_id, year) -- deliberately not widened to
    # include prompt_version. Product intent is "one current prediction per
    # group per year," not a history of versions; a regeneration under a new
    # prompt_version overwrites the single row for that group/year, same as
    # it always has. prompt_version is stored so the cache CHECK above can
    # tell current from stale, not to preserve old-version rows.
    prediction_id = str(uuid.uuid4())
    try:
        db.execute("""
            INSERT INTO family_predictions
                (id, group_id, year, raw_response, financial_peaks,
                 caution_windows, child_milestones, executive_summary,
                 llm_tokens_used, prompt_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (group_id, year) DO UPDATE SET
                id = EXCLUDED.id,
                raw_response = EXCLUDED.raw_response,
                financial_peaks = EXCLUDED.financial_peaks,
                caution_windows = EXCLUDED.caution_windows,
                child_milestones = EXCLUDED.child_milestones,
                executive_summary = EXCLUDED.executive_summary,
                llm_tokens_used = EXCLUDED.llm_tokens_used,
                prompt_version = EXCLUDED.prompt_version,
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
            PROMPT_VERSION,
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
