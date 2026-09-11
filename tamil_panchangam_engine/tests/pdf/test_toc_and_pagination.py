# tests/pdf/test_toc_and_pagination.py
"""
Phase 4 of the PDF redesign: page numbers, a running header, and a
table of contents (technical-appendix mode only) for the individual
monthly/yearly report.

_TOCDocTemplate.afterFlowable()'s "which paragraphs become ToC
entries" logic is the one piece of this feature cleanly unit-testable
in isolation -- it's a pure decision (is this a SectionTitle paragraph,
and is it the Contents heading itself) independent of ReportLab's
actual layout engine. The rest of Phase 4.2/4.3 (doc.multiBuild()
correctly resolving page numbers, _NumberedCanvas's two-pass "Page X
of Y" composing correctly with multiBuild's own two-pass ToC
resolution, the ToC actually appearing/not-appearing per toggle state)
is inherently an integration behavior across ReportLab's Platypus
internals -- verified by rendering real charts (v4+ and legacy
branches, both toggle states) and rasterizing the cover/ToC/footer
pages during development, the same way every other layout change in
this redesign was verified, rather than re-created here as a fragile
mock of ReportLab's internal build loop.
"""

import unittest
from unittest.mock import MagicMock

from reportlab.platypus import Paragraph, HRFlowable

from app.pdf.canonical_report.pdf_renderer import _TOCDocTemplate, _create_styles


class TestTOCDocTemplateAfterFlowable(unittest.TestCase):
    def setUp(self):
        self.styles = _create_styles()

    def _doc(self):
        # BaseDocTemplate.__init__ needs a real filename/buffer; afterFlowable
        # doesn't touch layout state, so a throwaway target is fine.
        import io
        doc = _TOCDocTemplate(io.BytesIO())
        doc.notify = MagicMock()
        doc.page = 7
        return doc

    def test_section_title_paragraph_registers_toc_entry(self):
        doc = self._doc()
        para = Paragraph("Life Area Guidance", self.styles['SectionTitle'])
        doc.afterFlowable(para)
        doc.notify.assert_called_once_with('TOCEntry', (0, "Life Area Guidance", 7))

    def test_contents_heading_itself_is_not_registered(self):
        """Otherwise the Contents page would list itself."""
        doc = self._doc()
        para = Paragraph("Contents", self.styles['SectionTitle'])
        doc.afterFlowable(para)
        doc.notify.assert_not_called()

    def test_subsection_title_paragraph_is_not_registered(self):
        doc = self._doc()
        para = Paragraph("Active Dasha Period", self.styles['SubsectionTitle'])
        doc.afterFlowable(para)
        doc.notify.assert_not_called()

    def test_non_paragraph_flowable_is_not_registered(self):
        doc = self._doc()
        doc.afterFlowable(HRFlowable())
        doc.notify.assert_not_called()

    def test_body_text_paragraph_is_not_registered(self):
        doc = self._doc()
        para = Paragraph("Just a regular sentence.", self.styles['BodyText'])
        doc.afterFlowable(para)
        doc.notify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
