from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from datetime import datetime, timezone
from typing import Any, Dict
import json

def _safe_json(val):
    """Accept both str (legacy DuckDB) and dict/list (Neon JSONB)."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    return json.loads(val)

from app.core.limiter import limiter

from app.db.session import get_db
from app.repositories.base_chart_repo import get_base_chart_by_id
from app.repositories.yearly_prediction_repo import save_yearly_prediction, get_yearly_prediction
from app.db.postgres import get_conn

from app.engines.yearly_prediction_envelope import build_yearly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope
from app.engines.interpretation_engine import build_interpretation_from_synthesis
from app.engines.paraphrasing_engine import paraphrase_interpretation
from app.engines.explainability_engine import build_explainability
from app.engines.ai_interpretation_engine import generate_interpretation as generate_ai_interpretation
from app.engines.explainability_filter import apply_explainability
from app.engines.llm_interpretation_orchestrator import generate_llm_interpretation

router = APIRouter(prefix="/prediction", tags=["Prediction"])


def _normalize_confidence(synthesis: Dict[str, Any]) -> Dict[str, Any]:
    """
    EPIC-7 guardrail: ensure confidence exists even if engines omit it.
    API layer only — do not move into engines.
    """
    if "confidence" not in synthesis or synthesis["confidence"] is None:
        synthesis["confidence"] = {
            "overall": 0.6,
            "variance": 0.0,
            "active_lords": [],
        }
    elif isinstance(synthesis["confidence"], (int, float)):
        synthesis["confidence"] = {
            "overall": float(synthesis["confidence"]),
            "variance": 0.0,
            "active_lords": [],
        }
    return synthesis


def _run_yearly_llm_background(
    base_chart_id: str,
    envelope: dict,
    synthesis: dict,
    ai_interpretation: dict,
    year: int,
    base_chart_payload: dict,
) -> None:
    period_key = str(year)
    try:
        llm_result = generate_llm_interpretation(
            base_chart_id=base_chart_id,
            envelope=envelope,
            synthesis=synthesis,
            deterministic_interpretation=ai_interpretation,
            year=year,
            period_type="yearly",
            period_key=period_key,
            feature_name="prediction",
            explainability_mode="full",
            base_chart_payload=base_chart_payload,
        )
        existing = get_yearly_prediction(base_chart_id=base_chart_id, year=year)
        if existing:
            interp = existing["interpretation"] if isinstance(existing["interpretation"], dict) else json.loads(existing["interpretation"])
            interp["llm_interpretation"] = llm_result.get("llm_interpretation")
            interp["llm_metadata"] = llm_result.get("llm_metadata")
            save_yearly_prediction(
                base_chart_id=base_chart_id,
                year=year,
                status="success",
                envelope=existing["envelope"] if isinstance(existing["envelope"], dict) else json.loads(existing["envelope"]),
                synthesis=existing["synthesis"] if isinstance(existing["synthesis"], dict) else json.loads(existing["synthesis"]),
                interpretation=interp,
                engine_version="v4.2",
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Background yearly LLM failed for {base_chart_id}/{year}: {e}")


@router.get("/yearly/llm-status")
def get_yearly_llm_status(base_chart_id: str, year: int):
    existing = get_yearly_prediction(base_chart_id=base_chart_id, year=year)
    if existing and existing.get("interpretation"):
        interp = existing["interpretation"] if isinstance(existing["interpretation"], dict) else json.loads(existing["interpretation"])
        if interp.get("llm_interpretation"):
            return {"status": "ready"}
    return {"status": "pending"}


@limiter.limit("10/hour")
@router.post("/yearly")
def generate_yearly_prediction(request: Request, payload: dict, background_tasks: BackgroundTasks, db=Depends(get_db)):
    """
    EPIC-9
    Yearly prediction endpoint.

    Rules:
    - No astrology in API
    - Reuse envelope + synthesis + interpretation
    - Explainability derived only
    - Response shape mirrors MonthlyPredictionResponse (yearly variant)
    """

    base_chart_id = payload.get("base_chart_id")
    year = payload.get("year")

    if not base_chart_id or year is None:
        raise HTTPException(
            status_code=400,
            detail="Missing base_chart_id or year"
        )

    # --------------------------------------------------
    # Fetch base chart (DuckDB source of truth)
    # --------------------------------------------------
    base_chart_record = get_base_chart_by_id(db, base_chart_id)

    if not base_chart_record:
        raise HTTPException(status_code=404, detail="Birth chart not found")

    # --------------------------------------------------
    # 🔑 CRITICAL FIX (matches monthly + weekly behavior)
    # DuckDB stores payload as TEXT → must JSON-decode
    # --------------------------------------------------
    raw_payload = (
        base_chart_record["payload"]
        if isinstance(base_chart_record, dict)
        else base_chart_record.payload
    )

    base_chart_payload = (
        _safe_json(raw_payload)
        if isinstance(raw_payload, str)
        else raw_payload
    )

    # --------------------------------------------------
    # Build yearly envelope
    # --------------------------------------------------
    envelope = build_yearly_prediction_envelope(
        base_chart=base_chart_payload,
        year=int(year),
    )

    synthesis = synthesize_from_envelope(envelope)
    synthesis = _normalize_confidence(synthesis)

    interpretation = build_interpretation_from_synthesis(
        envelope=envelope,
        synthesis=synthesis,
    )

    ai_interpretation = generate_ai_interpretation(
        envelope=envelope,
        synthesis=synthesis,
        year=int(year),
        month=1,
    )

    # Always use full detail level
    ai_interpretation = apply_explainability(ai_interpretation, "full")

    interpretation = paraphrase_interpretation(interpretation)
    interpretation["ai_interpretation"] = ai_interpretation

    # --------------------------------------------------
    # LLM Interpretation — deferred to background task
    # --------------------------------------------------
    interpretation["llm_interpretation"] = None
    interpretation["llm_metadata"] = {"provider": "none", "fallback_reason": None}

    explainability = build_explainability(
        dasha_context=envelope["dasha_context"],
        confidence=synthesis.get("confidence"),
        period_type="yearly",
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    prediction_id = f"yearly:{base_chart_id}:{int(year)}"

    summary = None
    if isinstance(interpretation, dict):
        summary = (
            interpretation.get("summary")
            or interpretation.get("headline")
        )

    # Save yearly prediction to database for PDF generation
    save_yearly_prediction(
        base_chart_id=base_chart_id,
        year=int(year),
        status="success",
        envelope=json.dumps(envelope),
        synthesis=json.dumps(synthesis),
        interpretation=json.dumps(interpretation),
        engine_version="v4.2",
    )

    background_tasks.add_task(
        _run_yearly_llm_background,
        base_chart_id=base_chart_id,
        envelope=envelope,
        synthesis=synthesis,
        ai_interpretation=ai_interpretation,
        year=int(year),
        base_chart_payload=base_chart_payload,
    )

    return {
        "id": prediction_id,
        "base_chart_id": base_chart_id,
        "year": int(year),
        "generated_at": generated_at,
        "status": "success",
        "summary": summary,
        "details": {
            "envelope": envelope,
            "synthesis": synthesis,
            "interpretation": interpretation,
        },
        "explainability": (
            explainability.model_dump()
            if hasattr(explainability, "model_dump")
            else explainability
        ),
        "llm_status": "pending",
    }
