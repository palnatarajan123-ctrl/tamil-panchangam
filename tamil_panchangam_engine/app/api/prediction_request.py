from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_db
from app.schemas.prediction_input import PredictionRequest
from app.services.prediction_request_service import (
    normalize_prediction_request,
    UnsupportedPredictionMode,
)
from app.services.prediction_aggregation_service import (
    build_prediction_report_snapshot,
)

router = APIRouter(prefix="/api/prediction", tags=["Prediction"])


@router.post("/request")
def request_prediction(
    req: PredictionRequest,
    db: Session = Depends(get_db),
):
    """
    EPIC-10.3
    Accepts structured prediction request.
    """

    try:
        normalized = normalize_prediction_request(req)
    except UnsupportedPredictionMode as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    # TEMP: delegate to existing monthly pipeline
    snapshot = build_prediction_report_snapshot(
        db=db,
        base_chart_id=normalized["base_chart_id"],
        year=normalized["year"],
        month=normalized["month"],
    )

    return snapshot
