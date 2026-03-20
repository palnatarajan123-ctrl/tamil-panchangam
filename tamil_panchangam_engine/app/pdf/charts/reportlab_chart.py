"""
South Indian Chart Renderer using ReportLab

Mirrors the frontend SouthIndianChart component logic exactly.
Uses lagna-based rotation for correct sign placement.
"""

from typing import Dict, List, Optional
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Group
from reportlab.lib.colors import Color, black, white

# Sign order (matches frontend SIGN_NAMES)
SIGN_NAMES = [
    "Mesham", "Rishabam", "Mithunam", "Kadakam", "Simmam", "Kanni",
    "Thulam", "Vrischikam", "Dhanusu", "Makaram", "Kumbham", "Meenam"
]

# Tamil abbreviations (3 chars uppercase)
SIGN_ABBREVS = {name: name[:3].upper() for name in SIGN_NAMES}

# Grid positions for houses 0-11 (matches frontend HOUSE_COORDS)
HOUSE_COORDS = [
    (1, 0), (2, 0), (3, 0),  # Top row: houses 0, 1, 2
    (3, 1),                   # Right col: house 3
    (3, 2),                   # Right col: house 4
    (3, 3), (2, 3), (1, 3), (0, 3),  # Bottom row: houses 5, 6, 7, 8
    (0, 2),                   # Left col: house 9
    (0, 1),                   # Left col: house 10
    (0, 0),                   # Top-left: house 11
]

# Name variations mapping to canonical index
NAME_TO_INDEX = {name: i for i, name in enumerate(SIGN_NAMES)}
NAME_TO_INDEX.update({
    "Simham": 4, "Simmam": 4,
    "Vrishchikam": 7, "Vrischikam": 7,
    "Kumbam": 10, "Kumbham": 10,
    "Kadagam": 3, "Kadakam": 3,
    "Meenam": 11,
    # English names
    "Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3,
    "Leo": 4, "Virgo": 5, "Libra": 6, "Scorpio": 7,
    "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11,
})

PLANET_ABBREVS = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke",
}

COLOR_GRID = Color(0.5, 0.5, 0.5)
COLOR_SIGN = Color(0.5, 0.5, 0.5)
COLOR_LAGNA = Color(0.85, 0.55, 0.35)  # Highlight lagna
COLOR_PLANET = black


def render_south_indian_chart_reportlab(
    chart_type: str,
    planet_signs: Dict[str, List[str]],
    lagna_sign: Optional[str] = None,
    title: Optional[str] = None,
    width: float = 260,
    height: float = 260
) -> Drawing:
    """
    Render a South Indian chart matching frontend logic.
    
    Args:
        chart_type: "D1" or "D9"
        planet_signs: Dict mapping sign names to list of planets
        lagna_sign: The ascendant sign name (for highlighting and rotation)
        title: Optional chart title
        width/height: Drawing dimensions
    """
    drawing = Drawing(width, height + 20)
    cell_size = width / 4
    
    # Determine lagna index for rotation
    lagna_idx = 0
    if lagna_sign:
        lagna_idx = NAME_TO_INDEX.get(lagna_sign, 0)
    
    # Build planets by sign index
    planets_by_rasi: Dict[int, List[str]] = {}
    for sign_name, planets in planet_signs.items():
        rasi_idx = NAME_TO_INDEX.get(sign_name)
        if rasi_idx is not None:
            planets_by_rasi[rasi_idx] = planets
    
    # Title
    if title:
        drawing.add(String(
            width / 2, height + 12, title,
            fontName='Helvetica-Bold', fontSize=12,
            textAnchor='middle', fillColor=black
        ))
    
    # Grid lines
    for i in range(5):
        y = height - (i * cell_size)
        drawing.add(Line(0, y, width, y, strokeColor=COLOR_GRID, strokeWidth=0.5))
    for i in range(5):
        x = i * cell_size
        drawing.add(Line(x, 0, x, height, strokeColor=COLOR_GRID, strokeWidth=0.5))
    
    # Diagonals in center
    drawing.add(Line(cell_size, height - cell_size, cell_size * 3, height - cell_size * 3, 
                     strokeColor=COLOR_GRID, strokeWidth=0.5))
    drawing.add(Line(cell_size * 3, height - cell_size, cell_size, height - cell_size * 3, 
                     strokeColor=COLOR_GRID, strokeWidth=0.5))
    
    # Render houses (using frontend rotation logic)
    for house_idx, (col, row) in enumerate(HOUSE_COORDS):
        rasi_idx = (house_idx + lagna_idx) % 12
        sign_name = SIGN_NAMES[rasi_idx]
        abbrev = sign_name[:3].upper()
        is_lagna = (rasi_idx == lagna_idx)
        
        x = col * cell_size
        y = height - (row * cell_size)  # Flip Y for ReportLab
        
        # Sign label
        label_color = COLOR_LAGNA if is_lagna else COLOR_SIGN
        drawing.add(String(
            x + cell_size / 2, y - 12, abbrev,
            fontName='Helvetica', fontSize=8,
            textAnchor='middle', fillColor=label_color
        ))

        # Lagna marker (asterisk keeps it compact)
        if is_lagna:
            drawing.add(String(
                x + cell_size / 2, y - 22, "*Lag*",
                fontName='Helvetica-Bold', fontSize=7,
                textAnchor='middle', fillColor=COLOR_LAGNA
            ))

        # Planets — positioned to stay within cell bounds.
        # cell_size=65, cell occupies y (top) to y-cell_size (bottom).
        # With lagna: planets start at y-32, spacing 9pt, cap at 3 planets.
        # Without lagna: planets start at y-24, spacing 10pt, up to 4 planets.
        planets = planets_by_rasi.get(rasi_idx, [])
        planet_start = y - (32 if is_lagna else 24)
        planet_spacing = 9
        max_planets = 3 if is_lagna else 4
        cell_bottom = y - cell_size + 3  # 3pt safety margin
        for idx, planet in enumerate(planets[:max_planets]):
            py = planet_start - (idx * planet_spacing)
            if py < cell_bottom:
                break
            abbrev_p = PLANET_ABBREVS.get(planet, planet[:2])
            drawing.add(String(
                x + cell_size / 2, py, abbrev_p,
                fontName='Helvetica-Bold', fontSize=8,
                textAnchor='middle', fillColor=COLOR_PLANET
            ))
    
    # Center label
    cx, cy = width / 2, height / 2
    drawing.add(String(
        cx, cy + 6, chart_type,
        fontName='Helvetica-Bold', fontSize=16,
        textAnchor='middle', fillColor=Color(0.4, 0.4, 0.4)
    ))
    drawing.add(String(
        cx, cy - 10, "South Indian",
        fontName='Helvetica', fontSize=10,
        textAnchor='middle', fillColor=Color(0.5, 0.5, 0.5)
    ))
    
    return drawing
