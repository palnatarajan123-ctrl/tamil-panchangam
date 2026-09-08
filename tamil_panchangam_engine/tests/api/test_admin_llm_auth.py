# tests/api/test_admin_llm_auth.py
"""
admin_llm.py's entire route set had ZERO auth dependency of any kind --
not even get_current_user, let alone require_admin -- found during an
unrelated frontend-auth-bug investigation, 2026-09-08. /toggle could
disable the LLM feature for every user, /budget could change the spend
cap, /clear-cache could wipe prediction_llm_interpretation entirely
(no base_chart_id = delete every row), all callable by anyone, no login
required.

This file is the ONLY place in the whole test suite that uses FastAPI's
TestClient rather than calling route handler functions directly -- and
that's deliberate, not a style choice: every other test file in this repo
calls handlers as plain Python functions with pre-supplied arguments,
which BYPASSES Depends() resolution entirely (the same interpretation.py
gotcha found earlier this session) and so cannot actually prove an auth
dependency is wired up. Testing "does this route require admin" requires
going through real route dispatch.

get_conn is mocked for the admin-authorized case on every route that
touches the DB, so these tests never read or write real data -- the
toggle/budget/clear-cache routes especially must never run for real
against a live database in an automated test.
"""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user, require_admin


ADMIN_USER = {"id": "test-admin-id", "email": "admin@test.com", "role": "admin"}
NON_ADMIN_USER = {"id": "test-user-id", "email": "user@test.com", "role": "user"}

# (method, path, json_body) for every admin_llm.py route
ROUTES = [
    ("GET", "/api/admin/llm/status", None),
    ("GET", "/api/admin/llm/usage/monthly", None),
    ("GET", "/api/admin/llm/usage/recent", None),
    ("GET", "/api/admin/llm/fallback-summary", None),
    ("POST", "/api/admin/llm/toggle", {"enabled": True}),
    ("GET", "/api/admin/llm/summary", None),
    ("GET", "/api/admin/llm/calls", None),
    ("POST", "/api/admin/llm/budget", {"monthly_budget_usd": 100.0}),
    ("POST", "/api/admin/llm/clear-cache", {}),
]


def _cm(mock_conn):
    """Wrap a MagicMock as a context manager, matching get_conn()'s `with` usage."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_conn)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _mock_conn_for(path: str) -> MagicMock:
    """Build a mock DB connection whose .fetchone()/.fetchall() return
    shapes matching what each route expects, so the admin-authorized case
    reaches a real 2xx instead of a 500 from unpacking a MagicMock."""
    conn = MagicMock()
    if path in ("/api/admin/llm/usage/recent", "/api/admin/llm/fallback-summary"):
        conn.execute.return_value.fetchall.return_value = []
    elif path == "/api/admin/llm/calls":
        conn.execute.return_value.fetchall.return_value = []
        conn.execute.return_value.fetchone.return_value = (0,)
    elif path == "/api/admin/llm/clear-cache":
        conn.execute.return_value.fetchone.return_value = (0,)
    return conn


class TestAdminLLMRequiresAuth(unittest.TestCase):
    """Every route: no auth -> 401, non-admin -> 403."""

    def setUp(self):
        self.client = TestClient(app)

    def _call(self, method, path, json_body):
        if method == "GET":
            return self.client.get(path)
        return self.client.post(path, json=json_body)

    def test_no_auth_returns_401_on_every_route(self):
        for method, path, body in ROUTES:
            with self.subTest(route=f"{method} {path}"):
                resp = self._call(method, path, body)
                self.assertEqual(
                    resp.status_code, 401,
                    f"{method} {path} should 401 with no auth, got {resp.status_code}: {resp.text}",
                )

    def test_non_admin_returns_403_on_every_route(self):
        app.dependency_overrides[get_current_user] = lambda: NON_ADMIN_USER
        try:
            for method, path, body in ROUTES:
                with self.subTest(route=f"{method} {path}"):
                    resp = self._call(method, path, body)
                    self.assertEqual(
                        resp.status_code, 403,
                        f"{method} {path} should 403 for a non-admin, got {resp.status_code}: {resp.text}",
                    )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_admin_passes_the_auth_gate_on_every_route(self):
        """Not necessarily 200 -- some routes' downstream logic may still
        fail against a mocked connection -- but never 401/403, proving the
        auth dependency itself resolves correctly for a real admin."""
        app.dependency_overrides[require_admin] = lambda: ADMIN_USER
        try:
            for method, path, body in ROUTES:
                with self.subTest(route=f"{method} {path}"):
                    mock_conn = _mock_conn_for(path)
                    with patch("app.api.admin_llm.get_conn", return_value=_cm(mock_conn)):
                        resp = self._call(method, path, body)
                    self.assertNotIn(
                        resp.status_code, (401, 403),
                        f"{method} {path} should pass auth for a real admin, got {resp.status_code}: {resp.text}",
                    )
        finally:
            app.dependency_overrides.pop(require_admin, None)


if __name__ == "__main__":
    unittest.main()
