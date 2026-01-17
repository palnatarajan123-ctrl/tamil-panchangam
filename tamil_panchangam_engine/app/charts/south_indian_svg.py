"""
This module will generate South Indian style chart SVG:
- 12-house square grid
- Planetary placements with degrees
- Aspect lines (optional)
- D1 (Rasi) and D9 (Navamsa) layouts

"""

import svgwrite
from typing import Dict, List

BOX_SIZE = 120
FONT_SIZE = 14

RASI_GRID = [
    ["Mesham", "Rishabam", "Mithunam", "Kadakam"],
    ["Simmam", "Kanni", "Thulam", "Vrischikam"],
    ["Dhanusu", "Makaram", "Kumbham", "Meenam"]
]

def generate_south_indian_chart_svg(
    chart_data: Dict[str, List[str]],
    title: str = "Rasi Chart"
) -> svgwrite.Drawing:
    """
    Generate South Indian square-style Rasi chart as SVG.
    """

    width = BOX_SIZE * 4
    height = BOX_SIZE * 3
    dwg = svgwrite.Drawing(size=(width, height))

    # Title
    dwg.add(dwg.text(
        title,
        insert=(width / 2, 20),
        text_anchor="middle",
        font_size=16,
        font_weight="bold"
    ))

    y_offset = 30

    for row_idx, row in enumerate(RASI_GRID):
        for col_idx, rasi in enumerate(row):
            x = col_idx * BOX_SIZE
            y = row_idx * BOX_SIZE + y_offset

            # Draw box
            dwg.add(dwg.rect(
                insert=(x, y),
                size=(BOX_SIZE, BOX_SIZE),
                fill="white",
                stroke="black"
            ))

            # Rasi name
            dwg.add(dwg.text(
                rasi,
                insert=(x + 5, y + 15),
                font_size=10,
                font_weight="bold"
            ))

            # Planets
            planets = chart_data.get(rasi, [])
            for idx, planet in enumerate(planets):
                dwg.add(dwg.text(
                    planet,
                    insert=(x + 10, y + 35 + idx * FONT_SIZE),
                    font_size=FONT_SIZE
                ))

    return dwg
