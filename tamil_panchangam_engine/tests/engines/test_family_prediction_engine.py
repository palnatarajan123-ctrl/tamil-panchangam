# tests/engines/test_family_prediction_engine.py
"""
Tests for family_prediction_engine._build_family_context()'s Phase 1
extension: yogas, upagrahas, kp_sublords, predictive_signals per member.

Audit found this function only read dashas.vimshottari per member — yogas,
upagrahas, kp_sublords, and predictive_signals were computed and stored on
every member's base_chart.payload but never read here, even though the full
payload was already being fetched (no query change needed for this fix).

Payload shapes below are copied from real chart data verified against the
live DB during development, not guessed.
"""

import unittest
from unittest.mock import MagicMock

from app.engines.family_prediction_engine import _build_family_context, PROMPT_VERSION, run_family_prediction


def _base_member(role="husband", name="Test Person", **overrides):
    payload = {
        "birth_details": {"name": name, "date_of_birth": "1980-01-01"},
        "ephemeris": {"moon": {"rasi": "Mesham", "nakshatra": {"name": "Ashwini"}}},
        "dashas": {"vimshottari": {}},
    }
    payload.update(overrides)
    return {"member": {"role": role, "display_name": name}, "payload": payload}


class TestYogasInFamilyContext(unittest.TestCase):
    def test_present_yogas_line_appears(self):
        member = _base_member(yogas={
            "error": None,
            "yogas": [{"name": "Raja Yoga", "present": True}],
            "summary": {"yoga_names": ["Raja Yoga", "Vimala Yoga"], "total_yogas": 2},
        })
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertIn("Present Yogas: Raja Yoga, Vimala Yoga", ctx)

    def test_empty_yogas_dict_no_crash_no_line(self):
        """Real data: some members have payload['yogas'] == {} entirely
        (never computed), not the usual error/yogas/summary shape."""
        member = _base_member(yogas={})
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertNotIn("Present Yogas:", ctx)

    def test_yogas_with_error_set_no_line(self):
        member = _base_member(yogas={"error": "computation failed", "yogas": [], "summary": {}})
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertNotIn("Present Yogas:", ctx)


class TestUpagrahaInFamilyContext(unittest.TestCase):
    def test_gulika_line_appears_with_rasi_and_lord(self):
        member = _base_member(upagrahas={
            "gulika": {"rasi": "Sagittarius", "rasi_lord": "Jupiter", "longitude_deg": 250.0},
            "mandi": {"rasi": "Sagittarius", "rasi_lord": "Jupiter", "longitude_deg": 250.0},
        })
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertIn("Gulika (karmic shadow point): Sagittarius, ruled by Jupiter", ctx)

    def test_no_upagrahas_no_line(self):
        member = _base_member()  # no upagrahas key at all
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertNotIn("Gulika", ctx)


class TestKpSublordsInFamilyContext(unittest.TestCase):
    def test_kp_present_wealth_significators_line_appears(self):
        member = _base_member(kp_sublords={
            "planets": {}, "house_cusps": {},
            "cuspal_significators": {"2": ["Venus", "Saturn"], "11": ["Mercury"]},
        })
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertIn("KP wealth-house significators: Venus, Saturn", ctx)

    def test_kp_none_no_line_no_crash(self):
        """Most charts won't have kp_sublords at all — payload.get() returns
        None, not a missing key. Must not crash on None.get(...)."""
        member = _base_member(kp_sublords=None)
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertNotIn("KP wealth-house", ctx)

    def test_kp_absent_key_no_line_no_crash(self):
        member = _base_member()  # kp_sublords key not present at all
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertNotIn("KP wealth-house", ctx)


class TestPredictiveSignalsInFamilyContext(unittest.TestCase):
    def _ps_member(self, event_windows=None, active_yogas=None):
        return _base_member(predictive_signals={
            "computed_for": "2026-08",
            "active_yogas": active_yogas or [],
            "event_windows": event_windows or [],
        })

    def test_currently_active_yogas_line_appears(self):
        member = self._ps_member(active_yogas=[
            {"name": "Sarala Yoga", "currently_active": True},
            {"name": "Not Active Yoga", "currently_active": False},
        ])
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertIn("Currently Active Yogas (2026): Sarala Yoga", ctx)
        self.assertNotIn("Not Active Yoga", ctx)

    def test_high_confidence_window_matching_year_included(self):
        member = self._ps_member(event_windows=[
            {"window_start": "2026-05-17", "window_end": "2026-05-30",
             "life_area": "self", "direction": "opportunity", "confidence": "very high"},
        ])
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertIn("High-Confidence Windows (2026):", ctx)
        self.assertIn("2026-05-17 to 2026-05-30", ctx)

    def test_low_confidence_window_excluded(self):
        member = self._ps_member(event_windows=[
            {"window_start": "2026-05-17", "window_end": "2026-05-30",
             "life_area": "self", "direction": "opportunity", "confidence": "medium"},
        ])
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertNotIn("High-Confidence Windows", ctx)

    def test_window_from_different_year_excluded(self):
        """predictive_signals isn't inherently year-scoped -- must filter by
        the prediction year explicitly, not trust computed_for."""
        member = self._ps_member(event_windows=[
            {"window_start": "2027-01-10", "window_end": "2027-01-24",
             "life_area": "self", "direction": "opportunity", "confidence": "high"},
        ])
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertNotIn("High-Confidence Windows", ctx)

    def test_empty_predictive_signals_no_crash(self):
        member = _base_member()  # no predictive_signals key at all
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertNotIn("Currently Active Yogas", ctx)
        self.assertNotIn("High-Confidence Windows", ctx)


class TestExistingFieldsRegression(unittest.TestCase):
    """The Phase 1 change adds lines -- must not touch the pre-existing
    nakshatra/rasi/dasha/sade-sati/porutham output."""

    def test_base_fields_unaffected_by_new_data(self):
        member = _base_member(
            role="wife", name="Priya",
            yogas={"summary": {"yoga_names": ["Raja Yoga"]}},
            upagrahas={"gulika": {"rasi": "Cancer", "rasi_lord": "Moon"}},
        )
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026)
        self.assertIn("--- WIFE: Priya ---", ctx)
        self.assertIn("Nakshatra: Ashwini", ctx)
        self.assertIn("Rasi: Mesham", ctx)
        self.assertIn("Date of Birth: 1980-01-01", ctx)
        # Sade Sati's Active/Not-active value depends on today's real transiting
        # Saturn position relative to this minimal fixture's Moon rasi, not on
        # anything Phase 1 touched -- just confirm the line still renders.
        self.assertIn("Sade Sati:", ctx)


class TestPromptVersionGating(unittest.TestCase):
    """
    Phase C: family_predictions had NO version-gating mechanism at all --
    caching was keyed solely on (group_id, year), so a prompt/context
    change would silently keep serving stale cached rows for any group
    with an existing prediction that year, with no way to detect it.
    """

    def test_prompt_version_is_family_v2_0(self):
        """Regression guard: reverting this would silently re-enable
        serving stale rows for every group with an existing cached
        prediction, the same way a natal_v2.1 revert would have."""
        self.assertEqual(PROMPT_VERSION, "family_v2.0")

    def test_cache_check_query_filters_on_prompt_version(self):
        """Confirms the real cache-check SQL (not a re-implementation)
        includes prompt_version as a filter, mirroring the mechanism
        verified for natal_v2.2 earlier this session."""
        import os

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None  # cache miss

        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            result = run_family_prediction(
                group={"id": "g1", "name": "Test"},
                members_with_charts=[],
                year=2026,
                db=mock_db,
            )
        finally:
            if old_key is not None:
                os.environ["ANTHROPIC_API_KEY"] = old_key

        # No API key -> bails out right after the cache check, before any
        # LLM call, so the mock's first execute() call is the cache-check.
        self.assertEqual(result.get("error"), "LLM not configured — ANTHROPIC_API_KEY missing")

        sql, params = mock_db.execute.call_args_list[0].args
        self.assertIn("prompt_version = ?", sql)
        self.assertIn(PROMPT_VERSION, params)

    def test_insert_writes_current_prompt_version(self):
        """The UPSERT must write PROMPT_VERSION, not leave the column null
        for newly-generated rows."""
        import inspect
        source = inspect.getsource(run_family_prediction)
        self.assertIn("prompt_version", source)
        self.assertIn("PROMPT_VERSION,", source)


if __name__ == "__main__":
    unittest.main()
