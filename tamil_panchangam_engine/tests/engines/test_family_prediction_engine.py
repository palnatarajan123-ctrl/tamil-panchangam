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

import json
import unittest
from unittest.mock import MagicMock, patch

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
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertIn("Present Yogas: Raja Yoga, Vimala Yoga", ctx)

    def test_empty_yogas_dict_no_crash_no_line(self):
        """Real data: some members have payload['yogas'] == {} entirely
        (never computed), not the usual error/yogas/summary shape."""
        member = _base_member(yogas={})
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertNotIn("Present Yogas:", ctx)

    def test_yogas_with_error_set_no_line(self):
        member = _base_member(yogas={"error": "computation failed", "yogas": [], "summary": {}})
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertNotIn("Present Yogas:", ctx)


class TestUpagrahaInFamilyContext(unittest.TestCase):
    def test_gulika_line_appears_with_rasi_and_lord(self):
        member = _base_member(upagrahas={
            "gulika": {"rasi": "Sagittarius", "rasi_lord": "Jupiter", "longitude_deg": 250.0},
            "mandi": {"rasi": "Sagittarius", "rasi_lord": "Jupiter", "longitude_deg": 250.0},
        })
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertIn("Gulika (karmic shadow point): Sagittarius, ruled by Jupiter", ctx)

    def test_no_upagrahas_no_line(self):
        member = _base_member()  # no upagrahas key at all
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertNotIn("Gulika", ctx)


class TestKpSublordsInFamilyContext(unittest.TestCase):
    def test_kp_present_wealth_significators_line_appears(self):
        member = _base_member(kp_sublords={
            "planets": {}, "house_cusps": {},
            "cuspal_significators": {"2": ["Venus", "Saturn"], "11": ["Mercury"]},
        })
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertIn("KP wealth-house significators: Venus, Saturn", ctx)

    def test_kp_none_no_line_no_crash(self):
        """Most charts won't have kp_sublords at all — payload.get() returns
        None, not a missing key. Must not crash on None.get(...)."""
        member = _base_member(kp_sublords=None)
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertNotIn("KP wealth-house", ctx)

    def test_kp_absent_key_no_line_no_crash(self):
        member = _base_member()  # kp_sublords key not present at all
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
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
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertIn("Currently Active Yogas (2026): Sarala Yoga", ctx)
        self.assertNotIn("Not Active Yoga", ctx)

    def test_high_confidence_window_matching_year_included(self):
        member = self._ps_member(event_windows=[
            {"window_start": "2026-05-17", "window_end": "2026-05-30",
             "life_area": "self", "direction": "opportunity", "confidence": "very high"},
        ])
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertIn("High-Confidence Windows (2026):", ctx)
        self.assertIn("2026-05-17 to 2026-05-30", ctx)

    def test_low_confidence_window_excluded(self):
        member = self._ps_member(event_windows=[
            {"window_start": "2026-05-17", "window_end": "2026-05-30",
             "life_area": "self", "direction": "opportunity", "confidence": "medium"},
        ])
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertNotIn("High-Confidence Windows", ctx)

    def test_window_from_different_year_excluded(self):
        """predictive_signals isn't inherently year-scoped -- must filter by
        the prediction year explicitly, not trust computed_for."""
        member = self._ps_member(event_windows=[
            {"window_start": "2027-01-10", "window_end": "2027-01-24",
             "life_area": "self", "direction": "opportunity", "confidence": "high"},
        ])
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
        self.assertNotIn("High-Confidence Windows", ctx)

    def test_empty_predictive_signals_no_crash(self):
        member = _base_member()  # no predictive_signals key at all
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
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
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, MagicMock())
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


def _couple_member(role, member_id, name, rasi="Mesham", nak="Ashwini", **overrides):
    payload = {
        "birth_details": {"name": name, "date_of_birth": "1980-01-01"},
        "ephemeris": {"moon": {"rasi": rasi, "nakshatra": {"name": nak}}},
        "dashas": {"vimshottari": {}},
    }
    payload.update(overrides)
    return {"member": {"id": member_id, "role": role, "display_name": name}, "payload": payload}


class TestGetOrComputePorutham(unittest.TestCase):
    """
    Direct tests for _get_or_compute_porutham() -- the cache-first lookup
    that PHASE F1 replaced the generic "factor Kuta compatibility" note
    with. Includes a regression test for a real bug found live while
    verifying this function against a real cache-miss group: the write-back
    initially omitted "name" from the cached husband/wife dicts, which
    silently broke the dedicated /porutham endpoint's read path (its
    response includes "name", and the frontend renders husband?.name ||
    "Husband" -- a name-less cache write meant real names got replaced by
    the generic fallback label for any group whose Porutham was computed
    here first, before ever hitting the endpoint).
    """

    def test_cache_hit_returns_porutham_subdict_only(self):
        mock_db = MagicMock()
        cached_row = ({
            "husband": {"name": "Ravi", "nakshatra": "Ashwini", "rasi": "Mesham"},
            "wife": {"name": "Priya", "nakshatra": "Hasta", "rasi": "Kanni"},
            "porutham": {"total_score": 16, "max_score": 33, "grade": "Average", "points": []},
        },)
        mock_db.execute.return_value.fetchone.return_value = cached_row

        from app.engines.family_prediction_engine import _get_or_compute_porutham
        result = _get_or_compute_porutham(
            mock_db, "group-1", "h-id", "Ravi", "Ashwini", "Mesham",
            "w-id", "Priya", "Hasta", "Kanni",
        )
        self.assertEqual(result, {"total_score": 16, "max_score": 33, "grade": "Average", "points": []})
        # Cache hit -> only the SELECT should have run, no INSERT.
        self.assertEqual(mock_db.execute.call_count, 1)

    def test_cache_miss_computes_and_writes_name_field(self):
        """
        Regression test for the found-and-fixed bug: the write-back must
        include 'name', not just nakshatra/rasi.

        Patches _generate_porutham_commentary (Phase H1) so this stays a
        fast, offline unit test -- without this patch, is_llm_enabled()
        hits the REAL database (it doesn't use the mocked db param, it
        calls get_conn() internally) and, if enabled, this test would
        make a real, billed Anthropic API call. Caught live: this exact
        test took 1.32s unpatched vs 0.60s with ANTHROPIC_API_KEY unset,
        confirming a real network call was happening.
        """
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None  # cache miss

        from app.engines.family_prediction_engine import _get_or_compute_porutham
        with patch("app.llm.payload_builder._generate_porutham_commentary", return_value="Test commentary."):
            result = _get_or_compute_porutham(
                mock_db, "group-1", "h-id", "Ravi", "Ashwini", "Mesham",
                "w-id", "Priya", "Hasta", "Kanni",
            )
        self.assertIsNotNone(result)
        self.assertIn("total_score", result)

        # Second execute() call is the INSERT -- confirm the written JSON
        # includes "name" for both husband and wife, not just nak/rasi.
        insert_sql, insert_params = mock_db.execute.call_args_list[1].args
        self.assertIn("INSERT INTO family_porutham_cache", insert_sql)
        written_json = insert_params[3]
        written = json.loads(written_json)
        self.assertEqual(written["husband"]["name"], "Ravi")
        self.assertEqual(written["wife"]["name"], "Priya")
        self.assertIn("nakshatra", written["husband"])
        self.assertIn("rasi", written["husband"])
        self.assertEqual(written["commentary"], "Test commentary.")

    def test_missing_nak_rasi_returns_none_no_db_call(self):
        mock_db = MagicMock()
        from app.engines.family_prediction_engine import _get_or_compute_porutham
        result = _get_or_compute_porutham(
            mock_db, "group-1", "h-id", "Ravi", "", "Mesham",  # missing nakshatra
            "w-id", "Priya", "Hasta", "Kanni",
        )
        self.assertIsNone(result)
        mock_db.execute.assert_not_called()

    def test_missing_member_id_returns_none(self):
        mock_db = MagicMock()
        from app.engines.family_prediction_engine import _get_or_compute_porutham
        result = _get_or_compute_porutham(
            mock_db, "group-1", None, "Ravi", "Ashwini", "Mesham",
            "w-id", "Priya", "Hasta", "Kanni",
        )
        self.assertIsNone(result)


class TestPoruthamInFamilyContext(unittest.TestCase):
    """
    Phase F1: _build_family_context() now grounds the PORUTHAM section in a
    real compute_porutham() result instead of the generic "Factor Kuta
    compatibility into financial and relationship caution analysis" note.
    """

    def test_no_wife_no_porutham_section_no_crash(self):
        """Single husband, no wife -- guard must produce no section and
        must not touch the (mocked) db at all for Porutham."""
        member = _couple_member("husband", "h-id", "Ravi")
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None
        ctx = _build_family_context({"name": "Test Group"}, [member], 2026, mock_db)
        self.assertNotIn("PORUTHAM", ctx)

    def test_husband_and_wife_cache_hit_renders_real_breakdown(self):
        husband = _couple_member("husband", "h-id", "Ravi", rasi="Mesham", nak="Ashwini")
        wife = _couple_member("wife", "w-id", "Priya", rasi="Kanni", nak="Hasta")

        mock_db = MagicMock()
        cached_row = ({
            "husband": {"name": "Ravi", "nakshatra": "Ashwini", "rasi": "Mesham"},
            "wife": {"name": "Priya", "nakshatra": "Hasta", "rasi": "Kanni"},
            "porutham": {
                "total_score": 16, "max_score": 33, "percent": 48.5, "grade": "Average",
                "mandatory_fail": False,
                "points": [
                    {"name": "Dinam", "score": 0, "max": 3, "pass": False},
                    {"name": "Nadi", "score": 8, "max": 8, "pass": True, "mandatory": True},
                    {"name": "Rajju", "score": 0, "max": 0, "pass": True, "mandatory": True},
                ],
            },
        },)
        mock_db.execute.return_value.fetchone.return_value = cached_row

        ctx = _build_family_context({"name": "Test Group", "id": "group-1"}, [husband, wife], 2026, mock_db)

        self.assertIn("--- PORUTHAM (Husband x Wife compatibility, 10-point Tamil Kuta system) ---", ctx)
        self.assertIn("Score: 16/33 (48.5%) — Average", ctx)
        self.assertIn("Mandatory categories: all passed", ctx)
        self.assertIn("Dinam 0/3", ctx)
        self.assertIn("Nadi 8/8", ctx)
        self.assertIn("Rajju pass", ctx)

    def test_mandatory_failure_named_in_context(self):
        husband = _couple_member("husband", "h-id", "Ravi")
        wife = _couple_member("wife", "w-id", "Priya")
        mock_db = MagicMock()
        cached_row = ({
            "porutham": {
                "total_score": 8, "max_score": 33, "percent": 24.2, "grade": "Poor",
                "mandatory_fail": True,
                "points": [
                    {"name": "Nadi", "score": 0, "max": 8, "pass": False, "mandatory": True},
                    {"name": "Rajju", "score": 0, "max": 0, "pass": True, "mandatory": True},
                ],
            },
        },)
        mock_db.execute.return_value.fetchone.return_value = cached_row
        ctx = _build_family_context({"name": "Test Group", "id": "group-1"}, [husband, wife], 2026, mock_db)
        self.assertIn("Mandatory categories: FAILED: Nadi", ctx)

    def test_no_result_no_generic_fallback_text(self):
        """When Porutham can't be computed (e.g. missing nak/rasi), there
        must be NO section at all -- not a fallback to the old generic
        'factor Kuta compatibility' instruction, which would make the
        LLM's output look grounded in real data when it isn't."""
        husband = _couple_member("husband", "h-id", "Ravi", rasi="", nak="")
        wife = _couple_member("wife", "w-id", "Priya", rasi="", nak="")
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None
        ctx = _build_family_context({"name": "Test Group", "id": "group-1"}, [husband, wife], 2026, mock_db)
        self.assertNotIn("PORUTHAM", ctx)
        self.assertNotIn("Factor Kuta compatibility", ctx)


if __name__ == "__main__":
    unittest.main()
