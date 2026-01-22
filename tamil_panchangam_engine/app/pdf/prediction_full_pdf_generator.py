"""
Deterministic Full Prediction PDF Generator

EPIC-15A.B
- Comprehensive yearly prediction report
- Birth + Dasha + 12-month outlook
- No AI (EPIC-16 hook only)
- No astrology logic
"""

import io
from typing import List, Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib import colors

from svglib.svglib import svg2rlg

from app.pdf.prediction_full_pdf_context import PredictionFullPdfContext


# ===============================
# Layout Constants
# ===============================

PAGE_WIDTH, PAGE_HEIGHT = A4

LEFT_MARGIN = RIGHT_MARGIN = 0.75 * inch
TOP_MARGIN = BOTTOM_MARGIN = 0.75 * inch

SECTION_SPACING = 0.3 * inch
LINE_SPACING = 0.15 * inch

CHART_WIDTH = 3.5 * inch
CHART_HEIGHT = 3.5 * inch


# ===============================
# Public API
# ===============================

def generate_prediction_full_pdf(
    pdf_context: PredictionFullPdfContext
) -> bytes:
    """
    Generate the Full Prediction Report PDF.

    Deterministic:
    Same context => same output.
    """

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=RIGHT_MARGIN,
        leftMargin=LEFT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )

    styles = getSampleStyleSheet()
    story: List = []

    # ------------------------------------------------
    # Cover Page
    # ------------------------------------------------

    story.append(
        Paragraph(
            "<b>Comprehensive Astrology Prediction Report</b>",
            styles["Title"],
        )
    )
    story.append(Spacer(1, SECTION_SPACING))

    story.append(
        Paragraph(
            _format_metadata(pdf_context.metadata),
            styles["Normal"],
        )
    )
    story.append(Spacer(1, SECTION_SPACING))

    story.append(PageBreak())

    # ------------------------------------------------
    # Birth Foundation
    # ------------------------------------------------

    story.append(Paragraph("<b>Birth Foundation</b>", styles["Heading2"]))
    story.append(Spacer(1, LINE_SPACING))

    for key, value in pdf_context.birth_summary.items():
        story.append(
            Paragraph(f"<b>{key}:</b> {value}", styles["Normal"])
        )
        story.append(Spacer(1, LINE_SPACING))

    story.append(Spacer(1, SECTION_SPACING))
    story.append(_render_charts_table(pdf_context.charts))
    story.append(Spacer(1, SECTION_SPACING))

    # Birth Highlights
    if pdf_context.birth_highlights:
        story.append(Paragraph("<b>Birth Highlights</b>", styles["Heading3"]))
        story.append(Spacer(1, LINE_SPACING))

        for item in pdf_context.birth_highlights:
            story.append(
                Paragraph(
                    f"<b>{item.get('title')}:</b> {item.get('description')}",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, LINE_SPACING))

    story.append(PageBreak())

    # ------------------------------------------------
    # Dasha & Antar Overview
    # ------------------------------------------------

    story.append(
        Paragraph("<b>Vimshottari Dasha Overview</b>", styles["Heading2"])
    )
    story.append(Spacer(1, LINE_SPACING))

    for key, value in pdf_context.dasha_summary.items():
        story.append(
            Paragraph(f"<b>{key}:</b> {value}", styles["Normal"])
        )
        story.append(Spacer(1, LINE_SPACING))

    if pdf_context.antar_influence:
        story.append(Spacer(1, SECTION_SPACING))
        story.append(
            Paragraph("<b>Active Antar Dasha Influence</b>", styles["Heading3"])
        )
        story.append(Spacer(1, LINE_SPACING))

        for item in pdf_context.antar_influence:
            story.append(
                Paragraph(item.get("description", ""), styles["Normal"])
            )
            story.append(Spacer(1, LINE_SPACING))

    story.append(PageBreak())

    # ------------------------------------------------
    # Monthly Predictions (One Month Per Page)
    # ------------------------------------------------

    for month_block in pdf_context.monthly_predictions:
        story.append(
            Paragraph(
                f"<b>{month_block.get('month')}</b>",
                styles["Heading2"],
            )
        )
        story.append(Spacer(1, LINE_SPACING))

        if month_block.get("theme"):
            story.append(
                Paragraph(
                    f"<b>Theme:</b> {month_block.get('theme')}",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, LINE_SPACING))

        # Life Areas
        for area in month_block.get("life_areas", []):
            story.append(
                Paragraph(
                    f"<b>{area.get('area')}</b> "
                    f"({area.get('confidence', 'medium').capitalize()} confidence)",
                    styles["Heading4"],
                )
            )
            story.append(Spacer(1, LINE_SPACING))
            story.append(
                Paragraph(area.get("interpretation", ""), styles["Normal"])
            )
            story.append(Spacer(1, LINE_SPACING))

        # Timing
        timing = month_block.get("timing", {})
        if timing:
            story.append(Spacer(1, LINE_SPACING))
            story.append(
                Paragraph("<b>Timing Highlights</b>", styles["Heading4"])
            )

            if timing.get("supportive_windows"):
                story.append(
                    Paragraph(
                        f"Supportive: {', '.join(timing['supportive_windows'])}",
                        styles["Normal"],
                    )
                )

            if timing.get("caution_windows"):
                story.append(
                    Paragraph(
                        f"Caution: {', '.join(timing['caution_windows'])}",
                        styles["Normal"],
                    )
                )

        story.append(PageBreak())

    # ------------------------------------------------
    # Explainability
    # ------------------------------------------------

    if pdf_context.explainability:
        story.append(
            Paragraph("<b>Why These Predictions Were Made</b>", styles["Heading2"])
        )
        story.append(Spacer(1, LINE_SPACING))

        for item in pdf_context.explainability:
            story.append(
                Paragraph(f"- {item.get('reason')}", styles["Normal"])
            )
            story.append(Spacer(1, LINE_SPACING))

        story.append(PageBreak())

    # ------------------------------------------------
    # Remedies & Recommendations
    # ------------------------------------------------

    if pdf_context.remedies:
        story.append(
            Paragraph("<b>Remedies & Recommendations</b>", styles["Heading2"])
        )
        story.append(Spacer(1, LINE_SPACING))

        for remedy in pdf_context.remedies:
            story.append(
                Paragraph(
                    f"<b>{remedy.get('title')}:</b> {remedy.get('description')}",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, LINE_SPACING))

        story.append(PageBreak())

    # ------------------------------------------------
    # Footer
    # ------------------------------------------------

    story.append(
        Paragraph(
            "<font size=8 color=grey>"
            "This report is generated deterministically using astrological rules. "
            "AI-generated explanations may be added in future versions and will "
            "always be explicitly labeled."
            "</font>",
            styles["Normal"],
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ===============================
# Helper Functions
# ===============================

def _format_metadata(metadata: Dict[str, str]) -> str:
    lines = []
    for key in sorted(metadata.keys()):
        lines.append(f"<b>{key}:</b> {metadata[key]}")
    return "<br/>".join(lines)


def _render_charts_table(charts: Dict[str, str]) -> Table:
    d1_svg = charts.get("d1_svg")
    d9_svg = charts.get("d9_svg")

    d1_drawing = _svg_to_drawing(d1_svg) if d1_svg else None
    d9_drawing = _svg_to_drawing(d9_svg) if d9_svg else None

    data = [
        [
            _drawing_cell(d1_drawing, "Rasi Chart (D1)"),
            _drawing_cell(d9_drawing, "Navamsa Chart (D9)"),
        ]
    ]

    table = Table(data, colWidths=[CHART_WIDTH, CHART_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _svg_to_drawing(svg_str: str):
    drawing = svg2rlg(io.BytesIO(svg_str.encode("utf-8")))
    drawing.scale(
        CHART_WIDTH / drawing.width,
        CHART_HEIGHT / drawing.height,
    )
    return drawing


def _drawing_cell(drawing, title: str):
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>{title}</b>", styles["Normal"]))
    elements.append(Spacer(1, LINE_SPACING))

    if drawing:
        elements.append(drawing)
    else:
        elements.append(
            Paragraph("Chart not available", styles["Normal"])
        )

    return elements
