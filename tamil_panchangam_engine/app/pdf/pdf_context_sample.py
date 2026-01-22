"""
Sample PdfContext for EPIC-15A

Used ONLY for:
- Local PDF generation
- Determinism validation
- Rendering sanity checks

⚠️ This file must NOT import astrology engines.
⚠️ This file must NOT touch DB or API.
"""

from datetime import datetime

from app.pdf.pdf_context import PdfContext
from app.pdf.charts.chart_models import ChartSvgInput
from app.pdf.charts.south_indian_svg import render_south_indian_chart_svg


# -------------------------------------------------
# Sample Chart Inputs (Hardcoded)
# -------------------------------------------------

D1_INPUT = ChartSvgInput(
    chart_type="D1",
    planet_signs={
        "Sun": "Aries",
        "Moon": "Cancer",
        "Mars": "Leo",
        "Mercury": "Taurus",
        "Jupiter": "Sagittarius",
        "Venus": "Pisces",
        "Saturn": "Aquarius",
        "Rahu": "Gemini",
        "Ketu": "Sagittarius",
    },
    title="Rasi Chart (D1)",
)

D9_INPUT = ChartSvgInput(
    chart_type="D9",
    planet_signs={
        "Sun": "Leo",
        "Moon": "Taurus",
        "Mars": "Capricorn",
        "Mercury": "Virgo",
        "Jupiter": "Cancer",
        "Venus": "Pisces",
        "Saturn": "Libra",
        "Rahu": "Scorpio",
        "Ketu": "Taurus",
    },
    dignity={
        "Sun": "neutral",
        "Moon": "exalted",
        "Mars": "exalted",
        "Mercury": "exalted",
        "Jupiter": "exalted",
        "Venus": "exalted",
        "Saturn": "exalted",
        "Rahu": "neutral",
        "Ketu": "neutral",
    },
    title="Navamsa Chart (D9)",
)

# -------------------------------------------------
# Render SVGs
# -------------------------------------------------

D1_SVG = render_south_indian_chart_svg(D1_INPUT)
D9_SVG = render_south_indian_chart_svg(D9_INPUT)

# -------------------------------------------------
# Sample PdfContext
# -------------------------------------------------

sample_pdf_context = PdfContext(
    metadata={
        "chart_id": "sample-chart-001",
        "prediction_id": "sample-prediction-2026-01",
        "month": "January",
        "year": "2026",
        "generated_at": datetime.utcnow().isoformat(),
    },
    birth_summary={
        "Name": "Sample User",
        "Date of Birth": "1990-05-12",
        "Time of Birth": "10:32 AM",
        "Place of Birth": "Chennai, India",
        "Moon Sign": "Cancer",
        "Ascendant": "Aries",
    },
    charts={
        "d1_svg": D1_SVG,
        "d9_svg": D9_SVG,
    },
    narrative={
        "overview": (
            "This month reflects a period of steady progress supported by "
            "strong planetary alignments. Effort applied consistently is "
            "likely to yield visible results."
        )
    },
    life_areas=[
        {
            "area": "Career",
            "interpretation": (
                "Career matters show forward momentum. Opportunities arise "
                "through disciplined effort and strategic planning."
            ),
        },
        {
            "area": "Relationships",
            "interpretation": (
                "Relationships benefit from patience and open communication. "
                "Avoid impulsive reactions."
            ),
        },
        {
            "area": "Health",
            "interpretation": (
                "Maintain balance in daily routines. Small adjustments to "
                "sleep and diet can have noticeable benefits."
            ),
        },
    ],
    explainability=[
        {
            "reason": (
                "The active dasha lord is well-supported by benefic transits, "
                "indicating stable outcomes."
            )
        },
        {
            "reason": (
                "Navamsa dignities reinforce confidence in long-term areas of "
                "growth, particularly career and learning."
            )
        },
    ],
)
