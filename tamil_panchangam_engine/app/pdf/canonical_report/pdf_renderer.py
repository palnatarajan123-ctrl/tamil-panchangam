"""
Canonical PDF Report Builder - PDF Renderer

Uses ReportLab Platypus for structured, template-like PDF generation.
Builds PDF from story elements (similar to HTML blocks).
"""

import io
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
)
from reportlab.graphics.shapes import Drawing, Rect
import base64

from .models import CanonicalReportData
from .config import COLORS, MARGIN
from io import BytesIO

try:
    from svglib.svglib import svg2rlg
    HAS_SVGLIB = True
except ImportError:
    HAS_SVGLIB = False


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
    
    return styles


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
                scale = 180 / max(drawing.width, drawing.height)
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
    
    d1_chart = _render_chart_from_svg(data.chart_images.d1_rasi, "D1")
    d9_chart = _render_chart_from_svg(data.chart_images.d9_navamsa, "D9")
    
    chart_row = [d1_chart, d9_chart]
    chart_table = Table([chart_row], colWidths=[2.8*inch, 2.8*inch])
    chart_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(chart_table)
    elements.append(Spacer(1, 0.3*inch))
    
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
    
    elements.append(Paragraph("Active Dasha Period", styles['SubsectionTitle']))
    
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
    elements.append(table)
    
    elements.append(Spacer(1, 0.3*inch))
    
    elements.append(Paragraph("Current Transits (Gochara)", styles['SubsectionTitle']))
    
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
    elements.append(table)
    
    elements.append(Spacer(1, 0.3*inch))
    
    elements.append(Paragraph("Nakshatra & Timing", styles['SubsectionTitle']))
    
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
    elements.append(table)
    
    elements.append(Spacer(1, 0.3*inch))
    
    elements.append(Paragraph("Pakshi / Rhythm Context", styles['SubsectionTitle']))
    
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
    elements.append(table)
    
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
    
    if data.is_v2 and data.monthly_theme:
        elements.append(Paragraph(
            f"<b>{data.monthly_theme.title}</b>",
            styles['SubsectionTitle']
        ))
        elements.append(Paragraph(data.monthly_theme.narrative, styles['BodyText']))
        elements.append(Spacer(1, 0.3*inch))
    
    if data.is_v2 and data.overview_v2:
        elements.append(Paragraph("Energy & Focus", styles['SubsectionTitle']))
        elements.append(Paragraph(data.overview_v2.energy_pattern, styles['BodyText']))
        
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
    elif data.prediction_overview:
        elements.append(Paragraph("Overview", styles['SubsectionTitle']))
        elements.append(Paragraph(data.prediction_overview, styles['BodyText']))
        elements.append(Spacer(1, 0.3*inch))
    
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
    
    for area in data.prediction_areas:
        area_elements = [
            Paragraph(f"<b>{area.area}</b> ({area.score}/100 - {_score_to_label(area.score)})", 
                     styles['BodyText']),
        ]
        
        if area.interpretation:
            area_elements.append(Paragraph(area.interpretation, styles['BodyText']))
        
        if area.deeper_explanation:
            area_elements.append(Paragraph(
                f"<i>{area.deeper_explanation}</i>", 
                styles['BodyText']
            ))
        
        if area.opportunity:
            area_elements.append(Paragraph(
                f"<b>Opportunity:</b> {area.opportunity}", 
                styles['BodyText']
            ))
        
        if area.watch_out:
            area_elements.append(Paragraph(
                f"<b>Watch Out:</b> {area.watch_out}", 
                styles['BodyText']
            ))
        
        if area.one_action:
            area_elements.append(Paragraph(
                f"<b>One Action:</b> {area.one_action}", 
                styles['BodyText']
            ))
        
        if area.guidance:
            area_elements.append(Paragraph(
                f"<b>Guidance:</b> {area.guidance}", 
                styles['BodyText']
            ))
        
        if area.attribution:
            attr = area.attribution
            attr_lines = []
            
            main_parts = []
            if attr.planets:
                main_parts.append(f"Planets: {', '.join(attr.planets)}")
            if attr.dasha:
                main_parts.append(f"Dasha: {attr.dasha}")
            if main_parts:
                attr_lines.append(" | ".join(main_parts))
            
            if attr.engines:
                attr_lines.append(f"Engines: {', '.join(attr.engines)}")
            
            if attr.signals:
                signal_strs = []
                for sig in attr.signals:
                    signal_strs.append(f"{sig.engine} ({sig.direction}, {sig.weight:.2f})")
                attr_lines.append(f"Signals: {' | '.join(signal_strs)}")
            
            if attr_lines:
                area_elements.append(Paragraph(
                    f"<font size='9' color='gray'>ASTROLOGICAL ATTRIBUTION</font>",
                    styles['BodyText']
                ))
                for line in attr_lines:
                    area_elements.append(Paragraph(
                        f"<font size='8' color='gray'>{line}</font>",
                        styles['BodyText']
                    ))
        
        area_elements.append(Spacer(1, 0.2*inch))
        elements.append(KeepTogether(area_elements))
    
    elements.append(PageBreak())
    
    return elements


def _build_practices_reflection(data: CanonicalReportData, styles) -> List:
    """Build practices section."""
    elements = []
    
    if data.is_v2 and data.practices_v2:
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
        
        if data.practices_v2.reflection_question:
            elements.append(Spacer(1, 0.15*inch))
            elements.append(Paragraph(
                f"<b>Reflection Question:</b>", 
                styles['BodyText']
            ))
            elements.append(Paragraph(
                f"<i>\"{data.practices_v2.reflection_question}\"</i>", 
                styles['BodyText']
            ))
        
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
    
    if data.is_v2 and data.closing_v2:
        elements.append(Paragraph("Key Takeaways", styles['SectionTitle']))
        
        if data.closing_v2.key_takeaways:
            for takeaway in data.closing_v2.key_takeaways:
                elements.append(Paragraph(f"• {takeaway}", styles['BodyText']))
            elements.append(Spacer(1, 0.2*inch))
        
        if data.closing_v2.encouragement:
            elements.append(Paragraph(
                f"<i>{data.closing_v2.encouragement}</i>",
                styles['BodyText']
            ))
    else:
        elements.append(Paragraph("Closing Note", styles['SectionTitle']))
        
        elements.append(Paragraph(data.closing_note, styles['BodyText']))
        
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
    
    elements.append(Paragraph("Divisional Charts (Vargas)", styles['SectionTitle']))
    
    elements.append(Paragraph(
        "Divisional charts (Vargas) refine the birth chart analysis by examining "
        "specific life areas. These follow the Classical Parashara method.",
        styles['BodyText']
    ))
    
    elements.append(Spacer(1, 0.2*inch))
    
    chart_info = [
        ("D10 - Dasamsa", data.chart_images.d10_dasamsa, "Career & Authority", has_d10),
        ("D2 - Hora", data.chart_images.d2_hora, "Wealth & Sustenance", has_d2),
        ("D7 - Saptamsa", data.chart_images.d7_saptamsa, "Creativity & Children", has_d7),
    ]
    
    charts_rendered = []
    labels = []
    
    for label, svg_data, purpose, has_data in chart_info:
        if has_data:
            charts_rendered.append(_render_chart_from_svg(svg_data, label.split(" - ")[0]))
            labels.append(f"{label}\n({purpose})")
    
    if charts_rendered:
        if len(charts_rendered) <= 2:
            chart_table = Table([charts_rendered], colWidths=[2.5*inch] * len(charts_rendered))
            label_table = Table([labels], colWidths=[2.5*inch] * len(labels))
        else:
            chart_table = Table([charts_rendered[:2], charts_rendered[2:] + [""]], colWidths=[2.5*inch, 2.5*inch])
            label_table = Table([labels[:2], labels[2:] + [""]], colWidths=[2.5*inch, 2.5*inch])
        
        chart_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(chart_table)
        
        label_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.Color(*COLORS["muted"])),
        ]))
        elements.append(label_table)
    
    elements.append(PageBreak())
    
    return elements


def _build_methodology_appendix(data: CanonicalReportData, styles) -> List:
    """Build methodology appendix section."""
    elements = []
    
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
