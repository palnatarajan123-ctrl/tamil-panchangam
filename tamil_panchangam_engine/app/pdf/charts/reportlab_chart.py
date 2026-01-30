"""
South Indian Chart Renderer using ReportLab

Renders D1/D9 charts directly to ReportLab Drawing objects for PDF embedding.
No external SVG libraries required.
"""

from typing import Dict, List, Optional
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Group
from reportlab.lib.colors import Color, black, white

CHART_SIZE = 200
CELL_SIZE = CHART_SIZE // 4
GRID_PADDING = 10

SOUTH_INDIAN_SIGN_POSITIONS = {
    "Leo":         (0, 0),
    "Virgo":       (1, 0),
    "Libra":       (2, 0),
    "Scorpio":     (3, 0),
    "Cancer":      (0, 1),
    "Sagittarius": (3, 1),
    "Gemini":      (0, 2),
    "Capricorn":   (3, 2),
    "Taurus":      (0, 3),
    "Aries":       (1, 3),
    "Pisces":      (2, 3),
    "Aquarius":    (3, 3),
}

SIGN_ABBREVS = {
    "Aries": "MES", "Taurus": "RIS", "Gemini": "MIT", "Cancer": "KAD",
    "Leo": "SIM", "Virgo": "KAN", "Libra": "THU", "Scorpio": "VRI",
    "Sagittarius": "DHA", "Capricorn": "MAK", "Aquarius": "KUM", "Pisces": "MEE",
    "Mesham": "MES", "Rishabam": "RIS", "Mithunam": "MIT", "Kadagam": "KAD",
    "Simham": "SIM", "Kanni": "KAN", "Thulam": "THU", "Vrishchikam": "VRI",
    "Dhanusu": "DHA", "Makaram": "MAK", "Kumbam": "KUM", "Meenam": "MEE"
}

TAMIL_TO_ENGLISH = {
    "Mesham": "Aries", "Rishabam": "Taurus", "Mithunam": "Gemini", "Kadagam": "Cancer",
    "Simham": "Leo", "Kanni": "Virgo", "Thulam": "Libra", "Vrishchikam": "Scorpio",
    "Dhanusu": "Sagittarius", "Makaram": "Capricorn", "Kumbam": "Aquarius", "Meenam": "Pisces",
    "Vrischikam": "Scorpio", "Kumbham": "Aquarius", "Kadakam": "Cancer",
}

PLANET_ABBREVS = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke",
    "Ascendant": "As", "Lagna": "As"
}

COLOR_EXALTED = Color(0.1, 0.5, 0.22)
COLOR_DEBILITATED = Color(0.7, 0.14, 0.09)
COLOR_DEFAULT = black
COLOR_SIGN_LABEL = Color(0.4, 0.4, 0.4)
COLOR_GRID = Color(0.3, 0.3, 0.3)


def render_south_indian_chart_reportlab(
    chart_type: str,
    planet_signs: Dict[str, List[str]],
    title: Optional[str] = None,
    dignity: Optional[Dict[str, str]] = None,
    width: float = CHART_SIZE,
    height: float = CHART_SIZE
) -> Drawing:
    """
    Render a South Indian chart as a ReportLab Drawing.
    
    Args:
        chart_type: "D1" or "D9"
        planet_signs: Dict mapping sign names to list of planets
        title: Optional chart title
        dignity: Optional dict of planet dignities for coloring
        width: Drawing width
        height: Drawing height
    
    Returns:
        ReportLab Drawing object ready for PDF embedding
    """
    drawing = Drawing(width, height + 25)
    
    cell_size = min(width, height) / 4
    
    if title:
        drawing.add(String(
            width / 2, height + 15,
            title,
            fontName='Helvetica-Bold',
            fontSize=10,
            textAnchor='middle',
            fillColor=black
        ))
    
    for row in range(5):
        y = height - (row * cell_size)
        drawing.add(Line(0, y, width, y, strokeColor=COLOR_GRID, strokeWidth=1))
    
    for col in range(5):
        x = col * cell_size
        drawing.add(Line(x, 0, x, height, strokeColor=COLOR_GRID, strokeWidth=1))
    
    for sign_name, (col, row) in SOUTH_INDIAN_SIGN_POSITIONS.items():
        x = col * cell_size + 3
        y = height - (row * cell_size) - 12
        abbrev = SIGN_ABBREVS.get(sign_name, sign_name[:2])
        drawing.add(String(
            x, y, abbrev,
            fontName='Helvetica',
            fontSize=8,
            fillColor=COLOR_SIGN_LABEL
        ))
    
    for sign_name, planets in planet_signs.items():
        lookup_name = TAMIL_TO_ENGLISH.get(sign_name, sign_name)
        if lookup_name not in SOUTH_INDIAN_SIGN_POSITIONS:
            continue
        
        col, row = SOUTH_INDIAN_SIGN_POSITIONS[lookup_name]
        base_x = col * cell_size + 3
        base_y = height - (row * cell_size) - 26
        
        for idx, planet in enumerate(sorted(planets)[:4]):
            abbrev = PLANET_ABBREVS.get(planet, planet[:2])
            
            color = COLOR_DEFAULT
            if dignity:
                status = dignity.get(planet)
                if status == "exalted":
                    color = COLOR_EXALTED
                elif status == "debilitated":
                    color = COLOR_DEBILITATED
            
            y_offset = idx * 11
            drawing.add(String(
                base_x, base_y - y_offset, abbrev,
                fontName='Helvetica-Bold',
                fontSize=9,
                fillColor=color
            ))
    
    center_x = width / 2
    center_y = height / 2
    
    if chart_type == "D9":
        label = "D9"
    else:
        label = "D1"
    
    drawing.add(String(
        center_x, center_y + 5, label,
        fontName='Helvetica-Bold',
        fontSize=14,
        textAnchor='middle',
        fillColor=Color(0.6, 0.6, 0.6)
    ))
    drawing.add(String(
        center_x, center_y - 10, "South Indian",
        fontName='Helvetica',
        fontSize=8,
        textAnchor='middle',
        fillColor=Color(0.6, 0.6, 0.6)
    ))
    
    return drawing
