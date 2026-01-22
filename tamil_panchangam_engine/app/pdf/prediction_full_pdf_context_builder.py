"""
Prediction Full PDF Context Builder

Assembles a PredictionFullPdfContext from authoritative,
already-computed outputs.

Rules:
- No astrology computation
- No inference
- No mutation
- No engine calls
"""

from datetime import datetime

from app.pdf.prediction_full_pdf_context import PredictionFullPdfContext
from app.pdf.charts.chart_models import ChartSvgInput
from app.pdf.charts.south_indian_svg import render_south_indian_chart_svg


def build_prediction_full_pdf_context(
    *,
    chart_id: str,
    year: int,
    birth_interpretation: dict,
    birth_explainability: list,
    dasha_summary: dict,
    antar_influence: list,
    monthly_interpretations: list,
    monthly_explainability: list,
    remedies: list,
    d1_chart: dict,
    d9_chart: dict,
    d9_dignity: dict | None,
) -> PredictionFullPdfContext:
    """
    Build the Full Prediction PDF context.

    Inputs MUST already be computed and normalized upstream.
    """

    # ----------------------------
    # Render Charts (SVG)
    # ----------------------------

    d1_svg = render_south_indian_chart_svg(
        ChartSvgInput(
            chart_type="D1",
            planet_signs=d1_chart,
            title="Rasi Chart (D1)",
        )
    )

    d9_svg = render_south_indian_chart_svg(
        ChartSvgInput(
            chart_type="D9",
            planet_signs=d9_chart,
            dignity=d9_dignity,
            title="Navamsa Chart (D9)",
        )
    )

    # ----------------------------
    # Assemble Monthly Predictions
    # ----------------------------

    monthly_predictions = []

    for item in monthly_interpretations:
        monthly_predictions.append(
            {
                "month": item.get("month"),
                "theme": item.get("theme"),
                "life_areas": item.get("life_areas", []),
                "timing": item.get("timing", {}),
            }
        )

    # ----------------------------
    # Assemble Final Context
    # ----------------------------

    return PredictionFullPdfContext(
        metadata={
            "chart_id": chart_id,
            "year": str(year),
            "generated_at": datetime.utcnow().isoformat(),
        },
        birth_summary=birth_interpretation.get("birth_summary", {}),
        charts={
            "d1_svg": d1_svg,
            "d9_svg": d9_svg,
        },
        birth_highlights=birth_interpretation.get("highlights", []),
        dasha_summary=dasha_summary,
        antar_influence=antar_influence or [],
        monthly_predictions=monthly_predictions,
        explainability=(
            birth_explainability or []
        ) + (
            monthly_explainability or []
        ),
        remedies=remedies or [],
        ai_explanation=None,  # Explicitly off for EPIC-15A
    )
