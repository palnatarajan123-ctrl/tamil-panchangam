# app/api/prediction.py

from fastapi import APIRouter, HTTPException
from datetime import datetime
import json

from app.db.duckdb import get_conn

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

from app.models.schema import (
    MonthlyPredictionRequest,
    MonthlyPredictionResponse,
)

router = APIRouter(prefix="/api/prediction", tags=["Prediction"])


@router.post("/monthly", response_model=MonthlyPredictionResponse)
def generate_monthly_prediction(payload: MonthlyPredictionRequest):
    """
    EPIC-4 + EPIC-6 + EPIC-8

    Monthly prediction with:
    - Envelope (facts only)
    - Synthesis
    - Interpretation
    - Explainability (derived, not persisted)
    """

    # -------------------------------------------------
    # 1. Load immutable base chart (DuckDB)
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

    # Normalize base chart payload
    base_chart_payload = (
        base_chart["payload"]
        if isinstance(base_chart["payload"], dict)
        else json.loads(base_chart["payload"])
    )

    # -------------------------------------------------
    # 2. Check for persisted monthly prediction
    # -------------------------------------------------
    existing = get_monthly_prediction(
        base_chart_id=payload.base_chart_id,
        year=payload.year,
        month=payload.month,
    )

    if existing:
        envelope = json.loads(existing["envelope"])
        synthesis = json.loads(existing["synthesis"])
        interpretation = (
            json.loads(existing["interpretation"])
            if existing.get("interpretation")
            else None
        )

        # -------------------------------------------------
        # Backward compatibility: synthesis
        # -------------------------------------------------
        if "confidence" not in synthesis:
            synthesis["confidence"] = {
                "level": "medium",
                "reason": "Confidence not computed in legacy prediction",
                "source": "system-default",
            }

        # -------------------------------------------------
        # Backward compatibility: envelope
        # -------------------------------------------------
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
                "is_maha_active": True,
                "confidence": "high",
                "active_lords": [active_dasha["lord"]],
            }

    else:
        # -------------------------------------------------
        # 3. Build monthly prediction envelope (EPIC-6)
        # -------------------------------------------------
        envelope = build_monthly_prediction_envelope(
            base_chart=base_chart_payload,
            year=payload.year,
            month=payload.month,
        )

        # -------------------------------------------------
        # 4. Synthesis
        # -------------------------------------------------
        synthesis = synthesize_from_envelope(envelope)

        # -------------------------------------------------
        # 🔒 Synthesis normalization (EPIC-6 guard)
        # -------------------------------------------------
        if "confidence" not in synthesis:
            synthesis["confidence"] = {
                "level": "medium",
                "reason": "Confidence not computed by synthesis engine",
                "source": "system-default",
            }

        # -------------------------------------------------
        # 5. Interpretation
        # -------------------------------------------------
        interpretation = build_interpretation_from_synthesis(
            envelope=envelope,
            synthesis=synthesis,
        )

        # -------------------------------------------------
        # 6. Optional paraphrasing
        # -------------------------------------------------
        interpretation = paraphrase_interpretation(
            interpretation,
            enabled=True,
        )

        # -------------------------------------------------
        # 7. Persist monthly prediction (NO explainability)
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
                engine_version="monthly-prediction-v1",
            )


    # -------------------------------------------------
    # 8. Explainability (derived, EPIC-8)
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
    # 9. Final response
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
    )
