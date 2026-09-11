# tests/engines/test_budget_guard_user_cap.py
"""
Task 3/backlog #1 (2026-09-10): per-account daily LLM spend cap in
budget_guard.py -- independent of, and in addition to, the existing
global monthly auto-pause (_check_budget()/llm_budget.monthly_budget_usd).

These call check_user_llm_cap()/get_user_daily_spend()/log_llm_call()
directly as plain functions (not via TestClient) -- unlike Task 2's auth
sweep, there's no Depends()/route-dispatch question here: these are
engine-layer functions with no FastAPI dependency injection involved, so
a direct call exercises the real code path.
"""

import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.engines.budget_guard import (
    check_user_llm_cap,
    get_user_daily_spend,
    log_llm_call,
)


def _conn_with(*, cap_row=None, daily_spend=0.0):
    """A mock connection: first .execute() (the llm_budget cap lookup)
    returns cap_row via fetchone(); every subsequent .execute() (the daily
    spend SUM) returns (daily_spend,) via fetchone()."""
    conn = MagicMock()
    cap_result = MagicMock()
    cap_result.fetchone.return_value = cap_row
    spend_result = MagicMock()
    spend_result.fetchone.return_value = (daily_spend,)
    conn.execute.side_effect = [cap_result, spend_result]
    return conn


class TestGetUserDailySpend(unittest.TestCase):
    def test_returns_summed_cost(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (3.4567,)
        spend = get_user_daily_spend(conn, "user-a")
        self.assertAlmostEqual(spend, 3.4567)

    def test_returns_zero_when_no_rows(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (0.0,)
        spend = get_user_daily_spend(conn, "user-with-no-calls")
        self.assertEqual(spend, 0.0)


class TestCheckUserLlmCap(unittest.TestCase):
    def test_under_cap_does_not_raise(self):
        conn = _conn_with(cap_row=(2.0,), daily_spend=1.50)
        check_user_llm_cap(conn, "user-a")  # should not raise

    def test_at_cap_raises_429(self):
        conn = _conn_with(cap_row=(2.0,), daily_spend=2.0)
        with self.assertRaises(HTTPException) as ctx:
            check_user_llm_cap(conn, "user-a")
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("Daily AI usage limit", ctx.exception.detail)

    def test_over_cap_raises_429(self):
        conn = _conn_with(cap_row=(2.0,), daily_spend=5.0)
        with self.assertRaises(HTTPException) as ctx:
            check_user_llm_cap(conn, "user-a")
        self.assertEqual(ctx.exception.status_code, 429)

    def test_missing_budget_row_falls_back_to_default_cap(self):
        # No llm_budget row at all -- falls back to the $2.00 hardcoded
        # default (same value as bootstrap.py's column DEFAULT).
        conn = _conn_with(cap_row=None, daily_spend=5.0)
        with self.assertRaises(HTTPException) as ctx:
            check_user_llm_cap(conn, "user-a")
        self.assertEqual(ctx.exception.status_code, 429)

    def test_budget_lookup_failure_fails_open_not_closed(self):
        """A DB error on the cap lookup itself should not lock every
        account out of every LLM endpoint -- matches _check_budget()'s
        own try/except-and-log-and-continue posture for the global cap."""
        conn = MagicMock()
        conn.execute.side_effect = Exception("db unavailable")
        check_user_llm_cap(conn, "user-a")  # should not raise


class TestLogLlmCallUserId(unittest.TestCase):
    """log_llm_call() also calls _check_budget(db) internally (since
    status defaults to "success"), which runs further conn.execute()
    calls -- so these assertions look at call_args_list[0], the actual
    INSERT, not call_args (the LAST call made)."""

    def test_user_id_is_stored_on_the_insert(self):
        conn = MagicMock()
        log_llm_call(
            conn, chart_id="chart-1", call_type="daily_guidance", period="2026-09-10",
            input_tokens=100, output_tokens=50, user_id="user-a",
        )
        insert_sql, params = conn.execute.call_args_list[0].args
        self.assertIn("user_id", insert_sql)
        self.assertIn("user-a", params)

    def test_user_id_defaults_to_none_for_existing_call_sites(self):
        """Every pre-existing call site omits user_id -- must keep working
        unchanged (backward compatibility, not a breaking signature
        change)."""
        conn = MagicMock()
        log_llm_call(
            conn, chart_id="chart-1", call_type="prediction", period="2026-09",
            input_tokens=100, output_tokens=50,
        )
        _, params = conn.execute.call_args_list[0].args
        self.assertIsNone(params[-1])  # user_id is the last bound param


class TestDailyRouteGracefulDegradation(unittest.TestCase):
    """/api/prediction/daily specifically degrades gracefully when capped
    (200 + llm_guidance: null + llm_capped: true, non-LLM Panchangam data
    intact) rather than hard-429ing like natal_interpretation.py's two
    routes -- a per-account budget cap is the same *kind* of condition as
    the existing is_llm_enabled() global-disable path already degrades
    gracefully from, not an identity/security failure like Turnstile/auth,
    and this route (unlike the natal ones) already computes real non-LLM
    data worth preserving. See _generate_daily_llm_guidance()'s docstring
    in app/api/daily.py for the full reasoning."""

    TEST_USER = {"id": "user-a-id", "email": "a@test.com", "name": "A", "role": "user"}

    def setUp(self):
        from app.main import app
        from app.core.auth import get_current_user
        self.app = app
        self.client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: self.TEST_USER

    def tearDown(self):
        from app.core.auth import get_current_user
        self.app.dependency_overrides.pop(get_current_user, None)

    def _sample_payload(self):
        return {
            "birth_details": {
                "name": "Test Person", "latitude": 13.0827, "longitude": 80.2707,
                "timezone": "Asia/Kolkata",
            },
            "ephemeris": {"moon": {"nakshatra": {"index": 5}, "longitude_deg": 100.0}},
            "chart_metadata": {"ayanamsa": "lahiri"},
        }

    def test_capped_user_gets_200_with_null_guidance_and_intact_panchangam_data(self):
        capped = HTTPException(status_code=429, detail="Daily AI usage limit reached")
        with patch("app.api.daily._get_base_chart_payload", return_value=self._sample_payload()), \
             patch("app.api.daily.get_conn", return_value=MagicMock()), \
             patch("app.engines.budget_guard.check_user_llm_cap", side_effect=capped):
            resp = self.client.get(
                "/api/prediction/daily",
                params={"base_chart_id": "chart-1", "date": "2026-09-10"},
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertIsNone(body["llm_guidance"])
        self.assertTrue(body["llm_capped"])
        # Non-LLM Panchangam data survived the cap -- not discarded.
        self.assertEqual(body["base_chart_id"], "chart-1")
        for key in ("tithi", "nakshatra", "rahu_kaalam", "yamagandam", "gulika_kaalam"):
            self.assertIn(key, body)

    def test_uncapped_user_gets_llm_capped_false(self):
        with patch("app.api.daily._get_base_chart_payload", return_value=self._sample_payload()), \
             patch("app.api.daily.get_conn", return_value=MagicMock()), \
             patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=False):
            # is_llm_enabled=False takes the pre-existing global-disable
            # path (checked first) -- llm_capped must stay False there,
            # not get confused with the new capped path.
            resp = self.client.get(
                "/api/prediction/daily",
                params={"base_chart_id": "chart-1", "date": "2026-09-10"},
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertIsNone(body["llm_guidance"])
        self.assertFalse(body["llm_capped"])


if __name__ == "__main__":
    unittest.main()
