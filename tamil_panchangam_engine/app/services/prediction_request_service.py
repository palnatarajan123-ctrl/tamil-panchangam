# app/services/prediction_request_service.py

from datetime import date
from app.schemas.prediction_input import PredictionRequest


class UnsupportedPredictionMode(Exception):
    pass


def normalize_prediction_request(
    req: PredictionRequest,
) -> dict:
    """
    EPIC-10.2
    Normalize PredictionRequest into legacy-compatible parameters.

    TEMPORARY:
    - Supports monthly mode only
    - Event-based is validated but rejected
    """

    if req.timeframe.mode != "monthly":
        raise UnsupportedPredictionMode(
            "Only monthly predictions are supported at this time"
        )

    if not req.timeframe.year or not req.timeframe.month:
        raise ValueError("Year and month required for monthly prediction")

    return {
        "base_chart_id": req.base_chart_id,
        "year": req.timeframe.year,
        "month": req.timeframe.month,
        "triggers": req.triggers.dict(),
        "levers": req.levers.dict(),
        "focus_areas": req.focus_areas,
        "constraints": req.constraints.dict(),
        "output": req.output.dict(),
    }
