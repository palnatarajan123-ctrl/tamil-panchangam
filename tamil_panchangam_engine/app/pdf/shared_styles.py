# app/pdf/shared_styles.py
"""
Shared PDF styling constants and canvas utilities, used by every PDF
report renderer under app/pdf/ (canonical_report, family_report).

Extracted 2026-09-11 during the PDF redesign's family-report (#3) pass
to fix the root duplication problem Phase 0's inventory identified:
family_report/family_pdf_renderer.py carried its own hand-copied
COLORS dict -- identical in value to canonical_report/config.py's, but
manually kept in sync, not imported -- alongside a header comment
claiming "same card-style layout as canonical_report/pdf_renderer.py"
despite zero actual code sharing. Both renderers now import from here
instead of maintaining independent copies.

Verified this extraction is a pure refactor: rendered the same real
charts/family group before and after and byte-diffed the output --
identical.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdfcanvas

COLORS = {
    "primary": (0.2, 0.15, 0.4),
    "secondary": (0.4, 0.35, 0.5),
    "accent": (0.8, 0.6, 0.2),
    "text": (0.1, 0.1, 0.1),
    "muted": (0.5, 0.5, 0.5),
    "background": (0.98, 0.97, 0.95),
}

MARGIN = 50


class NumberedCanvas(pdfcanvas.Canvas):
    """Standard two-pass "Page X of Y" canvas: showPage() snapshots each
    page's drawing state instead of finalizing it immediately, and
    save() replays every snapshot once the total page count is known,
    stamping the running header + footer onto each page at that point.
    Skips the cover page (page 1) -- it's self-evidently page 1 and
    doesn't need a header repeating its own title back at it.
    """

    def __init__(self, *args, header_text: str = "", **kwargs):
        pdfcanvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self._header_text = header_text

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_decoration(num_pages)
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)

    def _draw_page_decoration(self, page_count: int):
        if self._pageNumber == 1:
            return

        page_width, page_height = A4
        muted = colors.Color(*COLORS["muted"])

        self.setFont('Helvetica', 8)
        self.setFillColor(muted)
        self.drawString(MARGIN, page_height - 32, self._header_text)
        self.setStrokeColor(muted)
        self.setLineWidth(0.5)
        self.line(MARGIN, page_height - 38, page_width - MARGIN, page_height - 38)

        self.setFont('Helvetica', 8)
        self.setFillColor(muted)
        self.drawCentredString(page_width / 2, 28, f"Page {self._pageNumber} of {page_count}")
