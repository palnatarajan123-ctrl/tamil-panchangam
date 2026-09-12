# app/pdf/family_report/family_pdf_renderer.py
"""
Family Prediction PDF Renderer.
Uses ReportLab Platypus -- shares COLORS/MARGIN/NumberedCanvas with
canonical_report/pdf_renderer.py via app.pdf.shared_styles (extracted
2026-09-11; this file used to carry its own hand-copied, independently-
synced COLORS dict identical in value but not import, which is exactly
the kind of drift this extraction fixes). Layout code itself (styles,
table builders, section builders) is still independent -- only the
color/canvas primitives are shared so far.
"""

import io
import logging
from datetime import date
from typing import List, Optional

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

from app.pdf.shared_styles import COLORS, MARGIN, NumberedCanvas as _NumberedCanvas

logger = logging.getLogger(__name__)

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

# Porutham grade -> color (porutham_engine.py's four grades: Excellent/
# Good/Average/Poor). Reuses the colors already defined above rather
# than inventing a new palette for this one badge.
GRADE_COLORS = {
    "excellent": FAVORABLE_COLOR,
    "good": FAVORABLE_COLOR,
    "average": CAUTION_COLOR,
    "poor": TROUGH_COLOR,
}


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


def _section_header(text: str, styles) -> List:
    """Top-level heading + a colored accent rule beneath it -- same
    visual device canonical_report/pdf_renderer.py's _section_header()
    establishes for #1/#2, applied here so all three report types share
    one visual identity. This report has no subsection level to
    distinguish from (every heading here is top-level), so this isn't
    fixing an internal hierarchy problem -- it's adopting the
    cross-report convention (Phase 3, #3 pass).
    """
    return [
        Paragraph(text, styles['FamilySectionTitle']),
        HRFlowable(
            width="100%", thickness=1.2,
            color=colors.Color(*COLORS["accent"]),
            spaceBefore=0, spaceAfter=10,
        ),
    ]


def _header_table_style(header_bg) -> TableStyle:
    """header_bg: a colors.Color (not a raw tuple -- lets call sites
    pass an existing named Color constant like CAUTION_COLOR directly
    instead of needing a second, manually-matched tuple copy of it)."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
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
    elements = list(_section_header("Executive Summary", styles))
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
    elements = list(_section_header("Financial Peaks &amp; Troughs", styles))

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
    table.setStyle(_header_table_style(colors.Color(*COLORS["primary"])))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))
    return elements


def _build_caution_windows(windows: list, styles) -> List:
    if not windows:
        return []
    elements = list(_section_header("Shared Caution Windows", styles))

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
    # Caution Windows is the one table that's semantically about what to
    # watch out for, so it gets the report's actual warning color
    # (CAUTION_COLOR, already defined for exactly this but never wired
    # in anywhere) instead of a third, unrelated neutral hue -- resolves
    # the previous primary/secondary/accent three-way header-color
    # spread into a meaningful two-color scheme: neutral data vs. caution.
    table.setStyle(_header_table_style(CAUTION_COLOR))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))
    return elements


def _build_child_milestones(milestones: list, styles) -> List:
    if not milestones:
        return []
    elements = list(_section_header("Child Milestones", styles))

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
        indicator_color = FAVORABLE_COLOR if fav else CAUTION_COLOR
        outlook_cell = f'<font color="#{_rgb_hex(indicator_color)}"><b>{indicator}</b></font> {outlook}'

        rows.append([
            Paragraph(str(m.get("child_name", "")), styles['FamilyTableCell']),
            Paragraph(str(m.get("milestone_type", "")).replace("_", " ").title(), styles['FamilyTableCell']),
            Paragraph(str(m.get("period", "")), styles['FamilyTableCell']),
            Paragraph(outlook_cell, styles['FamilyTableCell']),
        ])

    col_widths = [90, 90, 90, 170]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    # Neutral header (matches Financial Peaks/Porutham) -- the accent
    # gold this used to have was one more unrelated hue in the same
    # three-way spread Caution Windows' header just resolved; per-row
    # favorable/unfavorable meaning is carried by the ✓/⚠ indicator
    # itself, not the table shell.
    table.setStyle(_header_table_style(colors.Color(*COLORS["primary"])))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))
    return elements


def _build_porutham(
    porutham: Optional[dict], husband_name: Optional[str], wife_name: Optional[str], styles,
    commentary: Optional[str] = None,
) -> List:
    """
    Dedicated Porutham (10-point Tamil Kuta compatibility) table.

    Placement decision: called right after _build_caution_windows() in
    render_family_pdf() below, NOT at end-of-document. Same subject matter
    as Shared Caution Windows -- Phase F1 already grounds the relationship-
    themed caution window narrative in this exact data, so the concrete
    numbers belong immediately next to that narrative, not detached from it.

    Jargon: this is a written-report surface (same convention as Phase F1's
    prompt), so the table uses classical category labels (Nadi, Rajju,
    Ganam, etc.) as data labels -- appropriate for a technical table, same
    distinction canonical_report/pdf_renderer.py's KP tables already draw
    between plain-language narrative prose and a labeled technical table.

    commentary (Phase H3): the LLM-generated, family-tone paragraph cached
    alongside the Porutham result since Phase H1, explaining the mechanism
    behind the grade (e.g. a mandatory-category fail overriding the raw
    percentage). Rendered between the score summary and the category
    table, same placement as the UI's PoruthamBreakdown component (Phase
    H2) so the PDF and in-app view read consistently. Older cached rows
    predating this field simply omit the paragraph -- no backfill here
    either, matching Phase H2's same call.

    Guards for no-pairing / no-result the same way every other section in
    this file guards on empty input: returns [] so nothing renders, not a
    broken or empty-looking section.
    """
    if not porutham or porutham.get("error"):
        return []
    points = porutham.get("points", [])
    if not points:
        return []

    elements = list(_section_header("Compatibility (Porutham)", styles))

    summary_style = ParagraphStyle(
        'PoruthamSummary', parent=styles['FamilyBody'],
        alignment=TA_CENTER, spaceAfter=10,
    )
    names_line = f"{husband_name or 'Husband'} &amp; {wife_name or 'Wife'}"
    grade = str(porutham.get('grade', ''))
    # Grade used to display as bare text ("— Poor") with no visual
    # treatment at all -- same category of issue as #1's bare Tara Bala
    # names, just milder since a full explanatory paragraph (commentary,
    # below) already follows it here. GRADE_COLORS reuses colors already
    # defined in this file for exactly this kind of favorable/caution
    # framing (FAVORABLE_COLOR/CAUTION_COLOR/TROUGH_COLOR).
    grade_color = GRADE_COLORS.get(grade.lower(), CAUTION_COLOR)
    score_line = (
        f"{porutham.get('total_score')}/{porutham.get('max_score')} "
        f"({porutham.get('percent')}%) — "
        f'<font color="#{_rgb_hex(grade_color)}"><b>{grade}</b></font>'
    )
    elements.append(Paragraph(f"<b>{names_line}</b><br/>{score_line}", summary_style))
    elements.append(Spacer(1, 0.1 * inch))

    if commentary:
        commentary_style = ParagraphStyle(
            'PoruthamCommentary', parent=styles['FamilyBody'],
            spaceAfter=12, leading=14,
        )
        elements.append(Paragraph(commentary, commentary_style))
        elements.append(Spacer(1, 0.1 * inch))

    header = [
        Paragraph("Category", styles['FamilyTableHeader']),
        Paragraph("Result", styles['FamilyTableHeader']),
    ]
    rows = [header]
    for p in points:
        name = str(p.get("name", ""))
        if p.get("mandatory"):
            name += " (mandatory)"
        if p.get("max", 0) > 0:
            result = f"{p.get('score', 0)}/{p.get('max', 0)}"
        else:
            result = "Pass" if p.get("pass") else "Fail"
        rows.append([
            Paragraph(name, styles['FamilyTableCell']),
            Paragraph(result, styles['FamilyTableCell']),
        ])

    table = Table(rows, colWidths=[300, 140], repeatRows=1)
    table.setStyle(_header_table_style(colors.Color(*COLORS["primary"])))
    elements.append(KeepTogether([table]))
    elements.append(Spacer(1, 0.2 * inch))
    return elements


def _build_key_takeaways(takeaways: list, styles) -> List:
    if not takeaways:
        return []
    elements = list(_section_header("Key Takeaways", styles))
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


def render_children_timing_pdf(
    group_name: str,
    year_from: int,
    year_to: int,
    data: dict,
) -> bytes:
    """Render children timing analysis as PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    styles = _make_styles()
    story = []

    # Cover
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("Tamil Panchangam", styles['FamilyCoverTitle']))
    story.append(Paragraph("Children Timing Analysis", styles['FamilyCoverSubtitle']))
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph(f"<b>{group_name}</b>", styles['FamilyCoverSubtitle']))
    story.append(Paragraph(f"{year_from} \u2013 {year_to}", styles['FamilyCoverSubtitle']))
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph(f"Generated: {date.today().strftime('%B %d, %Y')}", styles['FamilyMuted']))
    story.append(Paragraph(
        "These are favorable astrological windows based on Vedic principles. "
        "All timings are indicative \u2014 consult a qualified Jyotishi for personal guidance.",
        styles['FamilyMuted']
    ))
    story.append(PageBreak())

    # Overall Outlook
    outlook = data.get("overall_outlook", "")
    if outlook:
        story.append(Paragraph("Overall Outlook", styles['FamilySectionTitle']))
        cell_style = ParagraphStyle('OutlookCell', parent=styles['FamilyBody'], leading=16)
        t = Table([[Paragraph(outlook, cell_style)]], colWidths=[440])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.Color(*COLORS["background"])),
            ('BOX', (0, 0), (0, 0), 1, colors.Color(*COLORS["accent"])),
            ('LEFTPADDING', (0, 0), (0, 0), 16),
            ('RIGHTPADDING', (0, 0), (0, 0), 16),
            ('TOPPADDING', (0, 0), (0, 0), 14),
            ('BOTTOMPADDING', (0, 0), (0, 0), 14),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    # Jupiter Insight
    jupiter_insight = data.get("jupiter_insight", "")
    if jupiter_insight:
        story.append(Paragraph("Jupiter's Role", styles['FamilySectionTitle']))
        t = Table([[Paragraph(jupiter_insight, styles['FamilyBody'])]], colWidths=[440])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.Color(0.97, 0.95, 0.88)),
            ('BOX', (0, 0), (0, 0), 1, colors.Color(*COLORS["accent"])),
            ('LEFTPADDING', (0, 0), (0, 0), 16),
            ('RIGHTPADDING', (0, 0), (0, 0), 16),
            ('TOPPADDING', (0, 0), (0, 0), 12),
            ('BOTTOMPADDING', (0, 0), (0, 0), 12),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    # Combined Favorable Windows
    windows = data.get("combined_windows", [])
    if windows:
        story.append(Paragraph("Favorable Windows", styles['FamilySectionTitle']))
        header = [
            Paragraph("Period", styles['FamilyTableHeader']),
            Paragraph("Strength", styles['FamilyTableHeader']),
            Paragraph("Basis", styles['FamilyTableHeader']),
            Paragraph("Guidance", styles['FamilyTableHeader']),
        ]
        rows = [header]
        for w in windows:
            guidance = w.get("plain_english", "")
            if w.get("cautions"):
                guidance += f"\n<i>Note: {w['cautions']}</i>"
            rows.append([
                Paragraph(str(w.get("period", "")), styles['FamilyTableCell']),
                Paragraph(str(w.get("strength", "")).title(), styles['FamilyTableCell']),
                Paragraph(str(w.get("basis", "")), styles['FamilyItalic']),
                Paragraph(guidance, styles['FamilyTableCell']),
            ])
        t = Table(rows, colWidths=[100, 65, 120, 155], repeatRows=1)
        t.setStyle(_header_table_style(colors.Color(*COLORS["primary"])))
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    # Remedies
    remedies = data.get("remedies", [])
    if remedies:
        story.append(Paragraph("Supportive Practices", styles['FamilySectionTitle']))
        bullet_paras = [Paragraph(f"\u2022 {r}", styles['FamilyBullet']) for r in remedies]
        t = Table([[bp] for bp in bullet_paras], colWidths=[440])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(*COLORS["background"])),
            ('BOX', (0, 0), (0, -1), 1, colors.Color(*COLORS["accent"])),
            ('LEFTPADDING', (0, 0), (0, -1), 16),
            ('RIGHTPADDING', (0, 0), (0, -1), 16),
            ('TOPPADDING', (0, 0), (0, -1), 6),
            ('BOTTOMPADDING', (0, 0), (0, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    story += _build_footer(styles)
    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def render_child_prediction_pdf(
    child_name: str,
    year: int,
    data: dict,
) -> bytes:
    """Render per-child prediction as PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    styles = _make_styles()
    story = []

    # Cover
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("Tamil Panchangam", styles['FamilyCoverTitle']))
    story.append(Paragraph("Jyotisha Life Guide", styles['FamilyCoverSubtitle']))
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph(f"<b>{child_name}</b>", styles['FamilyCoverSubtitle']))
    story.append(Paragraph(str(year), styles['FamilyCoverSubtitle']))
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph(f"Generated: {date.today().strftime('%B %d, %Y')}", styles['FamilyMuted']))
    story.append(Paragraph(
        "Child predictions are based on classical Vedic Jyotisha and are indicative in nature. "
        "Marriage and life milestone timings are distant future windows \u2014 "
        "circumstances and individual choices always shape outcomes.",
        styles['FamilyMuted']
    ))
    story.append(PageBreak())

    # Overall Narrative
    narrative = data.get("overall_narrative", "")
    if narrative:
        story.append(Paragraph("Astrological Profile", styles['FamilySectionTitle']))
        t = Table([[Paragraph(narrative, styles['FamilyBody'])]], colWidths=[440])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.Color(*COLORS["background"])),
            ('BOX', (0, 0), (0, 0), 1, colors.Color(*COLORS["accent"])),
            ('LEFTPADDING', (0, 0), (0, 0), 16),
            ('RIGHTPADDING', (0, 0), (0, 0), 16),
            ('TOPPADDING', (0, 0), (0, 0), 14),
            ('BOTTOMPADDING', (0, 0), (0, 0), 14),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    # Education Timeline
    education = data.get("education", [])
    if education:
        story.append(Paragraph("Education Timeline", styles['FamilySectionTitle']))
        header = [
            Paragraph("Period", styles['FamilyTableHeader']),
            Paragraph("Type", styles['FamilyTableHeader']),
            Paragraph("Strength", styles['FamilyTableHeader']),
            Paragraph("Guidance", styles['FamilyTableHeader']),
        ]
        rows = [header]
        for e in education:
            rows.append([
                Paragraph(str(e.get("period", "")), styles['FamilyTableCell']),
                Paragraph(str(e.get("type", "")).title(), styles['FamilyTableCell']),
                Paragraph(str(e.get("subject_strength", "")).replace("_", " ").title(), styles['FamilyTableCell']),
                Paragraph(str(e.get("plain_english", "")), styles['FamilyTableCell']),
            ])
        t = Table(rows, colWidths=[110, 65, 80, 185], repeatRows=1)
        t.setStyle(_header_table_style(colors.Color(*COLORS["primary"])))
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    # Career Aptitude
    career = data.get("career_aptitude", {})
    if career:
        story.append(Paragraph("Career Aptitude", styles['FamilySectionTitle']))
        fields = ", ".join(career.get("favorable_fields", []))
        peak = career.get("peak_period", "")
        text = career.get("plain_english", "")
        if fields:
            text = f"<b>Favorable fields:</b> {fields}\n\n" + text
        if peak:
            text += f"\n\n<b>Peak foundation period:</b> {peak}"
        t = Table([[Paragraph(text, styles['FamilyBody'])]], colWidths=[440])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.Color(*COLORS["background"])),
            ('BOX', (0, 0), (0, 0), 1, colors.Color(*COLORS["secondary"])),
            ('LEFTPADDING', (0, 0), (0, 0), 16),
            ('RIGHTPADDING', (0, 0), (0, 0), 16),
            ('TOPPADDING', (0, 0), (0, 0), 12),
            ('BOTTOMPADDING', (0, 0), (0, 0), 12),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    # Life Milestones (Marriage Window + Leaving Home)
    mw = data.get("marriage_window", {})
    lh = data.get("leaving_home", {})
    if mw or lh:
        story.append(Paragraph("Life Milestones", styles['FamilySectionTitle']))
        if mw:
            mw_text = f"<b>Marriage Window</b> (indicative, distant future)\n{mw.get('plain_english', '')}"
            if mw.get("peak_window"):
                mw_text += f"\nFavorable window: {mw['peak_window']}"
            story.append(Paragraph(mw_text, styles['FamilyBody']))
        if lh:
            lh_text = f"<b>Leaving Home</b> ({str(lh.get('context', '')).title()})\n{lh.get('plain_english', '')}"
            if lh.get("window"):
                lh_text += f"\nWindow: {lh['window']}"
            story.append(Paragraph(lh_text, styles['FamilyBody']))
        story.append(Spacer(1, 0.1 * inch))

    # Health Cautions
    health = data.get("health_cautions", [])
    if health:
        story.append(Paragraph("Health Awareness", styles['FamilySectionTitle']))
        for h in health:
            story.append(Paragraph(
                f"<b>{h.get('period', '')}</b> \u2014 {h.get('area', '')}",
                styles['FamilyBullet']
            ))
            story.append(Paragraph(h.get("plain_english", ""), styles['FamilyItalic']))
        story.append(Spacer(1, 0.1 * inch))

    # Key Takeaways
    takeaways = data.get("key_takeaways", [])
    if takeaways:
        story += _build_key_takeaways(takeaways, styles)

    story += _build_footer(styles)
    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def render_family_pdf(
    group_name: str,
    member_names: List[str],
    year: int,
    prediction: dict,
    porutham: Optional[dict] = None,
    husband_name: Optional[str] = None,
    wife_name: Optional[str] = None,
    porutham_commentary: Optional[str] = None,
) -> bytes:
    """
    Render the family prediction as a PDF and return raw bytes.
    Mirrors the streaming pattern of canonical pdf_renderer.py.

    porutham/husband_name/wife_name: optional, only present when the group
    has a resolvable husband+wife pairing (see get_family_predictions_pdf()
    in app/api/family.py, which fetches it via the shared
    _get_or_compute_full_family_porutham() rather than a new lookup). None
    for a single-member or no-pairing group -- _build_porutham() below then
    correctly renders nothing rather than a broken/empty section.

    porutham_commentary (Phase H3): the cached family-tone commentary
    paragraph from the same lookup, threaded through separately since it
    lives alongside (not inside) the porutham dict in the cache shape.
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
    # Placement: immediately after Shared Caution Windows, not end-of-
    # document -- same subject matter (couple relationship dynamics) as
    # the caution-window narrative Phase F1 already grounds in this data.
    story += _build_porutham(porutham, husband_name, wife_name, styles, porutham_commentary)
    story += _build_child_milestones(prediction.get("child_milestones", []), styles)
    story += _build_key_takeaways(prediction.get("key_takeaways", []), styles)
    story += _build_footer(styles)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
