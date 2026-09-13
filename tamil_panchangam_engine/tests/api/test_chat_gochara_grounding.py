# tests/api/test_chat_gochara_grounding.py
"""
Regression test for the Ask Jyotishi chat-grounding gap.

_build_chat_context() previously had zero access to current/future
transit positions -- no call to compute_gochara() anywhere -- so any
question about a Gochara/peyarchi transit left the LLM to fabricate a
sign and house number from nothing. Confirmed via a real logged
conversation on chart 7c6e34be, where the LLM claimed Rahu was entering
Meena (Pisces)/12th house -- wrong sign entirely, not just a
house-counting discrepancy -- then doubled down twice before conceding
"I don't have the exact verified peyarchi date... in front of me right
now" on the third challenge. See CLAUDE.md's 2026-09-12 investigation.

These tests mock the DB layer (get_conn), same pattern as
test_chat_context.py, so they exercise the real _build_chat_context() +
_build_system_prompt() code path end-to-end.
"""
import unittest
from unittest.mock import MagicMock, patch

from app.api import chat as chat_module


def _payload_with_tamil_rasi_names() -> dict:
    # Tamil names, as actually stored on real chart payloads (ephemeris.py's
    # get_rasi() returns Tamil) -- Leo/Leo so the Tamil/English mismatch bug
    # (fixed separately) would have been visible here too if reintroduced.
    return {
        "birth_details": {
            "name": "Test Person",
            "date_of_birth": "1990-01-01",
            "time_of_birth": "10:00",
            "place_of_birth": "Chennai",
            "latitude": 13.0827,
            "longitude": 80.2707,
        },
        "ephemeris": {
            "lagna": {"rasi": "Simmam"},
            "moon": {"rasi": "Simmam", "longitude_deg": 130.0, "nakshatra": {"name": "Magha"}},
            "planets": {},
            "ayanamsa": "lahiri",
        },
        "dashas": {},
        "chart_metadata": {"node_type": "mean"},
    }


def _mock_conn_for_payload(payload: dict) -> MagicMock:
    conn = MagicMock()
    conn.execute.return_value.fetchone.side_effect = [(payload,), None, None]
    conn_cm = MagicMock()
    conn_cm.__enter__.return_value = conn
    conn_cm.__exit__.return_value = False
    return conn_cm


class TestChatGocharaGrounding(unittest.TestCase):
    def test_gochara_context_populated_with_real_transit_data(self):
        payload = _payload_with_tamil_rasi_names()
        with patch.object(chat_module, "get_conn", return_value=_mock_conn_for_payload(payload)):
            context = chat_module._build_chat_context("fake-chart-id")

        self.assertIn("gochara_context", context)
        g = context["gochara_context"]
        self.assertIn("jupiter", g)
        self.assertIn("saturn", g)
        self.assertIn("rahu_ketu", g)
        self.assertIn("transit_rasi", g["jupiter"])
        self.assertIn("from_moon_house", g["jupiter"])
        self.assertIn("from_lagna_house", g["jupiter"])
        self.assertIn("rahu_rasi", g["rahu_ketu"])
        self.assertIn("rahu_from_moon_house", g["rahu_ketu"])
        self.assertIn("rahu_from_lagna_house", g["rahu_ketu"])

    def test_current_transits_block_renders_into_system_prompt(self):
        payload = _payload_with_tamil_rasi_names()
        with patch.object(chat_module, "get_conn", return_value=_mock_conn_for_payload(payload)):
            context = chat_module._build_chat_context("fake-chart-id")

        system_prompt = chat_module._build_system_prompt(context)

        self.assertIn("## CURRENT TRANSITS (Gochara)", system_prompt)
        self.assertIn("Rahu: currently in", system_prompt)
        self.assertIn("Ketu: currently in", system_prompt)
        self.assertIn("from your Moon sign", system_prompt)
        self.assertIn("from your Ascendant", system_prompt)
        # The actual sign name must come from the real gochara computation,
        # not a placeholder -- confirms the block is grounded, not templated
        # with empty/missing data.
        rahu_rasi = context["gochara_context"]["rahu_ketu"]["rahu_rasi"]
        self.assertIn(rahu_rasi, system_prompt)

    def test_system_prompt_instructs_against_fabrication_and_doubling_down(self):
        """These three instruction blocks are static template text (no
        chart data needed) -- this pins their presence directly, since
        they're the actual fix for the fabrication/doubling-down failure
        mode observed in the real transcript, independent of whether any
        one chart happens to have gochara data available."""
        payload = _payload_with_tamil_rasi_names()
        with patch.object(chat_module, "get_conn", return_value=_mock_conn_for_payload(payload)):
            context = chat_module._build_chat_context("fake-chart-id")

        system_prompt = chat_module._build_system_prompt(context)

        self.assertIn("HOUSE-COUNTING CONVENTION", system_prompt)
        self.assertIn("GROUNDING", system_prompt)
        self.assertIn("I don't have that specific data available", system_prompt)
        self.assertIn("WHEN CHALLENGED", system_prompt)
        self.assertIn("do not simply repeat your prior claim with more confidence", system_prompt)

    def test_gochara_computation_failure_degrades_gracefully(self):
        """No latitude/longitude in birth_details, no moon rasi -- must not
        raise; context building must still complete for the rest of chat."""
        payload = _payload_with_tamil_rasi_names()
        payload["ephemeris"]["moon"]["rasi"] = ""
        with patch.object(chat_module, "get_conn", return_value=_mock_conn_for_payload(payload)):
            context = chat_module._build_chat_context("fake-chart-id")

        self.assertIn("gochara_context", context)
        self.assertFalse(context["gochara_context"])
        system_prompt = chat_module._build_system_prompt(context)
        # The static GROUNDING rule text itself mentions "CURRENT TRANSITS"
        # in passing -- check for the live-data section header specifically,
        # not that substring, to confirm no fabricated block was rendered.
        self.assertNotIn("## CURRENT TRANSITS (Gochara)", system_prompt)


if __name__ == "__main__":
    unittest.main()
