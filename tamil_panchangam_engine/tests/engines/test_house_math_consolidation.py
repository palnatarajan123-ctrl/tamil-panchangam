"""
Regression tests for the 2026-09-13 house-from-longitude consolidation.

The whole-sign house-from-longitude formula was hand-copied
independently across ~7 files (yoga_engine.py, house_strength_engine.py,
shadbala_engine.py, sade_sati_engine.py, ashtakavarga_engine.py,
drishti_engine.py) -- all verified formula-equivalent before
consolidating into app.utils.house_math. kp_engine.py (real Placidus
cusps) and transit_hits_engine.py (a genuinely different -- and
unverified as correct -- angular-distance formula, NOT whole-sign;
see CLAUDE.md's 2026-09-13 entry) were deliberately NOT touched.
See CLAUDE.md's 2026-09-13 entry.
"""
from app.utils.house_math import house_from_longitude, house_from_sign_number


def _old_house_from_longitude(target_lon, ref_lon):
    return ((int(target_lon // 30) - int(ref_lon // 30) + 12) % 12) + 1


def _old_house_from_sign_number(target_sign, ref_sign):
    return ((target_sign - ref_sign + 12) % 12) + 1


def test_house_from_longitude_matches_original_formula():
    import random
    random.seed(42)
    for _ in range(5000):
        t = random.uniform(0, 360)
        r = random.uniform(0, 360)
        assert house_from_longitude(t, r) == _old_house_from_longitude(t, r)


def test_house_from_sign_number_matches_original_formula_1indexed():
    for a in range(1, 13):
        for b in range(1, 13):
            assert house_from_sign_number(a, b) == _old_house_from_sign_number(a, b)


def test_house_from_sign_number_works_for_0indexed_inputs_too():
    """ashtakavarga_engine.py's fallback branch uses 0-indexed sign
    values (from RASI_TO_INDEX), unlike sade_sati_engine.py's 1-indexed
    ones -- confirm the formula is base-agnostic (only the difference
    between the two inputs matters)."""
    for a in range(0, 12):
        for b in range(0, 12):
            assert house_from_sign_number(a, b) == ((a - b) % 12) + 1


def test_same_sign_gives_house_1():
    assert house_from_longitude(15.0, 20.0) == 1  # both in Aries
    assert house_from_sign_number(3, 3) == 1


def test_next_sign_gives_house_2():
    assert house_from_longitude(35.0, 5.0) == 2  # Taurus from Aries
