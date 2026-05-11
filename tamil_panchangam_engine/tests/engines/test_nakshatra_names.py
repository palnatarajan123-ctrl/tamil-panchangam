"""Tests for nakshatra_names canonical lookup module."""

import pytest
from app.engines.nakshatra_names import (
    nakshatra_index,
    normalize_nakshatra,
    canonical_nakshatra_list,
    CANONICAL_NAMES,
)


def test_canonical_list_has_27():
    assert len(canonical_nakshatra_list()) == 27


def test_tamil_primary_names_recognized():
    assert nakshatra_index("Karthigai") == 2
    assert nakshatra_index("Mirugashirisham") == 4
    assert nakshatra_index("Thiruvadirai") == 5
    assert nakshatra_index("Punarpoosam") == 6
    assert nakshatra_index("Ayilyam") == 8
    assert nakshatra_index("Magam") == 9
    assert nakshatra_index("Chittirai") == 13
    assert nakshatra_index("Kettai") == 17
    assert nakshatra_index("Moolam") == 18
    assert nakshatra_index("Thiruvonam") == 21
    assert nakshatra_index("Avittam") == 22
    assert nakshatra_index("Sadayam") == 23
    assert nakshatra_index("Poorattadhi") == 24
    assert nakshatra_index("Uthirattadhi") == 25
    assert nakshatra_index("Revathi") == 26


def test_sanskrit_names_map_to_same_index():
    assert nakshatra_index("Ashwini") == nakshatra_index("Aswini")
    assert nakshatra_index("Krittika") == nakshatra_index("Karthigai")
    assert nakshatra_index("Mrigashira") == nakshatra_index("Mirugashirisham")
    assert nakshatra_index("Ardra") == nakshatra_index("Thiruvadirai")
    assert nakshatra_index("Punarvasu") == nakshatra_index("Punarpoosam")
    assert nakshatra_index("Pushya") == nakshatra_index("Poosam")
    assert nakshatra_index("Ashlesha") == nakshatra_index("Ayilyam")
    assert nakshatra_index("Magha") == nakshatra_index("Magam")
    assert nakshatra_index("Hasta") == nakshatra_index("Hastham")
    assert nakshatra_index("Chitra") == nakshatra_index("Chittirai")
    assert nakshatra_index("Vishakha") == nakshatra_index("Visakam")
    assert nakshatra_index("Anuradha") == nakshatra_index("Anusham")
    assert nakshatra_index("Jyeshtha") == nakshatra_index("Kettai")
    assert nakshatra_index("Mula") == nakshatra_index("Moolam")
    assert nakshatra_index("Shravana") == nakshatra_index("Thiruvonam")
    assert nakshatra_index("Dhanishta") == nakshatra_index("Avittam")
    assert nakshatra_index("Shatabhisha") == nakshatra_index("Sadayam")
    assert nakshatra_index("Revati") == nakshatra_index("Revathi")


def test_case_insensitive():
    assert nakshatra_index("KARTHIGAI") == 2
    assert nakshatra_index("ashwini") == 0
    assert nakshatra_index("Rohini") == 3


def test_purva_uttara_variants():
    assert nakshatra_index("Purva Phalguni") == 10
    assert nakshatra_index("Uttara Phalguni") == 11
    assert nakshatra_index("Purva Ashadha") == 19
    assert nakshatra_index("Uttara Ashadha") == 20
    assert nakshatra_index("Purva Ashada") == 19
    assert nakshatra_index("Uttara Ashada") == 20
    assert nakshatra_index("Purva Bhadrapada") == 24
    assert nakshatra_index("Uttara Bhadrapada") == 25


def test_unrecognized_returns_none():
    assert nakshatra_index("") is None
    assert nakshatra_index("NotANakshatra") is None


def test_normalize_returns_canonical():
    assert normalize_nakshatra("Krittika") == "Karthigai"
    assert normalize_nakshatra("Ashwini") == "Aswini"
    assert normalize_nakshatra("Mrigashira") == "Mirugashirisham"
    assert normalize_nakshatra("Dhanishta") == "Avittam"


def test_normalize_unknown_returns_input():
    assert normalize_nakshatra("SomeUnknown") == "SomeUnknown"


def test_index_ordering_consistent():
    for i, name in enumerate(CANONICAL_NAMES):
        assert nakshatra_index(name) == i


def test_all_ephemeris_sanskrit_names_resolve():
    """Every name from ephemeris.py NAKSHATRA_NAMES must resolve."""
    ephemeris_names = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
        "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
        "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
        "Anuradha", "Jyeshtha", "Mula", "Purva Ashada", "Uttara Ashada",
        "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
        "Uttara Bhadrapada", "Revati",
    ]
    for name in ephemeris_names:
        idx = nakshatra_index(name)
        assert idx is not None, f"Failed to resolve ephemeris name: {name}"
        assert 0 <= idx <= 26
