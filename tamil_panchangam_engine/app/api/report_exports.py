from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session

from app.db.session import get_db
from app.services.prediction_aggregation_service import (
    build_prediction_report_snapshot,
)
from app.pdf.report_builder import build_monthly_prediction_pdf

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/monthly/pdf")
def get_monthly_prediction_pdf(
    base_chart_id: str,
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    """
    EPIC-7.5.5
    Generate Monthly Prediction PDF

    - Loads persisted snapshot
    - Renders PDF
    - Streams bytes directly
    """

    try:
        snapshot = build_prediction_report_snapshot(
            db=db,
            base_chart_id=base_chart_id,
            year=year,
            month=month,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    # ✅ Builder returns bytes
    pdf_bytes = build_monthly_prediction_pdf(snapshot)

    filename = f"{base_chart_id}-{year}-{month:02d}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        },
    )
