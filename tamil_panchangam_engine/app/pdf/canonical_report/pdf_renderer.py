"""
Canonical PDF Report Builder - PDF Renderer

Uses ReportLab Platypus for structured, template-like PDF generation.
Builds PDF from story elements (similar to HTML blocks).
"""

import io
import logging
import re
from typing import List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
    KeepTogether,
    HRFlowable,
)
from reportlab.graphics.shapes import Drawing, Rect
import base64

from .models import CanonicalReportData
from .config import COLORS, MARGIN
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    from svglib.svglib import svg2rlg
    HAS_SVGLIB = True
except ImportError:
    HAS_SVGLIB = False
    logger.warning(
        "svglib not installed — SVG charts will not render in PDF exports. "
        "Run: pip install svglib==1.4.1"
    )


def _create_styles():
    """Create custom paragraph styles."""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='CoverTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=colors.Color(*COLORS["primary"]),
        spaceAfter=20,
        alignment=TA_CENTER,
    ))
    
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.Color(*COLORS["secondary"]),
        alignment=TA_CENTER,
        spaceAfter=10,
    ))
    
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.Color(*COLORS["primary"]),
        spaceBefore=20,
        spaceAfter=12,
        borderPadding=5,
    ))
    
    styles.add(ParagraphStyle(
        name='SubsectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.Color(*COLORS["secondary"]),
        spaceBefore=15,
        spaceAfter=8,
    ))
    
    # Override existing BodyText style with custom settings
    styles['BodyText'].fontSize = 11
    styles['BodyText'].textColor = colors.Color(*COLORS["text"])
    styles['BodyText'].alignment = TA_JUSTIFY
    styles['BodyText'].spaceAfter = 8
    styles['BodyText'].leading = 14
    
    styles.add(ParagraphStyle(
        name='MutedText',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.Color(*COLORS["muted"]),
        alignment=TA_CENTER,
        spaceAfter=5,
    ))
    
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    ))
    
    styles.add(ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.Color(*COLORS["text"]),
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='LifeAreaTitle',
        parent=styles['Normal'],
        fontSize=13,
        fontName='Helvetica-Bold',
        textColor=colors.Color(*COLORS["secondary"]),
        spaceBefore=4,
        spaceAfter=4,
    ))

    return styles


def _split_sentences(text: str, per_group: int = 2) -> list:
    """Split text into groups of N sentences for paragraph-level readability."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\u2018\u201c])', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [text]
    groups = []
    for i in range(0, len(sentences), per_group):
        groups.append(' '.join(sentences[i:i + per_group]))
    return groups


def _build_cover_page(data: CanonicalReportData, styles) -> List:
    """Build cover page elements."""
    elements = []
    
    elements.append(Spacer(1, 2*inch))
    
    elements.append(Paragraph(
        "Tamil Panchangam",
        styles['CoverTitle']
    ))
    
    elements.append(Paragraph(
        f"{data.report_type} Astrology Report",
        styles['CoverSubtitle']
    ))
    
    elements.append(Spacer(1, 0.5*inch))
    
    elements.append(Paragraph(
        data.period_label,
        styles['CoverSubtitle']
    ))
    
    elements.append(Spacer(1, inch))
    
    birth_info = [
        f"<b>{data.birth_details.name}</b>",
        f"Born: {data.birth_details.date} at {data.birth_details.time}",
        f"Place: {data.birth_details.place}",
    ]
    
    for line in birth_info:
        elements.append(Paragraph(line, styles['CoverSubtitle']))
    
    elements.append(Spacer(1, 2*inch))
    
    elements.append(Paragraph(
        f"Generated: {data.generated_at.strftime('%B %d, %Y')}",
        styles['MutedText']
    ))
    
    elements.append(Spacer(1, 0.3*inch))
    
    elements.append(Paragraph(
        "This report is for guidance and reflection purposes only. "
        "Astrology provides a lens for self-awareness, not deterministic predictions. "
        "Your choices and actions shape your path.",
        styles['MutedText']
    ))
    
    elements.append(PageBreak())
    
    return elements


def _build_how_to_read(styles) -> List:
    """Build 'How to Read This Report' section."""
    elements = []
    
    elements.append(Paragraph("How to Read This Report", styles['SectionTitle']))
    
    elements.append(Paragraph(
        "This report combines two types of information:",
        styles['BodyText']
    ))
    
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph(
        "<b>Deterministic Calculations</b>",
        styles['SubsectionTitle']
    ))
    
    elements.append(Paragraph(
        "The planetary positions, dasha periods, and transit data are calculated using "
        "precise astronomical algorithms (Drik Ganita) with the Lahiri Ayanamsa. "
        "These are objective astronomical facts about celestial positions at specific times.",
        styles['BodyText']
    ))
    
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph(
        "<b>Interpretive Guidance</b>",
        styles['SubsectionTitle']
    ))
    
    elements.append(Paragraph(
        "The interpretations and guidance are derived from classical Tamil astrology texts "
        "and traditions. They offer perspectives for reflection, not certainties. "
        "Use them as prompts for self-inquiry and conscious decision-making.",
        styles['BodyText']
    ))
    
    elements.append(Spacer(1, 0.3*inch))
    
    elements.append(Paragraph(
        "<i>Remember: You are not bound by the stars. Awareness is the first step to freedom.</i>",
        styles['BodyText']
    ))
    
    elements.append(PageBreak())
    
    return elements


def _render_chart_from_svg(svg_data_uri: str, chart_type: str):
    """Convert existing SVG data URI to ReportLab Drawing."""
    if HAS_SVGLIB and svg_data_uri and svg_data_uri.startswith("data:image/svg+xml;base64,"):
        try:
            svg_b64 = svg_data_uri.split(",", 1)[1]
            svg_bytes = base64.b64decode(svg_b64)
            drawing = svg2rlg(BytesIO(svg_bytes))
            if drawing:
                target_size = 300
                scale = target_size / max(drawing.width, drawing.height)
                drawing.width = drawing.width * scale
                drawing.height = drawing.height * scale
                drawing.scale(scale, scale)
                return drawing
        except Exception:
            pass
    
    placeholder_table = Table(
        [[f"{chart_type} Chart\n(View in app)"]],
        colWidths=[2*inch],
        rowHeights=[1.5*inch]
    )
    placeholder_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('BOX', (0, 0), (-1, -1), 1, colors.Color(*COLORS["muted"])),
    ]))
    return placeholder_table


def _build_natal_snapshot(data: CanonicalReportData, styles) -> List:
    """Build natal snapshot section with charts and birth reference."""
    elements = []
    
    elements.append(Paragraph("Natal Snapshot", styles['SectionTitle']))
    
    elements.append(Paragraph(
        "Your birth chart captures the celestial arrangement at your moment of birth. "
        "The Rasi (D1) chart shows planetary positions in zodiac signs, while the "
        "Navamsa (D9) chart reveals deeper soul-level patterns.",
        styles['BodyText']
    ))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Birth Chart (D1) with heading — keep heading and chart on same page
    d1_elements = []
    d1_elements.append(Paragraph("<b>Birth Chart (D1)</b>", styles['SubsectionTitle']))
    d1_elements.append(_render_chart_from_svg(data.chart_images.d1_rasi, "D1"))
    d1_elements.append(Spacer(1, 0.2*inch))
    elements.append(KeepTogether(d1_elements))

    # Navamsa (D9) with heading — keep heading and chart on same page
    d9_elements = []
    d9_elements.append(Paragraph("<b>Navamsa (D9)</b>", styles['SubsectionTitle']))
    d9_elements.append(_render_chart_from_svg(data.chart_images.d9_navamsa, "D9"))
    d9_elements.append(Spacer(1, 0.3*inch))
    elements.append(KeepTogether(d9_elements))
    
    elements.append(Paragraph("Birth Reference", styles['SubsectionTitle']))
    
    ref = data.birth_reference
    birth_table_data = [
        ["Attribute", "Value"],
        ["Janma Nakshatra", ref.janma_nakshatra],
        ["Janma Rasi", ref.janma_rasi],
        ["Lagna (Ascendant)", ref.lagna],
        ["Moon Sign", ref.moon_sign],
        ["Nakshatra Lord", ref.nakshatra_lord],
        ["Birth Dasha", ref.birth_dasha],
    ]
    
    for role, planet in ref.functional_role_planets.items():
        if planet:
            birth_table_data.append([role.title(), planet])
    
    table = Table(birth_table_data, colWidths=[2.5*inch, 3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(*COLORS["primary"])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(*COLORS["muted"])),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    elements.append(table)
    elements.append(PageBreak())
    
    return elements


def _build_astrological_context(data: CanonicalReportData, styles) -> List:
    """Build astrological context section with dasha, transit, and timing tables."""
    elements = []
    
    elements.append(Paragraph("Astrological Context", styles['SectionTitle']))
    
    elements.append(Paragraph(
        f"Current planetary influences for {data.period_label}:",
        styles['BodyText']
    ))
    
    # Use KeepTogether to prevent heading/table separation
    dasha_elements = []
    dasha_elements.append(Paragraph("Active Dasha Period", styles['SubsectionTitle']))
    
    dasha = data.dasha_context
    dasha_table = [
        ["Attribute", "Value"],
        ["Current Mahadasha", dasha.mahadasha],
        ["Current Antardasha", dasha.antardasha],
        ["Dasha Balance", dasha.dasha_balance],
    ]
    
    if dasha.functional_benefics:
        dasha_table.append(["Functional Benefics", ", ".join(dasha.functional_benefics)])
    if dasha.functional_malefics:
        dasha_table.append(["Functional Malefics", ", ".join(dasha.functional_malefics)])
    
    table = Table(dasha_table, colWidths=[2*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(*COLORS["primary"])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(*COLORS["muted"])),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    dasha_elements.append(table)
    elements.append(KeepTogether(dasha_elements))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Use KeepTogether to prevent heading/table separation
    transit_elements = []
    transit_elements.append(Paragraph("Current Transits (Gochara)", styles['SubsectionTitle']))
    
    transit = data.transit_context
    transit_table = [
        ["Transit", "Position"],
        ["Jupiter", transit.jupiter_transit],
        ["Saturn", transit.saturn_transit],
        ["Rahu-Ketu Axis", transit.rahu_ketu_axis],
    ]
    
    table = Table(transit_table, colWidths=[2*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(*COLORS["primary"])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(*COLORS["muted"])),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    transit_elements.append(table)
    elements.append(KeepTogether(transit_elements))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Use KeepTogether to prevent heading/table separation
    timing_elements = []
    timing_elements.append(Paragraph("Nakshatra & Timing", styles['SubsectionTitle']))
    
    timing = data.nakshatra_timing
    timing_table = [
        ["Aspect", "Current Value"],
        ["Moon Nakshatra", timing.current_moon_nakshatra],
        ["Tara Bala", timing.tara_bala],
        ["Chandra Gati", timing.chandra_gati],
        ["Favorable Window", timing.favorable_window],
    ]
    
    table = Table(timing_table, colWidths=[2*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(*COLORS["primary"])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(*COLORS["muted"])),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    timing_elements.append(table)
    elements.append(KeepTogether(timing_elements))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Use KeepTogether to prevent heading/table separation
    pakshi_elements = []
    pakshi_elements.append(Paragraph("Pakshi / Rhythm Context", styles['SubsectionTitle']))
    
    pakshi = data.pakshi_rhythm
    pakshi_table = [
        ["Aspect", "Current Value"],
        ["Dominant Pakshi", pakshi.dominant_pakshi],
        ["Activity Phase", pakshi.activity_phase],
    ]
    
    table = Table(pakshi_table, colWidths=[2*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(*COLORS["primary"])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(*COLORS["muted"])),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    pakshi_elements.append(table)
    elements.append(KeepTogether(pakshi_elements))
    
    elements.append(PageBreak())
    
    return elements


def _score_to_label(score: int) -> str:
    """Convert score to human-readable label."""
    if score >= 75:
        return "Strong Support"
    elif score >= 65:
        return "Favorable"
    elif score >= 55:
        return "Mildly Supportive"
    elif score >= 45:
        return "Neutral"
    elif score >= 35:
        return "Watchful"
    else:
        return "Challenging"


def _score_to_color(score: int):
    """Convert score to color for visual indicator."""
    if score >= 65:
        return colors.Color(0.2, 0.6, 0.3)
    elif score >= 45:
        return colors.Color(0.6, 0.5, 0.2)
    else:
        return colors.Color(0.7, 0.3, 0.3)


def _build_predictions(data: CanonicalReportData, styles) -> List:
    """Build predictions section with full details and scores."""
    elements = []
    
    elements.append(Paragraph("Predictions", styles['SectionTitle']))
    
    if data.is_v3 and data.yearly_mantra:
        elements.append(Paragraph("Guiding Theme", styles['SubsectionTitle']))
        for j, grp in enumerate(_split_sentences(data.yearly_mantra)):
            elements.append(Paragraph(f"<b>{grp}</b>" if j == 0 else grp, styles['BodyText']))
        elements.append(Spacer(1, 0.3*inch))

    if data.is_v3 and data.dasha_transit_synthesis:
        elements.append(Paragraph("Dasha-Transit Synthesis", styles['SubsectionTitle']))
        for j, grp in enumerate(_split_sentences(data.dasha_transit_synthesis)):
            elements.append(Paragraph(f"<b>{grp}</b>" if j == 0 else grp, styles['BodyText']))
        elements.append(Spacer(1, 0.3*inch))
    elif data.is_v2 and data.monthly_theme:
        elements.append(Paragraph(
            f"<b>{data.monthly_theme.title}</b>",
            styles['SubsectionTitle']
        ))
        for j, grp in enumerate(_split_sentences(data.monthly_theme.narrative)):
            elements.append(Paragraph(f"<b>{grp}</b>" if j == 0 else grp, styles['BodyText']))
        elements.append(Spacer(1, 0.3*inch))

    if not data.is_v3 and data.is_v2 and data.overview_v2:
        elements.append(Paragraph("Energy & Focus", styles['SubsectionTitle']))
        for j, grp in enumerate(_split_sentences(data.overview_v2.energy_pattern)):
            elements.append(Paragraph(f"<b>{grp}</b>" if j == 0 else grp, styles['BodyText']))
        
        if data.overview_v2.key_focus:
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph("<b>Key Focus Areas:</b>", styles['BodyText']))
            for focus in data.overview_v2.key_focus:
                elements.append(Paragraph(f"• {focus}", styles['BodyText']))
        
        if data.overview_v2.avoid_or_be_mindful:
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph("<b>Be Mindful Of:</b>", styles['BodyText']))
            for item in data.overview_v2.avoid_or_be_mindful:
                elements.append(Paragraph(f"• {item}", styles['BodyText']))
        
        elements.append(Spacer(1, 0.3*inch))
    elif not data.is_v3 and data.prediction_overview:
        elements.append(Paragraph("Overview", styles['SubsectionTitle']))
        for j, grp in enumerate(_split_sentences(data.prediction_overview)):
            elements.append(Paragraph(f"<b>{grp}</b>" if j == 0 else grp, styles['BodyText']))
        elements.append(Spacer(1, 0.3*inch))
    
    # Prediction Confidence - shown once after summary, before life areas
    if data.methodology and data.methodology.calculation_confidence:
        conf_level = data.methodology.calculation_confidence
        conf_text = "Prediction Confidence: "
        
        if conf_level.lower() == "high":
            conf_text += "High - All planetary positions are clearly within sign boundaries."
        elif conf_level.lower() == "medium":
            conf_text += "Medium - Some influences fall near transitional boundaries. Interpret trends as ranges rather than absolutes."
        else:
            conf_text += "Sensitive - Some influences fall near transitional boundaries. Interpret trends as ranges rather than absolutes."
        
        elements.append(Paragraph(
            f"<font color='gray'><i>{conf_text}</i></font>",
            styles['BodyText']
        ))
        elements.append(Spacer(1, 0.2*inch))
    
    # Aggregated Astrological Attribution - shown once in prediction section header
    all_planets = set()
    all_engines = set()
    dasha_str = None
    for area in data.prediction_areas:
        if area.attribution:
            for p in area.attribution.planets:
                all_planets.add(p)
            for e in area.attribution.engines:
                all_engines.add(e)
            if area.attribution.dasha and area.attribution.dasha != "X":
                dasha_str = area.attribution.dasha
    
    if all_planets or all_engines or dasha_str:
        attr_parts = []
        if dasha_str:
            attr_parts.append(f"Dasha: {dasha_str}")
        if all_planets:
            attr_parts.append(f"Planets: {', '.join(sorted(all_planets))}")
        if all_engines:
            attr_parts.append(f"Engines: {', '.join(sorted(all_engines))}")
        
        elements.append(Paragraph(
            f"<font size='9' color='gray'>ASTROLOGICAL INFLUENCES</font>",
            styles['BodyText']
        ))
        elements.append(Paragraph(
            f"<font size='8' color='gray'>{' | '.join(attr_parts)}</font>",
            styles['BodyText']
        ))
        elements.append(Spacer(1, 0.2*inch))
    
    scores_data = [["Life Area", "Score", "Outlook"]]
    for area in data.prediction_areas:
        scores_data.append([
            area.area,
            f"{area.score}/100 ({_score_to_label(area.score)})",
            area.outlook.title()
        ])
    
    scores_table = Table(scores_data, colWidths=[2*inch, 2.2*inch, 1.5*inch])
    scores_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(*COLORS["primary"])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(*COLORS["muted"])),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(scores_table)
    elements.append(Spacer(1, 0.3*inch))
    
    elements.append(Paragraph("Detailed Insights", styles['SubsectionTitle']))
    elements.append(Spacer(1, 0.15*inch))

    for i, area in enumerate(data.prediction_areas):
        # Divider between sections (skip before the first)
        if i > 0:
            elements.append(HRFlowable(
                width="100%", thickness=0.5,
                color=colors.Color(0.82, 0.82, 0.82),
                spaceBefore=6, spaceAfter=10,
            ))

        area_elements = []

        # Heading: "Career - 65/100 | Favorable"
        heading = f"{area.area} - {area.score}/100  |  {_score_to_label(area.score)}"
        area_elements.append(Paragraph(heading, styles['LifeAreaTitle']))

        # Interpretation split into 2-sentence paragraph groups
        if area.interpretation:
            groups = _split_sentences(area.interpretation, per_group=2)
            for j, group in enumerate(groups):
                if j == 0:
                    # Bold the first sentence group as a visual lead-in
                    area_elements.append(Paragraph(f"<b>{group}</b>", styles['BodyText']))
                else:
                    area_elements.append(Paragraph(group, styles['BodyText']))

        if area.deeper_explanation and not data.is_v2 and not data.is_v3:
            area_elements.append(Paragraph(
                f"<i>{area.deeper_explanation}</i>",
                styles['BodyText']
            ))

        if area.guidance:
            area_elements.append(Paragraph(
                f"<b>Guidance:</b> {area.guidance}",
                styles['BodyText']
            ))

        if area.attribution and area.attribution.signals:
            area_elements.append(Spacer(1, 0.1*inch))
            area_elements.append(Paragraph("<b>Signals</b>", styles['BodyText']))
            for sig in area.attribution.signals:
                sign = "+" if sig.direction == "pos" else "-"
                sig_line = f"{sig.engine}  {sign}{abs(sig.weight):.2f}"
                area_elements.append(Paragraph(sig_line, styles['BodyText']))
                if sig.interpretive_hint:
                    area_elements.append(Paragraph(
                        f"<i>{sig.interpretive_hint}</i>",
                        styles['BodyText']
                    ))

        area_elements.append(Spacer(1, 0.25*inch))
        elements.append(KeepTogether(area_elements))
    
    elements.append(PageBreak())
    
    return elements


def _build_practices_reflection(data: CanonicalReportData, styles) -> List:
    """Build practices section."""
    elements = []
    
    if data.is_v3 and data.veda_remedy:
        elements.append(Paragraph("Veda Pariharam (Remedies)", styles['SectionTitle']))
        
        if data.veda_remedy.primary_remedy:
            elements.append(Paragraph(
                f"<b>Primary Remedy:</b> {data.veda_remedy.primary_remedy}", 
                styles['BodyText']
            ))
        
        if data.veda_remedy.supporting_practice:
            elements.append(Spacer(1, 0.15*inch))
            elements.append(Paragraph(
                f"<b>Supporting Practice:</b> {data.veda_remedy.supporting_practice}", 
                styles['BodyText']
            ))
        
        if data.veda_remedy.specific_remedies:
            elements.append(Spacer(1, 0.15*inch))
            elements.append(Paragraph("<b>Additional Remedies:</b>", styles['BodyText']))
            for remedy in data.veda_remedy.specific_remedies:
                elements.append(Paragraph(f"• {remedy}", styles['BodyText']))
        
        if data.danger_windows:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Mindfulness Windows:</b>", styles['BodyText']))
            for window in data.danger_windows:
                elements.append(Paragraph(f"• {window}", styles['BodyText']))
        
        elements.append(Spacer(1, 0.3*inch))
    elif data.is_v2 and data.practices_v2:
        elements.append(Paragraph("Practices & Reflection", styles['SectionTitle']))
        
        if data.practices_v2.daily_practice:
            elements.append(Paragraph(
                f"<b>Daily Practice:</b> {data.practices_v2.daily_practice}", 
                styles['BodyText']
            ))
        
        if data.practices_v2.weekly_practice:
            elements.append(Paragraph(
                f"<b>Weekly Practice:</b> {data.practices_v2.weekly_practice}", 
                styles['BodyText']
            ))
        
        if data.practices_v2.reflection_guidance:
            elements.append(Spacer(1, 0.15*inch))
            elements.append(Paragraph("<b>Reflection & Guidance:</b>", styles['BodyText']))
            for j, grp in enumerate(_split_sentences(data.practices_v2.reflection_guidance)):
                elements.append(Paragraph(f"<b>{grp}</b>" if j == 0 else grp, styles['BodyText']))
        
        elements.append(Spacer(1, 0.3*inch))
    elif data.practices:
        elements.append(Paragraph("Suggested Practices", styles['SectionTitle']))
        for practice in data.practices:
            elements.append(Paragraph(f"• {practice}", styles['BodyText']))
        elements.append(Spacer(1, 0.3*inch))
    
    return elements


def _build_closing(data: CanonicalReportData, styles) -> List:
    """Build closing section."""
    elements = []

    elements.append(PageBreak())

    if data.is_v3 and data.closing_v3:
        elements.append(Paragraph("Key Takeaways", styles['SectionTitle']))
        
        if data.closing_v3.key_takeaways:
            for takeaway in data.closing_v3.key_takeaways:
                elements.append(Paragraph(f"• {takeaway}", styles['BodyText']))
            elements.append(Spacer(1, 0.2*inch))
        
        if data.closing_v3.encouragement:
            for j, grp in enumerate(_split_sentences(data.closing_v3.encouragement)):
                elements.append(Paragraph(f"<i>{grp}</i>", styles['BodyText']))
    elif data.is_v2 and data.closing_v2:
        elements.append(Paragraph("Key Takeaways", styles['SectionTitle']))

        if data.closing_v2.key_takeaways:
            for takeaway in data.closing_v2.key_takeaways:
                elements.append(Paragraph(f"• {takeaway}", styles['BodyText']))
            elements.append(Spacer(1, 0.2*inch))

        if data.closing_v2.encouragement:
            for j, grp in enumerate(_split_sentences(data.closing_v2.encouragement)):
                elements.append(Paragraph(f"<i>{grp}</i>", styles['BodyText']))
    else:
        elements.append(Paragraph("Closing Note", styles['SectionTitle']))

        for j, grp in enumerate(_split_sentences(data.closing_note)):
            elements.append(Paragraph(f"<b>{grp}</b>" if j == 0 else grp, styles['BodyText']))
        
        if data.closing_affirmation:
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph(
                f"<i>\"{data.closing_affirmation}\"</i>",
                styles['BodyText']
            ))
    
    elements.append(Spacer(1, 0.5*inch))
    
    if data.llm_enhanced:
        elements.append(Paragraph(
            "This report includes AI-enhanced interpretations based on classical Tamil astrology principles.",
            styles['MutedText']
        ))
    
    elements.append(Paragraph(
        "Generated by Tamil Panchangam Astrology Engine",
        styles['MutedText']
    ))
    
    return elements


def _build_divisional_charts(data: CanonicalReportData, styles) -> List:
    """Build Tier-1 divisional charts section."""
    elements = []
    
    has_d2 = bool(data.chart_images.d2_hora)
    has_d7 = bool(data.chart_images.d7_saptamsa)
    has_d10 = bool(data.chart_images.d10_dasamsa)
    
    if not (has_d2 or has_d7 or has_d10):
        return elements
    
    elements.append(Paragraph("Tier-1 Divisional Charts", styles['SectionTitle']))
    
    elements.append(Paragraph(
        "Divisional charts (Vargas) refine the birth chart analysis by examining "
        "specific life areas. These follow the Classical Parashara method with "
        "arc-second precision for accurate planet placement.",
        styles['BodyText']
    ))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Dasamsa (D10) - Career
    if has_d10:
        d10_elements = []
        d10_elements.append(Paragraph("<b>Dasamsa (D10)</b> - Career & Authority", styles['SubsectionTitle']))
        d10_elements.append(Paragraph(
            "The Dasamsa divides each sign into 10 parts, revealing career potential, "
            "professional achievements, and societal status. Strong placements here "
            "indicate success in one's profession and public recognition.",
            styles['BodyText']
        ))
        d10_elements.append(Spacer(1, 0.1*inch))
        d10_elements.append(_render_chart_from_svg(data.chart_images.d10_dasamsa, "D10"))
        d10_elements.append(Spacer(1, 0.3*inch))
        elements.append(KeepTogether(d10_elements))
    
    # Hora (D2) - Wealth
    if has_d2:
        d2_elements = []
        d2_elements.append(Paragraph("<b>Hora (D2)</b> - Wealth & Sustenance", styles['SubsectionTitle']))
        d2_elements.append(Paragraph(
            "The Hora chart divides each sign into 2 parts (Sun and Moon horas), "
            "indicating wealth accumulation capacity and financial sustenance. "
            "Planets in Sun hora suggest self-earned wealth; Moon hora suggests inherited or accumulated wealth.",
            styles['BodyText']
        ))
        d2_elements.append(Spacer(1, 0.1*inch))
        d2_elements.append(_render_chart_from_svg(data.chart_images.d2_hora, "D2"))
        d2_elements.append(Spacer(1, 0.3*inch))
        elements.append(KeepTogether(d2_elements))
    
    # Saptamsa (D7) - Creativity & Children
    if has_d7:
        d7_elements = []
        d7_elements.append(Paragraph("<b>Saptamsa (D7)</b> - Creativity & Children", styles['SubsectionTitle']))
        d7_elements.append(Paragraph(
            "The Saptamsa divides each sign into 7 parts, showing creative potential, "
            "progeny matters, and artistic abilities. This chart is particularly "
            "important for understanding one's relationship with children and creative pursuits.",
            styles['BodyText']
        ))
        d7_elements.append(Spacer(1, 0.1*inch))
        d7_elements.append(_render_chart_from_svg(data.chart_images.d7_saptamsa, "D7"))
        d7_elements.append(Spacer(1, 0.3*inch))
        elements.append(KeepTogether(d7_elements))
    
    elements.append(PageBreak())
    
    return elements


def _build_methodology_appendix(data: CanonicalReportData, styles) -> List:
    """Build methodology appendix section."""
    elements = []

    elements.append(PageBreak())

    if not data.methodology:
        return elements
    
    elements.append(Paragraph("Appendix: Methodology", styles['SectionTitle']))
    
    elements.append(Paragraph(
        "This section documents the calculation standards and methodology used in this report.",
        styles['BodyText']
    ))
    
    elements.append(Spacer(1, 0.2*inch))
    
    method = data.methodology
    calc_confidence = getattr(method, 'calculation_confidence', 'high')
    method_table = [
        ["Standard", "Value"],
        ["Ephemeris Source", method.ephemeris_source],
        ["Ayanamsa", method.ayanamsa],
        ["Node Calculation", method.node_type],
        ["Division Method", method.division_method],
        ["Calculation Confidence", calc_confidence.title() if calc_confidence else "High"],
    ]
    
    table = Table(method_table, colWidths=[2.5*inch, 3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(*COLORS["primary"])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(*COLORS["muted"])),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    
    elements.append(Spacer(1, 0.3*inch))
    
    elements.append(Paragraph("Cusp Sensitivity Note", styles['SubsectionTitle']))
    
    elements.append(Paragraph(
        "For fast-moving celestial bodies (Moon, Mercury, Venus, Ascendant), placements very "
        "close to sign or divisional boundaries may vary slightly across different software or "
        "traditions due to minor differences in ayanamsa calculation, rounding approaches, or "
        "birth time precision limitations.",
        styles['BodyText']
    ))
    
    cusp_cases = getattr(method, 'cusp_cases', [])
    if cusp_cases:
        elements.append(Spacer(1, 0.15*inch))
        elements.append(Paragraph(
            "<b>Detected Cusp Placements:</b>",
            styles['BodyText']
        ))
        for case in cusp_cases:
            elements.append(Paragraph(f"• {case}", styles['BodyText']))
    
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph(
        "This system uses arc-second precision and deterministic boundary rules. No automatic "
        "adjustments are made, and degrees are not rounded before computing divisions.",
        styles['BodyText']
    ))
    
    elements.append(Spacer(1, 0.3*inch))
    
    elements.append(Paragraph("Reproducibility Guarantee", styles['SubsectionTitle']))
    
    elements.append(Paragraph(
        "Given identical inputs (date of birth, time of birth, geographic coordinates, "
        "and node type selection), this system will produce identical outputs on any date, "
        "on any device, indefinitely.",
        styles['BodyText']
    ))
    
    return elements


def render_pdf(data: CanonicalReportData) -> bytes:
    """
    Render complete PDF from report data.
    
    Returns PDF as bytes.
    """
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    
    styles = _create_styles()
    
    story = []
    
    story.extend(_build_cover_page(data, styles))
    story.extend(_build_how_to_read(styles))
    story.extend(_build_natal_snapshot(data, styles))
    story.extend(_build_divisional_charts(data, styles))
    story.extend(_build_astrological_context(data, styles))
    story.extend(_build_predictions(data, styles))
    story.extend(_build_practices_reflection(data, styles))
    story.extend(_build_closing(data, styles))
    story.extend(_build_methodology_appendix(data, styles))
    
    doc.build(story)
    
    buffer.seek(0)
    return buffer.read()
