# tests/api/test_natal_interpretation.py
"""
Tests for the natal_v2.2 Upagraha/Gulika-Mandi wiring fix.

Prior to this fix, natal_interpretation.py never referenced Gulika/Upagraha
data at all, and PROMPT_VERSION had not been bumped since before Gulika was
added (natal_v2.1 predates the Gulika feature by 5 weeks). Since this endpoint
caches permanently per chart_id+feature_name+prompt_version, the missing
version bump meant the fix would silently do nothing for every existing
chart without it.
"""

import unittest
from unittest.mock import MagicMock, patch

from app.api import natal_interpretation as natal_module


def _payload_with_upagrahas():
    return {
        "birth_details": {"name": "Test", "date_of_birth": "1990-01-01",
                           "time_of_birth": "10:00", "place_of_birth": "Chennai"},
        "ephemeris": {
            "lagna": {"rasi": "Aries", "longitude_deg": 10.0},
            "moon": {"rasi": "Cancer", "nakshatra": {"name": "Pushya", "pada": 2}},
            "planets": {},
            "ayanamsa": "lahiri",
        },
        "dashas": {},
        "upagrahas": {
            "gulika": {"longitude_deg": 100.0, "rasi": "Gemini", "rasi_lord": "Mercury",
                       "method": "parashari_lagna_at_mandi_kala"},
            "mandi": {"longitude_deg": 100.0, "rasi": "Gemini", "rasi_lord": "Mercury",
                      "method": "parashari_lagna_at_mandi_kala"},
        },
    }


def _payload_without_upagrahas():
    payload = _payload_with_upagrahas()
    del payload["upagrahas"]
    return payload


class TestPromptVersionBump(unittest.TestCase):
    def test_prompt_version_is_bumped_past_v2_1(self):
        """Regression guard: a revert back to natal_v2.1 would silently undo
        this fix for every chart (permanent per-version cache)."""
        self.assertEqual(natal_module.PROMPT_VERSION, "natal_v2.2")

    def test_engine_version_literal_unchanged_for_pdf_compat(self):
        """app/pdf/canonical_report/data_loader.py keys its natal-v2 parsing
        branch on the literal string "natal-v2.0" in the JSON output. The
        Upagraha addition is schema-compatible (one new optional field), so
        engine_version must NOT be bumped here — only PROMPT_VERSION (the
        cache key) changes. Confirms we didn't accidentally break the PDF
        renderer while fixing the cache-staleness bug."""
        self.assertIn('"engine_version": "natal-v2.0"', natal_module.NATAL_USER_TEMPLATE)
        self.assertEqual(natal_module._fallback_response()["engine_version"], "natal-v2.0")


class TestBuildNatalContextUpagraha(unittest.TestCase):
    def test_gulika_line_present_when_upagrahas_in_payload(self):
        context = natal_module._build_natal_context(_payload_with_upagrahas())
        self.assertIn("Gulika (Mandi): Gemini, ruled by Mercury", context)

    def test_gulika_line_absent_when_no_upagrahas_in_payload(self):
        context = natal_module._build_natal_context(_payload_without_upagrahas())
        self.assertNotIn("Gulika", context)


class TestSystemPromptInstructsOnGulikaWording(unittest.TestCase):
    def test_system_prompt_forbids_gulika_mandi_in_output(self):
        self.assertIn("Never use the words \"Gulika\", \"Mandi\", or \"Upagraha\"",
                       natal_module.NATAL_SYSTEM_PROMPT)

    def test_user_template_has_optional_karmic_shadow_field(self):
        self.assertIn("karmic_shadow_note", natal_module.NATAL_USER_TEMPLATE)
        self.assertIn("OPTIONAL", natal_module.NATAL_USER_TEMPLATE)


class TestCacheVersionFiltering(unittest.TestCase):
    """
    Mirrors the v5->v6 weekly/monthly/yearly migration mechanism: _get_cached()
    filters on module-level PROMPT_VERSION, so bumping it makes old
    natal_v2.1 rows unreachable without deleting them, and the endpoint falls
    through to a fresh LLM generation.
    """

    def test_get_cached_queries_with_bumped_version(self):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_conn
        mock_cm.__exit__.return_value = False

        with patch.object(natal_module, "get_conn", return_value=mock_cm):
            natal_module._get_cached("some-chart-id")

        args, _ = mock_conn.execute.call_args
        params = args[1]
        self.assertIn("natal_v2.2", params)
        self.assertNotIn("natal_v2.1", params)


if __name__ == "__main__":
    unittest.main()
