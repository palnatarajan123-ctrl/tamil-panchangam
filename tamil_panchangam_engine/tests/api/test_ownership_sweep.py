# tests/api/test_ownership_sweep.py
"""
Task 2 Part B (backlog #2, 2026-09-10): ownership tests using the same
TestClient + app.dependency_overrides pattern as test_admin_llm_auth.py --
the only pattern that actually exercises Depends() resolution instead of
calling route handlers as plain Python functions (see that file's
docstring for why the latter can't prove auth/ownership wiring works).

Covers, per the task list:
  - GET /api/base-chart/{id} and /api/base-chart/birth-chart
  - prediction endpoints keyed by chart id: monthly/weekly/yearly
  - GET /api/prospects/{id}/porutham
  - GET /api/family/groups/{group_id} (confirming the existing 404 fix,
    not re-fixing it)

Every one of these is expected to return 404 (not 403) for a resource
that exists but isn't the caller's -- the project's "don't reveal
existence to a non-owner" policy, applied consistently across all of
them in the 2026-09-08/09 security-hardening commits this test locks in.

The user identity never changes between the "non-owner" and "owner"
cases below (same TEST_USER is logged in throughout) -- what changes is
which account the DB says actually owns the resource, exactly mirroring
how the real check works (row ownership, not caller identity).

For the three prediction routes (monthly/weekly/yearly), only the
ownership gate is verified, not a full 200 -- reaching a genuine success
response requires mocking an entire ephemeris/synthesis/LLM pipeline
downstream of the gate, which is out of scope for an auth test and
already has its own engine-level test coverage elsewhere. Each "owner"
test asserts exactly 500, not a loose "not in (401,403,404)" -- verified
with raise_server_exceptions=True that all three fail identically with
KeyError: 'birth_details' from build_monthly_prediction_envelope() (and
its weekly/yearly equivalents), three call-frames past each route's own
ownership gate, purely because the mock payload here is the bare string
"{}". Pinning the exact code means a later change that makes these fail
differently -- or succeed outright against richer mock data -- breaks
these tests loudly instead of silently passing for the wrong reason.
TestClient is constructed with raise_server_exceptions=False for those
three so the error surfaces as a response status to assert on, rather
than crashing the test itself.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user

TEST_USER = {"id": "user-a-id", "email": "usera@test.com", "name": "User A", "role": "user"}


def _cm(mock_conn):
    """Wrap a MagicMock as a context manager, matching get_conn()'s `with` usage."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_conn)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _conn_returning(*, fetchone=None, fetchall=None):
    """A single mock connection where every .execute(...) call returns the
    same canned .fetchone()/.fetchall() values -- fine wherever a route
    only ever needs one shape of result regardless of how many statements
    it runs (e.g. all SELECTs return the same "no rows" for a not-found
    lookup)."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = fetchone
    conn.execute.return_value.fetchall.return_value = fetchall or []
    return conn


def _conn_sequence(*results):
    """A mock connection whose successive .execute(...) calls each return
    the next pre-built result mock, in order -- for routes that run
    several different queries needing different shapes back."""
    conn = MagicMock()
    conn.execute.side_effect = list(results)
    return conn


def _result(*, fetchone=None, fetchall=None):
    r = MagicMock()
    r.fetchone.return_value = fetchone
    r.fetchall.return_value = fetchall or []
    return r


class OwnershipTestBase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: TEST_USER

    def tearDown(self):
        app.dependency_overrides.pop(get_current_user, None)


class TestBaseChartOwnership(OwnershipTestBase):
    """GET /api/base-chart/{id} and GET /api/base-chart/birth-chart."""

    def setUp(self):
        super().setUp()
        from app.models.schema import BASE_CHART_STORE
        self._store = BASE_CHART_STORE
        self._store["chart-owned"] = {
            "id": "chart-owned",
            "checksum": "abc123",
            "locked": True,
            "created_at": datetime.now(timezone.utc),
            # empty ephemeris/functional_roles so the GET /{id} route's
            # on-the-fly recompute branch is a no-op, not an engine call.
            "data": {"functional_roles": {}, "ephemeris": {}},
            "fingerprint": "fp1",
        }

    def tearDown(self):
        super().tearDown()
        self._store.pop("chart-owned", None)

    def test_get_by_id_non_owner_gets_404(self):
        with patch("app.api.base_chart.user_owns_chart", return_value=False):
            resp = self.client.get("/api/base-chart/chart-owned")
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_get_by_id_owner_gets_200(self):
        with patch("app.api.base_chart.user_owns_chart", return_value=True):
            resp = self.client.get("/api/base-chart/chart-owned")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["id"], "chart-owned")

    def test_get_by_id_nonexistent_chart_gets_404_before_ownership_check(self):
        with patch("app.api.base_chart.user_owns_chart", return_value=True):
            resp = self.client.get("/api/base-chart/does-not-exist")
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_birth_chart_non_owner_gets_404(self):
        with patch("app.api.base_chart.get_base_chart_by_id", return_value={"payload": "{}"}), \
             patch("app.api.base_chart.user_owns_chart", return_value=False):
            resp = self.client.get("/api/base-chart/birth-chart", params={"base_chart_id": "chart-owned"})
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_birth_chart_owner_gets_200(self):
        with patch("app.api.base_chart.get_base_chart_by_id", return_value={"payload": "{}"}), \
             patch("app.api.base_chart.user_owns_chart", return_value=True), \
             patch("app.api.base_chart.build_birth_chart_view_model", return_value={"stub": True}):
            resp = self.client.get("/api/base-chart/birth-chart", params={"base_chart_id": "chart-owned"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"view": {"stub": True}})


class TestPredictionOwnership(unittest.TestCase):
    """POST /api/prediction/{monthly,weekly,yearly} -- ownership gate only
    (see module docstring for why not a full 200)."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        app.dependency_overrides[get_current_user] = lambda: TEST_USER

    def tearDown(self):
        app.dependency_overrides.pop(get_current_user, None)

    def test_monthly_non_owner_gets_404(self):
        with patch("app.api.prediction.get_base_chart_by_id", return_value={"locked": True, "payload": "{}"}), \
             patch("app.api.prediction.user_owns_chart", return_value=False):
            resp = self.client.post(
                "/api/prediction/monthly",
                json={"base_chart_id": "chart-x", "year": 2026, "month": 1},
            )
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_monthly_owner_passes_ownership_gate(self):
        # Pinned to exactly 500, not a loose "not in (401,403,404)" -- verified
        # with raise_server_exceptions=True that this is a KeyError:
        # 'birth_details' raised from build_monthly_prediction_envelope()
        # (app/engines/prediction_envelope.py:98), reached via
        # generate_monthly_prediction() at app/api/prediction.py:334 -- three
        # layers past the ownership gate at prediction.py:150-158, purely
        # because the mock payload here is the bare string "{}". Pinning the
        # exact code means a future change that makes this fail differently
        # (or unexpectedly succeeds against better mock data) breaks this
        # test loudly instead of silently passing for the wrong reason.
        with patch("app.api.prediction.get_base_chart_by_id", return_value={"locked": True, "payload": "{}"}), \
             patch("app.api.prediction.user_owns_chart", return_value=True):
            resp = self.client.post(
                "/api/prediction/monthly",
                json={"base_chart_id": "chart-x", "year": 2026, "month": 1},
            )
        self.assertEqual(resp.status_code, 500, resp.text)

    def test_weekly_non_owner_gets_404(self):
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: MagicMock()
        try:
            with patch("app.api.prediction_weekly.user_owns_chart", return_value=False):
                resp = self.client.post(
                    "/api/prediction/weekly",
                    json={"base_chart_id": "chart-x", "year": 2026, "week": 1},
                )
            self.assertEqual(resp.status_code, 404, resp.text)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_weekly_owner_passes_ownership_gate(self):
        # Pinned to exactly 500 -- same KeyError: 'birth_details' as monthly
        # (see that test's comment), verified with raise_server_exceptions=True:
        # reached via the envelope-building layer, well past this route's
        # ownership gate.
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: MagicMock()
        try:
            with patch("app.api.prediction_weekly.user_owns_chart", return_value=True), \
                 patch("app.api.prediction_weekly.get_base_chart_by_id",
                       return_value={"locked": True, "payload": "{}"}):
                resp = self.client.post(
                    "/api/prediction/weekly",
                    json={"base_chart_id": "chart-x", "year": 2026, "week": 1},
                )
            self.assertEqual(resp.status_code, 500, resp.text)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_yearly_non_owner_gets_404(self):
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: MagicMock()
        try:
            with patch("app.api.prediction_yearly.get_base_chart_by_id",
                       return_value={"locked": True, "payload": "{}"}), \
                 patch("app.api.prediction_yearly.user_owns_chart", return_value=False):
                resp = self.client.post(
                    "/api/prediction/yearly",
                    json={"base_chart_id": "chart-x", "year": 2026},
                )
            self.assertEqual(resp.status_code, 404, resp.text)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_yearly_owner_passes_ownership_gate(self):
        # Pinned to exactly 500 -- same KeyError: 'birth_details' as monthly
        # (see that test's comment), verified with raise_server_exceptions=True:
        # reached via the envelope-building layer, well past this route's
        # ownership gate.
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: MagicMock()
        try:
            with patch("app.api.prediction_yearly.get_base_chart_by_id",
                       return_value={"locked": True, "payload": "{}"}), \
                 patch("app.api.prediction_yearly.user_owns_chart", return_value=True):
                resp = self.client.post(
                    "/api/prediction/yearly",
                    json={"base_chart_id": "chart-x", "year": 2026},
                )
            self.assertEqual(resp.status_code, 500, resp.text)
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestProspectOwnership(OwnershipTestBase):
    """GET /api/prospects/{id}/porutham."""

    def test_non_owner_gets_404(self):
        # row: (id, user_id, source_chart_id, candidate_chart_id, source_role, result_json)
        row = ("prospect-1", "someone-else-id", "chart-a", "chart-b", "boy", None)
        conn = _conn_returning(fetchone=row)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            resp = self.client.get("/api/prospects/prospect-1/porutham")
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_nonexistent_prospect_gets_404(self):
        conn = _conn_returning(fetchone=None)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            resp = self.client.get("/api/prospects/does-not-exist/porutham")
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_owner_gets_200(self):
        # Pre-cached result_json means _get_or_compute_prospect_porutham()
        # returns it directly with no chart lookups needed.
        cached_result = {
            "boy": {"chart_id": "chart-a", "name": "A", "nakshatra": "Aswini", "rasi": "Mesha"},
            "girl": {"chart_id": "chart-b", "name": "B", "nakshatra": "Bharani", "rasi": "Mesha"},
            "porutham": {"total_score": 8, "max_score": 10, "grade": "Good"},
            "commentary": "stub",
        }
        row = ("prospect-1", TEST_USER["id"], "chart-a", "chart-b", "boy", cached_result)
        conn = _conn_returning(fetchone=row)
        with patch("app.api.prospects.get_conn", return_value=_cm(conn)):
            resp = self.client.get("/api/prospects/prospect-1/porutham")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["porutham"]["grade"], "Good")


class TestFamilyGroupOwnership(OwnershipTestBase):
    """GET /api/family/groups/{group_id} -- confirming the existing
    security-fix 404 behavior (see family.py's _assert_group_owner
    docstring), not re-fixing it."""

    def test_non_owner_gets_404(self):
        # row: (id, user_id, name, primary_chart_id, created_at, updated_at)
        group_row = ("group-1", "someone-else-id", "Their Family", None, "2026-01-01", "2026-01-01")
        conn = _conn_returning(fetchone=group_row)
        with patch("app.api.family.get_conn", return_value=_cm(conn)):
            resp = self.client.get("/api/family/groups/group-1")
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_nonexistent_group_gets_404(self):
        conn = _conn_returning(fetchone=None)
        with patch("app.api.family.get_conn", return_value=_cm(conn)):
            resp = self.client.get("/api/family/groups/does-not-exist")
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_owner_gets_200(self):
        now = datetime.now(timezone.utc)
        group_row = ("group-1", TEST_USER["id"], "My Family", None, now, now)
        conn = _conn_sequence(
            _result(fetchone=group_row),   # _assert_group_owner
            _result(fetchall=[]),          # member_rows (no members)
            _result(fetchone=None),        # _resolve_primary_chart fallback query
        )
        with patch("app.api.family.get_conn", return_value=_cm(conn)):
            resp = self.client.get("/api/family/groups/group-1")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["id"], "group-1")
        self.assertEqual(body["members"], [])


if __name__ == "__main__":
    unittest.main()
