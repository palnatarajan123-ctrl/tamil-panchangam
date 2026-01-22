"""
PdfContext Builder

Transforms interpretation + explainability outputs
into a canonical PdfContext for deterministic PDF rendering.
"""

from datetime import datetime

from app.pdf.pdf_context import PdfContext
from app.pdf.charts.chart_models import ChartSvgInput
from app.pdf.charts.south_indian_svg import render_south_indian_chart_svg


def build_pdf_context(
    *,
    chart_id: str,
    prediction_id: str,
    month: int,
    year: int,
    interpretation: dict,
    explainability: list,
    d1_chart: dict,
    d9_chart: dict,
    d9_dignity: dict | None,
) -> PdfContext:
    """
    Build PdfContext from authoritative outputs.

    Rules:
    - No astrology logic
    - No inference
    - No mutation
    """

    # ----------------------------
    # Charts (SVG rendering)
    # ----------------------------

    d1_input = ChartSvgInput(
        chart_type="D1",
        planet_signs=d1_chart,
        title="Rasi Chart (D1)",
    )

    d9_input = ChartSvgInput(
        chart_type="D9",
        planet_signs=d9_chart,
        dignity=d9_dignity,
        title="Navamsa Chart (D9)",
    )

    d1_svg = render_south_indian_chart_svg(d1_input)
    d9_svg = render_south_indian_chart_svg(d9_input)

    # ----------------------------
    # PdfContext Assembly
    # ----------------------------

    return PdfContext(
        metadata={
            "chart_id": chart_id,
            "prediction_id": prediction_id,
            "month": str(month),
            "year": str(year),
            "generated_at": datetime.utcnow().isoformat(),
        },
        birth_summary=interpretation.get("birth_summary", {}),
        charts={
            "d1_svg": d1_svg,
            "d9_svg": d9_svg,
        },
        narrative=interpretation.get("narrative", {}),
        life_areas=interpretation.get("life_areas", []),
        explainability=explainability or [],
    )
