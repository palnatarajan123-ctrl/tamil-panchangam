from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from app.db.session import get_db
from app.core.auth import get_current_user
from app.repositories.base_chart_repo import user_owns_chart
from app.services.prediction_aggregation_service import (
    build_prediction_report_snapshot,
)
from app.services.prediction_ui_mapper import (
    map_snapshot_to_ui_read_model,
)

router = APIRouter(prefix="/ui", tags=["UI Reports"])


@router.get("/monthly-report")
def get_monthly_ui_report(
    base_chart_id: str,
    year: int,
    month: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    EPIC-7.3
    UI Read-Only Monthly Report Endpoint

    - Loads persisted snapshot
    - Maps to UI read model
    - No computation or mutation
    """

    # Ownership check (security fix, 2026-09-08): 404 either way so a
    # non-owner can't tell whether the chart exists.
    if not user_owns_chart(db, user, base_chart_id):
        raise HTTPException(status_code=404, detail="Base chart not found")

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
