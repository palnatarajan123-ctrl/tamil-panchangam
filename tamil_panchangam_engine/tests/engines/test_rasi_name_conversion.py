"""
Regression tests for the Tamil/English rasi-name mismatch bug.

Chart payloads store ephemeris.moon.rasi / ephemeris.lagna.rasi in Tamil
(e.g. "Simmam"), but gochara_engine.py and moon_transit_engine.py key
their house-counting lookups in English ("Leo"). Passing the Tamil name
straight through used to silently fall back to index 0 ("as if Moon is
in Aries") for every non-Aries chart -- see CLAUDE.md's 2026-09-12
Rahu-Ketu peyarchi investigation for the real production incident this
traces back to.
"""
from datetime import datetime

from app.utils.rasi_utils import to_english_rasi, ENGLISH_TO_TAMIL_RASI
from app.engines.gochara_engine import compute_gochara
from app.engines.moon_transit_engine import compute_chandra_gati


def test_to_english_rasi_converts_tamil():
    assert to_english_rasi("Simmam") == "Leo"
    assert to_english_rasi("Mesham") == "Aries"


def test_to_english_rasi_passes_through_english_and_none():
    assert to_english_rasi("Leo") == "Leo"
    assert to_english_rasi(None) is None
    assert to_english_rasi("") == ""


def test_all_twelve_tamil_names_round_trip():
    for english, tamil in ENGLISH_TO_TAMIL_RASI.items():
        assert to_english_rasi(tamil) == english


def test_gochara_house_from_moon_matches_for_tamil_and_english_input():
    kwargs = dict(
        reference_date_utc=datetime(2026, 12, 10),
        latitude=13.08,
        longitude=80.27,
    )
    tamil_result = compute_gochara(natal_moon_rasi="Simmam", natal_lagna_rasi="Simmam", **kwargs)
    english_result = compute_gochara(natal_moon_rasi="Leo", natal_lagna_rasi="Leo", **kwargs)

    assert tamil_result["rahu_ketu"]["rahu_from_moon_house"] == english_result["rahu_ketu"]["rahu_from_moon_house"]
    assert tamil_result["saturn"]["from_moon_house"] == english_result["saturn"]["from_moon_house"]
    assert tamil_result["jupiter"]["from_moon_house"] == english_result["jupiter"]["from_moon_house"]


def test_gochara_rahu_house_for_capricorn_transit_from_leo_moon():
    # Capricorn is the 6th sign counted from Leo -- independent of the
    # Tamil/English bug, this pins the actual expected value so a future
    # regression can't silently reintroduce the Aries-fallback behavior.
    result = compute_gochara(
        reference_date_utc=datetime(2026, 12, 10),
        latitude=13.08,
        longitude=80.27,
        natal_moon_rasi="Simmam",
        natal_lagna_rasi="Simmam",
    )
    assert result["rahu_ketu"]["rahu_rasi"] == "Capricorn"
    assert result["rahu_ketu"]["rahu_from_moon_house"] == 6


def test_chandra_gati_house_from_natal_matches_for_tamil_and_english_input():
    tamil_result = compute_chandra_gati(2026, 12, "Simmam")
    english_result = compute_chandra_gati(2026, 12, "Leo")

    tamil_houses = [p["house_from_natal"] for p in tamil_result["moon_positions"]]
    english_houses = [p["house_from_natal"] for p in english_result["moon_positions"]]
    assert tamil_houses == english_houses
