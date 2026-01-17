from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from typing import Any, Dict

from app.db.session import get_db
from app.repositories.base_chart_repo import get_base_chart_by_id

from app.engines.weekly_prediction_envelope import build_weekly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope
from app.engines.interpretation_engine import build_interpretation_from_synthesis
from app.engines.explainability_engine import build_explainability

# OPTIONAL (recommended): persist weekly predictions like monthly
# If you don't have this repo yet, add it in EPIC-9 persistence step.
try:
    from app.repositories.weekly_prediction_repo import save_weekly_prediction
except Exception:  # pragma: no cover
    save_weekly_prediction = None


router = APIRouter(prefix="/api/prediction", tags=["Prediction"])


def _normalize_confidence(synthesis: Dict[str, Any]) -> Dict[str, Any]:
    """
    EPIC-7 guardrail: ensure confidence exists even if engines omit it.
    Do NOT move into engines. API layer only.
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
        raise HTTPException(status_code=400, detail="Missing base_chart_id, year, or week")

    # Fetch chart from DuckDB via repo (source of truth)
    base_chart = get_base_chart_by_id(db, base_chart_id)
    if not base_chart:
        raise HTTPException(status_code=404, detail="Birth chart not found")

    envelope = build_weekly_prediction_envelope(
        base_chart=base_chart.payload,
        year=int(year),
        week=int(week),
    )

    synthesis = synthesize_from_envelope(envelope)
    synthesis = _normalize_confidence(synthesis)

    interpretation = build_interpretation_from_synthesis(envelope, synthesis)

    # Derived only (never persisted)
    explainability = build_explainability(
        dasha_context=envelope["dasha_context"],
        confidence=synthesis.get("confidence"),
        period_type="weekly",
    )

    generated_at = datetime.now(timezone.utc).isoformat()

    # Persist weekly prediction (recommended; aligns with locked truth)
    # If repo is not present yet, we still return response without persistence.
    prediction_id = f"weekly:{base_chart_id}:{int(year)}:{int(week)}"
    if save_weekly_prediction:
        try:
            save_weekly_prediction(
                db=db,
                base_chart_id=base_chart_id,
                year=int(year),
                week=int(week),
                status="success",
                envelope=envelope,
                synthesis=synthesis,
                interpretation=interpretation,
                engine_version=synthesis.get("engine_version", "unknown"),
            )
        except Exception as e:
            # Persistence failure should be explicit
            raise HTTPException(status_code=500, detail=f"Failed to persist weekly prediction: {str(e)}")

    # Summary: keep minimal + deterministic.
    # If your interpretation engine already returns a summary field, prefer it.
    summary = None
    if isinstance(interpretation, dict):
        summary = interpretation.get("summary") or interpretation.get("headline")

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
        "explainability": explainability.model_dump() if hasattr(explainability, "model_dump") else explainability,
    }
