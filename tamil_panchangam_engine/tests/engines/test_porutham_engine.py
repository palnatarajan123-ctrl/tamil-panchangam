"""
Tests for porutham_engine.py

Nakshatra reference (0-based index):
  0=Ashwini, 1=Bharani, 2=Krittika, 3=Rohini, 4=Mrigashira, 5=Ardra,
  6=Punarvasu, 7=Pushya, 8=Ashlesha, 9=Magha, 10=Purva Phalguni,
  11=Uttara Phalguni, 12=Hasta, 13=Chitra, 14=Swati, 15=Vishakha,
  16=Anuradha, 17=Jyeshtha, 18=Mula, 19=Purva Ashadha, ...

Rasi reference (0-based index):
  0=Aries, 1=Taurus, 2=Gemini, 3=Cancer, 4=Leo, 5=Virgo,
  6=Libra, 7=Scorpio, 8=Sagittarius, 9=Capricorn, 10=Aquarius, 11=Pisces

NADI (0=Adi, 1=Madhya, 2=Antya):
  [0,1,2,2,1,0,0,1,2,0,1,2,2,1,0,0,1,2,0,1,2,2,1,0,0,1,2]

GANA (0=Deva, 1=Manushya, 2=Rakshasa):
  [0,2,1,0,1,2,0,0,2,2,1,0,0,2,0,1,0,2,2,1,1,0,2,2,1,0,0]
"""

import pytest
from app.engines.porutham_engine import (
    _nakshatra_index,
    _rasi_index,
    score_nadi,
    score_ganam,
    score_rasi,
    compute_porutham,
)


# ── 1. Nadi dosha — same Nadi ─────────────────────────────────────────────────

def test_nadi_same_nadi_dosha():
    """Ashwini(0, Adi) and Punarvasu(6, Adi) share Adi nadi → dosha."""
    result = score_nadi(0, 6)
    assert result["score"] == 0
    assert result["pass"] is False
    assert result.get("mandatory") is True


def test_nadi_dosha_propagates_mandatory_fail():
    """compute_porutham must set mandatory_fail=True when Nadi matches."""
    result = compute_porutham("Ashwini", "Aries", "Punarvasu", "Aries")
    assert result["mandatory_fail"] is True
    nadi = next(p for p in result["points"] if p["name"] == "Nadi")
    assert nadi["score"] == 0
    assert nadi["pass"] is False


# ── 2. Nadi clean — different Nadi ───────────────────────────────────────────

def test_nadi_different_nadi_full_score():
    """Ashwini(0, Adi=0) and Bharani(1, Madhya=1) → different nadi → score=8."""
    result = score_nadi(0, 1)
    assert result["score"] == 8
    assert result["pass"] is True


# ── 3. Gana same ──────────────────────────────────────────────────────────────

def test_gana_same_full_score():
    """Ashwini(0, Deva) and Rohini(3, Deva) → same Gana → score=6."""
    result = score_ganam(0, 3)
    assert result["score"] == 6
    assert result["pass"] is True


# ── 4. Gana Deva + Manushya ───────────────────────────────────────────────────

def test_gana_deva_plus_manushya():
    """
    Ashwini(0, Deva) boy + Mrigashira(4, Manushya) girl → score=5.
    Note: engine returns 5 (not 3) for this combination.
    Reversed (boy=Manushya, girl=Deva) scores 0.
    """
    result = score_ganam(0, 4)
    assert result["score"] == 5

    # Reversed direction is unfavorable
    result_rev = score_ganam(4, 0)
    assert result_rev["score"] == 0


# ── 5. Gana Deva + Rakshasa ───────────────────────────────────────────────────

def test_gana_deva_plus_rakshasa_zero():
    """Ashwini(0, Deva) + Bharani(1, Rakshasa) → score=0."""
    result = score_ganam(0, 1)
    assert result["score"] == 0
    assert result["pass"] is False


# ── 6. Rasi Shashta-Ashtama (6th / 8th from boy) ────────────────────────────

def test_rasi_shashta_sixth_position():
    """Girl Virgo(5) is 6th from boy Aries(0) → diff=5 → score=0."""
    result = score_rasi(0, 5)
    assert result["score"] == 0


def test_rasi_ashtama_eighth_position():
    """Girl Scorpio(7) is 8th from boy Aries(0) → diff=7 → score=0."""
    result = score_rasi(0, 7)
    assert result["score"] == 0


# ── 7. Rasi Saptama (7th from each) ─────────────────────────────────────────

def test_rasi_saptama_seventh():
    """Girl Libra(6) is 7th from boy Aries(0) → diff=6 → score=7 (max)."""
    result = score_rasi(0, 6)
    assert result["score"] == 7
    assert result["pass"] is True


def test_rasi_saptama_fifth_from_boy():
    """diff=4 (5th from boy) also scores 7 — same scoring band."""
    result = score_rasi(0, 4)
    assert result["score"] == 7


# ── 8. Total score always 0–33 ────────────────────────────────────────────────

@pytest.mark.parametrize("boy_nak,boy_rasi,girl_nak,girl_rasi", [
    ("Ashwini",       "Aries",       "Rohini",         "Cancer"),
    ("Bharani",       "Taurus",      "Punarvasu",      "Gemini"),
    ("Mrigashira",    "Gemini",      "Hasta",          "Virgo"),
    ("Rohini",        "Cancer",      "Swati",          "Libra"),
    ("Ashwini",       "Aries",       "Purva Ashadha",  "Sagittarius"),
])
def test_total_score_within_bounds(boy_nak, boy_rasi, girl_nak, girl_rasi):
    result = compute_porutham(boy_nak, boy_rasi, girl_nak, girl_rasi)
    assert "error" not in result
    assert 0 <= result["total_score"] <= 33
    assert result["max_score"] == 33


# ── 9. Grade/tier mapping ─────────────────────────────────────────────────────
#
# Engine uses percentage thresholds (not raw-score thresholds):
#   pct >= 75  → "Excellent"
#   pct >= 55  → "Good"
#   pct >= 36  → "Average"
#   else        → "Poor"
# mandatory_fail overrides to "Poor" regardless of score.

def test_grade_excellent():
    """
    Ashwini+Aries vs Purva Ashadha+Sagittarius scores 26/33 (78.8%) → Excellent.
    Verified: Dinam=0, Ganam=5, Yoni=2, Rasi=7, Rasiyathipaty=4, Nadi=8.
    """
    result = compute_porutham("Ashwini", "Aries", "Purva Ashadha", "Sagittarius")
    assert result["grade"] == "Excellent"
    assert result["mandatory_fail"] is False
    assert result["total_score"] == 26


def test_grade_good():
    """
    Rohini+Cancer vs Swati+Libra scores 19/33 (57.6%) → Good.
    """
    result = compute_porutham("Rohini", "Cancer", "Swati", "Libra")
    assert result["grade"] == "Good"
    assert result["mandatory_fail"] is False
    assert result["total_score"] == 19


def test_grade_poor_via_mandatory_fail():
    """
    mandatory_fail forces grade to Poor even if numeric score is moderate.
    Ashwini+Aries vs Punarvasu+Aries: Nadi dosha → grade=Poor.
    """
    result = compute_porutham("Ashwini", "Aries", "Punarvasu", "Aries")
    assert result["grade"] == "Poor"
    assert result["mandatory_fail"] is True


def test_percent_field_consistent_with_total():
    """percent == round(total_score / 33 * 100, 1)."""
    result = compute_porutham("Ashwini", "Aries", "Purva Ashadha", "Sagittarius")
    expected_pct = round(result["total_score"] / 33 * 100, 1)
    assert result["percent"] == expected_pct


# ── 10. String input resolution ──────────────────────────────────────────────

def test_nakshatra_index_rohini():
    """'Rohini' resolves to index 3."""
    assert _nakshatra_index("Rohini") == 3


def test_nakshatra_index_case_insensitive():
    assert _nakshatra_index("rohini") == 3
    assert _nakshatra_index("ROHINI") == 3


def test_rasi_index_taurus():
    """'Taurus' resolves to index 1."""
    assert _rasi_index("Taurus") == 1


def test_rasi_index_case_insensitive():
    assert _rasi_index("taurus") == 1
    assert _rasi_index("TAURUS") == 1


def test_string_inputs_do_not_raise():
    """compute_porutham must not raise for valid string inputs."""
    result = compute_porutham("Rohini", "Taurus", "Ashwini", "Aries")
    assert "error" not in result
    assert isinstance(result["total_score"], int)


def test_unrecognized_inputs_return_error_dict():
    """Unresolvable nakshatra/rasi names return an error dict, not an exception."""
    result = compute_porutham("BadNak", "BadRasi", "AlsoWrong", "Nope")
    assert "error" in result
    assert result["total_score"] == 0
    assert result["grade"] == "Unknown"


def test_rasi_index_unrecognized_returns_none():
    assert _rasi_index("UnknownRasi") is None


def test_rasi_index_empty_returns_none():
    assert _rasi_index("") is None
