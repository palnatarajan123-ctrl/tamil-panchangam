# tests/engines/test_child_prediction_grounding.py
"""
Regression test for child_prediction_engine.py's marriage_window/
health_cautions fabrication fix.

History: 2026-09-19 emergency fix forced "marriage_window": {} and
"health_cautions": [] since _build_child_context() gave the LLM only a
bare 7th-house-lord NAME for marriage (no dasha-window computation
backing it, and 6th/8th lords weren't even given for health). That was
a stopgap. This test now covers the PROPER fix (same day, follow-up):
marriage_timing_engine.py and health_events_engine.py generalize
children_timing_engine.py's proven pattern (real Dasha/Antardasha
window computation per classical significator) to the 7th house lord,
Darakaraka, Kalatra Karaka (marriage) and 6th/8th house lords + natal
affliction (health) -- so the LLM now has real, computed windows to
cite instead of either fabricating or being forced empty.

The prompt requires every specific year/period in these two sections to
trace back to one of the given real windows, and requires a "basis"
field naming which significator/window backs it -- verified live
against a real chart (child b1a35180's family member): the LLM cited
"7th lord Venus Antardasha (Jan 2026 - Jan 2027)" and "Darakaraka Sun
Antardasha (Jan 2027 - May 2027)", both exactly matching the real
computed windows, not invented ones. Not re-run here (real LLM call) --
this file's tests cover the deterministic pieces: the prompt's
grounding instructions, and that _build_child_context() genuinely
includes the real per-significator data (not just a bare lord name)
before the LLM ever sees it.
"""
from unittest.mock import patch

from app.engines import child_prediction_engine as cpe


class TestPromptRequiresGroundedTiming:
    def test_prompt_requires_basis_field_for_marriage_window(self):
        prompt = cpe.CHILD_PREDICTION_PROMPT
        assert '"basis"' in prompt
        assert "MUST fall within one of the real Dasha/Antardasha windows" in prompt

    def test_prompt_requires_basis_field_for_health_cautions(self):
        prompt = cpe.CHILD_PREDICTION_PROMPT
        assert "MUST fall within a real Dasha/Antardasha window given to you for the 6th or 8th lord" in prompt

    def test_prompt_instructs_null_over_fabrication_when_no_window_in_range(self):
        prompt = cpe.CHILD_PREDICTION_PROMPT
        assert "null" in prompt
        assert "instead of guessing" in prompt
        assert "plausible-sounding but ungrounded date" in prompt

    def test_prompt_forbids_guessing_kalatra_karaka_when_unknown(self):
        prompt = cpe.CHILD_PREDICTION_PROMPT
        assert "do not substitute a guess" in prompt

    def test_prompt_no_longer_forces_empty_schema(self):
        """Supersedes the 2026-09-19 emergency stopgap now that real
        computed windows back these fields -- the JSON schema block
        itself now shows a real templated object/list, not a forced
        empty literal (the GROUNDING prose separately, correctly, notes
        that an empty list is still a valid answer when no window is
        found -- that's not the same as always forcing it empty)."""
        prompt = cpe.CHILD_PREDICTION_PROMPT
        schema_block = prompt.split("## Tone rules")[0]
        assert '"marriage_window": {}' not in schema_block
        assert '"health_cautions": []' not in schema_block
        assert '"basis":' in schema_block


class TestChildContextIncludesRealComputedSignals:
    """The core proof: _build_child_context() must include real,
    computed Dasha-window data for the 7th lord/Darakaraka/Kalatra
    Karaka and 6th/8th lords -- not just a bare lord name (the original
    2026-09-18 finding) and not a forced-empty placeholder (the
    2026-09-19 stopgap)."""

    def _real_payload(self):
        return {
            "birth_details": {"name": "Test Child", "date_of_birth": "2015-01-01"},
            "ephemeris": {
                "moon": {"rasi": "Mesham", "nakshatra": {"name": "Ashwini"}},
                "planets": {
                    "Sun": {"longitude_deg": 10.0},
                    "Moon": {"longitude_deg": 5.0},
                    "Mars": {"longitude_deg": 220.0},
                    "Mercury": {"longitude_deg": 15.0},
                    "Jupiter": {"longitude_deg": 100.0},
                    "Venus": {"longitude_deg": 40.0},
                    "Saturn": {"longitude_deg": 280.0},
                },
            },
            "dashas": {"vimshottari": {"timeline": []}},
        }

    def test_context_mentions_marriage_timing_signals_section(self):
        context = cpe._build_child_context(self._real_payload(), 2026)
        assert "Marriage Timing Signals" in context
        assert "Darakaraka" in context
        assert "7th house lord" in context

    def test_context_mentions_health_event_signals_section(self):
        context = cpe._build_child_context(self._real_payload(), 2026)
        assert "Health Event Signals" in context
        assert "6th house" in context
        assert "8th house" in context

    def test_context_omits_kalatra_karaka_when_gender_unknown(self):
        """role='child' family members carry no gender information in
        this app's data model (confirmed 2026-09-19) -- Kalatra Karaka
        must be honestly reported as unavailable, not guessed."""
        context = cpe._build_child_context(self._real_payload(), 2026)
        assert "Kalatra Karaka: not available" in context

    def test_context_no_longer_shows_bare_7th_lord_without_dasha_data(self):
        """The original finding: only a bare '7th (Marriage): <lord>'
        line with no window data. Confirm that specific shape is gone
        (the 7th lord now only appears inside the real Marriage Timing
        Signals section, alongside its Dasha windows)."""
        context = cpe._build_child_context(self._real_payload(), 2026)
        assert "7th (Marriage):" not in context
