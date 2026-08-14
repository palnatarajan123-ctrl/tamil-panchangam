# tests/api/test_daily_guidance.py
"""
Tests for the daily.py LLM guidance text fix: _generate_daily_llm_guidance()
previously read rahu_kaalam and yamagandam from `result` but never
gulika_kaalam, even though the Daily API response already included it.

These tests mock anthropic.Anthropic so no live API call happens in the
suite; a real live call was run manually during development to confirm the
addition doesn't push the 150-token completion cap (max_tokens=150, the
actual governing constraint here — MAX_COMPLETION_TOKENS in payload_builder.py
is unused by this endpoint, confirmed by grep) -- output used 107/150 tokens
with stop_reason="end_turn" (no truncation).
"""

import unittest
from unittest.mock import MagicMock, patch

from app.api import daily as daily_module


def _sample_result():
    return {
        "date": "2026-08-17",
        "nakshatra": {"name": "Chittirai", "pada": 2},
        "tara_bala": {"name": "Pratyak Tara", "quality": "challenging"},
        "tithi": {"name": "Panchami", "paksha": "Shukla"},
        "rahu_kaalam": {"start": "07:31", "end": "09:05", "segment": 2},
        "yamagandam": {"start": "10:39", "end": "12:14", "segment": 4},
        "gulika_kaalam": {"start": "13:46", "end": "15:20", "segment": 6},
    }


class TestDailyGuidanceIncludesGulika(unittest.TestCase):
    def _run_with_mocked_llm(self):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Some guidance text.")]
        mock_message.usage.input_tokens = 200
        mock_message.usage.output_tokens = 100

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=True), \
             patch.dict(daily_module.os.environ, {"ANTHROPIC_API_KEY": "fake-key-for-test"}), \
             patch("anthropic.Anthropic", return_value=mock_client), \
             patch.object(daily_module, "get_conn", side_effect=Exception("no db in unit test")):
            daily_module._generate_daily_llm_guidance(_sample_result(), "Test Person", "fake-chart-id")

        return mock_client.messages.create.call_args

    def test_gulika_kaalam_present_in_prompt_sent_to_llm(self):
        call_args = self._run_with_mocked_llm()
        self.assertIsNotNone(call_args, "LLM was not called — check the mock patches")
        prompt_text = call_args.kwargs["messages"][0]["content"]
        self.assertIn("Gulika Kaalam: 13:46 to 15:20", prompt_text)

    def test_rahu_and_yama_still_present_alongside_gulika(self):
        """Regression check: adding Gulika didn't drop the existing windows."""
        call_args = self._run_with_mocked_llm()
        prompt_text = call_args.kwargs["messages"][0]["content"]
        self.assertIn("Rahu Kaalam: 07:31 to 09:05", prompt_text)
        self.assertIn("Yamagandam: 10:39 to 12:14", prompt_text)

    def test_max_tokens_still_150(self):
        """Regression guard: this fix must not have touched the completion
        cap — it only adds an input line. If this ever changes, the
        real-call verification in the commit message (107/150 tokens used)
        needs to be re-checked."""
        call_args = self._run_with_mocked_llm()
        self.assertEqual(call_args.kwargs["max_tokens"], 150)


if __name__ == "__main__":
    unittest.main()
