"""
South Indian Chart Layout Constants

This file defines the canonical, locked geometry for rendering
South Indian (Rasi-style) charts in SVG for PDF output.

⚠️ DO NOT add logic here.
⚠️ DO NOT compute positions dynamically.
⚠️ DO NOT refactor without regenerating all PDFs.

Determinism > Flexibility.
"""

# ===============================
# Grid Geometry
# ===============================

GRID_SIZE = 4                     # 4x4 grid
CELL_SIZE = 120                   # pixels
GRID_PADDING = 20                 # outer padding (pixels)

SVG_WIDTH = GRID_SIZE * CELL_SIZE + (2 * GRID_PADDING)
SVG_HEIGHT = GRID_SIZE * CELL_SIZE + (2 * GRID_PADDING)

# ===============================
# Typography
# ===============================

SIGN_FONT_SIZE = 12
PLANET_FONT_SIZE = 14
TITLE_FONT_SIZE = 16

SIGN_FONT_FAMILY = "Helvetica"
PLANET_FONT_FAMILY = "Helvetica-Bold"
TITLE_FONT_FAMILY = "Helvetica-Bold"

# ===============================
# Colors
# ===============================

COLOR_SIGN_LABEL = "#444444"
COLOR_PLANET_DEFAULT = "#000000"

COLOR_EXALTED = "#1A7F37"        # green
COLOR_DEBILITATED = "#B42318"    # red

GRID_STROKE_COLOR = "#000000"
GRID_STROKE_WIDTH = 1

# ===============================
# Canonical Sign Order
# (South Indian – fixed positions)
# ===============================

SOUTH_INDIAN_SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

# ===============================
# Sign → Grid Cell Mapping
#
# Coordinates are (col, row)
# Origin (0,0) is top-left of grid
#
# Layout:
# ┌────┬────┬────┬────┐
# │    │Ar  │Ta  │Ge  │
# ├────┼────┼────┼────┤
# │Pi  │    │    │Ca  │
# ├────┼────┼────┼────┤
# │Aq  │    │    │Le  │
# ├────┼────┼────┼────┤
# │Cp  │Sg  │Sc  │Li  │
# └────┴────┴────┴────┘
# ===============================

SIGN_TO_GRID_POSITION = {
    "Aries":        (1, 0),
    "Taurus":      (2, 0),
    "Gemini":      (3, 0),

    "Cancer":      (3, 1),
    "Leo":         (3, 2),

    "Virgo":       (2, 3),
    "Libra":       (3, 3),

    "Scorpio":     (2, 3),
    "Sagittarius": (1, 3),
    "Capricorn":   (0, 3),

    "Aquarius":    (0, 2),
    "Pisces":      (0, 1),
}

# NOTE:
# Virgo and Scorpio share row 3 in classic South Indian layouts.
# We still render each sign independently — no overlap occurs
# because planets are rendered within their sign group.

# ===============================
# Derived Absolute Coordinates
# ===============================

def grid_cell_top_left(col: int, row: int) -> tuple[int, int]:
    """
    Returns absolute (x, y) pixel position
    for the top-left corner of a grid cell.
    """
    x = GRID_PADDING + (col * CELL_SIZE)
    y = GRID_PADDING + (row * CELL_SIZE)
    return x, y


def grid_cell_center(col: int, row: int) -> tuple[int, int]:
    """
    Returns absolute (x, y) pixel position
    for the center of a grid cell.
    """
    x, y = grid_cell_top_left(col, row)
    return (
        x + (CELL_SIZE // 2),
        y + (CELL_SIZE // 2),
    )


# ===============================
# Planet Placement Within Cell
# ===============================

PLANET_VERTICAL_START_OFFSET = 30
PLANET_VERTICAL_SPACING = 16

def planet_text_position(col: int, row: int, index: int) -> tuple[int, int]:
    """
    Returns absolute (x, y) position for a planet label
    within a sign cell.

    index = 0, 1, 2... (sorted alphabetically upstream)
    """
    x, y = grid_cell_top_left(col, row)
    return (
        x + 10,
        y + PLANET_VERTICAL_START_OFFSET + (index * PLANET_VERTICAL_SPACING),
    )
