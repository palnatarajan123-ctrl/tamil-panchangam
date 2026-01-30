from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from typing import Any, Dict
import json

from app.db.session import get_db
from app.repositories.base_chart_repo import get_base_chart_by_id

from app.engines.weekly_prediction_envelope import build_weekly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope
from app.engines.interpretation_engine import build_interpretation_from_synthesis
from app.engines.paraphrasing_engine import paraphrase_interpretation
from app.engines.explainability_engine import build_explainability
from app.engines.ai_interpretation_engine import generate_interpretation as generate_ai_interpretation
from app.engines.explainability_filter import apply_explainability
from app.engines.llm_interpretation_orchestrator import generate_llm_interpretation

# OPTIONAL (recommended): persist weekly predictions like monthly
try:
    from app.repositories.weekly_prediction_repo import save_weekly_prediction
except Exception:  # pragma: no cover
    save_weekly_prediction = None


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


@router.post("/weekly")
def generate_weekly_prediction(payload: dict, db=Depends(get_db)):
    """
    EPIC-9
    Weekly prediction endpoint.

    Rules:
    - No astrology in API
    - Reuse envelope + synthesis + interpretation
    - Explainability derived only
    - Must tolerate antar_lord = null
    - Response shape mirrors MonthlyPredictionResponse (weekly variant)
    """

    base_chart_id = payload.get("base_chart_id")
    year = payload.get("year")
    week = payload.get("week")

    if not base_chart_id or year is None or week is None:
        raise HTTPException(
            status_code=400,
            detail="Missing base_chart_id, year, or week"
        )

    # --------------------------------------------------
    # Fetch base chart (DuckDB source of truth)
    # --------------------------------------------------
    base_chart_record = get_base_chart_by_id(db, base_chart_id)

    if not base_chart_record:
        raise HTTPException(status_code=404, detail="Birth chart not found")

    # --------------------------------------------------
    # 🔑 CRITICAL FIX (matches monthly behavior)
    # DuckDB stores payload as TEXT → must JSON-decode
    # --------------------------------------------------
    raw_payload = (
        base_chart_record["payload"]
        if isinstance(base_chart_record, dict)
        else base_chart_record.payload
    )

    base_chart_payload = (
        json.loads(raw_payload)
        if isinstance(raw_payload, str)
        else raw_payload
    )

    # --------------------------------------------------
    # Build weekly envelope
    # --------------------------------------------------
    envelope = build_weekly_prediction_envelope(
        base_chart=base_chart_payload,
        year=int(year),
        week=int(week),
    )

    synthesis = synthesize_from_envelope(envelope)
    synthesis = _normalize_confidence(synthesis)

    interpretation = build_interpretation_from_synthesis(
        envelope=envelope,
        synthesis=synthesis,
    )

    approx_month = min(12, max(1, (int(week) - 1) // 4 + 1))
    ai_interpretation = generate_ai_interpretation(
        envelope=envelope,
        synthesis=synthesis,
        year=int(year),
        month=approx_month,
    )

    # Apply explainability filter to AI interpretation
    explainability_level = payload.get("explainability_level", "full")
    ai_interpretation = apply_explainability(ai_interpretation, explainability_level)

    interpretation = paraphrase_interpretation(interpretation)
    interpretation["ai_interpretation"] = ai_interpretation

    # --------------------------------------------------
    # LLM Interpretation (language-only enhancement)
    # --------------------------------------------------
    period_key = f"{int(year)}-W{int(week):02d}"
    llm_result = generate_llm_interpretation(
        base_chart_id=base_chart_id,
        envelope=envelope,
        synthesis=synthesis,
        deterministic_interpretation=ai_interpretation,
        year=int(year),
        period_type="weekly",
        period_key=period_key,
        feature_name="prediction",
        prompt_version="interpretation_v2",
        explainability_mode=explainability_level,
    )
    interpretation["llm_interpretation"] = llm_result.get("llm_interpretation")
    interpretation["llm_metadata"] = llm_result.get("llm_metadata")

    explainability = build_explainability(
        dasha_context=envelope["dasha_context"],
        confidence=synthesis.get("confidence"),
        period_type="weekly",
    )

    generated_at = datetime.now(timezone.utc).isoformat()

    prediction_id = f"weekly:{base_chart_id}:{int(year)}:{int(week)}"

    # --------------------------------------------------
    # Weekly persistence intentionally disabled
    # Monthly remains system of record
    # --------------------------------------------------
    pass

    summary = None
    if isinstance(interpretation, dict):
        summary = (
            interpretation.get("summary")
            or interpretation.get("headline")
        )

    return {
        "id": prediction_id,
        "base_chart_id": base_chart_id,
        "year": int(year),
        "week": int(week),
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
    }
