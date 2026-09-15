# app/engines/llm_interpretation_orchestrator.py
"""
LLM Interpretation Orchestrator v1.0

Coordinates LLM-based language interpretation for astrology predictions.
Handles:
- Admin LLM disabled flag check
- Cache reuse
- Token limit enforcement
- Monthly budget enforcement
- OpenAI API calls
- Schema validation
- Persistence
- Deterministic fallback

The LLM is ONLY for language generation - all astrology is pre-computed.
"""

import uuid
import logging
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Literal

from app.db.postgres import get_conn
from app.engines.budget_guard import log_llm_call
from app.llm.token_estimator import check_token_limits, get_max_completion_tokens
from app.llm.providers import anthropic_provider as openai_provider  # openai_provider alias kept for internal references
from app.llm.payload_builder import (
    build_llm_payload,
    validate_payload_size,
    extract_payload_inputs,
    MAX_COMPLETION_TOKENS
)

logger = logging.getLogger(__name__)

LLM_MONTHLY_TOKEN_BUDGET = 3_500_000
# EMERGENCY RAISE, active through the 2026-09-30/10-01 monthly reset
# only -- was 1_000_000. A manual backfill run (Karana/Ashtakavarga/
# top_signals fixes, see CLAUDE.md) pushed real month-to-date usage to
# 1,014,767, exceeding the original cap and causing real users'
# concurrent monthly/yearly/weekly generation requests to silently fall
# back to deterministic-only content (fallback_reason="budget_exceeded")
# with no user-facing indication, in addition to stalling the backfill
# itself. Sized to cover, for the rest of September 2026: already-used
# tokens at the time of the raise (1,014,767) + projected remaining
# organic traffic + the full backfill completion (Ashtakavarga's
# remaining rows + the top_signals fix's 76-row backfill) + margin --
# see CLAUDE.md's 2026-09-15 entries for the full calculation and the
# actual final total (2,543,833 used by the time all backfill work
# finished). Requires the deploy running this code to actually restart/
# redeploy before it takes effect for live traffic -- a source change
# alone does not affect an already-running process.
#
# DECIDED PERMANENT VALUE: 1_500_000/month, effective from the next
# monthly reset (2026-10-01) onward -- NOT applied yet. Real Sept 1-14
# organic-only usage (428,763 tokens over 4 active days out of 14)
# extrapolates to a worst-case ~918,780/month if that rate held for a
# full 30-day month, which would leave the ORIGINAL 1,000,000 cap only
# ~8% headroom with zero room for admin/backfill work or growth --
# 1,500,000 restores a genuine ~58% margin over that worst case. Do NOT
# apply 1,500,000 before the October reset: September's cumulative usage
# already exceeds it from this backfill alone, so setting it now would
# immediately re-trigger the same real-user-facing fallback this raise
# was meant to fix. Whoever owns this constant needs to make this change
# manually at/after 2026-10-01 -- no automation exists for it (see
# CLAUDE.md's admin-visibility backlog entry, itself a product of this
# incident having no alerting until it was hit by accident).

# v2.0: Upagraha context added (Gulika/Mandi)
PROMPT_VERSION_BY_WINDOW = {
    "weekly": "v6",
    "monthly": "v7",
    "yearly": "v7"
}
PROMPT_VERSION = "v7"  # fallback


def _load_prompt_template(version: str = "v2") -> str:
    """Load the interpretation prompt template."""
    prompt_file = f"interpretation_prompt_{version}.txt"
    prompt_paths = [
        Path(__file__).parent.parent / "llm" / "prompts" / prompt_file,
        Path(f"tamil_panchangam_engine/app/llm/prompts/{prompt_file}"),
    ]
    
    for path in prompt_paths:
        if path.exists():
            return path.read_text()
    
    return "You are a narrative assistant. Return JSON matching the schema."


def is_llm_enabled() -> bool:
    """
    THE single source of truth for "may any LLM call be made right now,
    anywhere in the app." Every LLM-calling code path -- a route handler,
    the orchestrator itself, a background regeneration task -- must check
    this, and only this, before doing any LLM-related work. No per-module
    reimplementation, no raw SQL against either table below, no locally
    cached copy of either flag.

    Consolidated 2026-09-11 (Part A of the stale-fallback-cache follow-up):
    two independent flags previously existed with no single function
    combining them --
      - llm_config.llm_enabled: the admin's manual on/off toggle
        (admin_llm.py's /toggle route, via set_llm_enabled() below).
      - llm_budget.llm_enabled: the automatic spend-based auto-pause,
        set by budget_guard._check_budget() when monthly $ spend crosses
        the configured threshold.
    /toggle already best-effort syncs both on a manual flip (see its own
    comment), but that sync is wrapped in a swallowed exception -- a
    fresh source of ambiguity if it ever silently failed. Three call
    sites (chat.py once, family.py twice) were independently re-querying
    llm_budget.llm_enabled directly via raw SQL as their OWN gate,
    bypassing this function and its (previously nonexistent) awareness of
    the budget-auto-pause condition entirely -- meaning natal-
    interpretation/kp-interpretation/daily/monthly/yearly, which DID
    already call this function, were never actually honoring the
    budget-auto-pause either, only the manual toggle. Returns False if
    EITHER source says off -- true only if both agree the LLM may run.
    """
    try:
        with get_conn() as conn:
            config_row = conn.execute(
                "SELECT value FROM llm_config WHERE key = 'llm_enabled'"
            ).fetchone()
            manually_enabled = config_row[0].lower() == "true" if config_row else True

            budget_row = conn.execute(
                "SELECT llm_enabled FROM llm_budget WHERE id = 1"
            ).fetchone()
            budget_enabled = bool(budget_row[0]) if budget_row else True

            return manually_enabled and budget_enabled
    except Exception as e:
        logger.warning(f"Failed to check LLM config: {e}")
    return True


def get_llm_pause_reason() -> Optional[str]:
    """The human-facing reason the LLM is currently paused, if it is --
    'manual' (admin toggle) or 'budget_exceeded' (auto-pause), mirroring
    llm_budget.paused_reason. A details lookup for user-facing messaging
    ONLY -- never use this for a gating decision, that's is_llm_enabled()'s
    job exclusively. Returns None if the LLM is currently enabled or the
    reason can't be determined."""
    if is_llm_enabled():
        return None
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT paused_reason FROM llm_budget WHERE id = 1"
            ).fetchone()
            if row and row[0]:
                return row[0]
    except Exception as e:
        logger.warning(f"Failed to read LLM pause reason: {e}")
    return "manual"


def set_llm_enabled(enabled: bool) -> bool:
    """Set LLM enabled/disabled state."""
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO llm_config (key, value, updated_at)
                VALUES ('llm_enabled', ?, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET 
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                ["true" if enabled else "false"]
            )
            return True
    except Exception as e:
        logger.error(f"Failed to set LLM config: {e}")
        return False


def get_monthly_token_usage() -> Dict[str, Any]:
    """Get token usage for current month."""
    try:
        with get_conn() as conn:
            result = conn.execute("""
                SELECT COALESCE(SUM(total_tokens), 0) AS tokens_used
                FROM llm_token_usage
                WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
            """).fetchone()
            
            tokens_used = int(result[0]) if result else 0
            
            return {
                "budget": LLM_MONTHLY_TOKEN_BUDGET,
                "used": tokens_used,
                "remaining": max(0, LLM_MONTHLY_TOKEN_BUDGET - tokens_used),
                "percent_used": round((tokens_used / LLM_MONTHLY_TOKEN_BUDGET) * 100, 1)
            }
    except Exception as e:
        logger.error(f"Failed to get token usage: {e}")
        return {
            "budget": LLM_MONTHLY_TOKEN_BUDGET,
            "used": 0,
            "remaining": LLM_MONTHLY_TOKEN_BUDGET,
            "percent_used": 0.0
        }


def _check_cache(
    base_chart_id: str,
    period_type: str,
    period_key: str,
    feature_name: str,
    prompt_version: str,
    explainability_mode: str = "standard"
) -> Optional[Dict[str, Any]]:
    """Check for cached LLM interpretation. Cache key includes explainability_mode (v1.9)."""
    try:
        with get_conn() as conn:
            result = conn.execute("""
                SELECT content_json, fallback_reason FROM prediction_llm_interpretation
                WHERE base_chart_id = ?
                AND period_type = ?
                AND period_key = ?
                AND feature_name = ?
                AND prompt_version = ?
                AND COALESCE(explainability_mode, 'standard') = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, [base_chart_id, period_type, period_key, feature_name, prompt_version, explainability_mode]).fetchone()
            
            if result and result[0]:
                fallback_reason = result[1] if len(result) > 1 else None
                # llm_disabled: serve the cached deterministic result — LLM is
                # administratively off so retrying would just fail again.
                if fallback_reason == "llm_disabled":
                    logger.info(f"LLM cache hit (llm_disabled): {base_chart_id}/{period_type}/{period_key}")
                    if isinstance(result[0], str):
                        return json.loads(result[0])
                    return result[0]
                # Any other fallback_reason (anthropic_key_missing, budget_exceeded,
                # missing_interpretive_hint, invalid_payload_none_leak, etc.) means a
                # transient failure was cached. Force a retry on every request so a
                # restored API key or cleared budget gets a real LLM call.
                if fallback_reason is not None:
                    logger.info(
                        f"LLM cache skip (transient fallback '{fallback_reason}'): "
                        f"{base_chart_id}/{period_type}/{period_key}"
                    )
                    return None
                logger.info(f"LLM cache hit: {base_chart_id}/{period_type}/{period_key}/{explainability_mode}")
                if isinstance(result[0], str):
                    return json.loads(result[0])
                return result[0]
    except Exception as e:
        logger.warning(f"Cache lookup failed: {e}")
    
    return None


def _extract_reflection_text(content_json: Dict[str, Any]) -> Optional[str]:
    """Extract reflection_text from LLM response for separate storage."""
    # Check v2 format first
    practices = content_json.get("practices_and_reflection", {})
    if isinstance(practices, dict):
        reflection = practices.get("reflection_guidance")
        if reflection and isinstance(reflection, str) and reflection.strip():
            return reflection.strip()
    
    # Check v1 format (if any)
    window_summary = content_json.get("window_summary", {})
    if isinstance(window_summary, dict):
        reflection = window_summary.get("reflection")
        if reflection and isinstance(reflection, str) and reflection.strip():
            return reflection.strip()
    
    return None


def _persist_interpretation(
    base_chart_id: str,
    period_type: str,
    period_key: str,
    feature_name: str,
    prompt_version: str,
    provider: Optional[str],
    model: Optional[str],
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    content_json: Dict[str, Any],
    fallback_reason: Optional[str],
    explainability_mode: str = "standard"
) -> None:
    """Persist LLM interpretation and token usage. Includes explainability_mode (v1.9)."""
    try:
        interpretation_id = str(uuid.uuid4())
        
        # FIX 3: Extract reflection_text for separate storage
        reflection_text = _extract_reflection_text(content_json) if not fallback_reason else None
        
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO prediction_llm_interpretation (
                    id, base_chart_id, period_type, period_key, feature_name,
                    provider, model, prompt_version, prompt_tokens,
                    completion_tokens, total_tokens, content_json,
                    fallback_reason, reflection_text, explainability_mode, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [
                interpretation_id, base_chart_id, period_type, period_key,
                feature_name, provider, model, prompt_version, prompt_tokens,
                completion_tokens, total_tokens, json.dumps(content_json),
                fallback_reason, reflection_text, explainability_mode
            ])
            
            if total_tokens > 0 and not fallback_reason:
                usage_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO llm_token_usage (
                        id, feature_name, prompt_version, total_tokens, created_at
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, [usage_id, feature_name, prompt_version, total_tokens])

            # Log to unified llm_calls table for budget tracking
            log_llm_call(
                db=conn,
                chart_id=base_chart_id,
                call_type="prediction",
                period=f"{period_type}/{period_key}",
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                status="error" if fallback_reason else "success",
                fallback_reason=fallback_reason,
            )
                
    except Exception as e:
        logger.error(f"Failed to persist interpretation: {e}")


def _build_context_for_llm(
    envelope: Dict[str, Any],
    synthesis: Dict[str, Any],
    deterministic_interpretation: Dict[str, Any],
    period_type: str,
    period_key: str,
    explainability_mode: str
) -> Dict[str, Any]:
    """
    Build the context to pass to the LLM.
    
    Only includes synthesized meaning - never raw astrology computation.
    """
    lagna = envelope.get("lagna", {})
    nakshatra = envelope.get("nakshatra_context", {})
    dasha = envelope.get("dasha_context", {})
    
    life_areas = []
    synthesis_life_areas = synthesis.get("life_areas", {})
    for area_name, area_data in synthesis_life_areas.items():
        if isinstance(area_data, dict):
            area_context = {
                "area": area_name,
                "score": area_data.get("score", 50),
                "strength_label": _score_to_strength(area_data.get("score", 50)),
                "top_signals": area_data.get("top_signals", [])[:3]
            }
            life_areas.append(area_context)
    
    return {
        "period_type": period_type,
        "period_label": period_key,
        "lagna_label": lagna.get("label", lagna.get("rasi", "Unknown")),
        "moon_nakshatra": nakshatra.get("janma_nakshatra", "Unknown"),
        "mahadasha_lord": dasha.get("maha_lord", "Unknown"),
        "antardasha_lord": dasha.get("antar_lord", "Unknown"),
        "life_areas": life_areas,
        "explainability_mode": explainability_mode,
        "deterministic_summary": deterministic_interpretation.get("window_summary", {}).get("summary", ""),
        "ayanamsa": envelope.get("reference", {}).get("ayanamsa", "lahiri"),
    }


def _score_to_strength(score: int) -> str:
    """Convert numeric score to strength label."""
    if score >= 65:
        return "supportive"
    elif score >= 45:
        return "neutral"
    else:
        return "watchful"


def _validate_llm_output(output: Dict[str, Any]) -> bool:
    """Validate LLM output against schema (supports v1, v2, and v3)."""
    logger.debug(f"Validating LLM output keys: {list(output.keys())}")

    engine_version = output.get("engine_version", "")

    if engine_version and "v7" in engine_version:
        # life_areas is the only truly required field
        life_areas_raw = output.get("life_areas")
        if life_areas_raw is None:
            logger.warning("v7 validation failed: missing life_areas")
            return False

        # Accept both dict (keyed by area name) and list
        if isinstance(life_areas_raw, dict):
            areas = list(life_areas_raw.values())
        elif isinstance(life_areas_raw, list):
            areas = life_areas_raw
        else:
            logger.warning(
                f"v7 validation failed: life_areas is {type(life_areas_raw).__name__}, expected dict or list"
            )
            return False

        if len(areas) < 2:
            logger.warning(f"v7 validation failed: only {len(areas)} life_areas, need at least 2")
            return False

        for area in areas:
            if not isinstance(area, dict):
                continue
            if not area.get("plain_english"):
                logger.warning(f"v7 validation failed: area missing plain_english: {list(area.keys())}")
                return False

        # main_theme: prefer executive_summary.main_theme, accept top-level fallback
        exec_summary = output.get("executive_summary", {})
        main_theme = (
            (exec_summary.get("main_theme") if isinstance(exec_summary, dict) else None)
            or output.get("main_theme")
        )
        if not main_theme:
            logger.warning(
                "v7 validation failed: missing main_theme "
                "(checked executive_summary.main_theme and top-level main_theme)"
            )
            return False

        # event_predictions, annual_theme, yoga_activation_summary are all optional
        return True

    if engine_version == "ai-interpretation-v6.0":
        required_keys = [
            "executive_summary", "why_this_period",
            "life_areas", "remedies", "key_takeaways"
        ]
        if not all(k in output for k in required_keys):
            missing = [k for k in required_keys if k not in output]
            logger.warning(f"LLM v6 output missing keys: {missing}")
            return False
        exec_summary = output.get("executive_summary", {})
        if not exec_summary.get("main_theme"):
            return False
        life_areas = output.get("life_areas", {})
        if not isinstance(life_areas, dict) or len(life_areas) < 2:
            return False
        for area_name, area_data in life_areas.items():
            if not isinstance(area_data, dict):
                continue
            if not area_data.get("plain_english"):
                return False
        return True

    if engine_version == "ai-interpretation-v5.0":
        required_keys = [
            "executive_summary", "why_this_period",
            "life_areas", "remedies", "key_takeaways"
        ]
        if not all(k in output for k in required_keys):
            missing = [k for k in required_keys if k not in output]
            logger.warning(f"LLM v5 output missing keys: {missing}")
            return False
        exec_summary = output.get("executive_summary", {})
        if not exec_summary.get("main_theme"):
            return False
        life_areas = output.get("life_areas", {})
        if not isinstance(life_areas, dict) or len(life_areas) < 2:
            return False
        for area_name, area_data in life_areas.items():
            if not isinstance(area_data, dict):
                continue
            if not area_data.get("plain_english"):
                return False
        return True

    if engine_version == "ai-interpretation-v4.0":
        required_keys = [
            "executive_summary", "why_this_period",
            "life_areas", "remedies", "key_takeaways"
        ]
        if not all(k in output for k in required_keys):
            missing = [k for k in required_keys if k not in output]
            logger.warning(f"LLM v4 output missing keys: {missing}")
            return False
        exec_summary = output.get("executive_summary", {})
        if not exec_summary.get("main_theme"):
            logger.warning("LLM v4 output missing executive_summary.main_theme")
            return False
        life_areas = output.get("life_areas", {})
        if not isinstance(life_areas, dict) or len(life_areas) < 2:
            logger.warning(f"LLM v4 output has insufficient life_areas: {len(life_areas) if isinstance(life_areas, dict) else 'not a dict'}")
            return False
        for area_name, area_data in life_areas.items():
            if not isinstance(area_data, dict):
                continue
            if not area_data.get("plain_english"):
                logger.warning(f"LLM v4 output missing plain_english in {area_name}")
                return False
        return True

    if engine_version == "ai-interpretation-v3.0":
        required_keys = ["yearly_mantra", "dasha_transit_synthesis", "life_areas", "veda_remedy"]
        if not all(k in output for k in required_keys):
            present = [k for k in required_keys if k in output]
            missing = [k for k in required_keys if k not in output]
            logger.warning(f"LLM v3 output missing keys: {missing}. Present: {present}")
            return False
        
        if not output.get("yearly_mantra"):
            logger.warning("LLM v3 output missing yearly_mantra content")
            return False
        
        return True
    
    if engine_version == "ai-interpretation-v2.0":
        required_keys = ["monthly_theme", "overview", "life_areas", "practices_and_reflection", "closing"]
        if not all(k in output for k in required_keys):
            logger.warning(f"LLM v2 output missing required keys. Got: {list(output.keys())}")
            return False
        
        theme = output.get("monthly_theme", {})
        if not theme.get("title") or not theme.get("narrative"):
            logger.warning("LLM v2 output missing monthly_theme title/narrative")
            return False
        
        overview = output.get("overview", {})
        if not overview.get("energy_pattern"):
            logger.warning("LLM v2 output missing overview.energy_pattern")
            return False
        
        return True
    
    # Guard: a versioned v7 response that reaches here is a validator bug, not a v1 response
    if engine_version and "v7" in engine_version:
        logger.error(
            f"v7 response fell through to legacy v1 validator — bug in _validate_llm_output: "
            f"engine_version={engine_version!r}"
        )
        return False

    required_keys = ["window_summary", "life_areas"]

    if not all(k in output for k in required_keys):
        logger.warning(f"LLM output missing required keys. Got: {list(output.keys())}")
        return False

    window = output.get("window_summary", {})
    logger.debug(f"Window summary keys: {list(window.keys())}")

    has_overview = window.get("overview") or window.get("summary")
    if not has_overview:
        logger.warning(f"LLM output missing window summary/overview. Window keys: {list(window.keys())}")
        return False

    return True


def generate_llm_interpretation(
    base_chart_id: str,
    envelope: Dict[str, Any],
    synthesis: Dict[str, Any],
    deterministic_interpretation: Dict[str, Any],
    year: int,
    period_type: Literal["weekly", "monthly", "yearly"],
    period_key: str,
    feature_name: str = "prediction",
    prompt_version: Optional[str] = None,
    explainability_mode: str = "standard",
    base_chart_payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate LLM-enhanced interpretation (v3.0 Siddhar-Tradition Synthesizer).
    
    Orchestrates the full LLM interpretation flow:
    1. Check if LLM is enabled
    2. Check cache
    3. Enforce token limits and budget
    4. Call OpenAI with enriched v3 payload
    5. Validate and persist
    6. Fallback to deterministic if needed
    """
    # v1.8: Use window_type-specific prompt version to prevent stale cache
    effective_prompt_version = prompt_version or PROMPT_VERSION_BY_WINDOW.get(period_type, PROMPT_VERSION)
    
    result = {
        "llm_interpretation": None,
        "llm_metadata": {
            "provider": "none",
            "model": None,
            "prompt_version": effective_prompt_version,
            "fallback_reason": None,
            "tokens_used": 0
        }
    }
    
    if not is_llm_enabled():
        logger.info("LLM disabled - using deterministic fallback")
        result["llm_interpretation"] = deterministic_interpretation
        result["llm_metadata"]["fallback_reason"] = "llm_disabled"
        _persist_interpretation(
            base_chart_id, period_type, period_key, feature_name,
            effective_prompt_version, None, None, 0, 0, 0,
            deterministic_interpretation, "llm_disabled", explainability_mode
        )
        return result
    
    cached = _check_cache(base_chart_id, period_type, period_key, feature_name, effective_prompt_version, explainability_mode)
    if cached:
        result["llm_interpretation"] = cached
        result["llm_metadata"]["provider"] = "cache"
        result["llm_metadata"]["fallback_reason"] = None
        return result
    
    usage = get_monthly_token_usage()
    if usage["remaining"] <= 0:
        logger.warning("Monthly token budget exceeded")
        result["llm_interpretation"] = deterministic_interpretation
        result["llm_metadata"]["fallback_reason"] = "budget_exceeded"
        _persist_interpretation(
            base_chart_id, period_type, period_key, feature_name,
            effective_prompt_version, None, None, 0, 0, 0,
            deterministic_interpretation, "budget_exceeded", explainability_mode
        )
        return result
    
    if not openai_provider.is_available():
        logger.info("Anthropic not available - using deterministic fallback")
        result["llm_interpretation"] = deterministic_interpretation
        result["llm_metadata"]["fallback_reason"] = "anthropic_key_missing"
        _persist_interpretation(
            base_chart_id, period_type, period_key, feature_name,
            effective_prompt_version, None, None, 0, 0, 0,
            deterministic_interpretation, "anthropic_key_missing", explainability_mode
        )
        return result
    
    payload_inputs = extract_payload_inputs(
        envelope, synthesis, period_type, period_key,
        base_chart_payload=base_chart_payload
    )
    
    try:
        payload = build_llm_payload(
            period_type=period_type,
            period_label=payload_inputs["period_label"],
            lagna=payload_inputs["lagna"],
            moon_nakshatra=payload_inputs["moon_nakshatra"],
            active_dasha=payload_inputs["active_dasha"],
            life_area_scores=payload_inputs["life_area_scores"],
            top_signals_by_life_area=payload_inputs["top_signals_by_life_area"],
            explainability_mode=explainability_mode,
            transit_context=payload_inputs.get("transit_context"),
            dasha_timing=payload_inputs.get("dasha_timing"),
            moon_rasi=payload_inputs.get("moon_rasi"),
            birth_year=payload_inputs.get("birth_year"),
            lagnadipathi_status=payload_inputs.get("lagnadipathi_status"),
            saturn_phase=payload_inputs.get("saturn_phase"),
            rahu_ketu_axis=payload_inputs.get("rahu_ketu_axis"),
            yogas=payload_inputs.get("yogas"),
            chandrashtama_periods=payload_inputs.get("chandrashtama_periods"),
            nakshatra_pada=payload_inputs.get("nakshatra_pada"),
            sade_sati_data=payload_inputs.get("sade_sati_data"),
            shadbala_data=payload_inputs.get("shadbala_data"),
            ayanamsa=payload_inputs.get("ayanamsa", "lahiri"),
            kp_sublords=payload_inputs.get("kp_sublords"),
            divisional_signals=payload_inputs.get("divisional_signals"),
            panchangam_context=payload_inputs.get("panchangam_context"),
            shadbala_detail=payload_inputs.get("shadbala_detail"),
            bav_context=payload_inputs.get("bav_context"),
            upagraha_context=payload_inputs.get("upagraha_context"),
            predictive_signals=payload_inputs.get("predictive_signals"),
        )
    except AssertionError as e:
        logger.error(f"Dasha payload leak detected: {e}")
        result["llm_interpretation"] = deterministic_interpretation
        result["llm_metadata"]["fallback_reason"] = "dasha_payload_leak"
        _persist_interpretation(
            base_chart_id, period_type, period_key, feature_name,
            effective_prompt_version, None, None, 0, 0, 0,
            deterministic_interpretation, "dasha_payload_leak", explainability_mode
        )
        return result
    except RuntimeError as e:
        # PART 2: Fail-fast - missing interpretive_hint triggers fallback to deterministic
        logger.warning(f"LLM blocked (interpretive_hint missing): {e}")
        result["llm_interpretation"] = deterministic_interpretation
        result["llm_metadata"]["fallback_reason"] = "missing_interpretive_hint"
        _persist_interpretation(
            base_chart_id, period_type, period_key, feature_name,
            effective_prompt_version, None, None, 0, 0, 0,
            deterministic_interpretation, "missing_interpretive_hint", explainability_mode
        )
        return result
    
    # FIX 1: Hard-stop check for "None" placeholder leakage (exact spec compliance)
    payload_json = json.dumps(payload)
    try:
        if "None" in payload_json:
            logger.error("Invalid placeholder detected in LLM payload")
            raise ValueError("Invalid LLM payload: placeholder leakage")
    except ValueError:
        # On exception: Skip LLM, fall back to deterministic, log fallback_reason
        result["llm_interpretation"] = deterministic_interpretation
        result["llm_metadata"]["fallback_reason"] = "invalid_payload_none_leak"
        _persist_interpretation(
            base_chart_id, period_type, period_key, feature_name,
            effective_prompt_version, None, None, 0, 0, 0,
            deterministic_interpretation, "invalid_payload_none_leak", explainability_mode
        )
        return result
    
    is_valid, reason, estimated_tokens = validate_payload_size(payload, period_type)
    if not is_valid:
        logger.warning(f"Payload validation failed: {reason} (estimated {estimated_tokens} tokens)")
        result["llm_interpretation"] = deterministic_interpretation
        result["llm_metadata"]["fallback_reason"] = reason
        _persist_interpretation(
            base_chart_id, period_type, period_key, feature_name,
            effective_prompt_version, None, None, 0, 0, 0,
            deterministic_interpretation, reason, explainability_mode
        )
        return result
    
    system_prompt = _load_prompt_template(effective_prompt_version)
    user_prompt = f"Generate interpretation:\n\n{json.dumps(payload, indent=2)}"
    
    max_completion = MAX_COMPLETION_TOKENS.get(period_type, 900)
    llm_response, usage_info, error = openai_provider.call_openai(
        system_prompt, user_prompt, max_completion
    )
    
    usage_info = usage_info or {}
    
    if error:
        logger.warning(f"Anthropic call failed: {error}")
        result["llm_interpretation"] = deterministic_interpretation
        result["llm_metadata"]["fallback_reason"] = error
        _persist_interpretation(
            base_chart_id, period_type, period_key, feature_name,
            effective_prompt_version, "anthropic", "claude-opus-4-6", 0, 0, 0,
            deterministic_interpretation, error, explainability_mode
        )
        return result

    if llm_response is None or not _validate_llm_output(llm_response):
        logger.warning("LLM output validation failed or response is None")
        result["llm_interpretation"] = deterministic_interpretation
        result["llm_metadata"]["fallback_reason"] = "validation_failed"
        _persist_interpretation(
            base_chart_id, period_type, period_key, feature_name,
            effective_prompt_version, "anthropic", usage_info.get("model"),
            usage_info.get("prompt_tokens", 0),
            usage_info.get("completion_tokens", 0),
            usage_info.get("total_tokens", 0),
            deterministic_interpretation, "validation_failed", explainability_mode
        )
        return result

    llm_response["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["llm_interpretation"] = llm_response
    result["llm_metadata"]["provider"] = "anthropic"
    result["llm_metadata"]["model"] = usage_info.get("model")
    result["llm_metadata"]["tokens_used"] = usage_info.get("total_tokens", 0)

    _persist_interpretation(
        base_chart_id, period_type, period_key, feature_name,
        effective_prompt_version, "anthropic", usage_info.get("model"),
        usage_info.get("prompt_tokens", 0),
        usage_info.get("completion_tokens", 0),
        usage_info.get("total_tokens", 0),
        llm_response, None, explainability_mode
    )
    
    logger.info(
        f"LLM interpretation generated: {base_chart_id}/{period_type}/{period_key} "
        f"[{usage_info.get('total_tokens', 0)} tokens]"
    )
    
    return result
