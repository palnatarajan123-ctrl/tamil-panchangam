"""
PDF Report Builder

Generates:
- Monthly Prediction PDF (EPIC-7.5.x)

Rules:
- No DB access
- No recomputation
- Snapshot is immutable source of truth
- PDF consumes UI Read Model only
"""

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from app.models.report_schema import PredictionReportSnapshot
from app.services.prediction_ui_mapper import build_monthly_prediction_ui_model


# ============================================================
# CONSTANTS
# ============================================================

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 40
RIGHT_MARGIN = PAGE_WIDTH - 40
TOP_MARGIN = PAGE_HEIGHT - 40
BOTTOM_MARGIN = 50
LINE_HEIGHT = 14


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def build_monthly_prediction_pdf(
    snapshot: PredictionReportSnapshot,
    output_path,
) -> None:
    """
    EPIC-7.5.5
    Build Monthly Prediction PDF from snapshot.

    - No DB
    - No astrology logic
    - Uses UI read model
    - Writes to file-like buffer
    """

    ui = build_monthly_prediction_ui_model(snapshot)

    pdf = canvas.Canvas(output_path, pagesize=A4)
    y = TOP_MARGIN

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(LEFT_MARGIN, y, "Monthly Astrology Report")
    y -= 26

    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        LEFT_MARGIN,
        y,
        f"Period: {ui.meta.period_label} | Engine: {ui.meta.engine_version}",
    )
    y -= 14
    pdf.drawString(
        LEFT_MARGIN,
        y,
        f"Generated: {ui.meta.generated_at.isoformat()}",
    )
    y -= 24

    # --------------------------------------------------------
    # IDENTITY
    # --------------------------------------------------------
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(LEFT_MARGIN, y, "Birth Details")
    y -= 18

    pdf.setFont("Helvetica", 11)
    pdf.drawString(LEFT_MARGIN, y, f"Name: {ui.identity.name}")
    y -= 14
    pdf.drawString(LEFT_MARGIN, y, f"Place of Birth: {ui.identity.place_of_birth}")
    y -= 14
    pdf.drawString(LEFT_MARGIN, y, f"Date of Birth: {ui.identity.birth_date}")
    y -= 14
    pdf.drawString(
        LEFT_MARGIN,
        y,
        f"Lagna: {ui.identity.lagna} | Moon Sign: {ui.identity.moon_sign}",
    )
    y -= 24

    # --------------------------------------------------------
    # OVERVIEW
    # --------------------------------------------------------
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(LEFT_MARGIN, y, "Monthly Overview")
    y -= 18

    pdf.setFont("Helvetica", 11)
    pdf.drawString(LEFT_MARGIN, y, ui.overview["headline"])
    y -= 14
    pdf.drawString(
        LEFT_MARGIN,
        y,
        f"Overall Score: {ui.overview['overall_score']} "
        f"| Tone: {ui.overview['tone']} "
        f"| Confidence: {ui.overview['confidence']}",
    )
    y -= 26

    # --------------------------------------------------------
    # LIFE AREAS
    # --------------------------------------------------------
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(LEFT_MARGIN, y, "Life Areas")
    y -= 20

    for area in ui.life_areas:
        if y < BOTTOM_MARGIN + 100:
            pdf.showPage()
            y = TOP_MARGIN
            pdf.setFont("Helvetica", 11)

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(
            LEFT_MARGIN,
            y,
            f"{area.label} "
            f"(Score: {area.score}, "
            f"Confidence: {area.confidence}, "
            f"Tone: {area.sentiment})",
        )
        y -= 16

        pdf.setFont("Helvetica", 11)
        y = _draw_paragraph(pdf, area.summary, y)
        y -= 6
        y = _draw_paragraph(pdf, area.detail, y)
        y -= 16

    # --------------------------------------------------------
    # TIMING / PANCHA PAKSHI
    # --------------------------------------------------------
    if y < BOTTOM_MARGIN + 120:
        pdf.showPage()
        y = TOP_MARGIN

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(LEFT_MARGIN, y, "Timing & Activity Guidance")
    y -= 18

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        LEFT_MARGIN,
        y,
        f"Dominant Pakshi: {ui.timing.dominant_pakshi}",
    )
    y -= 14

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(LEFT_MARGIN, y, "Recommended:")
    y -= 14

    pdf.setFont("Helvetica", 11)
    for item in ui.timing.recommended:
        pdf.drawString(LEFT_MARGIN + 16, y, f"• {item}")
        y -= 12

    y -= 10
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(LEFT_MARGIN, y, "Avoid:")
    y -= 14

    pdf.setFont("Helvetica", 11)
    for item in ui.timing.avoid:
        pdf.drawString(LEFT_MARGIN + 16, y, f"• {item}")
        y -= 12

    # --------------------------------------------------------
    # DISCLAIMERS
    # --------------------------------------------------------
    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(LEFT_MARGIN, TOP_MARGIN, "Disclaimer")
    y = TOP_MARGIN - 20

    pdf.setFont("Helvetica", 10)
    for d in ui.disclaimers:
        pdf.drawString(LEFT_MARGIN, y, f"• {d}")
        y -= 14

    pdf.save()


# ============================================================
# HELPERS
# ============================================================

def _draw_paragraph(pdf, text: str, y: float) -> float:
    """
    Basic word-wrapped paragraph renderer.
    """
    max_width = RIGHT_MARGIN - LEFT_MARGIN
    words = text.split(" ")
    line = ""

    for word in words:
        test_line = f"{line} {word}".strip()
        if pdf.stringWidth(test_line, "Helvetica", 11) <= max_width:
            line = test_line
        else:
            pdf.drawString(LEFT_MARGIN, y, line)
            y -= LINE_HEIGHT
            line = word

    if line:
        pdf.drawString(LEFT_MARGIN, y, line)
        y -= LINE_HEIGHT

    return y
