# tests/api/test_chat_context.py
"""
Regression test for the chat.py Upagraha wiring bug:

_build_chat_context() previously never populated context["upagraha_context"],
so the "## KARMIC SHADOW (Upagrahas)" block in the chat system prompt was
dead code from the moment Gulika/Upagraha support was added — the `if
context.get("upagraha_context")` check always evaluated to None/falsy.

These tests mock the DB layer (get_conn) so they exercise the real
_build_chat_context() + _build_system_prompt() code path end-to-end,
rather than re-implementing the prompt-building logic in the test.
"""

import unittest
from unittest.mock import MagicMock, patch

from app.api import chat as chat_module


def _base_payload(with_upagrahas: bool) -> dict:
    payload = {
        "birth_details": {
            "name": "Test Person",
            "date_of_birth": "1990-01-01",
            "time_of_birth": "10:00",
            "place_of_birth": "Chennai",
        },
        "ephemeris": {
            "lagna": {"rasi": "Aries"},
            "moon": {"rasi": "Cancer", "nakshatra": {"name": "Pushya"}},
            "planets": {},
        },
        "dashas": {},
    }
    if with_upagrahas:
        gulika_entry = {
            "longitude_deg": 100.0,
            "rasi": "Cancer",
            "rasi_lord": "Moon",
            "method": "parashari_lagna_at_mandi_kala",
        }
        payload["upagrahas"] = {"gulika": gulika_entry, "mandi": gulika_entry}
    return payload


def _mock_conn_for_payload(payload: dict) -> MagicMock:
    """Build a get_conn() replacement whose context-managed conn.execute(...)
    .fetchone() returns (payload,) for the chart query, then None for the
    monthly/yearly prediction queries, matching call order in
    _build_chat_context()."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.side_effect = [(payload,), None, None]

    conn_cm = MagicMock()
    conn_cm.__enter__.return_value = conn
    conn_cm.__exit__.return_value = False
    return conn_cm


class TestChatUpagrahaContext(unittest.TestCase):
    def test_context_populated_when_chart_has_upagraha_payload(self):
        payload = _base_payload(with_upagrahas=True)
        with patch.object(chat_module, "get_conn", return_value=_mock_conn_for_payload(payload)):
            context = chat_module._build_chat_context("fake-chart-id")

        self.assertIn("upagraha_context", context)
        self.assertIsNotNone(context["upagraha_context"])
        self.assertEqual(context["upagraha_context"].get("gulika_rasi"), "Cancer")
        self.assertEqual(context["upagraha_context"].get("gulika_lord"), "Moon")

    def test_context_empty_when_chart_has_no_upagraha_payload(self):
        payload = _base_payload(with_upagrahas=False)
        with patch.object(chat_module, "get_conn", return_value=_mock_conn_for_payload(payload)):
            context = chat_module._build_chat_context("fake-chart-id")

        self.assertIn("upagraha_context", context)
        self.assertFalse(context["upagraha_context"])

    def test_karmic_shadow_block_renders_into_actual_system_prompt(self):
        """Exercises the real _build_system_prompt() — the exact function
        chat_stream() calls — not a re-implementation of its logic."""
        payload = _base_payload(with_upagrahas=True)
        with patch.object(chat_module, "get_conn", return_value=_mock_conn_for_payload(payload)):
            context = chat_module._build_chat_context("fake-chart-id")

        system_prompt = chat_module._build_system_prompt(context)

        self.assertIn("## KARMIC SHADOW (Upagrahas)", system_prompt)
        self.assertIn("Cancer", system_prompt)
        self.assertIn("ruled by Moon", system_prompt)
        # The block instructs the LLM never to name the technique directly.
        self.assertIn("Never use the words 'Gulika' or 'Mandi'", system_prompt)

    def test_karmic_shadow_block_absent_when_no_upagraha_data(self):
        payload = _base_payload(with_upagrahas=False)
        with patch.object(chat_module, "get_conn", return_value=_mock_conn_for_payload(payload)):
            context = chat_module._build_chat_context("fake-chart-id")

        system_prompt = chat_module._build_system_prompt(context)

        self.assertNotIn("KARMIC SHADOW", system_prompt)


def _pre_refactor_build_system_prompt(context: dict, reading_as_name=None) -> str:
    """
    Verbatim copy of the system-prompt assembly as it existed inline in
    chat_stream() BEFORE the extraction into _build_system_prompt() (only
    `req.reading_as_name` -> `reading_as_name` since this is no longer a
    request object). Kept here, independent of app/api/chat.py, so the
    regression test below is a real before/after comparison rather than
    the refactored function compared against itself.
    """
    system_prompt = chat_module.SYSTEM_PROMPT_TEMPLATE.format(**context)
    if context.get("divisional_summary"):
        system_prompt = system_prompt.replace(
            "- Key planets:",
            f"- D10 career chart: {context['divisional_summary']}\n- Key planets:"
        )
    if context.get("upagraha_context"):
        upa = context["upagraha_context"]
        gulika_rasi = upa.get("gulika_rasi", "")
        gulika_lord = upa.get("gulika_lord", "")
        if gulika_rasi:
            system_prompt += (
                "\n\n## KARMIC SHADOW (Upagrahas)\n"
                f"Gulika (shadow of Saturn) falls in {gulika_rasi}"
                + (f", ruled by {gulika_lord}" if gulika_lord else "")
                + ".\n"
                "When the user asks about persistent struggle, hidden friction, or why "
                "certain areas feel stuck despite good dashas — reference this karmic shadow. "
                "Frame as karmic work in progress, not doom. "
                "Never use the words 'Gulika' or 'Mandi' in your response.\n"
            )
    if reading_as_name:
        system_prompt = f"Reading from {reading_as_name}'s chart.\n\n" + system_prompt
    return system_prompt


class TestSystemPromptExtractionIsNoOp(unittest.TestCase):
    """
    The chat.py fix extracted the ENTIRE system-prompt assembly (template
    fill + divisional + upagraha + reading-as-name) out of chat_stream()
    into _build_system_prompt(), not just the upagraha piece. These tests
    prove the extraction was behavior-preserving for every branch, by
    diffing against an independently-kept pre-refactor copy of the logic
    — not by comparing the new function against itself.
    """

    def _full_context(self, **overrides) -> dict:
        base = {
            "name": "Test Person", "date": "1990-01-01", "time": "10:00",
            "place": "Chennai", "lagna_sign": "Aries", "moon_sign": "Cancer",
            "moon_nakshatra": "Pushya", "mahadasha": "Jupiter", "antardasha": "Saturn",
            "planets_summary": "Sun in Capricorn", "yogas_summary": "none notable",
            "shadbala_summary": "not available", "sade_sati_summary": "not active",
            "monthly_summary": "not available", "yearly_summary": "not available",
            "divisional_summary": "", "upagraha_context": {},
        }
        base.update(overrides)
        return base

    def test_plain_context_byte_identical(self):
        context = self._full_context()
        self.assertEqual(
            chat_module._build_system_prompt(context),
            _pre_refactor_build_system_prompt(context),
        )

    def test_divisional_summary_byte_identical(self):
        context = self._full_context(divisional_summary="D10 career: Sun in Capricorn (exalted)")
        self.assertEqual(
            chat_module._build_system_prompt(context),
            _pre_refactor_build_system_prompt(context),
        )

    def test_reading_as_name_byte_identical(self):
        context = self._full_context()
        self.assertEqual(
            chat_module._build_system_prompt(context, "Priya"),
            _pre_refactor_build_system_prompt(context, "Priya"),
        )

    def test_all_branches_combined_byte_identical(self):
        context = self._full_context(
            divisional_summary="D10 career: Saturn in Libra",
            upagraha_context={"gulika_rasi": "Cancer", "gulika_lord": "Moon", "note": "x"},
        )
        self.assertEqual(
            chat_module._build_system_prompt(context, "Priya"),
            _pre_refactor_build_system_prompt(context, "Priya"),
        )

    def test_upagraha_context_present_but_no_rasi_byte_identical(self):
        """Edge case: upagraha_context dict present but falsy-for-rendering
        (no gulika_rasi) — both old and new code must skip the block."""
        context = self._full_context(upagraha_context={"note": "x"})
        self.assertEqual(
            chat_module._build_system_prompt(context),
            _pre_refactor_build_system_prompt(context),
        )


if __name__ == "__main__":
    unittest.main()
