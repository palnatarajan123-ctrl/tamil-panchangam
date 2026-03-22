from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime, timezone
from typing import Any, Dict
import json
import logging

logger = logging.getLogger(__name__)

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
from app.engines.llm_interpretation_orchestrator import generate_llm_interpretation, is_llm_enabled

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


@limiter.limit("10/hour")
@router.post("/yearly")
def generate_yearly_prediction(request: Request, payload: dict, db=Depends(get_db)):
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
    # LLM Interpretation (language-only enhancement)
    # --------------------------------------------------
    period_key = str(int(year))
    llm_result = generate_llm_interpretation(
        base_chart_id=base_chart_id,
        envelope=envelope,
        synthesis=synthesis,
        deterministic_interpretation=ai_interpretation,
        year=int(year),
        period_type="yearly",
        period_key=period_key,
        feature_name="prediction",
        explainability_mode="full",
        base_chart_payload=base_chart_payload,
    )
    interpretation["llm_interpretation"] = llm_result.get("llm_interpretation")
    interpretation["llm_metadata"] = llm_result.get("llm_metadata")

    # --------------------------------------------------
    # Overwrite guard: don't clobber a real Anthropic result with a fallback
    # --------------------------------------------------
    existing = get_yearly_prediction(base_chart_id=base_chart_id, year=int(year))
    if existing:
        existing_interp = (
            existing["interpretation"]
            if isinstance(existing["interpretation"], dict)
            else json.loads(existing["interpretation"])
        )
        existing_meta = existing_interp.get("llm_metadata", {})
        new_meta = interpretation.get("llm_metadata", {})
        if existing_meta.get("provider") == "anthropic" and new_meta.get("fallback_reason"):
            interpretation["llm_interpretation"] = existing_interp.get("llm_interpretation")
            interpretation["llm_metadata"] = existing_interp.get("llm_metadata")

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
        envelope=envelope,
        synthesis=synthesis,
        interpretation=interpretation,
        engine_version="v4.2",
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
        "llm_status": None,
    }
