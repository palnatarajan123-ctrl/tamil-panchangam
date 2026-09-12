"""
Canonical PDF Report Builder - Configuration

Centralized configuration for PDF generation:
- Report versions
- Token limits
- Section names
- Styling defaults

COLORS and MARGIN are re-exported from app.pdf.shared_styles (not
defined here) so this module and family_report/family_pdf_renderer.py
draw from one source instead of two independently-synced copies --
see shared_styles.py's docstring for why. Kept as re-exports (not
removed) so `from .config import COLORS, MARGIN` keeps working
everywhere in this package without touching every call site.
"""

from app.pdf.shared_styles import COLORS, MARGIN

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

FONTS = {
    "heading": "Helvetica-Bold",
    "body": "Helvetica",
    "mono": "Courier",
}

PAGE_SIZE = "A4"
