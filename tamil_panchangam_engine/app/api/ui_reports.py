from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from app.db.session import get_db
from app.services.prediction_aggregation_service import (
    build_prediction_report_snapshot,
)
from app.services.prediction_ui_mapper import (
    map_snapshot_to_ui_read_model,
)

router = APIRouter(prefix="/api/ui", tags=["UI Reports"])


@router.get("/monthly-report")
def get_monthly_ui_report(
    base_chart_id: str,
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    """
    EPIC-7.3
    UI Read-Only Monthly Report Endpoint

    - Loads persisted snapshot
    - Maps to UI read model
    - No computation or mutation
    """

    try:
        snapshot = build_prediction_report_snapshot(
            db=db,
            base_chart_id=base_chart_id,
            year=year,
            month=month,
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    ui_model = map_snapshot_to_ui_read_model(snapshot)

    return ui_model
