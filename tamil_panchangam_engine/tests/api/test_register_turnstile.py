# tests/api/test_register_turnstile.py
"""
Task 3/backlog #1 (2026-09-10): /api/auth/register now requires Cloudflare
Turnstile verification, via the exact same shared verify_turnstile()
implementation base_chart.py's /create already used (app/core/turnstile.py)
-- same DISABLE_TURNSTILE-gated bypass, same "missing token = reject"
behavior, no second copy of the check logic.

Real TestClient, not direct function calls, per the pattern established in
test_admin_llm_auth.py / test_auth_sweep.py -- Depends()/decorator-order
issues wouldn't show up calling register() as a plain function.

Missing-token cases never need to mock get_conn or verify_turnstile's own
network call: `if not token or not verify_turnstile(token)` short-circuits
before the DB or the network are touched at all. Only the "bad token" and
"DISABLE_TURNSTILE bypass" cases mock anything.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def _cm(mock_conn):
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_conn)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


class TestRegisterTurnstile(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Belt-and-suspenders: make sure no ambient DISABLE_TURNSTILE from
        # a local .env leaks into these tests -- each test sets it
        # explicitly where it matters.
        self._env_patch = patch.dict(os.environ, {}, clear=False)
        self._env_patch.start()
        os.environ.pop("DISABLE_TURNSTILE", None)

    def tearDown(self):
        self._env_patch.stop()

    def _register_payload(self, **overrides):
        payload = {
            "email": "newuser@example.com",
            "password": "SuperSecret123",
            "name": "New User",
        }
        payload.update(overrides)
        return payload

    def test_missing_token_rejected_with_403(self):
        resp = self.client.post("/api/auth/register", json=self._register_payload())
        self.assertEqual(resp.status_code, 403, resp.text)
        self.assertIn("CAPTCHA", resp.json()["detail"])

    def test_empty_string_token_rejected_with_403(self):
        resp = self.client.post(
            "/api/auth/register", json=self._register_payload(turnstile_token="")
        )
        self.assertEqual(resp.status_code, 403, resp.text)

    def test_invalid_token_rejected_with_403(self):
        with patch("app.api.auth.verify_turnstile", return_value=False):
            resp = self.client.post(
                "/api/auth/register",
                json=self._register_payload(turnstile_token="bad-token"),
            )
        self.assertEqual(resp.status_code, 403, resp.text)

    def test_valid_token_passes_the_turnstile_gate(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None  # no existing user
        with patch("app.api.auth.verify_turnstile", return_value=True), \
             patch("app.api.auth.get_conn", return_value=_cm(conn)):
            resp = self.client.post(
                "/api/auth/register",
                json=self._register_payload(turnstile_token="good-token"),
            )
        self.assertEqual(resp.status_code, 201, resp.text)
        self.assertIn("access_token", resp.json())

    def test_disable_turnstile_env_flag_bypasses_check_entirely(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        os.environ["DISABLE_TURNSTILE"] = "true"
        try:
            with patch("app.api.auth.verify_turnstile", return_value=False), \
                 patch("app.api.auth.get_conn", return_value=_cm(conn)):
                # verify_turnstile mocked to False -- if the bypass didn't
                # actually skip the check, this would still 403.
                resp = self.client.post(
                    "/api/auth/register",
                    json=self._register_payload(),  # no token at all
                )
        finally:
            os.environ.pop("DISABLE_TURNSTILE", None)
        self.assertEqual(resp.status_code, 201, resp.text)


if __name__ == "__main__":
    unittest.main()
