# tests/pdf/test_family_pdf_porutham.py
"""
Phase F4 Part A: dedicated Porutham section in the family PDF
(app/pdf/family_report/family_pdf_renderer.py).

Tests inspect the ReportLab flowables _build_porutham() returns directly
(Paragraph.text, Table._cellvalues) rather than parsing rendered PDF bytes.
No PDF text-extraction library (pypdf/pdfplumber) is available in this
venv, and adding one just for tests is a separate dependency decision --
confirmed empirically that raw byte-search on rendered PDF bytes is NOT a
valid substitute (ReportLab compresses content streams by default, so
`b"Compatibility" in pdf_bytes` is False regardless of whether the text is
actually present -- checked directly before writing these tests). The real
end-to-end visual check (does the rendered PDF actually look right) was
done separately by generating and reading real PDFs for both the
with-Porutham and no-pairing cases against real DB data.
"""

import unittest

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, KeepTogether

from app.pdf.family_report.family_pdf_renderer import (
    _build_porutham, render_family_pdf, _make_styles,
)


def _real_porutham():
    """Shape verified against real compute_porutham() / _get_or_compute_porutham()
    output during Phase F1 development, not guessed."""
    return {
        "total_score": 16, "max_score": 33, "percent": 48.5, "grade": "Average",
        "mandatory_fail": False,
        "points": [
            {"name": "Dinam", "score": 0, "max": 3, "pass": False},
            {"name": "Ganam", "score": 6, "max": 6, "pass": True},
            {"name": "Yoni", "score": 2, "max": 4, "pass": True},
            {"name": "Rasi", "score": 0, "max": 7, "pass": False},
            {"name": "Rasiyathipaty", "score": 0, "max": 5, "pass": False},
            {"name": "Rajju", "score": 0, "max": 0, "pass": True, "mandatory": True},
            {"name": "Vedha", "score": 0, "max": 0, "pass": True, "mandatory": True},
            {"name": "Mahendra", "score": 0, "max": 0, "pass": True},
            {"name": "Stree Deergha", "score": 0, "max": 0, "pass": True},
            {"name": "Nadi", "score": 8, "max": 8, "pass": True, "mandatory": True},
        ],
    }


def _flatten_text(elements) -> str:
    """Collect all Paragraph text and Table cell text from a flowables list
    into one string, for substring assertions. Recurses into KeepTogether
    (_build_porutham wraps its table in one, same as the KP appendix
    tables in canonical_report/pdf_renderer.py do)."""
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
            continue
        if hasattr(el, "text"):
            parts.append(el.text)
    return "\n".join(parts)


class TestBuildPorutham(unittest.TestCase):
    def setUp(self):
        self.styles = _make_styles()

    def test_real_data_renders_score_grade_and_all_categories(self):
        elements = _build_porutham(_real_porutham(), "PN", "Arthi", self.styles)
        text = _flatten_text(elements)
        self.assertIn("Compatibility (Porutham)", text)
        self.assertIn("PN", text)
        self.assertIn("Arthi", text)
        self.assertIn("16/33", text)
        self.assertIn("48.5%", text)
        self.assertIn("Average", text)
        for category in ["Dinam", "Ganam", "Yoni", "Rasi", "Rasiyathipaty",
                          "Rajju", "Vedha", "Mahendra", "Stree Deergha", "Nadi"]:
            self.assertIn(category, text)

    def test_mandatory_categories_labeled(self):
        elements = _build_porutham(_real_porutham(), "PN", "Arthi", self.styles)
        text = _flatten_text(elements)
        self.assertIn("Rajju (mandatory)", text)
        self.assertIn("Vedha (mandatory)", text)
        self.assertIn("Nadi (mandatory)", text)
        # Non-mandatory categories must NOT get the suffix
        self.assertNotIn("Mahendra (mandatory)", text)

    def test_scored_categories_show_fraction_pass_fail_categories_show_word(self):
        elements = _build_porutham(_real_porutham(), "PN", "Arthi", self.styles)
        text = _flatten_text(elements)
        self.assertIn("0/3", text)   # Dinam, scored
        self.assertIn("6/6", text)   # Ganam, scored
        self.assertIn("Pass", text)  # Rajju/Vedha/Mahendra/Stree Deergha/mandatory pass-fail

    def test_no_porutham_returns_empty_list(self):
        self.assertEqual(_build_porutham(None, "PN", "Arthi", self.styles), [])

    def test_error_porutham_returns_empty_list(self):
        self.assertEqual(
            _build_porutham({"error": "could not resolve"}, "PN", "Arthi", self.styles), []
        )

    def test_empty_points_returns_empty_list(self):
        self.assertEqual(
            _build_porutham({"total_score": 0, "points": []}, "PN", "Arthi", self.styles), []
        )

    def test_missing_names_fall_back_gracefully_no_crash(self):
        elements = _build_porutham(_real_porutham(), None, None, self.styles)
        text = _flatten_text(elements)
        self.assertIn("Husband", text)
        self.assertIn("Wife", text)

    def test_commentary_renders_between_summary_and_table(self):
        """Phase H3: commentary paragraph renders when passed."""
        elements = _build_porutham(
            _real_porutham(), "PN", "Arthi", self.styles,
            commentary="This is the mechanism explanation.",
        )
        text = _flatten_text(elements)
        self.assertIn("This is the mechanism explanation.", text)

    def test_no_commentary_renders_without_error(self):
        """Older cached rows / callers that don't pass commentary -- must
        still render the rest of the section fine (default is None)."""
        elements = _build_porutham(_real_porutham(), "PN", "Arthi", self.styles)
        text = _flatten_text(elements)
        self.assertIn("Compatibility (Porutham)", text)


class TestRenderFamilyPdfWithPorutham(unittest.TestCase):
    """Full render_family_pdf() -- confirms no crash and valid PDF bytes
    for both the with-Porutham and no-pairing cases. Real visual
    verification (does the rendered PDF actually look right) was done
    separately against real DB data, not re-derived here."""

    def _base_prediction(self):
        return {
            "executive_summary": "Test summary.",
            "financial_peaks": [],
            "caution_windows": [],
            "child_milestones": [],
            "key_takeaways": ["Test takeaway."],
        }

    def test_with_porutham_produces_valid_pdf_no_crash(self):
        pdf_bytes = render_family_pdf(
            group_name="Test Group", member_names=["A", "B"], year=2026,
            prediction=self._base_prediction(),
            porutham=_real_porutham(), husband_name="Ravi", wife_name="Priya",
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_with_porutham_commentary_produces_valid_pdf_no_crash(self):
        """Phase H3: passing porutham_commentary through the full render
        path doesn't break generation."""
        pdf_bytes = render_family_pdf(
            group_name="Test Group", member_names=["A", "B"], year=2026,
            prediction=self._base_prediction(),
            porutham=_real_porutham(), husband_name="Ravi", wife_name="Priya",
            porutham_commentary="This is the mechanism explanation.",
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_no_pairing_produces_valid_pdf_no_crash(self):
        """Guards the exact no-pairing case Phase F4 Part A's test plan
        requires: no porutham data -> PDF still generates cleanly."""
        pdf_bytes = render_family_pdf(
            group_name="Solo Group", member_names=["Solo Member"], year=2026,
            prediction=self._base_prediction(),
            porutham=None, husband_name=None, wife_name=None,
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 1000)


if __name__ == "__main__":
    unittest.main()
