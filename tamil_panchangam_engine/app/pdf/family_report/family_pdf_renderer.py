# app/pdf/family_report/family_pdf_renderer.py
"""
Family Prediction PDF Renderer.
Uses ReportLab Platypus — same card-style layout as canonical_report/pdf_renderer.py.
"""

import io
import logging
from datetime import date
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)

logger = logging.getLogger(__name__)

# Match config.py COLORS exactly
COLORS = {
    "primary": (0.2, 0.15, 0.4),
    "secondary": (0.4, 0.35, 0.5),
    "accent": (0.8, 0.6, 0.2),
    "text": (0.1, 0.1, 0.1),
    "muted": (0.5, 0.5, 0.5),
    "background": (0.98, 0.97, 0.95),
}
MARGIN = 50

# Type → color mapping for PDF badges
PEAK_COLOR = colors.Color(0.13, 0.45, 0.20)
TROUGH_COLOR = colors.Color(0.70, 0.20, 0.20)
THEME_COLORS = {
    "health": colors.Color(0.70, 0.20, 0.20),
    "relationship": colors.Color(0.70, 0.30, 0.55),
    "finance": colors.Color(0.13, 0.45, 0.20),
    "travel": colors.Color(0.15, 0.40, 0.70),
    "general": colors.Color(0.40, 0.40, 0.40),
}
FAVORABLE_COLOR = colors.Color(0.13, 0.45, 0.20)
CAUTION_COLOR = colors.Color(0.80, 0.55, 0.10)


def _make_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='FamilyCoverTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=colors.Color(*COLORS["primary"]),
        spaceAfter=16,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='FamilyCoverSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.Color(*COLORS["secondary"]),
        spaceAfter=8,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='FamilySectionTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.Color(*COLORS["primary"]),
        spaceBefore=20,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name='FamilyBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.Color(*COLORS["text"]),
        alignment=TA_JUSTIFY,
        spaceAfter=8,
        leading=15,
    ))
    styles.add(ParagraphStyle(
        name='FamilyMuted',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.Color(*COLORS["muted"]),
        spaceAfter=4,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='FamilyTableHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.white,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        name='FamilyTableCell',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.Color(*COLORS["text"]),
        alignment=TA_LEFT,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        name='FamilyBullet',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.Color(*COLORS["text"]),
        leftIndent=16,
        spaceAfter=5,
        leading=15,
        bulletIndent=4,
    ))
    styles.add(ParagraphStyle(
        name='FamilyItalic',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.Color(*COLORS["muted"]),
        fontName='Helvetica-Oblique',
        spaceAfter=4,
        leftIndent=8,
    ))

    return styles


def _header_table_style(header_bg: tuple) -> TableStyle:
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(*header_bg)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
            colors.Color(*COLORS["background"]), colors.white
        ]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])


def _build_cover(group_name: str, member_names: List[str], year: int, styles) -> List:
    elements = []
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph("Tamil Panchangam", styles['FamilyCoverTitle']))
    elements.append(Paragraph("Family Astrology Report", styles['FamilyCoverSubtitle']))
    elements.append(Spacer(1, 0.4 * inch))
    elements.append(Paragraph(f"<b>{group_name}</b>", styles['FamilyCoverSubtitle']))
    elements.append(Paragraph(str(year), styles['FamilyCoverSubtitle']))
    elements.append(Spacer(1, 0.4 * inch))
    if member_names:
        elements.append(Paragraph(
            "Family Members: " + " · ".join(member_names),
            styles['FamilyCoverSubtitle']
        ))
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph(
        f"Generated: {date.today().strftime('%B %d, %Y')}",
        styles['FamilyMuted']
    ))
    elements.append(Paragraph(
        "This report is for guidance and reflection purposes only. "
        "Vedic astrology describes tendencies, not certainties.",
        styles['FamilyMuted']
    ))
    elements.append(PageBreak())
    return elements


def _build_executive_summary(summary: str, styles) -> List:
    if not summary:
        return []
    elements = [
        Paragraph("Executive Summary", styles['FamilySectionTitle']),
    ]
    # Card background via table
    cell_style = ParagraphStyle(
        'SummaryCell', parent=styles['FamilyBody'],
        textColor=colors.Color(*COLORS["text"]),
        leading=16,
    )
    table = Table(
        [[Paragraph(summary, cell_style)]],
        colWidths=[440],
    )
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.Color(*COLORS["background"])),
        ('BOX', (0, 0), (0, 0), 1, colors.Color(*COLORS["accent"])),
        ('LEFTPADDING', (0, 0), (0, 0), 16),
        ('RIGHTPADDING', (0, 0), (0, 0), 16),
        ('TOPPADDING', (0, 0), (0, 0), 14),
        ('BOTTOMPADDING', (0, 0), (0, 0), 14),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))
    return elements


def _build_financial_peaks(peaks: list, styles) -> List:
    if not peaks:
        return []
    elements = [Paragraph("Financial Peaks &amp; Troughs", styles['FamilySectionTitle'])]

    header = [
        Paragraph("Period", styles['FamilyTableHeader']),
        Paragraph("Type", styles['FamilyTableHeader']),
        Paragraph("Strength", styles['FamilyTableHeader']),
        Paragraph("What it means", styles['FamilyTableHeader']),
    ]
    rows = [header]

    for peak in peaks:
        ptype = str(peak.get("type", "")).lower()
        type_color = PEAK_COLOR if ptype == "peak" else TROUGH_COLOR
        type_label = f'<font color="#{_rgb_hex(type_color)}">' \
                     f'<b>{"▲ Peak" if ptype == "peak" else "▼ Trough"}</b></font>'
        members = ", ".join(peak.get("members_involved", []))
        what = peak.get("plain_english", "")
        if peak.get("driven_by"):
            what += f"\n<i>{peak['driven_by']}</i>"
        if members:
            what += f"\nInvolves: {members}"

        rows.append([
            Paragraph(str(peak.get("period", "")), styles['FamilyTableCell']),
            Paragraph(type_label, styles['FamilyTableCell']),
            Paragraph(str(peak.get("strength", "")), styles['FamilyTableCell']),
            Paragraph(what, styles['FamilyTableCell']),
        ])

    col_widths = [110, 70, 65, 195]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(_header_table_style(COLORS["primary"]))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))
    return elements


def _build_caution_windows(windows: list, styles) -> List:
    if not windows:
        return []
    elements = [Paragraph("Shared Caution Windows", styles['FamilySectionTitle'])]

    header = [
        Paragraph("Period", styles['FamilyTableHeader']),
        Paragraph("Theme", styles['FamilyTableHeader']),
        Paragraph("Intensity", styles['FamilyTableHeader']),
        Paragraph("Guidance", styles['FamilyTableHeader']),
    ]
    rows = [header]

    for w in windows:
        theme = str(w.get("theme", "general")).lower()
        guidance = w.get("plain_english", "")
        affected = ", ".join(w.get("members_affected", []))
        if affected:
            guidance += f"\nAffects: {affected}"
        if w.get("remedy_hint"):
            guidance += f"\n<i>{w['remedy_hint']}</i>"

        rows.append([
            Paragraph(str(w.get("period", "")), styles['FamilyTableCell']),
            Paragraph(str(w.get("theme", "general")).title(), styles['FamilyTableCell']),
            Paragraph(str(w.get("intensity", "")).title(), styles['FamilyTableCell']),
            Paragraph(guidance, styles['FamilyTableCell']),
        ])

    col_widths = [110, 70, 65, 195]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(_header_table_style(COLORS["secondary"]))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))
    return elements


def _build_child_milestones(milestones: list, styles) -> List:
    if not milestones:
        return []
    elements = [Paragraph("Child Milestones", styles['FamilySectionTitle'])]

    header = [
        Paragraph("Child", styles['FamilyTableHeader']),
        Paragraph("Milestone", styles['FamilyTableHeader']),
        Paragraph("Period", styles['FamilyTableHeader']),
        Paragraph("Outlook", styles['FamilyTableHeader']),
    ]
    rows = [header]

    for m in milestones:
        fav = m.get("favorable", True)
        outlook = m.get("plain_english", "")
        indicator = "✓" if fav else "⚠"
        outlook_cell = f"{indicator} {outlook}"

        rows.append([
            Paragraph(str(m.get("child_name", "")), styles['FamilyTableCell']),
            Paragraph(str(m.get("milestone_type", "")).replace("_", " ").title(), styles['FamilyTableCell']),
            Paragraph(str(m.get("period", "")), styles['FamilyTableCell']),
            Paragraph(outlook_cell, styles['FamilyTableCell']),
        ])

    col_widths = [90, 90, 90, 170]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(_header_table_style(COLORS["accent"]))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))
    return elements


def _build_key_takeaways(takeaways: list, styles) -> List:
    if not takeaways:
        return []
    elements = [Paragraph("Key Takeaways", styles['FamilySectionTitle'])]
    bullet_paragraphs = [
        Paragraph(f"• {t}", styles['FamilyBullet'])
        for t in takeaways
    ]
    card_content = [[bp] for bp in bullet_paragraphs]
    # Wrap in a single-column table for the card background
    flat_content = [[Paragraph("", styles['FamilyBody'])]]  # dummy
    table = Table(
        [[bp] for bp in bullet_paragraphs],
        colWidths=[440],
    )
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(*COLORS["background"])),
        ('BOX', (0, 0), (0, -1), 1, colors.Color(*COLORS["accent"])),
        ('LEFTPADDING', (0, 0), (0, -1), 16),
        ('RIGHTPADDING', (0, 0), (0, -1), 16),
        ('TOPPADDING', (0, 0), (0, -1), 6),
        ('BOTTOMPADDING', (0, 0), (0, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))
    return elements


def _build_footer(styles) -> List:
    return [
        HRFlowable(width="100%", thickness=0.5, color=colors.Color(*COLORS["muted"])),
        Spacer(1, 0.1 * inch),
        Paragraph(
            "Generated by Tamil Panchangam · Vedic Jyotisha",
            styles['FamilyMuted']
        ),
    ]


def _rgb_hex(c: colors.Color) -> str:
    """Convert ReportLab Color to hex string (no leading #)."""
    r = int(c.red * 255)
    g = int(c.green * 255)
    b = int(c.blue * 255)
    return f"{r:02x}{g:02x}{b:02x}"


def render_family_pdf(
    group_name: str,
    member_names: List[str],
    year: int,
    prediction: dict,
) -> bytes:
    """
    Render the family prediction as a PDF and return raw bytes.
    Mirrors the streaming pattern of canonical pdf_renderer.py.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    styles = _make_styles()
    story = []

    story += _build_cover(group_name, member_names, year, styles)
    story += _build_executive_summary(prediction.get("executive_summary", ""), styles)
    story += _build_financial_peaks(prediction.get("financial_peaks", []), styles)
    story += _build_caution_windows(prediction.get("caution_windows", []), styles)
    story += _build_child_milestones(prediction.get("child_milestones", []), styles)
    story += _build_key_takeaways(prediction.get("key_takeaways", []), styles)
    story += _build_footer(styles)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
