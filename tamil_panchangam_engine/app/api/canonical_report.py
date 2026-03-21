"""
Canonical PDF Report API

THIS IS THE SINGLE ENTRY POINT FOR ALL PDF GENERATION.

There must be NO other PDF generation endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from typing import Optional
import logging
from app.core.limiter import limiter

from app.pdf.canonical_report import build_canonical_report, REPORT_VERSION
from app.pdf.canonical_report.report_builder import (
    ReportBuildError,
    get_report_filename,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


@limiter.limit("10/hour")
@router.get("/pdf")
def generate_pdf_report(
    request: Request,
    base_chart_id: str = Query(..., description="Base chart UUID"),
    report_type: str = Query(..., description="Report type: 'monthly' or 'yearly'"),
    year: int = Query(..., description="Prediction year"),
    month: Optional[int] = Query(None, description="Prediction month (required for monthly)"),
):
    """
    Generate a canonical PDF report.
    
    This is the ONLY endpoint for PDF generation.
    
    The report reads ALL data from database/cache.
    It NEVER recalculates any astrological data.
    
    Args:
        base_chart_id: Base chart UUID
        report_type: 'monthly' or 'yearly'
        year: Prediction year
        month: Prediction month (required for monthly reports)
    
    Returns:
        PDF file as attachment
    """
    
    if report_type == "monthly" and month is None:
        raise HTTPException(
            status_code=400,
            detail="Month is required for monthly reports"
        )
    
    if report_type not in ("monthly", "yearly"):
        raise HTTPException(
            status_code=400,
            detail="report_type must be 'monthly' or 'yearly'"
        )
    
    if month is not None and (month < 1 or month > 12):
        raise HTTPException(
            status_code=400,
            detail="Month must be between 1 and 12"
        )
    
    try:
        pdf_bytes = build_canonical_report(
            base_chart_id=base_chart_id,
            report_type=report_type,
            year=year,
            month=month,
        )
    except ReportBuildError as e:
        logger.error(f"Report build failed: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error generating report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate report. Please try again."
        )
    
    filename = get_report_filename(base_chart_id, report_type, year, month)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Version": REPORT_VERSION,
        }
    )


@router.get("/pdf/preview")
def preview_pdf_report(
    base_chart_id: str = Query(..., description="Base chart UUID"),
    report_type: str = Query(..., description="Report type: 'monthly' or 'yearly'"),
    year: int = Query(..., description="Prediction year"),
    month: Optional[int] = Query(None, description="Prediction month (required for monthly)"),
):
    """
    Preview a PDF report inline (same as generate but displayed in browser).
    """
    
    if report_type == "monthly" and month is None:
        raise HTTPException(
            status_code=400,
            detail="Month is required for monthly reports"
        )
    
    if report_type not in ("monthly", "yearly"):
        raise HTTPException(
            status_code=400,
            detail="report_type must be 'monthly' or 'yearly'"
        )
    
    try:
        pdf_bytes = build_canonical_report(
            base_chart_id=base_chart_id,
            report_type=report_type,
            year=year,
            month=month,
        )
    except ReportBuildError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error generating report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate report. Please try again."
        )
    
    filename = get_report_filename(base_chart_id, report_type, year, month)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "X-Report-Version": REPORT_VERSION,
        }
    )
