"""
Canonical PDF Report Builder - Configuration

Centralized configuration for PDF generation:
- Report versions
- Token limits
- Section names
- Styling defaults
"""

REPORT_VERSION = "1.0"
PROMPT_VERSION = "report_v1"

MAX_TOKENS_PER_SECTION = 800

SECTION_NAMES = [
    "cover",
    "how_to_read",
    "natal_snapshot",
    "core_life_themes",
    "astrological_context",
    "predictions",
    "practices_reflection",
    "summary_closing",
]

COLORS = {
    "primary": (0.2, 0.15, 0.4),
    "secondary": (0.4, 0.35, 0.5),
    "accent": (0.8, 0.6, 0.2),
    "text": (0.1, 0.1, 0.1),
    "muted": (0.5, 0.5, 0.5),
    "background": (0.98, 0.97, 0.95),
}

FONTS = {
    "heading": "Helvetica-Bold",
    "body": "Helvetica",
    "mono": "Courier",
}

PAGE_SIZE = "A4"
MARGIN = 50
