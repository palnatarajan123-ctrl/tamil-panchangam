# tests/api/test_chat_dispositor_grounding.py
"""
Regression test for chat.py's dispositor-grounding text (2026-09-17).

_build_system_prompt()'s CURRENT TRANSITS block previously stated only
the generic house-position reading (sign + house + effect), identical
for every chart with the same Moon-house transit. Now appends the
transited house's own natal-lord condition when gochara_engine.py's
dispositor analysis is present, giving the LLM a real, chart-specific
grounded fact instead of a generic reading.
"""
from app.api import chat as chat_module


def _context_with_dispositor(dispositor: dict) -> dict:
    return {
        "name": "Test", "date": "1990-01-01", "time": "10:00", "place": "Chennai",
        "lagna_sign": "Simmam", "moon_sign": "Simmam", "moon_nakshatra": "Magha",
        "mahadasha": "Sun", "antardasha": "Moon",
        "planets_summary": "not available", "yogas_summary": "none notable",
        "shadbala_summary": "not available", "sade_sati_summary": "not active",
        "monthly_summary": "not available", "yearly_summary": "not available",
        "divisional_summary": "",
        "upagraha_context": {},
        "gochara_context": {
            "saturn": {
                "transit_rasi": "Pisces", "from_moon_house": 7, "from_lagna_house": 1,
                "phase": "kantaka_sani", "effect": "challenging",
                "dispositor": dispositor,
            },
        },
        "ingress_context": {},
    }


class TestDispositorGroundingText:
    def test_yogakaraka_dispositor_appears_in_prompt(self):
        context = _context_with_dispositor({
            "lord": "Jupiter", "lord_placement": "own_sign",
            "lord_functional_role": "yogakaraka", "strength_bonus": 0.383,
        })
        prompt = chat_module._build_system_prompt(context)
        assert "this house's lord Jupiter is own sign in your natal chart" in prompt
        assert "a yogakaraka for your chart" in prompt

    def test_maraka_dispositor_appears_in_prompt(self):
        context = _context_with_dispositor({
            "lord": "Jupiter", "lord_placement": "own_sign",
            "lord_functional_role": "maraka", "strength_bonus": 0.05,
        })
        prompt = chat_module._build_system_prompt(context)
        assert "this house's lord Jupiter is own sign in your natal chart" in prompt
        assert "a maraka for your chart" in prompt

    def test_no_dispositor_no_extra_text(self):
        context = _context_with_dispositor(None)
        # dispositor=None means .get("dispositor") on the saturn dict is None
        context["gochara_context"]["saturn"].pop("dispositor", None)
        prompt = chat_module._build_system_prompt(context)
        assert "this house's lord" not in prompt
        assert "Saturn: currently in Pisces" in prompt
