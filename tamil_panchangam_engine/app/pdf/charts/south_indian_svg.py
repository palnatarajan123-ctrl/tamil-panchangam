"""
South Indian Chart SVG Renderer

Deterministic SVG renderer for D1 / D9 charts used in PDF generation.

Rules:
- Pure rendering only
- No astrology computation
- No randomness
- Same input => same SVG output
"""

from typing import List
from xml.sax.saxutils import escape

from app.pdf.charts.chart_models import ChartSvgInput
from app.pdf.charts.layout import (
    SVG_WIDTH,
    SVG_HEIGHT,
    GRID_SIZE,
    CELL_SIZE,
    GRID_PADDING,
    SOUTH_INDIAN_SIGNS,
    SIGN_TO_GRID_POSITION,
    GRID_STROKE_COLOR,
    GRID_STROKE_WIDTH,
    SIGN_FONT_SIZE,
    PLANET_FONT_SIZE,
    SIGN_FONT_FAMILY,
    PLANET_FONT_FAMILY,
    TITLE_FONT_SIZE,
    TITLE_FONT_FAMILY,
    COLOR_SIGN_LABEL,
    COLOR_PLANET_DEFAULT,
    COLOR_EXALTED,
    COLOR_DEBILITATED,
    grid_cell_center,
    planet_text_position,
)

# ===============================
# Public API
# ===============================

def render_south_indian_chart_svg(input: ChartSvgInput) -> str:
    """
    Render a South Indian chart as an SVG string.

    This function is:
    - Deterministic
    - Side-effect free
    - Safe for PDF embedding
    """

    svg_elements: List[str] = []

    # SVG Header
    svg_elements.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{SVG_WIDTH}" height="{SVG_HEIGHT}" '
        f'viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">'
    )

    # Title (defensive + chart-type aware)
    title = _resolve_title(input)
    if title:
        svg_elements.append(_render_title(title))

    # Grid
    svg_elements.extend(_render_grid())

    # Center label (chart-type aware)
    svg_elements.extend(_render_center_label(input))

    # Sign labels
    svg_elements.extend(_render_sign_labels())

    # Planets
    svg_elements.extend(_render_planets(input))

    # Close SVG
    svg_elements.append("</svg>")

    return "\n".join(svg_elements)


# ===============================
# Internal Helpers
# ===============================

def _resolve_title(input: ChartSvgInput) -> str:
    """
    Ensure correct title based on chart type.
    Callers may forget or pass incorrect labels.
    """

    if input.title:
        return input.title

    if input.chart_type == "D9":
        return "Navamsa Chart (D9)"

    return "Rāsi Chart (D1)"


def _render_title(title: str) -> str:
    x = SVG_WIDTH // 2
    y = GRID_PADDING // 2 + TITLE_FONT_SIZE

    return (
        f'<text x="{x}" y="{y}" '
        f'text-anchor="middle" '
        f'font-family="{TITLE_FONT_FAMILY}" '
        f'font-size="{TITLE_FONT_SIZE}">'
        f'{escape(title)}'
        f'</text>'
    )


def _render_grid() -> List[str]:
    elements = []

    for row in range(GRID_SIZE + 1):
        y = GRID_PADDING + (row * CELL_SIZE)
        elements.append(
            f'<line x1="{GRID_PADDING}" y1="{y}" '
            f'x2="{SVG_WIDTH - GRID_PADDING}" y2="{y}" '
            f'stroke="{GRID_STROKE_COLOR}" '
            f'stroke-width="{GRID_STROKE_WIDTH}"/>'
        )

    for col in range(GRID_SIZE + 1):
        x = GRID_PADDING + (col * CELL_SIZE)
        elements.append(
            f'<line x1="{x}" y1="{GRID_PADDING}" '
            f'x2="{x}" y2="{SVG_HEIGHT - GRID_PADDING}" '
            f'stroke="{GRID_STROKE_COLOR}" '
            f'stroke-width="{GRID_STROKE_WIDTH}"/>'
        )

    return elements


def _render_sign_labels() -> List[str]:
    elements = []

    for sign in SOUTH_INDIAN_SIGNS:
        if sign not in SIGN_TO_GRID_POSITION:
            continue

        col, row = SIGN_TO_GRID_POSITION[sign]
        cx, cy = grid_cell_center(col, row)

        elements.append(
            f'<text x="{cx}" y="{cy - (CELL_SIZE // 2) + 18}" '
            f'text-anchor="middle" '
            f'font-family="{SIGN_FONT_FAMILY}" '
            f'font-size="{SIGN_FONT_SIZE}" '
            f'fill="{COLOR_SIGN_LABEL}">'
            f'{sign}'
            f'</text>'
        )

    return elements


def _render_planets(input: ChartSvgInput) -> List[str]:
    elements = []

    planets_by_sign = {}
    for planet, sign in input.planet_signs.items():
        planets_by_sign.setdefault(sign, []).append(planet)

    for sign, planets in planets_by_sign.items():
        if sign not in SIGN_TO_GRID_POSITION:
            continue

        col, row = SIGN_TO_GRID_POSITION[sign]

        for idx, planet in enumerate(sorted(planets)):
            x, y = planet_text_position(col, row, idx)
            color = _planet_color(input, planet)

            elements.append(
                f'<text x="{x}" y="{y}" '
                f'font-family="{PLANET_FONT_FAMILY}" '
                f'font-size="{PLANET_FONT_SIZE}" '
                f'fill="{color}">'
                f'{escape(planet)}'
                f'</text>'
            )

    return elements


def _planet_color(input: ChartSvgInput, planet: str) -> str:
    """
    Determine planet color based on dignity (D9 only).
    """
    if not input.dignity:
        return COLOR_PLANET_DEFAULT

    status = input.dignity.get(planet)
    if status == "exalted":
        return COLOR_EXALTED
    if status == "debilitated":
        return COLOR_DEBILITATED

    return COLOR_PLANET_DEFAULT

def _render_center_label(input: ChartSvgInput) -> List[str]:
    """
    Render the center chart label (D1 / D9 aware).
    """

    cx = SVG_WIDTH // 2
    cy = SVG_HEIGHT // 2

    if input.chart_type == "D9":
        main_label = "Navamsa Chart (D9)"
    else:
        main_label = "Rāsi Chart (D1)"

    return [
        (
            f'<text x="{cx}" y="{cy - 6}" '
            f'text-anchor="middle" '
            f'font-family="{TITLE_FONT_FAMILY}" '
            f'font-size="{TITLE_FONT_SIZE}">'
            f'{escape(main_label)}'
            f'</text>'
        ),
        (
            f'<text x="{cx}" y="{cy + 14}" '
            f'text-anchor="middle" '
            f'font-family="{SIGN_FONT_FAMILY}" '
            f'font-size="{SIGN_FONT_SIZE}">'
            f'South Indian'
            f'</text>'
        ),
    ]
