# app/api/predictions_ui.py

from datetime import date
from fastapi import APIRouter, HTTPException

from app.schemas.prediction_input import (
    PredictionRequest,
    Epic6Defaults,
)
from app.schemas.predictions import PredictionUIResponse
from app.services.prediction_engine import (
    PredictionEngine,
    Epic6PredictionContext,
)

router = APIRouter(prefix="/ui", tags=["ui-predictions"])


# -------------------------------------------------
# Replace with your real services
# -------------------------------------------------

def get_dasha_service():
    from app.services.dasha import DashaService
    return DashaService()


def get_base_chart_or_404(base_chart_id: str):
    from app.repositories.base_chart_repo import get_base_chart_by_id
    chart = get_base_chart_by_id(base_chart_id)
    if chart is None:
        raise HTTPException(status_code=404, detail="Base chart not found")
    return chart


# -------------------------------------------------
# UI Prediction Endpoint (EPIC-6)
# -------------------------------------------------

@router.post("/predictions", response_model=PredictionUIResponse)
def create_ui_prediction(req: PredictionRequest):
    # 1. Normalize request for EPIC-6
    req = Epic6Defaults.normalize(req)

    # 2. Resolve timeframe
    if req.timeframe.mode == "monthly":
        if req.timeframe.year is None or req.timeframe.month is None:
            raise HTTPException(
                status_code=422,
                detail="Monthly mode requires year and month",
            )
        start = date(req.timeframe.year, req.timeframe.month, 1)
        if req.timeframe.month == 12:
            end = date(req.timeframe.year + 1, 1, 1)
        else:
            end = date(req.timeframe.year, req.timeframe.month + 1, 1)
        end = end.fromordinal(end.toordinal() - 1)
        label = start.strftime("%b %Y")

    elif req.timeframe.mode == "event":
        if not req.timeframe.start_date or not req.timeframe.end_date:
            raise HTTPException(
                status_code=422,
                detail="Event mode requires start_date and end_date",
            )
        start = req.timeframe.start_date
        end = req.timeframe.end_date
        label = f"{start} → {end}"

    else:
        raise HTTPException(status_code=400, detail="Unsupported timeframe mode")

    # 3. Validate base chart exists
    get_base_chart_or_404(req.base_chart_id)

    # 4. Build EPIC-6 execution context
    ctx = Epic6PredictionContext(
        base_chart_id=req.base_chart_id,
        start_date=start,
        end_date=end,
        confidence_threshold=req.constraints.confidence_threshold,
    )

    # 5. Execute deterministic engine
    engine = PredictionEngine(dasha_service=get_dasha_service())
    dasha_context, payload = engine.build_from_context(ctx)

    # 6. UI response (NO persistence)
    return PredictionUIResponse(
        status="OK",
        as_of=date.today(),
        base_chart_id=req.base_chart_id,
        period={
            "type": "MONTH" if req.timeframe.mode == "monthly" else "EVENT",
            "start_date": start,
            "end_date": end,
            "label": label,
        },
        dasha_context=dasha_context,
        prediction=payload,
    )

