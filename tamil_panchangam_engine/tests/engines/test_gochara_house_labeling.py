"""
Regression tests for missing Rasi/Lagna labeling on Gochara house numbers.

All three user-facing surfaces that display a Gochara house number used
to show a bare "H10" with no indication of which reference frame (Moon
sign vs Ascendant) it was counted from. Every real display in the app
counts from Moon (Rasi) -- see CLAUDE.md's 2026-09-12 Rahu-Ketu peyarchi
investigation -- so each surface now says "from Moon" explicitly.
"""
from app.engines.realtime_context_engine import (
    _format_transit,
    _format_saturn_transit,
    _format_rahu_ketu,
)
import inspect
from app.engines.synthesis_engine import synthesize_from_envelope


def test_realtime_jupiter_transit_labeled_from_moon():
    formatted = _format_transit({"transit_rasi": "Leo", "from_moon_house": 5, "effect": "favorable"}, "Jupiter")
    assert formatted == "Leo (H5 from Moon) - Favorable"


def test_realtime_saturn_transit_labeled_from_moon():
    formatted = _format_saturn_transit({"transit_rasi": "Capricorn", "from_moon_house": 9, "phase": "neutral"})
    assert formatted == "Capricorn (H9 from Moon)"

    formatted_special = _format_saturn_transit(
        {"transit_rasi": "Aries", "from_moon_house": 1, "phase": "janma_sani"}
    )
    assert formatted_special == "Aries (H1 from Moon) - Janma Sani"


def test_realtime_rahu_ketu_axis_labeled_from_moon():
    formatted = _format_rahu_ketu(
        {"rahu_from_moon_house": 10, "ketu_from_moon_house": 4, "theme": "home_career"}
    )
    assert formatted == "Rahu H10 / Ketu H4 (from Moon) (home_career)"


def test_synthesis_rahu_ketu_rationale_labeled_from_moon():
    # synthesize_from_envelope() is a single large function with no
    # extracted per-signal helper, and its GOCHARA_RAHU_KETU rationale
    # isn't part of its returned life_areas shape (see CLAUDE.md's
    # top_signals note on why non-house-tagged gochara signals don't
    # surface there) -- checking the source text directly is simpler
    # and just as reliable a guard against this exact f-string
    # regressing to its unlabeled form.
    source = inspect.getsource(synthesize_from_envelope)
    assert 'f"Rahu-Ketu axis {rahu_ketu.get(\'axis\', \'unknown\')} from Moon' in source
