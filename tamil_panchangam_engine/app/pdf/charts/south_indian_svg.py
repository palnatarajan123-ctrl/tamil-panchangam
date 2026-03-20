"""
South Indian Chart SVG Renderer

Mirrors the frontend SouthIndianChart component logic exactly.
Uses lagna-based rotation for correct sign placement.
"""

from typing import List, Dict, Optional
from xml.sax.saxutils import escape

from app.pdf.charts.chart_models import ChartSvgInput
from app.pdf.charts.layout import (
    CELL_SIZE, GRID_PADDING, GRID_SIZE,
    SVG_WIDTH, SVG_HEIGHT,
    SIGN_FONT_SIZE, PLANET_FONT_SIZE, TITLE_FONT_SIZE,
    PLANET_VERTICAL_START_OFFSET, PLANET_VERTICAL_SPACING,
)

# Sign order (matches frontend SIGN_NAMES)
SIGN_NAMES = [
    "Mesham", "Rishabam", "Mithunam", "Kadakam", "Simmam", "Kanni",
    "Thulam", "Vrischikam", "Dhanusu", "Makaram", "Kumbham", "Meenam"
]

# Grid positions for houses 0-11 (matches frontend HOUSE_COORDS)
HOUSE_COORDS = [
    (1, 0), (2, 0), (3, 0),
    (3, 1),
    (3, 2),
    (3, 3), (2, 3), (1, 3), (0, 3),
    (0, 2),
    (0, 1),
    (0, 0),
]

# Name variations mapping to canonical index
NAME_TO_INDEX: Dict[str, int] = {name: i for i, name in enumerate(SIGN_NAMES)}
NAME_TO_INDEX.update({
    "Simham": 4, "Simmam": 4,
    "Vrishchikam": 7, "Vrischikam": 7,
    "Kumbam": 10, "Kumbham": 10,
    "Kadagam": 3, "Kadakam": 3,
    "Meenam": 11,
    "Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3,
    "Leo": 4, "Virgo": 5, "Libra": 6, "Scorpio": 7,
    "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11,
})

COLOR_BG = "#f5f5f0"
COLOR_GRID = "#888888"
COLOR_SIGN = "#555555"
COLOR_LAGNA = "#b45309"
COLOR_PLANET = "#1a1a1a"
COLOR_EXALTED = "#15803d"
COLOR_DEBILITATED = "#b91c1c"
COLOR_CENTER_BG = "#e8e8e0"
COLOR_TITLE = "#1a1a1a"
COLOR_SUBTITLE = "#666666"


def render_south_indian_chart_svg(input: ChartSvgInput) -> str:
    """
    Render a South Indian chart as an SVG string.
    Uses lagna-based rotation matching the frontend.
    """
    svg_elements: List[str] = []
    
    lagna_idx = 0
    if input.lagna_sign:
        lagna_idx = NAME_TO_INDEX.get(input.lagna_sign, 0)
    
    # Build planets by sign index
    planets_by_rasi: Dict[int, List[str]] = {}
    for sign_name, planets in input.planet_signs.items():
        rasi_idx = NAME_TO_INDEX.get(sign_name)
        if rasi_idx is not None:
            planets_by_rasi[rasi_idx] = planets
    
    # SVG Header
    svg_elements.append('<?xml version="1.0" encoding="UTF-8"?>')
    svg_elements.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{SVG_WIDTH}" height="{SVG_HEIGHT}" '
        f'viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">'
    )
    
    # Background
    svg_elements.append(
        f'<rect x="0" y="0" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" '
        f'fill="{COLOR_BG}" rx="6"/>'
    )
    
    # Grid lines
    for i in range(5):
        y = GRID_PADDING + (i * CELL_SIZE)
        svg_elements.append(
            f'<line x1="{GRID_PADDING}" y1="{y}" '
            f'x2="{SVG_WIDTH - GRID_PADDING}" y2="{y}" '
            f'stroke="{COLOR_GRID}" stroke-width="1"/>'
        )
    for i in range(5):
        x = GRID_PADDING + (i * CELL_SIZE)
        svg_elements.append(
            f'<line x1="{x}" y1="{GRID_PADDING}" '
            f'x2="{x}" y2="{SVG_HEIGHT - GRID_PADDING}" '
            f'stroke="{COLOR_GRID}" stroke-width="1"/>'
        )
    
    # Diagonals
    svg_elements.append(
        f'<line x1="{GRID_PADDING + CELL_SIZE}" y1="{GRID_PADDING + CELL_SIZE}" '
        f'x2="{GRID_PADDING + CELL_SIZE*3}" y2="{GRID_PADDING + CELL_SIZE*3}" '
        f'stroke="{COLOR_GRID}" stroke-width="1"/>'
    )
    svg_elements.append(
        f'<line x1="{GRID_PADDING + CELL_SIZE*3}" y1="{GRID_PADDING + CELL_SIZE}" '
        f'x2="{GRID_PADDING + CELL_SIZE}" y2="{GRID_PADDING + CELL_SIZE*3}" '
        f'stroke="{COLOR_GRID}" stroke-width="1"/>'
    )
    
    # Render houses with lagna rotation
    for house_idx, (col, row) in enumerate(HOUSE_COORDS):
        rasi_idx = (house_idx + lagna_idx) % 12
        sign_name = SIGN_NAMES[rasi_idx]
        abbrev = sign_name[:3].upper()
        is_lagna = (rasi_idx == lagna_idx)
        
        x = GRID_PADDING + (col * CELL_SIZE)
        y = GRID_PADDING + (row * CELL_SIZE)
        cx = x + CELL_SIZE / 2
        
        # Sign label
        label_color = COLOR_LAGNA if is_lagna else COLOR_SIGN
        svg_elements.append(
            f'<text x="{cx}" y="{y + 22}" text-anchor="middle" '
            f'font-family="monospace" font-size="{SIGN_FONT_SIZE}" fill="{label_color}">'
            f'{escape(abbrev)}</text>'
        )
        
        # Lagna marker
        if is_lagna:
            svg_elements.append(
                f'<text x="{cx}" y="{y + 40}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="{SIGN_FONT_SIZE - 2}" font-weight="600" fill="{COLOR_LAGNA}">'
                f'Lagna</text>'
            )

        # Planets — start below the lagna label when present to avoid overlap
        # With lagna: baseline of "Lagna" text is y+40 (13px font), so planets start at y+58
        # Without lagna: sign baseline is y+22 (15px font), planets start at y+42
        planet_y_start = y + (58 if is_lagna else 42)
        planets = planets_by_rasi.get(rasi_idx, [])
        for idx, planet in enumerate(planets[:4]):
            planet_color = COLOR_PLANET
            if input.dignity:
                d = input.dignity.get(planet)
                if d == "exalted":
                    planet_color = COLOR_EXALTED
                elif d == "debilitated":
                    planet_color = COLOR_DEBILITATED

            py = planet_y_start + idx * PLANET_VERTICAL_SPACING
            svg_elements.append(
                f'<text x="{cx}" y="{py}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="{PLANET_FONT_SIZE}" font-weight="500" fill="{planet_color}">'
                f'{escape(planet)}</text>'
            )
    
    # Center panel
    center_x = GRID_PADDING + CELL_SIZE
    center_y = GRID_PADDING + CELL_SIZE
    svg_elements.append(
        f'<rect x="{center_x}" y="{center_y}" width="{CELL_SIZE*2}" height="{CELL_SIZE*2}" '
        f'fill="{COLOR_CENTER_BG}" rx="4"/>'
    )
    
    # Center label
    title = input.title or ("Navamsa Chart (D9)" if input.chart_type == "D9" else "Rasi Chart (D1)")
    subtitle = "D9 - Marriage & Dharma" if input.chart_type == "D9" else "South Indian"
    
    svg_elements.append(
        f'<text x="{SVG_WIDTH/2}" y="{SVG_HEIGHT/2 - 10}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="{TITLE_FONT_SIZE}" font-weight="700" fill="{COLOR_TITLE}">'
        f'{escape(title)}</text>'
    )
    svg_elements.append(
        f'<text x="{SVG_WIDTH/2}" y="{SVG_HEIGHT/2 + 14}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="{SIGN_FONT_SIZE}" fill="{COLOR_SUBTITLE}">'
        f'{escape(subtitle)}</text>'
    )
    
    svg_elements.append("</svg>")
    return "\n".join(svg_elements)
