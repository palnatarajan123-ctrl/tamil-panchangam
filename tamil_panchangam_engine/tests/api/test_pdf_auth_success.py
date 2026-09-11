# tests/api/test_pdf_auth_success.py
"""
Issue 1 (2026-09-11 regression investigation): PDF generation returned
"Not authenticated" for every user, on every chart, new or existing --
not a chart-state bug, not a backend auth bug. Confirmed via curl with a
genuinely valid, freshly-obtained bearer token that the backend was
correct all along (200, a real PDF) -- the bug was purely client-side:
several PDF buttons used window.open(url), which cannot attach an
Authorization header at all, so the backend always saw an unauthenticated
request. Fixed in prediction-screen.tsx, prospect-detail.tsx (both were
window.open()), and family-prediction-screen.tsx (a bare fetch() that
skipped apiRequest()'s 401-refresh retry).

This file adds the test class that was missing and let the bug through:
test_auth_sweep.py (backlog #2) already proves these routes reject an
UNAUTHENTICATED request -- and still does, nothing here changes that.
What was missing is the mirror case: proving a genuinely AUTHENTICATED,
owning request gets a real 200. A sweep that only asserts "no token ->
rejected" cannot catch a bug where the token is simply never sent by the
frontend -- that is a client-side gap no backend-only test can observe,
sweep or ownership-scoped alike. This file is the backend-side half of
closing that: it proves the route itself is not the problem (matching
what curl already showed), which is exactly the evidence needed to route
this class of bug to "frontend fix", not "backend fix", without guessing.

Real TestClient + dependency_overrides, per the pattern established in
test_admin_llm_auth.py / test_ownership_sweep.py. build_canonical_report()/
build_birth_chart_report() (real ReportLab PDF rendering, needs full
chart/prediction data) are mocked to isolate the auth/ownership gate --
same "not testing business logic, proving the gate resolves" scope as
test_ownership_sweep.py's prediction tests.
"""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user

TEST_USER = {"id": "user-a-id", "email": "usera@test.com", "name": "User A", "role": "user"}


def _cm(mock_conn):
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_conn)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _owns_chart_conn(owned: bool):
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ("row-id",) if owned else None
    return conn


class TestPdfAuthSuccessPath(unittest.TestCase):
    """The success-path counterpart the ownership sweep was missing:
    a genuinely authenticated owner must get a real 200, not just
    'unauthenticated requests get rejected'."""

    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: TEST_USER

    def tearDown(self):
        app.dependency_overrides.pop(get_current_user, None)

    def test_birth_chart_pdf_owner_gets_200_pdf(self):
        with patch("app.api.canonical_report.get_conn", return_value=_cm(_owns_chart_conn(True))), \
             patch("app.api.canonical_report.build_birth_chart_report", return_value=b"%PDF-1.4 fake"):
            resp = self.client.get(
                "/api/reports/birth-chart-pdf", params={"base_chart_id": "chart-1"}
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.headers["content-type"], "application/pdf")
        self.assertEqual(resp.content, b"%PDF-1.4 fake")

    def test_birth_chart_pdf_non_owner_gets_404_not_401(self):
        # Distinguishing this from Issue 1's actual bug matters: a
        # non-owner must be rejected for OWNERSHIP (404), never for
        # missing auth (401) -- a 401 here would mean the token genuinely
        # isn't reaching the route, which is Issue 1's exact symptom.
        with patch("app.api.canonical_report.get_conn", return_value=_cm(_owns_chart_conn(False))):
            resp = self.client.get(
                "/api/reports/birth-chart-pdf", params={"base_chart_id": "chart-1"}
            )
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_reports_pdf_owner_gets_200_pdf(self):
        with patch("app.api.canonical_report.get_conn", return_value=_cm(_owns_chart_conn(True))), \
             patch("app.api.canonical_report.build_canonical_report", return_value=b"%PDF-1.4 fake"):
            resp = self.client.get(
                "/api/reports/pdf",
                params={"base_chart_id": "chart-1", "report_type": "yearly", "year": 2026},
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.headers["content-type"], "application/pdf")

    def test_reports_pdf_missing_auth_gets_401_not_something_else(self):
        # No dependency_override here -- a bare unauthenticated request,
        # same as window.open() sent. Confirms the route itself rejects
        # cleanly (matching the curl evidence) -- the bug was that the
        # frontend never got this far with a token attached at all.
        app.dependency_overrides.pop(get_current_user, None)
        resp = self.client.get(
            "/api/reports/pdf",
            params={"base_chart_id": "chart-1", "report_type": "yearly", "year": 2026},
        )
        self.assertEqual(resp.status_code, 401, resp.text)
        app.dependency_overrides[get_current_user] = lambda: TEST_USER


if __name__ == "__main__":
    unittest.main()
