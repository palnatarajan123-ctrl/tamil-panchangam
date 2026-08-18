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

NADI (0=Adi, 1=Madhya, 2=Antya) -- corrected 2026-08-17, audit Phase 2:
  [0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,2,1,0,0,1,2]

GANA (0=Deva, 1=Manushya, 2=Rakshasa) -- corrected 2026-08-17, audit Phase 1:
  [0,1,2,1,0,1,0,0,2,2,1,1,0,2,0,2,0,2,2,1,1,0,2,2,1,1,0]
"""

import pytest
from app.engines.porutham_engine import (
    _nakshatra_index,
    _rasi_index,
    score_nadi,
    score_ganam,
    score_rasi,
    score_rajju,
    score_vedha,
    compute_porutham,
    GANA,
    NADI,
    RAJJU_GROUPS,
    VEDHA_PAIRS,
    VEDHA_SET,
)
from app.engines.nakshatra_names import canonical_nakshatra_list


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
#
# Corrected 2026-08-17 (Porutham audit, Phase 1): the prior versions of
# tests 3-5 below asserted against the OLD, buggy GANA table -- their
# docstrings claimed Rohini(3)=Deva and Mirugashirisham(4)=Manushya,
# which were 2 of the 8 misclassified nakshatras the audit found and
# fixed (both are actually Manushya and Deva respectively). Replaced with
# nakshatra pairs whose Gana is unaffected by the fix, and updated the
# Deva+Manushya case to the corrected symmetric scoring (was asymmetric:
# 5 one way, 0 reversed; now 5 both ways -- see score_ganam()'s docstring
# for why the asymmetry wasn't kept).

def test_gana_same_full_score():
    """Ashwini(0, Deva) and Mirugashirisham(4, Deva) → same Gana → score=6."""
    result = score_ganam(0, 4)
    assert result["score"] == 6
    assert result["pass"] is True


# ── 4. Gana Deva + Manushya ───────────────────────────────────────────────────

def test_gana_deva_plus_manushya():
    """
    Ashwini(0, Deva) + Bharani(1, Manushya) → score=5, symmetric --
    confirmed the same in both directions (see score_ganam() docstring).
    """
    result = score_ganam(0, 1)
    assert result["score"] == 5

    result_rev = score_ganam(1, 0)
    assert result_rev["score"] == 5


# ── 5. Gana Deva + Rakshasa ───────────────────────────────────────────────────

def test_gana_deva_plus_rakshasa_zero():
    """Ashwini(0, Deva) + Karthigai(2, Rakshasa) → score=0."""
    result = score_ganam(0, 2)
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
    Ashwini+Aries vs Bharani+Aries scores 20/33 (60.6%) → Good.

    Corrected 2026-08-17 (Porutham audit, Phase 1): the prior example
    (Rohini+Cancer vs Swati+Libra, expected 19/33) baked in the old
    buggy Gana table's misclassification of Rohini as Deva -- under the
    corrected table that pair now scores 18/33 (54.5%), just under the
    Good threshold, landing in Average instead. Replaced with a pair
    unaffected by the Gana fix.
    """
    result = compute_porutham("Ashwini", "Aries", "Bharani", "Aries")
    assert result["grade"] == "Good"
    assert result["mandatory_fail"] is False
    assert result["total_score"] == 20


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


# ── Phase 1 audit regression: full 27-nakshatra Gana table ────────────────────
#
# Locks in the corrected GANA table so this can't silently regress back to
# the 8-misclassification bug the 2026-08-17 audit found. Reference table
# cross-checked against 3+ independent sources this session (see
# porutham_engine.py's GANA comment).

_DEVA = ["Aswini", "Mirugashirisham", "Punarpoosam", "Poosam", "Hastham",
         "Swathi", "Anusham", "Thiruvonam", "Revathi"]
_MANUSHYA = ["Bharani", "Rohini", "Thiruvadirai", "Pooram", "Uthiram",
             "Pooradam", "Uthiradam", "Poorattadhi", "Uthirattadhi"]
_RAKSHASA = ["Karthigai", "Ayilyam", "Magam", "Chittirai", "Visakam",
             "Kettai", "Moolam", "Avittam", "Sadayam"]


@pytest.mark.parametrize("nak_name", _DEVA)
def test_gana_table_deva_group(nak_name):
    idx = _nakshatra_index(nak_name)
    assert GANA[idx] == 0, f"{nak_name} (idx {idx}) should be Deva (0), got {GANA[idx]}"


@pytest.mark.parametrize("nak_name", _MANUSHYA)
def test_gana_table_manushya_group(nak_name):
    idx = _nakshatra_index(nak_name)
    assert GANA[idx] == 1, f"{nak_name} (idx {idx}) should be Manushya (1), got {GANA[idx]}"


@pytest.mark.parametrize("nak_name", _RAKSHASA)
def test_gana_table_rakshasa_group(nak_name):
    idx = _nakshatra_index(nak_name)
    assert GANA[idx] == 2, f"{nak_name} (idx {idx}) should be Rakshasa (2), got {GANA[idx]}"


def test_gana_table_covers_all_27_nakshatras_exactly_once():
    names = canonical_nakshatra_list()
    assert len(names) == 27
    assert len(GANA) == 27
    covered = set(_DEVA) | set(_MANUSHYA) | set(_RAKSHASA)
    assert covered == set(names), covered.symmetric_difference(set(names))


# ── Phase 1 audit regression: Ganam scoring gradient (symmetric) ──────────────

def test_ganam_gradient_same_gana_six_regardless_of_which_gana():
    # Deva+Deva, Manushya+Manushya, Rakshasa+Rakshasa
    assert score_ganam(0, 4)["score"] == 6   # Deva+Deva
    assert score_ganam(1, 3)["score"] == 6   # Manushya+Manushya
    assert score_ganam(2, 8)["score"] == 6   # Rakshasa+Rakshasa


def test_ganam_gradient_deva_manushya_symmetric_five():
    assert score_ganam(0, 1)["score"] == 5
    assert score_ganam(1, 0)["score"] == 5


def test_ganam_gradient_manushya_rakshasa_symmetric_one():
    """
    Corrected 2026-08-17: prior code had this at 0 both directions. A
    fresh 2nd-source check for genuine directionality here was
    inconclusive (the Tamil-context source was internally inconsistent
    about which direction is worse), so per this session's tiebreak rule
    this stays symmetric rather than encoding an unconfirmed asymmetry.
    """
    assert score_ganam(1, 2)["score"] == 1
    assert score_ganam(2, 1)["score"] == 1


def test_ganam_gradient_deva_rakshasa_symmetric_zero():
    assert score_ganam(0, 2)["score"] == 0
    assert score_ganam(2, 0)["score"] == 0


# ── Phase 2 audit regression: full 27-nakshatra Nadi table ────────────────────
#
# Locks in the corrected NADI table so this can't silently regress back to
# the 6-misclassification bug the 2026-08-17 audit found. Nadi is a
# mandatory dosha category, so a wrong table here can flip a real
# pass/fail dealbreaker. Reference table cross-checked against 4+
# independent sources this session (see porutham_engine.py's NADI comment).

_AADI = ["Aswini", "Thiruvadirai", "Punarpoosam", "Uthiram", "Hastham",
         "Kettai", "Moolam", "Sadayam", "Poorattadhi"]
_MADHYA = ["Bharani", "Mirugashirisham", "Poosam", "Pooram", "Chittirai",
           "Anusham", "Pooradam", "Avittam", "Uthirattadhi"]
_ANTYA = ["Karthigai", "Rohini", "Ayilyam", "Magam", "Swathi", "Visakam",
          "Uthiradam", "Thiruvonam", "Revathi"]


@pytest.mark.parametrize("nak_name", _AADI)
def test_nadi_table_aadi_group(nak_name):
    idx = _nakshatra_index(nak_name)
    assert NADI[idx] == 0, f"{nak_name} (idx {idx}) should be Aadi (0), got {NADI[idx]}"


@pytest.mark.parametrize("nak_name", _MADHYA)
def test_nadi_table_madhya_group(nak_name):
    idx = _nakshatra_index(nak_name)
    assert NADI[idx] == 1, f"{nak_name} (idx {idx}) should be Madhya (1), got {NADI[idx]}"


@pytest.mark.parametrize("nak_name", _ANTYA)
def test_nadi_table_antya_group(nak_name):
    idx = _nakshatra_index(nak_name)
    assert NADI[idx] == 2, f"{nak_name} (idx {idx}) should be Antya (2), got {NADI[idx]}"


def test_nadi_table_covers_all_27_nakshatras_exactly_once():
    names = canonical_nakshatra_list()
    assert len(names) == 27
    assert len(NADI) == 27
    covered = set(_AADI) | set(_MADHYA) | set(_ANTYA)
    assert covered == set(names), covered.symmetric_difference(set(names))


# ── Phase 3 audit regression: full 27-nakshatra Rajju group table ─────────────
#
# Locks in the corrected RAJJU_GROUPS so this can't silently regress back
# to the scrambled-table bug the 2026-08-17 audit found -- every one of
# the 5 groups was previously split across 2-3 different engine groups,
# essentially a total mismatch. Rajju is a mandatory dosha category, so
# this was the highest-stakes fix in the whole audit. Reference groups
# cross-checked against 3 independent sources this session (all agreeing
# exactly, one Tamil-context specific) -- see porutham_engine.py's
# RAJJU_GROUPS comment.

_SIRO = ["Chittirai", "Mirugashirisham", "Avittam"]
_KANTHA = ["Thiruvadirai", "Rohini", "Swathi", "Hastham", "Thiruvonam", "Sadayam"]
_NABHI = ["Karthigai", "Uthiram", "Punarpoosam", "Visakam", "Poorattadhi", "Uthiradam"]
_KATI = ["Poosam", "Bharani", "Pooram", "Anusham", "Uthirattadhi", "Pooradam"]
_PADA = ["Aswini", "Ayilyam", "Magam", "Moolam", "Kettai", "Revathi"]

_RAJJU_REFERENCE_GROUPS = {
    "Siro": _SIRO, "Kantha": _KANTHA, "Nabhi": _NABHI, "Kati": _KATI, "Pada": _PADA,
}


@pytest.mark.parametrize("group_name,members", _RAJJU_REFERENCE_GROUPS.items())
def test_rajju_table_group_members_share_one_engine_group(group_name, members):
    """Every nakshatra in a reference group must land in the SAME engine
    group as every other member of that reference group (not just the
    right size) -- this is what actually broke before the fix."""
    idxs = [_nakshatra_index(m) for m in members]
    engine_groups_hit = set()
    for idx in idxs:
        for gi, group in enumerate(RAJJU_GROUPS):
            if idx in group:
                engine_groups_hit.add(gi)
    assert len(engine_groups_hit) == 1, (
        f"{group_name} members {members} should all share one engine "
        f"RAJJU_GROUPS entry, but landed in {len(engine_groups_hit)}"
    )


def test_rajju_table_covers_all_27_nakshatras_exactly_once():
    names = canonical_nakshatra_list()
    assert len(names) == 27
    assert sum(len(g) for g in RAJJU_GROUPS) == 27
    covered = set(_SIRO) | set(_KANTHA) | set(_NABHI) | set(_KATI) | set(_PADA)
    assert covered == set(names), covered.symmetric_difference(set(names))


def test_rajju_table_group_sizes():
    """Siro has 3 members; the other four have 6 each."""
    sizes = sorted(len(g) for g in RAJJU_GROUPS)
    assert sizes == [3, 6, 6, 6, 6]


def test_rajju_same_group_fails():
    """Two nakshatras in the same reference group (e.g. both Pada) -> fail."""
    result = score_rajju(_nakshatra_index("Aswini"), _nakshatra_index("Ayilyam"))
    assert result["pass"] is False
    assert result["mandatory"] is True


def test_rajju_different_group_passes():
    result = score_rajju(_nakshatra_index("Bharani"), _nakshatra_index("Swathi"))
    assert result["pass"] is True


def test_rajju_no_cancellation_exception_logic():
    """
    Confirmed by the audit: no classically-recognized cancellation/
    exception mechanism exists for Rajju dosha -- flat same-group=fail is
    correct as-is, not a gap to fill. This test just locks in that the
    function stays a pure group-membership check (no extra parameters,
    no special-casing) so a well-intentioned future "add the exception"
    change doesn't get made without discussion.
    """
    import inspect
    sig = inspect.signature(score_rajju)
    assert list(sig.parameters) == ["boy_nak", "girl_nak"]


# ── Phase 4 audit regression: full Vedha clash-pair table ─────────────────────
#
# Locks in the corrected VEDHA_PAIRS so this can't silently regress back
# to the fully-mismatched table (plus the dead, out-of-range (9,27)
# Magha placeholder) the 2026-08-17 audit found. Vedha is a mandatory
# dosha category, so a wrong or unreachable pair here can hide a real
# dealbreaker. Cross-checked against 2 independent sources this session,
# agreeing exactly -- see porutham_engine.py's VEDHA_PAIRS comment.

_VEDHA_REFERENCE_PAIRS = [
    ("Karthigai", "Visakam"), ("Aswini", "Kettai"), ("Rohini", "Swathi"),
    ("Bharani", "Anusham"), ("Thiruvadirai", "Thiruvonam"),
    ("Punarpoosam", "Uthiradam"), ("Poosam", "Pooradam"),
    ("Ayilyam", "Moolam"), ("Magam", "Revathi"),
    ("Pooram", "Uthirattadhi"), ("Uthiram", "Poorattadhi"),
    ("Hastham", "Sadayam"),
]

_VEDHA_UNPAIRED = ["Mirugashirisham", "Chittirai", "Avittam"]


@pytest.mark.parametrize("nak_a,nak_b", _VEDHA_REFERENCE_PAIRS)
def test_vedha_table_reference_pair_fails(nak_a, nak_b):
    result = score_vedha(_nakshatra_index(nak_a), _nakshatra_index(nak_b))
    assert result["pass"] is False, f"{nak_a}-{nak_b} should be a Vedha clash"
    assert result["mandatory"] is True


def test_vedha_table_has_exactly_12_pairs():
    assert len(VEDHA_PAIRS) == 12
    assert len(VEDHA_SET) == 12


def test_vedha_table_covers_24_of_27_nakshatras():
    names = canonical_nakshatra_list()
    paired = set()
    for a, b in _VEDHA_REFERENCE_PAIRS:
        paired.add(a)
        paired.add(b)
    assert len(paired) == 24
    unpaired = set(names) - paired
    assert unpaired == set(_VEDHA_UNPAIRED)


def test_vedha_magha_and_ashlesha_reachable_not_dead_indices():
    """
    Regression test for the exact bug found: the old code's dead
    (9, 27) placeholder meant Magha could NEVER fail Vedha against any
    real nakshatra, regardless of partner. Confirm both Magha and
    Ashlesha now correctly clash with their real partners.
    """
    magha = _nakshatra_index("Magam")
    revati = _nakshatra_index("Revathi")
    ashlesha = _nakshatra_index("Ayilyam")
    mula = _nakshatra_index("Moolam")

    assert score_vedha(magha, revati)["pass"] is False
    assert score_vedha(ashlesha, mula)["pass"] is False

    # Sanity: Magha does NOT clash with an unrelated nakshatra
    assert score_vedha(magha, _nakshatra_index("Aswini"))["pass"] is True


@pytest.mark.parametrize("nak_name", _VEDHA_UNPAIRED)
def test_vedha_unpaired_nakshatras_never_clash(nak_name):
    """Mirugashirisham, Chittirai, Avittam have no documented Vedha
    partner in either source -- confirm they never appear in VEDHA_SET
    (not a bug; this is the correct, sourced state)."""
    idx = _nakshatra_index(nak_name)
    for a, b in VEDHA_SET:
        assert idx not in (a, b), f"{nak_name} unexpectedly appears in a Vedha pair"
