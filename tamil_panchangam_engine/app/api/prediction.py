# app/api/prediction.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from datetime import datetime, timezone, timedelta
import json
from typing import Optional

def _safe_json(val):
    """Accept both str (legacy DuckDB) and dict/list (Neon JSONB)."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    return json.loads(val)

import logging
from app.core.limiter import limiter

logger = logging.getLogger(__name__)

from app.db.postgres import get_conn

from app.repositories.prediction_repo import (
    get_monthly_prediction,
    save_monthly_prediction,
)
from app.repositories.base_chart_repo import get_base_chart_by_id, user_owns_chart

from app.engines.prediction_envelope import build_monthly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope
from app.engines.interpretation_engine import build_interpretation_from_synthesis
from app.engines.paraphrasing_engine import paraphrase_interpretation
from app.engines.explainability_engine import build_explainability
from app.engines.ai_interpretation_engine import generate_interpretation as generate_ai_interpretation
from app.engines.explainability_filter import apply_explainability
from app.engines.llm_interpretation_orchestrator import generate_llm_interpretation, is_llm_enabled
from app.engines.corner_case_detector import assess_calculation_confidence

from app.core.auth import require_admin, get_current_user

from app.models.schema import (
    MonthlyPredictionRequest,
    MonthlyPredictionResponse,
)


router = APIRouter(prefix="/prediction", tags=["Prediction"])


def _run_llm_background(
    base_chart_id: str,
    envelope: dict,
    synthesis: dict,
    ai_interpretation: dict,
    year: int,
    month: int,
    base_chart_payload: dict,
) -> None:
    """
    Background task: generate LLM interpretation and update the persisted prediction.
    Runs after the HTTP response has been sent.
    """
    period_key = f"{year}-{month:02d}"
    try:
        llm_result = generate_llm_interpretation(
            base_chart_id=base_chart_id,
            envelope=envelope,
            synthesis=synthesis,
            deterministic_interpretation=ai_interpretation,
            year=year,
            period_type="monthly",
            period_key=period_key,
            feature_name="prediction",
            explainability_mode="full",
            base_chart_payload=base_chart_payload,
        )
        # Re-fetch the saved prediction and merge in LLM result
        existing = get_monthly_prediction(
            base_chart_id=base_chart_id, year=year, month=month
        )
        if existing:
            interp = (
                _safe_json(existing["interpretation"])
                if existing.get("interpretation")
                else {}
            )
            interp["llm_interpretation"] = llm_result.get("llm_interpretation")
            interp["llm_metadata"] = llm_result.get("llm_metadata")
            with get_conn() as conn:
                save_monthly_prediction(
                    conn,
                    base_chart_id=base_chart_id,
                    year=year,
                    month=month,
                    status="ok",
                    envelope=_safe_json(existing["envelope"]),
                    synthesis=_safe_json(existing["synthesis"]),
                    interpretation=interp,
                    engine_version="monthly-prediction-v2",
                )
    except Exception as e:
        logger.error(f"Background LLM task failed for {base_chart_id}/{period_key}: {e}")


@router.get("/monthly/llm-status")
def get_monthly_llm_status(base_chart_id: str, year: int, month: int, user: dict = Depends(get_current_user)):
    """
    Polling endpoint: returns "ready" only when llm_interpretation has been
    merged into monthly_predictions (not just written to prediction_llm_interpretation).
    This prevents the race where the frontend re-fetches before the merge completes.

    Checks fallback_reason, not just presence (2026-09-11 follow-up to the
    stale-fallback-cache fix above): llm_interpretation being present isn't
    enough on its own -- a chart stuck on a stale fallback ALREADY has
    llm_interpretation present (it's the fallback content itself), so a
    presence-only check reported "ready" immediately whenever
    generate_monthly_prediction() kicked off a fresh retry for exactly
    that case, before the retry had actually finished. The frontend would
    stop polling and redisplay the still-stale content for one refetch
    cycle.

    Any fallback_reason (including "llm_disabled") is treated as "not
    ready" here, uniformly -- deliberately NOT special-casing
    "llm_disabled" as an exception the way _check_cache() does one layer
    down. generate_monthly_prediction()'s retry trigger (above) is
    likewise unconditional on the reason string: it retries whenever
    is_llm_enabled() is currently true, regardless of what the stale
    fallback_reason says, so a chart cached while LLM was off correctly
    gets a fresh attempt the moment it's re-enabled. Special-casing
    "llm_disabled" as always-ready here would reintroduce this exact same
    race for that one reason: the POST endpoint might retry it, but
    polling would already have told the frontend "ready, stop" based on
    the stale row before that retry finished. If LLM is still genuinely
    disabled, the POST endpoint never sets llm_status="pending" in the
    first place (its own is_llm_enabled() guard skips the retry and
    returns llm_status=None), so the frontend never starts polling this
    endpoint for that case at all -- this "pending" fallback response is
    reachable only while a real retry is in flight.
    """
    with get_conn() as conn:
        if not user_owns_chart(conn, user, base_chart_id):
            raise HTTPException(status_code=404, detail="Base chart not found")

    existing = get_monthly_prediction(
        base_chart_id=base_chart_id, year=year, month=month
    )
    if existing and existing.get("interpretation"):
        interp = (
            _safe_json(existing["interpretation"])
            if isinstance(existing["interpretation"], str)
            else existing["interpretation"]
        )
        fallback_reason = interp.get("llm_metadata", {}).get("fallback_reason")
        if interp.get("llm_interpretation") and fallback_reason is None:
            return {"status": "ready"}
    return {"status": "pending"}


@limiter.limit("10/hour")
@router.post("/monthly", response_model=MonthlyPredictionResponse)
def generate_monthly_prediction(
    request: Request,
    payload: MonthlyPredictionRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    EPIC-4 + EPIC-6 + EPIC-8 + EPIC-3
    """

    # -------------------------------------------------
    # 1. Load immutable base chart
    # -------------------------------------------------
    with get_conn() as conn:
        base_chart = get_base_chart_by_id(
            conn,
            payload.base_chart_id,
        )
        owns_chart = user_owns_chart(conn, user, payload.base_chart_id)

    # Ownership check (security fix, 2026-09-08): 404 either way so a
    # non-owner can't tell whether the chart exists.
    if base_chart is None or not owns_chart:
        raise HTTPException(
            status_code=404,
            detail=f"Base chart not found: {payload.base_chart_id}",
        )

    if not base_chart.get("locked"):
        raise HTTPException(
            status_code=400,
            detail="Base chart is not locked",
        )

    base_chart_payload = (
        base_chart["payload"]
        if isinstance(base_chart["payload"], dict)
        else _safe_json(base_chart["payload"])
    )

    # -------------------------------------------------
    # 1a. Lazy upagraha backfill for pre-v2.0 charts
    # -------------------------------------------------
    if not base_chart_payload.get("upagrahas"):
        _birth_utc_str = base_chart_payload.get("birth_utc", "")
        _birth_details = base_chart_payload.get("birth_details", {})
        if _birth_utc_str and _birth_details:
            try:
                from app.engines.upagraha_engine import compute_gulika_mandi
                _bu = datetime.fromisoformat(_birth_utc_str.replace("Z", "+00:00"))
                _upa = compute_gulika_mandi(
                    birth_utc=_bu,
                    latitude=_birth_details.get("latitude", 0.0),
                    longitude=_birth_details.get("longitude", 0.0),
                    ayanamsa=base_chart_payload.get("ephemeris", {}).get("ayanamsa", "lahiri"),
                )
                base_chart_payload["upagrahas"] = _upa
                with get_conn() as conn:
                    conn.execute(
                        "UPDATE base_charts SET payload = payload || %s::jsonb WHERE id = %s",
                        (json.dumps({"upagrahas": _upa}), payload.base_chart_id),
                    )
                logger.info(f"Lazy upagraha backfill written: {payload.base_chart_id}")
            except Exception as _e:
                logger.warning(f"Lazy upagraha backfill failed for {payload.base_chart_id}: {_e}")

    # -------------------------------------------------
    # 1b. Lazy yogas backfill for pre-yoga-pipeline charts
    # -------------------------------------------------
    if not base_chart_payload.get("yogas", {}).get("yogas"):
        try:
            from app.engines.yoga_engine import compute_yogas
            _ygr = compute_yogas(base_chart_payload.get("ephemeris", {}), {})
            base_chart_payload["yogas"] = _ygr
            # Clear any stale predictive_signals so 1c recomputes with fresh yogas
            base_chart_payload.pop("predictive_signals", None)
            with get_conn() as conn:
                conn.execute(
                    "UPDATE base_charts SET payload = payload || %s::jsonb WHERE id = %s",
                    (json.dumps({"yogas": _ygr}), payload.base_chart_id),
                )
            logger.info(f"Lazy yogas backfill written: {payload.base_chart_id}")
        except Exception as _e:
            logger.warning(f"Lazy yogas backfill failed for {payload.base_chart_id}: {_e}")

    # -------------------------------------------------
    # 1c. Lazy predictive_signals computation
    # -------------------------------------------------
    _current_period = f"{payload.year}-{payload.month:02d}"
    _cached_signals = base_chart_payload.get("predictive_signals", {})
    if not _cached_signals or _cached_signals.get("computed_for") != _current_period:
        try:
            from app.engines.predictive_signals_engine import compute_predictive_signals
            _signals = compute_predictive_signals(
                payload=base_chart_payload,
                chart_id=payload.base_chart_id,
                year=payload.year,
                month=payload.month,
            )
            base_chart_payload["predictive_signals"] = _signals
        except Exception as _e:
            logger.warning(f"Predictive signals failed for {payload.base_chart_id}: {_e}")

    # -------------------------------------------------
    # 2. Check for persisted prediction
    # -------------------------------------------------
    existing = get_monthly_prediction(
        base_chart_id=payload.base_chart_id,
        year=payload.year,
        month=payload.month,
    )

    cache_hit = bool(existing)
    llm_status = None  # None = already present; "pending" = running in background

    if existing:
        envelope = _safe_json(existing["envelope"])
        synthesis = _safe_json(existing["synthesis"])
        interpretation = (
            _safe_json(existing["interpretation"])
            if existing.get("interpretation")
            else None
        )
        
        # Mark as returned from prediction cache (no new LLM call)
        if interpretation and "llm_metadata" in interpretation:
            interpretation["llm_metadata"]["from_cache"] = True
            interpretation["llm_metadata"]["tokens_used"] = 0  # No new tokens spent

        # Fallback: if llm_interpretation not yet merged into monthly_predictions,
        # read it directly from prediction_llm_interpretation table
        if interpretation and "llm_interpretation" not in interpretation:
            period_key = f"{payload.year}-{payload.month:02d}"
            with get_conn() as conn:
                llm_row = conn.execute(
                    """
                    SELECT content_json FROM prediction_llm_interpretation
                    WHERE base_chart_id = ?
                      AND period_type = 'monthly'
                      AND period_key = ?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    [payload.base_chart_id, period_key],
                ).fetchone()
            if llm_row and llm_row[0]:
                llm_data = (
                    _safe_json(llm_row[0])
                    if isinstance(llm_row[0], str)
                    else llm_row[0]
                )
                interpretation["llm_interpretation"] = (
                    llm_data.get("llm_interpretation") or llm_data
                )
        
        if interpretation and "ai_interpretation" in interpretation:
            interpretation["ai_interpretation"] = apply_explainability(
                interpretation["ai_interpretation"],
                "full"
            )
        
        # Add calculation confidence for cached predictions if missing
        if "calculation_confidence" not in envelope:
            ephemeris = base_chart_payload.get("ephemeris", {})
            try:
                calc_confidence = assess_calculation_confidence(ephemeris)
                envelope["calculation_confidence"] = calc_confidence
            except Exception as e:
                print(f"Warning: Failed to assess calculation confidence (cached): {e}")
                envelope["calculation_confidence"] = {"level": "high", "cusp_cases": []}

        if "confidence" not in synthesis:
            synthesis["confidence"] = {
                "overall": 0.6,
                "variance": 0.0,
                "source": "legacy-prediction",
            }

        if "dasha_context" not in envelope:
            active_dasha = envelope.get("time_ruler", {}).get(
                "vimshottari_dasha"
            )
            if not active_dasha:
                raise RuntimeError(
                    "Persisted envelope missing vimshottari dasha"
                )

            envelope["dasha_context"] = {
                "maha_lord": active_dasha["lord"],
                "antar_lord": None,
                "active_lords": [active_dasha["lord"]],
                "lord_weights": {active_dasha["lord"]: 1.0},
                "active": {
                    "maha": active_dasha,
                    "antar": None,
                },
                "timeline": [],
            }

        # Stale fallback-tagged cache entry (2026-09-11 follow-up to
        # Issue 2): a fallback result (fallback_reason set -- e.g.
        # prompt_too_large, budget_exceeded, a real Anthropic API error)
        # was being cached and served identically to a real one. Once a
        # chart+period combo hit ANY fallback, it stayed stuck showing
        # that exact fallback content -- and its ORIGINAL timestamp --
        # forever, even after the underlying cause was fixed (e.g. the
        # token-limit fix), because this cache-hit branch never
        # distinguished "done, real result" from "done, only because
        # generation failed." Confirmed against a real stale row from
        # before that fix (created 2026-09-11 17:12:55,
        # fallback_reason="prompt_too_large") still being served hours
        # after the fix was deployed and confirmed live. A fallback is a
        # failure-to-generate signal, not a valid cacheable result: don't
        # treat it as a final cache hit for the LLM portion -- re-kick a
        # background regeneration attempt, same as a genuine cache miss,
        # so a fix actually reaches previously-stuck charts instead of
        # only helping brand-new ones. The deterministic/envelope/
        # synthesis portions are still served from cache immediately,
        # same as the already-merged case -- only the LLM retry is new.
        existing_fallback_reason = (interpretation or {}).get("llm_metadata", {}).get("fallback_reason")
        if existing_fallback_reason and is_llm_enabled():
            logger.info(
                f"Stale fallback cache entry detected ({existing_fallback_reason}) for "
                f"{payload.base_chart_id}/monthly/{payload.year}-{payload.month:02d} -- "
                f"re-attempting LLM generation instead of re-serving it."
            )
            background_tasks.add_task(
                _run_llm_background,
                base_chart_id=payload.base_chart_id,
                envelope=envelope,
                synthesis=synthesis,
                ai_interpretation=(interpretation or {}).get("ai_interpretation", {}),
                year=payload.year,
                month=payload.month,
                base_chart_payload=base_chart_payload,
            )
            llm_status = "pending"

    else:
        # -------------------------------------------------
        # 3. Envelope
        # -------------------------------------------------
        envelope = build_monthly_prediction_envelope(
            base_chart=base_chart_payload,
            year=payload.year,
            month=payload.month,
        )
        
        # Add calculation confidence from corner case detector
        ephemeris = base_chart_payload.get("ephemeris", {})
        try:
            calc_confidence = assess_calculation_confidence(ephemeris)
            envelope["calculation_confidence"] = calc_confidence
        except Exception as e:
            print(f"Warning: Failed to assess calculation confidence: {e}")
            envelope["calculation_confidence"] = {"level": "high", "cusp_cases": []}

        # -------------------------------------------------
        # 4. Synthesis
        # -------------------------------------------------
        synthesis = synthesize_from_envelope(envelope)

        if "confidence" not in synthesis:
            synthesis["confidence"] = {
                "overall": 0.6,
                "variance": 0.0,
                "source": "system-default",
            }

        # -------------------------------------------------
        # 🔧 CRITICAL FIX: normalize life_areas
        # -------------------------------------------------
        life_areas = synthesis.get("life_areas")

        if isinstance(life_areas, dict) and "scores" in life_areas:
            synthesis = {
                **synthesis,
                "life_areas": life_areas["scores"],
            }

        print(
            "DEBUG normalized synthesis life areas =",
            synthesis.get("life_areas", {}).keys()
        )

        # -------------------------------------------------
        # 5. Interpretation
        # -------------------------------------------------
        interpretation = build_interpretation_from_synthesis(
            envelope=envelope,
            synthesis=synthesis,
        )

        print(
            "DEBUG interpretation BEFORE paraphrase life areas =",
            interpretation.get("interpretation", {}).keys()
        )

        # -------------------------------------------------
        # 6. AI Interpretation (Level 1-3 structured output)
        # -------------------------------------------------
        ai_interpretation = generate_ai_interpretation(
            envelope=envelope,
            synthesis=synthesis,
            year=payload.year,
            month=payload.month,
        )

        print(
            "DEBUG AI interpretation generated with momentum =",
            ai_interpretation.get("window_summary", {}).get("momentum")
        )

        # Always use full detail level
        ai_interpretation = apply_explainability(ai_interpretation, "full")

        # -------------------------------------------------
        # 7. Paraphrasing (legacy interpretation)
        # -------------------------------------------------
        interpretation = paraphrase_interpretation(
            interpretation
        )

        print(
            "DEBUG interpretation AFTER paraphrase life areas =",
            interpretation.get("interpretation", {}).keys()
        )

        if "interpretation" not in interpretation:
            raise RuntimeError(
                "Interpretation schema violation after paraphrasing"
            )
        
        interpretation["ai_interpretation"] = ai_interpretation

        # -------------------------------------------------
        # 8. Persist immediately (without LLM — will update in background)
        # -------------------------------------------------
        with get_conn() as conn:
            save_monthly_prediction(
                conn,
                base_chart_id=payload.base_chart_id,
                year=payload.year,
                month=payload.month,
                status="ok",
                envelope=envelope,
                synthesis=synthesis,
                interpretation=interpretation,
                engine_version="monthly-prediction-v2",
            )

        # -------------------------------------------------
        # 7b. LLM Interpretation — run in background after response
        # -------------------------------------------------
        if is_llm_enabled():
            background_tasks.add_task(
                _run_llm_background,
                base_chart_id=payload.base_chart_id,
                envelope=envelope,
                synthesis=synthesis,
                ai_interpretation=ai_interpretation,
                year=payload.year,
                month=payload.month,
                base_chart_payload=base_chart_payload,
            )
            llm_status = "pending"
        else:
            llm_status = None

    # -------------------------------------------------
    # 8. Explainability
    # -------------------------------------------------
    explainability = build_explainability(
        dasha_context=envelope["dasha_context"],
        confidence=synthesis["confidence"],
        period_type="monthly",
    )

    prediction_id = (
        f"{payload.base_chart_id}:{payload.year}:{payload.month}"
    )

    # -------------------------------------------------
    # 9. Response
    # -------------------------------------------------
    return MonthlyPredictionResponse(
        id=prediction_id,
        base_chart_id=payload.base_chart_id,
        year=payload.year,
        month=payload.month,
        generated_at=datetime.utcnow(),
        status="ok",
        summary="Monthly prediction computed.",
        details={
            "envelope": envelope,
            "synthesis": synthesis,
            "interpretation": interpretation,
        },
        explainability=explainability.model_dump(),
        cache_hit=cache_hit,
        llm_status=llm_status,
    )


@router.post("/rerun-llm/{base_chart_id}")
def rerun_llm_interpretation(
    base_chart_id: str,
    period_type: str,
    year: int,
    month: Optional[int] = None,
    _admin: dict = Depends(require_admin),
):
    """
    Admin-only: clear cached LLM interpretation for a specific period and force
    regeneration on the next prediction request.

    Rate-limited to one rerun per chart+period per 24 hours.
    """
    if period_type not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="period_type must be 'monthly' or 'yearly'")

    period_key = f"{year}-{month:02d}" if period_type == "monthly" and month else str(year)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    try:
        with get_conn() as conn:
            # 24h rate limit: block if a successful rerun already exists in window
            recent = conn.execute(
                """
                SELECT id FROM prediction_llm_interpretation
                WHERE base_chart_id = %s
                  AND period_type = %s
                  AND period_key = %s
                  AND fallback_reason IS NULL
                  AND created_at > %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (base_chart_id, period_type, period_key, cutoff),
            ).fetchone()

            if recent:
                raise HTTPException(
                    status_code=429,
                    detail="Already rerun in last 24h. Wait before rerunning again.",
                )

            # Clear prediction_llm_interpretation so no stale LLM row survives
            conn.execute(
                """
                DELETE FROM prediction_llm_interpretation
                WHERE base_chart_id = %s
                  AND period_type = %s
                  AND period_key = %s
                """,
                (base_chart_id, period_type, period_key),
            )

            # Also delete the envelope row so the next fetch rebuilds from
            # scratch and schedules a fresh background LLM call.
            # The envelope stores llm_interpretation inline after the background
            # merge — deleting it is the only way to force re-generation.
            if period_type == "monthly":
                conn.execute(
                    """
                    DELETE FROM monthly_predictions
                    WHERE base_chart_id = %s
                      AND year = %s
                      AND month = %s
                    """,
                    (base_chart_id, year, month),
                )
            else:
                conn.execute(
                    """
                    DELETE FROM yearly_predictions
                    WHERE base_chart_id = %s
                      AND year = %s
                    """,
                    (base_chart_id, year),
                )

        logger.info(
            f"Admin rerun-llm: {base_chart_id}/{period_type}/{period_key} "
            f"— envelope + LLM cache cleared by {_admin.get('email', '?')}"
        )
        return {
            "success": True,
            "base_chart_id": base_chart_id,
            "period_type": period_type,
            "period_key": period_key,
            "message": "Envelope and LLM cache cleared. Next fetch rebuilds with fresh v7.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"rerun-llm failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
