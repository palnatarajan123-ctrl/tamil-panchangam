# app/api/reports.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session
import io
import json

from app.db.session import get_db
from app.repositories.base_chart_repo import get_base_chart_by_id
from app.repositories.prediction_repo import get_predictions_for_year

# -----------------------------
# Legacy PDF (ReportLab ONLY)
# -----------------------------
from app.pdf.birth_chart_pdf_context_builder import (
    build_birth_chart_pdf_context,
)
from app.pdf.pdf_generator import (
    generate_birth_chart_pdf,
)

from app.pdf.prediction_full_pdf_context_builder import (
    build_prediction_full_pdf_context,
)
from app.pdf.prediction_full_pdf_generator import (
    generate_prediction_full_pdf,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


# -----------------------------
# Small, safe JSON normalizer
# -----------------------------
def _json(v, default):
    if v is None:
        return default
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return default


# =====================================================
# 1️⃣ Birth Chart PDF (LEGACY – ReportLab)
# /api/reports/charts/{base_chart_id}/pdf
# =====================================================

@router.get("/charts/{base_chart_id}/pdf")
def download_birth_chart_pdf(
    base_chart_id: str,
    db: Session = Depends(get_db),
):
    """
    EPIC-15A (Legacy)
    Birth Chart PDF (D1 + D9 only)

    NOTE:
    - Uses ReportLab
    - SVG → PDF
    - Known layout limitations
    """

    chart = get_base_chart_by_id(db, base_chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Birth chart not found")

    if not chart.get("locked"):
        raise HTTPException(status_code=400, detail="Base chart is not locked")

    # -----------------------------
    # Normalize ONCE
    # -----------------------------
    payload = _json(chart.get("payload"), {})

    birth_interpretation = _json(chart.get("birth_interpretation"), {})
    explainability = _json(chart.get("birth_explainability"), [])

    d1_chart = _json(
        chart.get("rasi_planet_signs"),
        payload.get("rasi", {}).get("planet_signs", {}),
    )

    d9_chart = _json(
        chart.get("navamsa_planet_signs"),
        payload.get("navamsa", {}).get("planet_signs", {}),
    )

    d9_dignity = _json(
        chart.get("navamsa_dignity"),
        payload.get("navamsa", {}).get("dignity"),
    )

    # -----------------------------
    # Build PDF Context
    # -----------------------------
    pdf_context = build_birth_chart_pdf_context(
        chart_id=chart["id"],
        birth_interpretation=birth_interpretation,
        d1_chart=d1_chart,
        d9_chart=d9_chart,
        d9_dignity=d9_dignity,
        explainability=explainability,
    )

    pdf_bytes = generate_birth_chart_pdf(pdf_context)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="birth_chart.pdf"'
        },
    )


# =====================================================
# 2️⃣ Prediction Full Report PDF (LEGACY)
# /api/reports/prediction/{chart_id}/{year}/full-report/pdf
# =====================================================

@router.get("/prediction/{chart_id}/{year}/full-report/pdf")
def download_full_prediction_report(
    chart_id: str,
    year: int,
    db: Session = Depends(get_db),
):
    """
    Comprehensive Prediction Report PDF (Legacy)
    """

    chart = get_base_chart_by_id(db, chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Birth chart not found")

    predictions = get_predictions_for_year(
        db=db,
        chart_id=chart_id,
        year=year,
    )

    if not predictions:
        raise HTTPException(
            status_code=404,
            detail="No predictions found for this year",
        )

    monthly_interpretations = []
    monthly_explainability = []

    for p in predictions:
        monthly_interpretations.append(_json(p.interpretation, {}))
        monthly_explainability.extend(_json(p.explainability, []))

    pdf_context = build_prediction_full_pdf_context(
        chart_id=chart_id,
        year=year,
        birth_interpretation=_json(chart.get("birth_interpretation"), {}),
        birth_explainability=_json(chart.get("birth_explainability"), []),
        dasha_summary=_json(chart.get("dasha_summary"), {}),
        antar_influence=_json(chart.get("antar_influence"), []),
        monthly_interpretations=monthly_interpretations,
        monthly_explainability=monthly_explainability,
        remedies=_json(chart.get("remedies"), []),
        d1_chart=_json(chart.get("rasi_planet_signs"), {}),
        d9_chart=_json(chart.get("navamsa_planet_signs"), {}),
        d9_dignity=_json(chart.get("navamsa_dignity"), None),
    )

    pdf_bytes = generate_prediction_full_pdf(pdf_context)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition":
            f'attachment; filename="prediction_report_{year}.pdf"',
        },
    )
