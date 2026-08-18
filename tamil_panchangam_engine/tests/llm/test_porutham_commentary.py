# tests/llm/test_porutham_commentary.py
"""
Phase H1: _generate_porutham_commentary() and _build_porutham_commentary_input()
(app/llm/payload_builder.py) -- the shared LLM-generated commentary
explaining the MECHANISM behind a Porutham grade, cached alongside the
rest of the Porutham result for both family and prospect surfaces.

These tests exercise the function's OWN gating/error-handling logic in
isolation (is_llm_enabled gate, missing API key, successful generation,
exception handling) with anthropic fully mocked -- every OTHER test in
this session that touches a function calling this one patches this
function out entirely (see tests/api/test_prospects.py and
tests/engines/test_family_prediction_engine.py's comments on why: without
patching, is_llm_enabled() hits the real database directly via its own
internal get_conn() call, not the mocked db/conn param, and a real,
billed Anthropic API call would follow). This file is where the function
itself actually gets exercised.
"""

import unittest
from unittest.mock import MagicMock, patch

from app.llm.payload_builder import (
    _generate_porutham_commentary,
    _build_porutham_commentary_input,
    _FAMILY_PORUTHAM_COMMENTARY_SYSTEM,
    _PROSPECT_PORUTHAM_COMMENTARY_SYSTEM,
)


def _real_porutham(mandatory_fail=False, failed_categories=None):
    """Shape verified against real compute_porutham() output this session
    (e.g. AN Sr x DV: mandatory_fail=True on Rajju+Nadi)."""
    points = [
        {"name": "Dinam", "score": 3, "max": 3, "pass": True},
        {"name": "Ganam", "score": 6, "max": 6, "pass": True},
        {"name": "Yoni", "score": 2, "max": 4, "pass": True},
        {"name": "Rasi", "score": 7, "max": 7, "pass": True},
        {"name": "Rasiyathipaty", "score": 5, "max": 5, "pass": True},
        {"name": "Rajju", "score": 0, "max": 0, "pass": True, "mandatory": True},
        {"name": "Vedha", "score": 0, "max": 0, "pass": True, "mandatory": True},
        {"name": "Mahendra", "score": 0, "max": 0, "pass": True},
        {"name": "Stree Deergha", "score": 0, "max": 0, "pass": True},
        {"name": "Nadi", "score": 8, "max": 8, "pass": True, "mandatory": True},
    ]
    if mandatory_fail:
        for p in points:
            if p.get("name") in (failed_categories or ["Nadi"]):
                p["pass"] = False
                p["score"] = 0
    return {
        "total_score": sum(p["score"] for p in points),
        "max_score": 33,
        "percent": 69.7,
        "grade": "Poor" if mandatory_fail else "Excellent",
        "mandatory_fail": mandatory_fail,
        "points": points,
    }


class TestBuildPoruthamCommentaryInput(unittest.TestCase):
    def test_basic_fields_present(self):
        text = _build_porutham_commentary_input(
            _real_porutham(), "Husband", "Ravi", "Wife", "Priya"
        )
        self.assertIn("Husband: Ravi", text)
        self.assertIn("Wife: Priya", text)
        self.assertIn("Grade: Excellent", text)
        self.assertIn("Mandatory category fail: NO", text)

    def test_mandatory_fail_names_failed_categories(self):
        text = _build_porutham_commentary_input(
            _real_porutham(mandatory_fail=True, failed_categories=["Rajju", "Nadi"]),
            "Person A", "DV", "Person B", "AN Sr",
        )
        self.assertIn("Mandatory category fail: YES", text)
        self.assertIn("Failed mandatory categories: Rajju, Nadi", text)

    def test_full_category_breakdown_included(self):
        text = _build_porutham_commentary_input(
            _real_porutham(), "Husband", "Ravi", "Wife", "Priya"
        )
        for category in ["Dinam", "Ganam", "Yoni", "Rasi", "Rasiyathipaty",
                          "Rajju", "Vedha", "Mahendra", "Stree Deergha", "Nadi"]:
            self.assertIn(category, text)

    def test_missing_names_fall_back_gracefully(self):
        text = _build_porutham_commentary_input(
            _real_porutham(), "Husband", None, "Wife", None
        )
        self.assertIn("Husband: Unknown", text)
        self.assertIn("Wife: Unknown", text)


class TestGeneratePoruthamCommentary(unittest.TestCase):
    def test_returns_none_when_llm_disabled(self):
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=False):
            result = _generate_porutham_commentary(_real_porutham(), "Ravi", "Priya", tone="family")
        self.assertIsNone(result)

    def test_returns_none_when_no_api_key(self):
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=True), \
             patch.dict("os.environ", {}, clear=True):
            result = _generate_porutham_commentary(_real_porutham(), "Ravi", "Priya", tone="family")
        self.assertIsNone(result)

    def test_returns_none_on_anthropic_exception_not_raise(self):
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=True), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}):
            with patch("anthropic.Anthropic", side_effect=RuntimeError("network down")):
                result = _generate_porutham_commentary(_real_porutham(), "Ravi", "Priya", tone="family")
        self.assertIsNone(result)

    def _mock_anthropic_client(self, text="Generated commentary text."):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=text)]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        return mock_client

    def test_family_tone_uses_family_system_prompt_and_husband_wife_labels(self):
        mock_client = self._mock_anthropic_client()
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=True), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
             patch("anthropic.Anthropic", return_value=mock_client):
            result = _generate_porutham_commentary(_real_porutham(), "Ravi", "Priya", tone="family")

        self.assertEqual(result, "Generated commentary text.")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        self.assertEqual(call_kwargs["system"], _FAMILY_PORUTHAM_COMMENTARY_SYSTEM)
        self.assertIn("Husband: Ravi", call_kwargs["messages"][0]["content"])
        self.assertIn("Wife: Priya", call_kwargs["messages"][0]["content"])

    def test_prospect_tone_uses_prospect_system_prompt_and_person_labels(self):
        mock_client = self._mock_anthropic_client()
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=True), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
             patch("anthropic.Anthropic", return_value=mock_client):
            result = _generate_porutham_commentary(_real_porutham(), "DV", "AN Sr", tone="prospect")

        self.assertEqual(result, "Generated commentary text.")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        self.assertEqual(call_kwargs["system"], _PROSPECT_PORUTHAM_COMMENTARY_SYSTEM)
        self.assertIn("Person A: DV", call_kwargs["messages"][0]["content"])
        self.assertIn("Person B: AN Sr", call_kwargs["messages"][0]["content"])

    def test_logs_llm_call_when_db_and_chart_id_given(self):
        mock_client = self._mock_anthropic_client()
        mock_db = MagicMock()
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=True), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
             patch("anthropic.Anthropic", return_value=mock_client), \
             patch("app.engines.budget_guard.log_llm_call") as mock_log:
            _generate_porutham_commentary(
                _real_porutham(), "Ravi", "Priya", tone="family",
                db=mock_db, log_chart_id="group-1",
            )
        mock_log.assert_called_once()
        self.assertEqual(mock_log.call_args.kwargs["chart_id"], "group-1")
        self.assertEqual(mock_log.call_args.kwargs["call_type"], "porutham_commentary_family")

    def test_no_log_call_when_db_not_given(self):
        """Prospect/family callers that don't pass db/log_chart_id must
        not crash trying to log."""
        mock_client = self._mock_anthropic_client()
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=True), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
             patch("anthropic.Anthropic", return_value=mock_client):
            result = _generate_porutham_commentary(_real_porutham(), "Ravi", "Priya", tone="family")
        self.assertEqual(result, "Generated commentary text.")

    def test_log_llm_call_failure_does_not_prevent_returning_commentary(self):
        mock_client = self._mock_anthropic_client()
        mock_db = MagicMock()
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=True), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
             patch("anthropic.Anthropic", return_value=mock_client), \
             patch("app.engines.budget_guard.log_llm_call", side_effect=RuntimeError("db down")):
            result = _generate_porutham_commentary(
                _real_porutham(), "Ravi", "Priya", tone="family",
                db=mock_db, log_chart_id="group-1",
            )
        self.assertEqual(result, "Generated commentary text.")


if __name__ == "__main__":
    unittest.main()
