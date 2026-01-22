from datetime import datetime

from app.pdf.birth_chart_pdf_context import BirthChartPdfContext
from app.pdf.charts.chart_models import ChartSvgInput
from app.pdf.charts.south_indian_svg import render_south_indian_chart_svg

def normalize_planet_signs(raw: dict) -> dict:
    """
    Convert:
      {"Sun": "Aries", "Moon": "Taurus"}
    → {"Aries": ["Sun"], "Taurus": ["Moon"]}
    """
    normalized = {}
    for planet, sign in raw.items():
        if not sign:
            continue
        normalized.setdefault(sign, []).append(planet)
    return normalized


def build_birth_chart_pdf_context(
    *,
    chart_id: str,
    birth_interpretation: dict,
    d1_chart: dict,
    d9_chart: dict,
    d9_dignity: dict | None,
    explainability: list,
) -> BirthChartPdfContext:

    # ✅ NORMALIZE HERE — ONCE
    d1_chart = normalize_planet_signs(d1_chart)
    d9_chart = normalize_planet_signs(d9_chart)

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

    return BirthChartPdfContext(
        metadata={
            "chart_id": chart_id,
            "generated_at": datetime.utcnow().isoformat(),
        },
        birth_summary=birth_interpretation.get("birth_summary", {}),
        charts={
            "d1_svg": d1_svg,
            "d9_svg": d9_svg,
        },
        highlights=birth_interpretation.get("highlights", []),
        explainability=explainability or [],
    )
