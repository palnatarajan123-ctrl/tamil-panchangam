# tests/pdf/test_canonical_report_prospects.py
"""
Phase G3: Phase G1 chart-to-chart prospect Porutham section in the
individual chart PDF (app/pdf/canonical_report/{data_loader,pdf_renderer,
models}.py). First PDF test coverage for this module (family_report/ got
its own coverage in Phase F4 Part A; canonical_report/ had none before
this).

Tests inspect ReportLab flowables directly (Paragraph.text,
Table._cellvalues), same technique and same reasoning as
tests/pdf/test_family_pdf_porutham.py -- raw PDF-byte search is not a
valid substitute (confirmed there: ReportLab compresses content streams,
so `b"..." in pdf_bytes` is False regardless of real content). Real
end-to-end visual verification (does the rendered PDF actually look
right) was done separately: generated and read real birth-chart PDFs for
both a with-active-prospect chart and a no-prospects chart against real
DB data.
"""

import unittest
from unittest.mock import MagicMock, patch

from reportlab.platypus import Table, KeepTogether

from app.pdf.canonical_report.pdf_renderer import (
    _build_prospects_section, _build_one_prospect_entry, _create_styles,
)
from app.pdf.canonical_report.models import CanonicalReportData, ProspectsData
from app.pdf.canonical_report.data_loader import load_prospects_for_chart


def _flatten_text(elements) -> str:
    """Collect all Paragraph text and Table cell text from a flowables
    list into one string, for substring assertions. Recurses into
    KeepTogether (_build_one_prospect_entry wraps each entry in one)."""
    parts = []
    for el in elements:
        if isinstance(el, KeepTogether):
            parts.append(_flatten_text(el._content))
            continue
        if isinstance(el, Table):
            for row in el._cellvalues:
                for cell in row:
                    if hasattr(cell, "text"):
                        parts.append(cell.text)
                    elif isinstance(cell, str):
                        parts.append(cell)
            continue
        if hasattr(el, "text"):
            parts.append(el.text)
    return "\n".join(parts)


def _real_entry(other_name="KK", score=23, max_score=33, percent=69.7, grade="Good"):
    """Shape verified against a real load_prospects_for_chart() call
    against real dev-DB data during Phase G3 development (real prospect
    AN Sr x KK, score 23/33), not guessed."""
    return {
        "other_name": other_name, "score": score, "max_score": max_score,
        "percent": percent, "grade": grade,
        "points": [
            {"name": "Dinam", "score": 3, "max": 3, "pass": True},
            {"name": "Ganam", "score": 0, "max": 6, "pass": False},
            {"name": "Yoni", "score": 2, "max": 4, "pass": True},
            {"name": "Rasi", "score": 7, "max": 7, "pass": True},
            {"name": "Rasiyathipaty", "score": 3, "max": 5, "pass": True},
            {"name": "Rajju", "score": 0, "max": 0, "pass": True, "mandatory": True},
            {"name": "Vedha", "score": 0, "max": 0, "pass": True, "mandatory": True},
            {"name": "Mahendra", "score": 0, "max": 0, "pass": False},
            {"name": "Stree Deergha", "score": 0, "max": 0, "pass": True},
            {"name": "Nadi", "score": 8, "max": 8, "pass": True, "mandatory": True},
        ],
    }


class TestBuildOneProspectEntry(unittest.TestCase):
    def setUp(self):
        self.styles = _create_styles()

    def test_real_data_renders_name_score_grade_and_all_categories(self):
        elements = _build_one_prospect_entry(_real_entry(), self.styles)
        text = _flatten_text(elements)
        self.assertIn("KK", text)
        self.assertIn("23/33", text)
        self.assertIn("69.7%", text)
        self.assertIn("Good", text)
        for category in ["Dinam", "Ganam", "Yoni", "Rasi", "Rasiyathipaty",
                          "Rajju", "Vedha", "Mahendra", "Stree Deergha", "Nadi"]:
            self.assertIn(category, text)

    def test_mandatory_categories_labeled(self):
        elements = _build_one_prospect_entry(_real_entry(), self.styles)
        text = _flatten_text(elements)
        self.assertIn("Rajju (mandatory)", text)
        self.assertIn("Vedha (mandatory)", text)
        self.assertIn("Nadi (mandatory)", text)
        self.assertNotIn("Mahendra (mandatory)", text)

    def test_scored_categories_show_fraction_pass_fail_show_word(self):
        elements = _build_one_prospect_entry(_real_entry(), self.styles)
        text = _flatten_text(elements)
        self.assertIn("3/3", text)   # Dinam, scored
        self.assertIn("0/6", text)   # Ganam, scored
        self.assertIn("Pass", text)  # Rajju/Vedha/Stree Deergha
        self.assertIn("FAIL", text)  # Mahendra

    def test_no_points_returns_empty_list(self):
        entry = _real_entry()
        entry["points"] = []
        self.assertEqual(_build_one_prospect_entry(entry, self.styles), [])

    def test_missing_other_name_falls_back_gracefully(self):
        entry = _real_entry(other_name=None)
        elements = _build_one_prospect_entry(entry, self.styles)
        text = _flatten_text(elements)
        self.assertIn("Candidate", text)

    def test_commentary_renders_when_present(self):
        """Phase H3: cached prospect-tone commentary renders between the
        score summary and the category table."""
        entry = _real_entry()
        entry["commentary"] = "This is the mechanism explanation."
        elements = _build_one_prospect_entry(entry, self.styles)
        text = _flatten_text(elements)
        self.assertIn("This is the mechanism explanation.", text)

    def test_no_commentary_key_renders_without_error(self):
        """Older cache rows predating Phase H1 have no "commentary" key at
        all -- must render fine, not crash on a missing key."""
        entry = _real_entry()
        elements = _build_one_prospect_entry(entry, self.styles)
        text = _flatten_text(elements)
        self.assertIn("KK", text)  # still renders normally


class TestBuildProspectsSection(unittest.TestCase):
    def setUp(self):
        self.styles = _create_styles()

    def _data(self, prospects=None):
        return MagicMock(spec=CanonicalReportData, prospects=prospects)

    def test_no_prospects_returns_empty_list(self):
        self.assertEqual(_build_prospects_section(self._data(None), self.styles), [])

    def test_empty_entries_returns_empty_list(self):
        data = self._data(ProspectsData(entries=[]))
        self.assertEqual(_build_prospects_section(data, self.styles), [])

    def test_single_prospect_renders_section_title_and_entry(self):
        data = self._data(ProspectsData(entries=[_real_entry()]))
        elements = _build_prospects_section(data, self.styles)
        text = _flatten_text(elements)
        self.assertIn("Compatibility Checks (Porutham)", text)
        self.assertIn("KK", text)
        self.assertIn("23/33", text)

    def test_multiple_prospects_each_get_own_entry(self):
        data = self._data(ProspectsData(entries=[
            _real_entry(other_name="KK", score=23, grade="Good"),
            _real_entry(other_name="NU", score=7, grade="Poor"),
        ]))
        elements = _build_prospects_section(data, self.styles)
        text = _flatten_text(elements)
        self.assertIn("KK", text)
        self.assertIn("NU", text)
        self.assertIn("23/33", text)
        self.assertIn("7/33", text)


class TestLoadProspectsForChart(unittest.TestCase):
    """
    Unscoped by user_id -- see load_prospects_for_chart()'s and
    ProspectsData's docstrings for why: canonical_report's PDF endpoints
    have no auth/user context anywhere, confirmed before implementing,
    and every other section here (KP, yogas, sade sati) is already
    chart-intrinsic rather than user-scoped.
    """

    def _cm(self, conn):
        cm = MagicMock()
        cm.__enter__.return_value = conn
        cm.__exit__.return_value = False
        return cm

    def test_no_rows_returns_none(self):
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []
        with patch("app.pdf.canonical_report.data_loader.get_conn", return_value=self._cm(conn)):
            result = load_prospects_for_chart("chart-1")
        self.assertIsNone(result)

    def test_cached_prospect_returns_prospects_data(self):
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            ("p1", "chart-1", "chart-2", "boy", {
                "boy": {"chart_id": "chart-1", "name": "AN Sr", "nakshatra": "X", "rasi": "Y"},
                "girl": {"chart_id": "chart-2", "name": "KK", "nakshatra": "A", "rasi": "B"},
                "porutham": {
                    "total_score": 23, "max_score": 33, "percent": 69.7, "grade": "Good",
                    "points": [{"name": "Nadi", "score": 8, "max": 8, "pass": True, "mandatory": True}],
                },
            }),
        ]
        with patch("app.pdf.canonical_report.data_loader.get_conn", return_value=self._cm(conn)):
            result = load_prospects_for_chart("chart-1")
        self.assertIsInstance(result, ProspectsData)
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(result.entries[0]["other_name"], "KK")
        self.assertEqual(result.entries[0]["score"], 23)
        self.assertIsNone(result.entries[0]["commentary"])  # not in cached row

    def test_commentary_threaded_through_from_cache_row(self):
        """Phase H3: a cached row that DOES have a "commentary" field
        (post-Phase-H1 cache write) must carry it into the entry dict."""
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            ("p1", "chart-1", "chart-2", "boy", {
                "boy": {"chart_id": "chart-1", "name": "AN Sr", "nakshatra": "X", "rasi": "Y"},
                "girl": {"chart_id": "chart-2", "name": "KK", "nakshatra": "A", "rasi": "B"},
                "porutham": {
                    "total_score": 23, "max_score": 33, "percent": 69.7, "grade": "Good",
                    "points": [{"name": "Nadi", "score": 8, "max": 8, "pass": True, "mandatory": True}],
                },
                "commentary": "Cached prospect commentary.",
            }),
        ]
        with patch("app.pdf.canonical_report.data_loader.get_conn", return_value=self._cm(conn)):
            result = load_prospects_for_chart("chart-1")
        self.assertEqual(result.entries[0]["commentary"], "Cached prospect commentary.")

    def test_no_resolvable_points_returns_none(self):
        """A prospect row whose Porutham has no points (e.g. missing
        nak/rasi on one chart) must not produce an empty/broken entry."""
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            ("p1", "chart-1", "chart-2", "boy", {
                "boy": {"chart_id": "chart-1", "name": "AN Sr"},
                "girl": {"chart_id": "chart-2", "name": "KK"},
                "porutham": {"total_score": 0, "points": []},
            }),
        ]
        with patch("app.pdf.canonical_report.data_loader.get_conn", return_value=self._cm(conn)):
            result = load_prospects_for_chart("chart-1")
        self.assertIsNone(result)

    def test_db_error_returns_none_no_crash(self):
        with patch("app.pdf.canonical_report.data_loader.get_conn", side_effect=RuntimeError("db down")):
            result = load_prospects_for_chart("chart-1")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
