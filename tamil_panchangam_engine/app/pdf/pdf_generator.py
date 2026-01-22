import io
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

from app.pdf.birth_chart_pdf_context import BirthChartPdfContext


def _svg_string_to_drawing(svg_string: str):
    svg_io = io.StringIO(svg_string)
    return svg2rlg(svg_io)


def generate_birth_chart_pdf(context: BirthChartPdfContext) -> bytes:
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    elements = []

    # ---- Title ----
    elements.append(Paragraph("<b>Birth Chart Report</b>", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))

    # ---- D1 Chart ----
    elements.append(Paragraph("<b>Rasi Chart (D1)</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    d1_drawing = _svg_string_to_drawing(context.charts["d1_svg"])
    elements.append(d1_drawing)
    elements.append(Spacer(1, 0.5 * inch))

    # ---- D9 Chart ----
    elements.append(Paragraph("<b>Navamsa Chart (D9)</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    d9_drawing = _svg_string_to_drawing(context.charts["d9_svg"])
    elements.append(d9_drawing)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
