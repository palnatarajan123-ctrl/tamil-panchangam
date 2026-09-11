# tests/pdf/test_table_style_consistency.py
"""
Phase 3 item 3 of the PDF redesign: several plain data tables
(Astrological Context's 4 tables, the Methodology table) had quietly
lost the bold header font Birth Reference established, and the
Upagrahas table was a completely different dark theme. Fixed by
extracting _data_table_style() from Birth Reference and routing every
plain data table through it.

These tests guard the actual visible symptom (a bold white header on a
dark purple background, not some other font/color) on the real
builder functions, not just on _data_table_style() in isolation --
that isolation test alone wouldn't have caught a builder function that
kept its own separate, un-migrated TableStyle literal.
"""

import unittest
from unittest.mock import MagicMock

from reportlab.lib import colors
from reportlab.platypus import Table

from app.pdf.canonical_report.pdf_renderer import (
    _data_table_style, _kp_table_style,
    _build_astrological_context, _build_methodology_appendix,
    _build_upagrahas_section, _create_styles,
)
from app.pdf.canonical_report.models import (
    CanonicalReportData, DashaContext, TransitContext,
    NakshatraTimingContext, PakshiRhythmContext, MethodologyInfo,
)

_PURPLE = colors.Color(0.2, 0.15, 0.4)


def _find_tables(elements):
    """Recurse into KeepTogether to find every Table in a flowables list."""
    found = []
    for el in elements:
        if isinstance(el, Table):
            found.append(el)
        elif hasattr(el, "_content"):  # KeepTogether
            found.extend(_find_tables(el._content))
    return found


def _header_row_is_bold_white_on_purple(table: Table) -> bool:
    """True if every header cell (row 0) is bold with white text --
    the exact treatment that went missing from several tables."""
    header_styles = table._cellStyles[0]
    return all(
        cs.fontname == 'Helvetica-Bold' and cs.color == colors.white
        for cs in header_styles
    )


class TestDataTableStyleIsSharedBase(unittest.TestCase):
    def test_kp_table_style_built_on_data_table_style(self):
        """_kp_table_style() must not be an independent re-implementation
        of the same header treatment -- it should share the same header
        color/bold/grid commands as _data_table_style(), just centered
        and smaller."""
        base = _data_table_style()
        kp = _kp_table_style()

        def as_dict(cmds):
            return {(c[0], c[1], c[2]): c[3:] for c in cmds}

        base_by_key = as_dict(base)
        kp_by_key = as_dict(kp)

        # Header background, text color, and bold font must match exactly.
        for key in [
            ('BACKGROUND', (0, 0), (-1, 0)),
            ('TEXTCOLOR', (0, 0), (-1, 0)),
            ('FONTNAME', (0, 0), (-1, 0)),
        ]:
            self.assertEqual(base_by_key[key], kp_by_key[key], f"{key} diverged between the two styles")

    def test_data_table_style_header_is_bold_white_on_primary_purple(self):
        cmds = _data_table_style()
        by_key = {(c[0], c[1], c[2]): c[3] for c in cmds}
        self.assertEqual(by_key[('BACKGROUND', (0, 0), (-1, 0))], _PURPLE)
        self.assertEqual(by_key[('TEXTCOLOR', (0, 0), (-1, 0))], colors.white)
        self.assertEqual(by_key[('FONTNAME', (0, 0), (-1, 0))], 'Helvetica-Bold')


class TestAstrologicalContextTablesUseSharedStyle(unittest.TestCase):
    """Regression test for the specific bug: these 4 tables were
    missing FONTNAME=Helvetica-Bold on the header row."""

    def setUp(self):
        self.styles = _create_styles()

    def test_all_four_tables_have_bold_header(self):
        data = MagicMock(
            spec=CanonicalReportData,
            period_label="September 2026",
            dasha_context=DashaContext(
                mahadasha="Jupiter", mahadasha_lord="Jupiter",
                antardasha="Venus", antardasha_lord="Venus",
                dasha_balance="6.0 years remaining",
            ),
            transit_context=TransitContext(
                jupiter_transit="Jupiter in Cancer", saturn_transit="Saturn in Pisces",
                rahu_ketu_axis="Rahu in Aquarius, Ketu in Leo",
            ),
            nakshatra_timing=NakshatraTimingContext(
                current_moon_nakshatra="Visakam", tara_bala="Sampat Tara - Wealth",
                chandra_gati="stable", favorable_window="Consult chart",
            ),
            pakshi_rhythm=PakshiRhythmContext(dominant_pakshi="Crow", activity_phase="Active"),
            sarvashtakavarga=None,
        )
        elements = _build_astrological_context(data, self.styles)
        tables = _find_tables(elements)
        self.assertEqual(len(tables), 4, "expected dasha/transit/timing/pakshi tables")
        for t in tables:
            self.assertTrue(
                _header_row_is_bold_white_on_purple(t),
                f"table header not bold white text: {t._cellvalues[0]}"
            )


class TestMethodologyTableUsesSharedStyle(unittest.TestCase):
    def test_methodology_table_has_bold_header(self):
        styles = _create_styles()
        data = MagicMock(
            spec=CanonicalReportData,
            methodology=MethodologyInfo(),
        )
        elements = _build_methodology_appendix(data, styles)
        tables = _find_tables(elements)
        self.assertEqual(len(tables), 1)
        self.assertTrue(_header_row_is_bold_white_on_purple(tables[0]))


class TestUpagrahasTableMatchesStandardConvention(unittest.TestCase):
    """Regression test for the most severe drift found: Upagrahas used
    a completely different dark theme (near-black header/body, light
    grey text) instead of the light purple-header convention every
    other table uses."""

    def test_upagrahas_table_no_longer_uses_dark_theme(self):
        styles = _create_styles()
        data = MagicMock(
            spec=CanonicalReportData,
            upagrahas={
                "gulika": {"rasi": "Gemini", "rasi_lord": "Mercury", "method": "parashari"},
                "mandi": {},
            },
        )
        elements = _build_upagrahas_section(data, styles)
        tables = _find_tables(elements)
        self.assertEqual(len(tables), 1)
        table = tables[0]
        self.assertTrue(_header_row_is_bold_white_on_purple(table))
        # The old dark theme used near-black (0.1, 0.06, 0.2) -- confirm
        # that specific color is gone from this table's commands.
        old_dark = colors.Color(0.1, 0.06, 0.2)
        for cmd in getattr(table, '_bkgrndcmds', []):
            self.assertNotIn(old_dark, cmd, "Upagrahas table still uses the old dark theme background")


if __name__ == "__main__":
    unittest.main()
