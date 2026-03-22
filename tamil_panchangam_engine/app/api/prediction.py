# app/api/prediction.py

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from datetime import datetime
import json

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
from app.repositories.base_chart_repo import get_base_chart_by_id

from app.engines.prediction_envelope import build_monthly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope
from app.engines.interpretation_engine import build_interpretation_from_synthesis
from app.engines.paraphrasing_engine import paraphrase_interpretation
from app.engines.explainability_engine import build_explainability
from app.engines.ai_interpretation_engine import generate_interpretation as generate_ai_interpretation
from app.engines.explainability_filter import apply_explainability
from app.engines.llm_interpretation_orchestrator import generate_llm_interpretation, is_llm_enabled
from app.engines.corner_case_detector import assess_calculation_confidence

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
def get_monthly_llm_status(base_chart_id: str, year: int, month: int):
    """
    Polling endpoint: returns "ready" only when llm_interpretation has been
    merged into monthly_predictions (not just written to prediction_llm_interpretation).
    This prevents the race where the frontend re-fetches before the merge completes.
    """
    existing = get_monthly_prediction(
        base_chart_id=base_chart_id, year=year, month=month
    )
    if existing and existing.get("interpretation"):
        interp = (
            _safe_json(existing["interpretation"])
            if isinstance(existing["interpretation"], str)
            else existing["interpretation"]
        )
        if interp.get("llm_interpretation"):
            return {"status": "ready"}
    return {"status": "pending"}


@limiter.limit("10/hour")
@router.post("/monthly", response_model=MonthlyPredictionResponse)
def generate_monthly_prediction(
    request: Request,
    payload: MonthlyPredictionRequest,
    background_tasks: BackgroundTasks,
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

    if base_chart is None:
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
