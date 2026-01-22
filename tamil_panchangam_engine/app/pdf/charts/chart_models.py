"""
Deterministic PDF Generator for Monthly Predictions

EPIC-15A:
- Pure rendering
- Deterministic output
- No astrology logic
- No AI
"""

import io
from typing import Dict, List

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
from reportlab.graphics import renderPDF

from app.pdf.pdf_context import PdfContext

# app/pdf/charts/chart_models.py

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ChartSvgInput:
    chart_type: str                  # "D1" or "D9"
    planet_signs: Dict[str, List[str]]  # {"Aries": ["Sun", "Moon"], ...}
    title: str
    dignity: Optional[Dict[str, str]] = None

# ===============================
# PDF Layout Constants
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

def generate_monthly_prediction_pdf(pdf_context: PdfContext) -> bytes:
    """
    Generate Monthly Prediction PDF as bytes.

    Deterministic:
    - Same PdfContext => same PDF bytes
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
        Paragraph(
            "<b>Monthly Astrology Prediction</b>",
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
    # Charts Section (D1 / D9)
    # ------------------------------------------------

    story.append(Paragraph("<b>Charts</b>", styles["Heading2"]))
    story.append(Spacer(1, LINE_SPACING))

    charts_table = _render_charts_table(pdf_context.charts)
    story.append(charts_table)

    story.append(Spacer(1, SECTION_SPACING))

    # ------------------------------------------------
    # Narrative Overview
    # ------------------------------------------------

    story.append(Paragraph("<b>Narrative Overview</b>", styles["Heading2"]))
    story.append(Spacer(1, LINE_SPACING))

    for _, text in pdf_context.narrative.items():
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, LINE_SPACING))

    story.append(Spacer(1, SECTION_SPACING))

    # ------------------------------------------------
    # Life Area Interpretations
    # ------------------------------------------------

    story.append(Paragraph("<b>Life Areas</b>", styles["Heading2"]))
    story.append(Spacer(1, LINE_SPACING))

    for area in pdf_context.life_areas:
        title = area.get("area", "Life Area")
        description = area.get("interpretation", "")

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

    story.append(Paragraph("<b>Why This Was Said</b>", styles["Heading2"]))
    story.append(Spacer(1, LINE_SPACING))

    for item in pdf_context.explainability:
        reason = item.get("reason", "")
        story.append(Paragraph(f"- {reason}", styles["Normal"]))
        story.append(Spacer(1, LINE_SPACING))

    # ------------------------------------------------
    # Footer
    # ------------------------------------------------

    story.append(Spacer(1, SECTION_SPACING))
    story.append(
        Paragraph(
            "<font size=8 color=grey>"
            "This report is generated deterministically from astrological rules. "
            "No AI reasoning was used."
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
    Render D1 and D9 SVG charts side-by-side in a table.
    """

    d1_svg = charts.get("d1_svg")
    d9_svg = charts.get("d9_svg")

    d1_drawing = _svg_to_drawing(d1_svg) if d1_svg else None
    d9_drawing = _svg_to_drawing(d9_svg) if d9_svg else None

    data = [
        [
            _drawing_cell(d1_drawing, "D1 Chart"),
            _drawing_cell(d9_drawing, "D9 Chart"),
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
    """
    Convert SVG string to ReportLab drawing.
    """
    svg_bytes = svg_str.encode("utf-8")
    return svg2rlg(io.BytesIO(svg_bytes))


def _drawing_cell(drawing, title: str):
    """
    Wrap a drawing with an optional title.
    """
    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph(f"<b>{title}</b>", styles["Normal"])
    )
    elements.append(Spacer(1, LINE_SPACING))

    if drawing:
        drawing.scale(
            CHART_WIDTH / drawing.width,
            CHART_HEIGHT / drawing.height,
        )
        elements.append(drawing)
    else:
        elements.append(
            Paragraph("Chart not available", styles["Normal"])
        )

    return elements
