"""
Deterministic Birth Chart PDF Generator

EPIC-15A.A
- Birth chart only
- Timeless
- No predictions
- No AI
- Fully deterministic
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
)
from reportlab.lib import colors

from svglib.svglib import svg2rlg

from app.pdf.birth_chart_pdf_context import BirthChartPdfContext


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

def generate_birth_chart_pdf(pdf_context: BirthChartPdfContext) -> bytes:
    """
    Generate Birth Chart PDF as bytes.

    Deterministic:
    - Same context => same output
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
    # Header / Cover
    # ------------------------------------------------

    story.append(
        Paragraph("<b>Birth Chart Report</b>", styles["Title"])
    )
    story.append(Spacer(1, SECTION_SPACING))

    story.append(
        Paragraph(
            _format_metadata(pdf_context.metadata),
            styles["Normal"],
        )
    )
    story.append(Spacer(1, SECTION_SPACING))

    # ------------------------------------------------
    # Birth Summary
    # ------------------------------------------------

    story.append(Paragraph("<b>Birth Summary</b>", styles["Heading2"]))
    story.append(Spacer(1, LINE_SPACING))

    for key, value in pdf_context.birth_summary.items():
        story.append(
            Paragraph(f"<b>{key}:</b> {value}", styles["Normal"])
        )
        story.append(Spacer(1, LINE_SPACING))

    story.append(Spacer(1, SECTION_SPACING))

    # ------------------------------------------------
    # Charts (D1 / D9)
    # ------------------------------------------------

    story.append(Paragraph("<b>Charts</b>", styles["Heading2"]))
    story.append(Spacer(1, LINE_SPACING))

    story.append(_render_charts_table(pdf_context.charts))
    story.append(Spacer(1, SECTION_SPACING))

    # ------------------------------------------------
    # Birth Highlights
    # ------------------------------------------------

    if pdf_context.highlights:
        story.append(Paragraph("<b>Birth Highlights</b>", styles["Heading2"]))
        story.append(Spacer(1, LINE_SPACING))

        for item in pdf_context.highlights:
            title = item.get("title", "Highlight")
            description = item.get("description", "")

            story.append(
                Paragraph(f"<b>{title}</b>", styles["Heading4"])
            )
            story.append(Spacer(1, LINE_SPACING))
            story.append(
                Paragraph(description, styles["Normal"])
            )
            story.append(Spacer(1, LINE_SPACING))

        story.append(Spacer(1, SECTION_SPACING))

    # ------------------------------------------------
    # Explainability
    # ------------------------------------------------

    if pdf_context.explainability:
        story.append(Paragraph("<b>Why These Themes Appear</b>", styles["Heading2"]))
        story.append(Spacer(1, LINE_SPACING))

        for item in pdf_context.explainability:
            reason = item.get("reason", "")
            story.append(
                Paragraph(f"- {reason}", styles["Normal"])
            )
            story.append(Spacer(1, LINE_SPACING))

        story.append(Spacer(1, SECTION_SPACING))

    # ------------------------------------------------
    # Footer
    # ------------------------------------------------

    story.append(
        Paragraph(
            "<font size=8 color=grey>"
            "This birth chart report is generated deterministically using "
            "traditional astrological rules. No AI-generated interpretation "
            "is included in this report."
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
    """
    Render metadata block.
    """
    lines = []
    for key in sorted(metadata.keys()):
        lines.append(f"<b>{key}:</b> {metadata[key]}")
    return "<br/>".join(lines)


def _render_charts_table(charts: Dict[str, str]) -> Table:
    """
    Render D1 and D9 SVG charts side-by-side.
    """

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

    table = Table(
        data,
        colWidths=[CHART_WIDTH, CHART_WIDTH],
    )

    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )

    return table


def _svg_to_drawing(svg_str: str):
    svg_bytes = svg_str.encode("utf-8")
    drawing = svg2rlg(io.BytesIO(svg_bytes))
    drawing.scale(
        CHART_WIDTH / drawing.width,
        CHART_HEIGHT / drawing.height,
    )
    return drawing


def _drawing_cell(drawing, title: str):
    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph(f"<b>{title}</b>", styles["Normal"])
    )
    elements.append(Spacer(1, LINE_SPACING))

    if drawing:
        elements.append(drawing)
    else:
        elements.append(
            Paragraph("Chart not available", styles["Normal"])
        )

    return elements
