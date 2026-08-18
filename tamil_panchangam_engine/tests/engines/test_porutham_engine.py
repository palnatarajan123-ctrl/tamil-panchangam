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
    score_yoni,
    score_rasiyathipaty,
    compute_porutham,
    GANA,
    NADI,
    RAJJU_GROUPS,
    VEDHA_PAIRS,
    VEDHA_SET,
    YONI,
    YONI_HOSTILE_PAIRS,
    RASI_LORDS,
    RASIYATHIPATY_FRIENDLY,
    RASIYATHIPATY_ENEMY,
    score_stree_deergha,
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
    """
    diff=4 (5th from boy, i.e. the 5th/9th relationship) also scores 7 --
    same scoring band as diff=6.

    Confirmed 2026-08-17 (Porutham audit, Phase 7): the audit initially
    flagged this as a possible bug (2 of 3 generic sources suggested
    unfavorable), but a Tamil-context source (dineshcheramastro.com)
    explicitly calls 5-9 "very good... one of the most favorable
    combinations," directly matching this existing treatment. Per this
    session's tiebreak rule, no change was made -- this locks in that
    the value stays 7, not a regression guard against a fix that never
    happened.
    """
    result = score_rasi(0, 4)
    assert result["score"] == 7


# ── Phase 7 audit regression: 4th/10th positional relationship ────────────────

def test_rasi_4th_10th_position_now_favorable():
    """
    Corrected 2026-08-17 (Porutham audit, Phase 7): diff=3 (4th position)
    and diff=9 (10th position) were scored 0 (unfavorable); fixed to 7
    (favorable, full marks) -- 3 of 4 sources this session place this in
    the same auspicious tier as 1/7 and 3/11.
    """
    result_4th = score_rasi(0, 3)   # Aries boy, Cancer girl -> diff=3
    assert result_4th["score"] == 7
    assert result_4th["pass"] is True

    result_10th = score_rasi(0, 9)  # Aries boy, Capricorn girl -> diff=9
    assert result_10th["score"] == 7
    assert result_10th["pass"] is True


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
    Ashwini+Aries vs Purva Ashadha+Sagittarius scores 27/33 (81.8%) → Excellent.
    Verified: Dinam=0, Ganam=5, Yoni=2, Rasi=7, Rasiyathipaty=5, Nadi=8.

    Corrected 2026-08-17 (Porutham audit, Phase 6): Rasiyathipaty was 4,
    not 5, under the old code -- Aries' lord Mars and Sagittarius' lord
    Jupiter are true mutual friends (each considers the other a friend),
    which the old gradient capped at 4 alongside asymmetric one-way
    friendships. The corrected gradient scores genuine mutual friendship
    the same as same-lord (5), so this pair's total moved from 26 to 27.
    """
    result = compute_porutham("Ashwini", "Aries", "Purva Ashadha", "Sagittarius")
    assert result["grade"] == "Excellent"
    assert result["mandatory_fail"] is False
    assert result["total_score"] == 27


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


# ── Phase 5 audit regression: full 27-nakshatra Yoni animal table ─────────────
#
# Locks in the corrected YONI table so this can't silently regress back
# to the scrambled table the 2026-08-17 audit found -- 13 of 14 reference
# animal-pairs were split across different engine codes, essentially a
# total mismatch. Cross-checked against 3 independent sources this
# session (resolving a genuine Purva/Uttara Phalguni Rat-vs-Cow ambiguity
# between the first 2 with a 3rd) -- see porutham_engine.py's YONI
# comment.

_YONI_REFERENCE_GROUPS = {
    "Horse": ["Aswini", "Sadayam"],
    "Elephant": ["Bharani", "Revathi"],
    "Goat": ["Karthigai", "Poosam"],
    "Serpent": ["Rohini", "Mirugashirisham"],
    "Dog": ["Thiruvadirai", "Moolam"],
    "Cat": ["Punarpoosam", "Ayilyam"],
    "Rat": ["Magam", "Pooram"],
    "Cow": ["Uthiram", "Uthirattadhi"],
    "Buffalo": ["Hastham", "Swathi"],
    "Tiger": ["Chittirai", "Visakam"],
    "Deer": ["Anusham", "Kettai"],
    "Monkey": ["Pooradam", "Thiruvonam"],
    "Mongoose": ["Uthiradam"],
    "Lion": ["Avittam", "Poorattadhi"],
}

_YONI_SWORN_ENEMIES = [
    ("Cat", "Rat"), ("Dog", "Deer"), ("Serpent", "Mongoose"),
    ("Elephant", "Lion"), ("Cow", "Tiger"), ("Horse", "Buffalo"),
    ("Monkey", "Goat"),
]


@pytest.mark.parametrize("animal,members", _YONI_REFERENCE_GROUPS.items())
def test_yoni_table_group_members_share_one_animal_code(animal, members):
    """Every nakshatra paired under one animal must land on the SAME
    engine YONI code as its partner -- this is what actually broke
    before the fix (13 of 14 pairs were split across different codes)."""
    codes = set(YONI[_nakshatra_index(m)] for m in members)
    assert len(codes) == 1, f"{animal} members {members} should share one code, got {codes}"


def test_yoni_table_covers_all_27_nakshatras_exactly_once():
    names = canonical_nakshatra_list()
    assert len(names) == 27
    assert len(YONI) == 27
    covered = set()
    for members in _YONI_REFERENCE_GROUPS.values():
        covered |= set(members)
    assert covered == set(names), covered.symmetric_difference(set(names))


def test_yoni_table_purva_uttara_phalguni_rat_cow_resolved():
    """
    The specific ambiguity the audit found and resolved with a 3rd
    source: Magha+Purva Phalguni=Rat (not Uttara Phalguni), Uttara
    Phalguni+Uttara Bhadrapada=Cow (not Purva Phalguni).
    """
    magha = YONI[_nakshatra_index("Magam")]
    purva_phalguni = YONI[_nakshatra_index("Pooram")]
    uttara_phalguni = YONI[_nakshatra_index("Uthiram")]
    uttara_bhadrapada = YONI[_nakshatra_index("Uthirattadhi")]
    assert magha == purva_phalguni, "Magha and Purva Phalguni should share the Rat code"
    assert uttara_phalguni == uttara_bhadrapada, "Uttara Phalguni and Uttara Bhadrapada should share the Cow code"
    assert magha != uttara_phalguni


@pytest.mark.parametrize("animal_a,animal_b", _YONI_SWORN_ENEMIES)
def test_yoni_sworn_enemy_pair_scores_zero(animal_a, animal_b):
    nak_a = _YONI_REFERENCE_GROUPS[animal_a][0]
    nak_b = _YONI_REFERENCE_GROUPS[animal_b][0]
    result = score_yoni(_nakshatra_index(nak_a), _nakshatra_index(nak_b))
    assert result["score"] == 0, f"{animal_a}-{animal_b} should be a sworn-enemy pair scoring 0"


def test_yoni_sworn_enemy_pairs_cover_all_14_animals_with_no_leftovers():
    """Structural sanity check: 7 pairs x 2 animals = all 14 animals,
    exactly once each -- confirms the enemy list is complete, not
    partial."""
    covered = set()
    for a, b in _YONI_SWORN_ENEMIES:
        covered.add(a)
        covered.add(b)
    assert covered == set(_YONI_REFERENCE_GROUPS.keys())
    assert len(_YONI_SWORN_ENEMIES) == 7


def test_yoni_same_animal_scores_four():
    result = score_yoni(_nakshatra_index("Aswini"), _nakshatra_index("Sadayam"))
    assert result["score"] == 4


def test_yoni_non_enemy_different_animal_collapses_to_neutral_two():
    """
    Deliberate, flagged Phase 5 decision: no source this session gave
    the complete Friendly/Neutral/Rival 3-way split, so every non-same,
    non-sworn-enemy pair collapses to 2 rather than guessing which of
    the 3 middle tiers it belongs to. Elephant+Buffalo (neither same nor
    a documented sworn-enemy pair) is the AN Sr x KK real test case.
    """
    result = score_yoni(_nakshatra_index("Bharani"), _nakshatra_index("Swathi"))
    assert result["score"] == 2


# ── Phase 6 audit regression: Graha Maitri friend/enemy table ─────────────────
#
# Locks in the corrected RASIYATHIPATY_FRIENDLY/ENEMY tables so this
# can't silently regress back to the bug the 2026-08-17 audit found --
# Sun, Moon, and Mars each had one wrong friend, and there was no
# concept of "neutral" at all (everything not a friend fell to the same
# bucket as enemy). Cross-checked against 3 independent sources this
# session including a genuine classical Tamil-language text -- see
# porutham_engine.py's RASIYATHIPATY_FRIENDLY comment.
#
# Planet index: 0=Sun, 1=Moon, 2=Mars, 3=Mercury, 4=Jupiter, 5=Venus, 6=Saturn

_PLANET_NAMES = {0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury", 4: "Jupiter", 5: "Venus", 6: "Saturn"}

_GRAHA_MAITRI_REFERENCE = {
    0: {"friend": {1, 2, 4}, "enemy": {5, 6}},
    1: {"friend": {0, 3}, "enemy": set()},
    2: {"friend": {0, 1, 4}, "enemy": {3}},
    3: {"friend": {0, 5}, "enemy": {1}},
    4: {"friend": {0, 1, 2}, "enemy": {3, 5}},
    5: {"friend": {3, 6}, "enemy": {0, 1}},
    6: {"friend": {3, 5}, "enemy": {0, 1, 2}},
}


@pytest.mark.parametrize("planet", range(7))
def test_graha_maitri_friend_set(planet):
    assert RASIYATHIPATY_FRIENDLY[planet] == _GRAHA_MAITRI_REFERENCE[planet]["friend"], (
        f"{_PLANET_NAMES[planet]}'s friend set is wrong"
    )


@pytest.mark.parametrize("planet", range(7))
def test_graha_maitri_enemy_set(planet):
    assert RASIYATHIPATY_ENEMY[planet] == _GRAHA_MAITRI_REFERENCE[planet]["enemy"], (
        f"{_PLANET_NAMES[planet]}'s enemy set is wrong"
    )


def test_graha_maitri_categories_partition_the_other_six_planets():
    """Every planet's friend/enemy/neutral sets should exactly partition
    the other 6 planets (no overlaps, no gaps)."""
    for p in range(7):
        friend = RASIYATHIPATY_FRIENDLY[p]
        enemy = RASIYATHIPATY_ENEMY[p]
        assert not (friend & enemy), f"{_PLANET_NAMES[p]} has overlapping friend/enemy sets"
        others = set(range(7)) - {p}
        neutral = others - friend - enemy
        assert friend | enemy | neutral == others


def test_graha_maitri_mercury_resolved_saturn_is_neutral_not_friend():
    """
    The specific contested finding resolved this phase: Mercury's
    friends are Sun and Venus only. A genuine classical Tamil-language
    source directly confirmed Saturn is NEUTRAL to Mercury, not a
    friend -- settling a 2-source disagreement the audit found.
    """
    assert 6 not in RASIYATHIPATY_FRIENDLY[3]  # Saturn not a Mercury friend
    assert 6 not in RASIYATHIPATY_ENEMY[3]     # nor an enemy -- neutral


def test_graha_maitri_moon_mercury_asymmetric_by_design():
    """Moon considers Mercury a friend; Mercury considers Moon an enemy.
    Confirmed asymmetric relationship, not a bug."""
    assert 3 in RASIYATHIPATY_FRIENDLY[1]  # Moon -> Mercury: friend
    assert 1 in RASIYATHIPATY_ENEMY[3]     # Mercury -> Moon: enemy


# ── Phase 6 audit regression: Rasiyathipaty 7-tier gradient ───────────────────

def test_rasiyathipaty_same_lord_five():
    # Aries(0) and Scorpio(7) are both Mars-ruled
    result = score_rasiyathipaty(0, 7)
    assert result["score"] == 5


def test_rasiyathipaty_mutual_friend_different_lords_five():
    """
    Aries' lord Mars and Sagittarius' lord Jupiter are true mutual
    friends (each considers the other a friend) -- scored 5, same as
    same-lord, per this phase's explicit product decision (the 2nd
    gradient source didn't name this case, but didn't contradict it
    either; mutual friendship is the strongest non-identical relationship
    the table can express).
    """
    result = score_rasiyathipaty(0, 8)  # Aries(Mars) x Sagittarius(Jupiter)
    assert result["score"] == 5


def test_rasiyathipaty_one_friend_one_neutral_four():
    # Cancer(Moon,1) x Aries(Mars,2): Moon->Mars neutral, Mars->Moon friend.
    result = score_rasiyathipaty(3, 0)  # Cancer(Moon) x Aries(Mars)
    assert result["score"] == 4


def test_rasiyathipaty_mutual_neutral_three():
    # Aries(Mars,2) x Taurus(Venus,5): Mars->Venus neutral, Venus->Mars neutral.
    result = score_rasiyathipaty(0, 1)  # Aries(Mars) x Taurus(Venus)
    assert result["score"] == 3


def test_rasiyathipaty_one_friend_one_enemy_one():
    # Cancer(Moon,1) x Gemini(Mercury,3): Moon->Mercury friend, Mercury->Moon enemy.
    result = score_rasiyathipaty(3, 2)  # Cancer(Moon) x Gemini(Mercury)
    assert result["score"] == 1


def test_rasiyathipaty_one_neutral_one_enemy_half():
    # Taurus(Venus,5) x Sagittarius(Jupiter,4): Venus->Jupiter neutral, Jupiter->Venus enemy.
    result = score_rasiyathipaty(1, 8)  # Taurus(Venus) x Sagittarius(Jupiter)
    assert result["score"] == 0.5


def test_rasiyathipaty_mutual_enemy_zero():
    # Leo(Sun,0) x Capricorn(Saturn,6): Sun->Saturn enemy, Saturn->Sun enemy.
    result = score_rasiyathipaty(4, 9)  # Leo(Sun) x Capricorn(Saturn)
    assert result["score"] == 0


def test_rasiyathipaty_gradient_passes_at_three_and_above():
    assert score_rasiyathipaty(0, 7)["pass"] is True   # 5
    assert score_rasiyathipaty(0, 1)["pass"] is True   # 3
    assert score_rasiyathipaty(3, 2)["pass"] is False  # 1
    assert score_rasiyathipaty(4, 9)["pass"] is False  # 0


# ── Phase 8 audit regression: Stree Deergha deliberate convention ─────────────
#
# No fix this phase (genuinely contested across sources, no Tamil-
# specific tiebreaker found). This locks in the current, documented
# convention (diff>=9, flat pass/fail, girl-to-boy direction) so a
# future session sees it's a deliberate choice, not an oversight.

def test_stree_deergha_direction_and_threshold_documented_convention():
    boy_nak = _nakshatra_index("Aswini")  # index 0
    # diff=8 (just under threshold) -> fail
    assert score_stree_deergha(boy_nak, 8)["pass"] is False
    # diff=9 (at threshold) -> pass
    assert score_stree_deergha(boy_nak, 9)["pass"] is True
    # diff=13 (well past threshold) -> pass
    assert score_stree_deergha(boy_nak, 13)["pass"] is True


def test_stree_deergha_not_mandatory():
    result = score_stree_deergha(_nakshatra_index("Aswini"), _nakshatra_index("Uthiram"))
    assert result.get("mandatory") is False
