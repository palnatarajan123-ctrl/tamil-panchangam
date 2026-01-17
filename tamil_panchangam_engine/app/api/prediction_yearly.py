from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from typing import Any, Dict

from app.db.session import get_db
from app.repositories.base_chart_repo import get_base_chart_by_id

from app.engines.yearly_prediction_envelope import build_yearly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope
from app.engines.interpretation_engine import build_interpretation_from_synthesis
from app.engines.explainability_engine import build_explainability

try:
    from app.repositories.yearly_prediction_repo import save_yearly_prediction
except Exception:  # pragma: no cover
    save_yearly_prediction = None


router = APIRouter(prefix="/api/prediction", tags=["Prediction"])


def _normalize_confidence(synthesis: Dict[str, Any]) -> Dict[str, Any]:
    """
    EPIC-7 API-layer guardrail.
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


@router.post("/yearly")
def generate_yearly_prediction(payload: dict, db=Depends(get_db)):
    """
    EPIC-9.1 / EPIC-10-ready
    Yearly prediction endpoint.

    Rules:
    - Reuse envelope + synthesis
    - No astrology in API
    - Explainability derived only
    """

    base_chart_id = payload.get("base_chart_id")
    year = payload.get("year")

    if not base_chart_id or year is None:
        raise HTTPException(status_code=400, detail="Missing base_chart_id or year")

    base_chart = get_base_chart_by_id(db, base_chart_id)
    if not base_chart:
        raise HTTPException(status_code=404, detail="Birth chart not found")

    envelope = build_yearly_prediction_envelope(
        base_chart=base_chart.payload,
        year=int(year),
    )

    synthesis = synthesize_from_envelope(envelope)
    synthesis = _normalize_confidence(synthesis)

    interpretation = build_interpretation_from_synthesis(envelope, synthesis)

    explainability = build_explainability(
        dasha_context=envelope["dasha_context"],
        confidence=synthesis.get("confidence"),
        period_type="yearly",
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    prediction_id = f"yearly:{base_chart_id}:{int(year)}"

    if save_yearly_prediction:
        save_yearly_prediction(
            base_chart_id=base_chart_id,
            year=int(year),
            status="success",
            envelope=envelope,
            synthesis=synthesis,
            interpretation=interpretation,
            engine_version=synthesis.get("engine_version", "unknown"),
        )

    summary = None
    if isinstance(interpretation, dict):
        summary = interpretation.get("summary") or interpretation.get("headline")

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
        "explainability": explainability.model_dump()
        if hasattr(explainability, "model_dump")
        else explainability,
    }
