# tests/engines/test_child_prediction_grounding.py
"""
Regression test for child_prediction_engine.py's marriage_window/
health_cautions fabrication fix (2026-09-19).

_build_child_context() gives the LLM only the child's 7th-house-lord
NAME for marriage (no dasha-window computation backing it at all --
unlike children_timing_engine.py's real technique for the 5th house),
and never even provides the 6th/8th house lords for health. The old
prompt still asked for and received a specific "earliest_favorable"
year, "peak_window" year range, and specific caution "period"/"area" --
softened with "never definitive" language, but still a concrete,
ungrounded timing claim shown to real parents via a live, reachable
screen (child-prediction-screen.tsx, confirmed linked from
family-screen.tsx for every child family member with no feature flag).

Fixed by changing the prompt schema to force "marriage_window": {} and
"health_cautions": [] until real dasha-window computation exists for
those topics -- both the UI (child-prediction-screen.tsx) and the PDF
renderer (family_pdf_renderer.py) already gracefully hide these
sections when empty/falsy, confirmed by direct code read, so this is a
clean omission, not an awkward "not available" placeholder shown to
parents.

Live-verified once (not repeated here to avoid a real LLM call on every
test run, matching this session's established practice for prompt-only
grounding fixes): a real live call against real child chart
`b1a35180-...` returned marriage_window={} and health_cautions=[]
exactly.
"""
import json
from unittest.mock import MagicMock, patch

from app.engines import child_prediction_engine as cpe


class TestPromptNoLongerAsksForFabricatedTiming:
    def test_prompt_forces_empty_marriage_window_and_health_cautions(self):
        prompt = cpe.CHILD_PREDICTION_PROMPT
        assert '"marriage_window": {}' in prompt
        assert '"health_cautions": []' in prompt

    def test_prompt_no_longer_requests_specific_year_fields(self):
        prompt = cpe.CHILD_PREDICTION_PROMPT
        assert "earliest_favorable" not in prompt
        assert "peak_window" not in prompt or "GROUNDING" in prompt

    def test_prompt_contains_explicit_grounding_instruction(self):
        prompt = cpe.CHILD_PREDICTION_PROMPT
        assert "GROUNDING" in prompt
        assert "do not invent a" in prompt.lower() or "not enough to support" in prompt.lower()


class TestRunChildPredictionHandlesEmptyGracefully:
    """Mocked-LLM test: confirm the parsing/persistence path in
    run_child_prediction() correctly handles the now-expected {}/[]
    shape without error -- the fabrication fix is prompt-text-based, so
    this proves the consuming code path isn't assuming non-empty
    content anywhere."""

    def _fake_db(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None  # cache miss
        return db

    def test_empty_marriage_window_and_health_cautions_parsed_and_returned(self):
        fake_response_json = json.dumps({
            "overall_narrative": "Test narrative.",
            "education": [],
            "career_aptitude": {"strong_houses": [], "favorable_fields": [], "peak_period": "", "plain_english": ""},
            "marriage_window": {},
            "leaving_home": {"window": "", "context": "education", "plain_english": ""},
            "health_cautions": [],
            "key_takeaways": [],
        })

        mock_content_block = MagicMock()
        mock_content_block.text = fake_response_json
        mock_response = MagicMock()
        mock_response.content = [mock_content_block]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        payload = {
            "birth_details": {"name": "Test Child", "date_of_birth": "2015-01-01"},
            "ephemeris": {"moon": {"rasi": "Mesham", "nakshatra": {"name": "Ashwini"}}},
            "dashas": {"vimshottari": {}},
        }

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}):
            with patch.object(cpe, "is_llm_enabled", return_value=True):
                with patch("anthropic.Anthropic", return_value=mock_client):
                    result = cpe.run_child_prediction(
                        member_id="fake-member-id",
                        chart_payload=payload,
                        year=2026,
                        db=self._fake_db(),
                    )

        assert "error" not in result
        assert result["marriage_window"] == {}
        assert result["health_cautions"] == []
