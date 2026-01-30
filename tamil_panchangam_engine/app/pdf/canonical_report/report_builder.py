"""
Canonical PDF Report Builder - Main Entry Point

THIS IS THE SINGLE AUTHORITATIVE REPORT BUILDER.

All PDF generation must go through this module.
It reads from database/cache only - no recalculation.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .data_loader import build_report_data, ReportDataNotFoundError
from .pdf_renderer import render_pdf
from .config import REPORT_VERSION

logger = logging.getLogger(__name__)


class ReportBuildError(Exception):
    """Raised when report building fails."""
    pass


def build_canonical_report(
    base_chart_id: str,
    report_type: str,
    year: int,
    month: Optional[int] = None,
) -> bytes:
    """
    Build a canonical PDF report.
    
    This is the SINGLE ENTRY POINT for all PDF generation.
    
    Args:
        base_chart_id: The base chart UUID
        report_type: 'monthly' or 'yearly'
        year: The prediction year
        month: The prediction month (required for monthly)
    
    Returns:
        PDF bytes
    
    Raises:
        ReportBuildError: If report data is missing or rendering fails
    """
    
    if report_type == "monthly" and not month:
        raise ReportBuildError("Month is required for monthly reports")
    
    if report_type not in ("monthly", "yearly"):
        raise ReportBuildError(f"Invalid report type: {report_type}")
    
    logger.info(f"Building {report_type} report: {base_chart_id}/{year}/{month or 'full'}")
    
    try:
        report_data = build_report_data(
            base_chart_id=base_chart_id,
            report_type=report_type,
            year=year,
            month=month,
        )
    except ReportDataNotFoundError as e:
        logger.error(f"Report data not found: {e}")
        raise ReportBuildError(str(e))
    except Exception as e:
        logger.error(f"Failed to load report data: {e}")
        raise ReportBuildError(f"Failed to load report data: {e}")
    
    try:
        pdf_bytes = render_pdf(report_data)
    except Exception as e:
        logger.error(f"Failed to render PDF: {e}")
        raise ReportBuildError(f"Failed to render PDF: {e}")
    
    logger.info(f"Report generated: {len(pdf_bytes)} bytes")
    
    return pdf_bytes


def get_report_filename(
    base_chart_id: str,
    report_type: str,
    year: int,
    month: Optional[int] = None,
) -> str:
    """Generate a standardized filename for the report."""
    
    chart_short = base_chart_id[:8]
    
    if report_type == "monthly" and month:
        return f"panchangam_{chart_short}_{year}_{month:02d}.pdf"
    else:
        return f"panchangam_{chart_short}_{year}_yearly.pdf"
