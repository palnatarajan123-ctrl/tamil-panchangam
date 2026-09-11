# tests/api/test_monthly_fallback_cache.py
"""
Follow-up to Issue 2 (2026-09-11): a fallback result (fallback_reason
set -- e.g. "prompt_too_large") was being cached in monthly_predictions
and served identically to a real one. Once a chart+period combo hit ANY
fallback, it stayed stuck showing that exact fallback content -- and its
ORIGINAL timestamp -- forever, even after the underlying cause was fixed
(the token-limit raise, commit 0152787), because generate_monthly_
prediction()'s cache-hit branch never distinguished "done, real result"
from "done, only because generation failed."

Confirmed against real data, not assumed: a stale row from before that
fix (base_chart_id 11656fc5-..., created 2026-09-11 17:34:58,
fallback_reason="prompt_too_large") was still being served hours after
the fix was deployed and confirmed live on prod (git_sha matched
origin/main HEAD exactly). Re-requesting it after this fix now correctly
re-attempts generation and, moments later, produces a real
ai-interpretation-v7.0 result (verified live: 16058 tokens_used,
provider="anthropic", fallback_reason=None) -- the row is genuinely
self-healed, not just re-labeled.

Also covers get_monthly_llm_status()'s companion fix: it previously
returned "ready" based on llm_interpretation's mere PRESENCE, which a
stale fallback row already satisfies (the fallback content IS
llm_interpretation) -- so polling would report "ready" immediately after
a retry was kicked off, before the retry had actually finished, and the
frontend would stop polling and briefly redisplay the still-stale
content. Found live while verifying the cache fix above, fixed in the
same pass since it's directly adjacent and cheap.

Real TestClient + dependency_overrides, per the pattern established in
test_admin_llm_auth.py / test_ownership_sweep.py.
"""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user

TEST_USER = {"id": "user-a-id", "email": "usera@test.com", "name": "User A", "role": "user"}

MINIMAL_CHART = {
    "locked": True,
    "payload": {
        "birth_details": {"name": "Test", "latitude": 13.08, "longitude": 80.27},
        "ephemeris": {"moon": {"nakshatra": {"index": 3}}},
        "upagrahas": {"gulika": "House 8"},          # truthy -- skip lazy backfill
        "yogas": {"yogas": [{"name": "Test Yoga"}]},  # truthy -- skip lazy backfill
        "predictive_signals": {"computed_for": "2026-09"},  # matches test period -- skip lazy recompute
    },
}


def _existing_row(fallback_reason):
    """A cached monthly_predictions row shaped like a real one, with a
    controllable llm_metadata.fallback_reason."""
    envelope = {
        "dasha_context": {"maha_lord": "Mercury", "antar_lord": "Rahu"},
        "calculation_confidence": {"level": "high", "cusp_cases": []},
    }
    synthesis = {"confidence": {"overall": 0.6, "variance": 0.0}, "life_areas": {}}
    interpretation = {
        "ai_interpretation": {"engine_version": "ai-interpretation-v1.0", "window_summary": {}},
        "llm_interpretation": {"engine_version": "ai-interpretation-v1.0"},
        "llm_metadata": {
            "model": None, "provider": "none", "tokens_used": 0,
            "prompt_version": "v7", "fallback_reason": fallback_reason,
        },
    }
    return {"envelope": envelope, "synthesis": synthesis, "interpretation": interpretation}


class TestStaleFallbackCacheSelfHeals(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: TEST_USER

    def tearDown(self):
        app.dependency_overrides.pop(get_current_user, None)

    def _post_monthly(self):
        return self.client.post(
            "/api/prediction/monthly",
            json={"base_chart_id": "chart-1", "year": 2026, "month": 9},
        )

    def test_fallback_tagged_cache_hit_retries_instead_of_re_serving(self):
        with patch("app.api.prediction.get_base_chart_by_id", return_value=MINIMAL_CHART), \
             patch("app.api.prediction.user_owns_chart", return_value=True), \
             patch("app.api.prediction.get_monthly_prediction",
                   return_value=_existing_row(fallback_reason="prompt_too_large")), \
             patch("app.api.prediction.is_llm_enabled", return_value=True), \
             patch("app.api.prediction._run_llm_background") as mock_bg:
            resp = self._post_monthly()

        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["llm_status"], "pending")
        mock_bg.assert_called_once()
        _, kwargs = mock_bg.call_args
        self.assertEqual(kwargs["base_chart_id"], "chart-1")
        self.assertEqual(kwargs["year"], 2026)
        self.assertEqual(kwargs["month"], 9)

    def test_real_cached_result_is_not_retried(self):
        """No regression: a genuinely successful cached result (no
        fallback_reason) must still be served as final, not re-triggered
        every time -- that's the whole point of caching."""
        with patch("app.api.prediction.get_base_chart_by_id", return_value=MINIMAL_CHART), \
             patch("app.api.prediction.user_owns_chart", return_value=True), \
             patch("app.api.prediction.get_monthly_prediction",
                   return_value=_existing_row(fallback_reason=None)), \
             patch("app.api.prediction.is_llm_enabled", return_value=True), \
             patch("app.api.prediction._run_llm_background") as mock_bg:
            resp = self._post_monthly()

        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertIsNone(resp.json()["llm_status"])
        mock_bg.assert_not_called()

    def test_llm_disabled_fallback_retries_once_llm_is_re_enabled(self):
        """No special-casing of "llm_disabled" -- a chart cached while
        LLM was administratively off should get a fresh attempt the
        moment an admin re-enables it, same as any other fallback
        reason. Deliberately NOT matching _check_cache()'s own
        (lower-level, out of scope here) special treatment of this one
        reason as always-final."""
        with patch("app.api.prediction.get_base_chart_by_id", return_value=MINIMAL_CHART), \
             patch("app.api.prediction.user_owns_chart", return_value=True), \
             patch("app.api.prediction.get_monthly_prediction",
                   return_value=_existing_row(fallback_reason="llm_disabled")), \
             patch("app.api.prediction.is_llm_enabled", return_value=True), \
             patch("app.api.prediction._run_llm_background") as mock_bg:
            resp = self._post_monthly()

        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["llm_status"], "pending")
        mock_bg.assert_called_once()

    def test_no_retry_when_llm_still_administratively_disabled(self):
        """Don't spawn a pointless background task if LLM is still off
        globally -- it would just fail again immediately for the same
        reason. Covers both a transient fallback reason and
        "llm_disabled" itself, since neither should retry while genuinely
        still disabled."""
        for fallback_reason in ("prompt_too_large", "llm_disabled"):
            with self.subTest(fallback_reason=fallback_reason):
                with patch("app.api.prediction.get_base_chart_by_id", return_value=MINIMAL_CHART), \
                     patch("app.api.prediction.user_owns_chart", return_value=True), \
                     patch("app.api.prediction.get_monthly_prediction",
                           return_value=_existing_row(fallback_reason=fallback_reason)), \
                     patch("app.api.prediction.is_llm_enabled", return_value=False), \
                     patch("app.api.prediction._run_llm_background") as mock_bg:
                    resp = self._post_monthly()

                self.assertEqual(resp.status_code, 200, resp.text)
                self.assertIsNone(resp.json()["llm_status"])
                mock_bg.assert_not_called()


class TestMonthlyLlmStatusFallbackAware(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: TEST_USER

    def tearDown(self):
        app.dependency_overrides.pop(get_current_user, None)

    def _status(self):
        return self.client.get(
            "/api/prediction/monthly/llm-status",
            params={"base_chart_id": "chart-1", "year": 2026, "month": 9},
        )

    def test_stale_fallback_reports_pending_not_ready(self):
        with patch("app.api.prediction.user_owns_chart", return_value=True), \
             patch("app.api.prediction.get_conn"), \
             patch("app.api.prediction.get_monthly_prediction",
                   return_value=_existing_row(fallback_reason="prompt_too_large")):
            resp = self._status()
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["status"], "pending")

    def test_real_result_reports_ready(self):
        with patch("app.api.prediction.user_owns_chart", return_value=True), \
             patch("app.api.prediction.get_conn"), \
             patch("app.api.prediction.get_monthly_prediction",
                   return_value=_existing_row(fallback_reason=None)):
            resp = self._status()
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["status"], "ready")

    def test_llm_disabled_fallback_reports_pending_not_ready(self):
        """Not special-cased as ready, deliberately -- see this route's
        own docstring for why: the POST endpoint may retry an
        llm_disabled-tagged row too (once LLM is re-enabled), and this
        endpoint reporting "ready" early for that reason specifically
        would reintroduce the exact race just fixed, just for one
        reason string instead of all of them. Unreachable via the
        frontend's own flow unless a retry is genuinely in flight (see
        docstring) -- checking it here as a direct unit test regardless,
        for the contract this function promises on its own terms."""
        with patch("app.api.prediction.user_owns_chart", return_value=True), \
             patch("app.api.prediction.get_conn"), \
             patch("app.api.prediction.get_monthly_prediction",
                   return_value=_existing_row(fallback_reason="llm_disabled")):
            resp = self._status()
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["status"], "pending")


class TestNoLlmCallWhileGloballyDisabled(unittest.TestCase):
    """Part A (2026-09-11 follow-up): the definitive proof requested --
    with the global flag OFF, hitting a fallback-tagged cached row
    repeatedly must never result in any LLM call, spied on at the actual
    LLM-calling function (not just the background-task wrapper one layer
    up, for a more direct guarantee than trusting _run_llm_background's
    own internal gate alone). Flipping the flag ON must then trigger
    exactly one regeneration attempt on the next request -- proving the
    fix is specifically "don't retry while disabled", not "never retry
    a fallback at all" (that part of the original fix must be preserved).
    """

    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: TEST_USER

    def tearDown(self):
        app.dependency_overrides.pop(get_current_user, None)

    def _post_monthly(self):
        return self.client.post(
            "/api/prediction/monthly",
            json={"base_chart_id": "chart-1", "year": 2026, "month": 9},
        )

    def test_disabled_then_enabled_across_repeated_requests(self):
        with patch("app.api.prediction.get_base_chart_by_id", return_value=MINIMAL_CHART), \
             patch("app.api.prediction.user_owns_chart", return_value=True), \
             patch("app.api.prediction.get_monthly_prediction",
                   return_value=_existing_row(fallback_reason="prompt_too_large")), \
             patch("app.engines.llm_interpretation_orchestrator.openai_provider.call_openai") as mock_call_llm, \
             patch("app.api.prediction.is_llm_enabled", return_value=False):
            # Repeated requests, flag OFF -- the actual LLM-calling
            # function must never be invoked, not once, across any of them.
            for _ in range(3):
                resp = self._post_monthly()
                self.assertEqual(resp.status_code, 200, resp.text)
                self.assertIsNone(resp.json()["llm_status"])
            mock_call_llm.assert_not_called()

            # Flip the flag ON (same test, same mocked cache row still
            # tagged as a stale fallback) -- the very next request must
            # now trigger exactly one regeneration attempt.
            with patch("app.api.prediction.is_llm_enabled", return_value=True), \
                 patch("app.api.prediction._run_llm_background") as mock_bg:
                resp = self._post_monthly()
                self.assertEqual(resp.status_code, 200, resp.text)
                self.assertEqual(resp.json()["llm_status"], "pending")
                mock_bg.assert_called_once()

            # Still zero real LLM calls in this test -- _run_llm_background
            # itself was mocked for the enabled case above (isolating the
            # gate/scheduling decision from the full generation pipeline,
            # which is exercised for real elsewhere, live, in this
            # investigation -- see this file's module docstring).
            mock_call_llm.assert_not_called()


class TestFreshGenerationWhileDisabledIsTaggedNotSilent(unittest.TestCase):
    """Found live during the 2026-09-11 closing-pass verification (with
    real Anthropic billing restored, testing the disabled-admin-toggle
    path end to end for the first time against a genuinely NEW chart+
    period): a brand-new chart+period generated for the FIRST time while
    LLM was administratively off returned 200 with real computed data but
    interpretation.llm_metadata entirely UNSET -- not even
    fallback_reason="llm_disabled". Every earlier test of the disabled
    path (this file, test_is_llm_enabled_consolidation.py) reused an
    ALREADY-cache-hit row, which always has this key once
    generate_llm_interpretation() has run on it at least once -- this
    fresh-generation branch skips calling that function entirely when
    disabled, so it never got tagged. No signal meant no banner could
    show on the frontend -- silently ambiguous, exactly the class of gap
    Part A was about, just in a code path not exercised by the fallback-
    retry tests above. Also matters for the retry trigger itself: without
    this tag, a later re-fetch of this same row wouldn't recognize it as
    disabled-not-real either.
    """

    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: TEST_USER

    def tearDown(self):
        app.dependency_overrides.pop(get_current_user, None)

    def test_fresh_generation_while_disabled_tags_llm_disabled(self):
        envelope = {
            "dasha_context": {"maha_lord": "Mercury", "antar_lord": "Rahu"},
            "calculation_confidence": {"level": "high", "cusp_cases": []},
        }
        synthesis = {"confidence": {"overall": 0.6, "variance": 0.0}, "life_areas": {}}
        ai_interp = {"engine_version": "ai-interpretation-v1.0", "window_summary": {"momentum": "steady"}}
        explainability_mock = MagicMock()
        explainability_mock.model_dump.return_value = {}

        with patch("app.api.prediction.get_base_chart_by_id", return_value=MINIMAL_CHART), \
             patch("app.api.prediction.user_owns_chart", return_value=True), \
             patch("app.api.prediction.get_monthly_prediction", return_value=None), \
             patch("app.api.prediction.is_llm_enabled", return_value=False), \
             patch("app.api.prediction.build_monthly_prediction_envelope", return_value=envelope), \
             patch("app.api.prediction.synthesize_from_envelope", return_value=synthesis), \
             patch("app.api.prediction.build_interpretation_from_synthesis",
                   return_value={"interpretation": {}}), \
             patch("app.api.prediction.generate_ai_interpretation", return_value=ai_interp), \
             patch("app.api.prediction.paraphrase_interpretation", side_effect=lambda x: x), \
             patch("app.api.prediction.apply_explainability", side_effect=lambda x, _: x), \
             patch("app.api.prediction.assess_calculation_confidence",
                   return_value={"level": "high", "cusp_cases": []}), \
             patch("app.api.prediction.build_explainability", return_value=explainability_mock), \
             patch("app.api.prediction.save_monthly_prediction") as mock_save, \
             patch("app.api.prediction._run_llm_background") as mock_bg:
            resp = self.client.post(
                "/api/prediction/monthly",
                json={"base_chart_id": "chart-1", "year": 2026, "month": 9},
            )

        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertIsNone(body["llm_status"])
        interp = body["details"]["interpretation"]
        self.assertEqual(interp["llm_metadata"]["fallback_reason"], "llm_disabled")
        mock_bg.assert_not_called()

        # The persisted row must ALSO carry this tag, not just the
        # in-memory response -- otherwise a later re-fetch of this exact
        # row (the cache-hit branch) would see no fallback_reason at all
        # and neither show the paused banner nor recognize it as
        # retry-eligible once re-enabled.
        _, save_kwargs = mock_save.call_args
        saved_interpretation = save_kwargs.get("interpretation")
        self.assertEqual(
            saved_interpretation["llm_metadata"]["fallback_reason"], "llm_disabled"
        )


if __name__ == "__main__":
    unittest.main()
