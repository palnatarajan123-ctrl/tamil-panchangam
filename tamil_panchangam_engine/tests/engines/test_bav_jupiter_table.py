# tests/engines/test_bav_jupiter_table.py
"""
Jupiter's Bhinnashtakavarga (bhinnashtakavarga_engine.BAV_TABLES["jupiter"]),
fixed 2026-10-02: Saturn's contribution row was [3, 5, 6, 11, 12]; classical
(BPHS / B.V. Raman) is [3, 5, 6, 12]. Jupiter's total was 57, must be 56.

Verified against two independent worked examples, per sign, not just the sum:
  1. B.V. Raman's Standard Horoscope -- Jupiter's published BAV per sign
     (vedastro.org "Mastering Ashtakavarga Part 2").
  2. 24 Mar 1989 04:45 IST, Rudraprayag (thevedichoroscope.com "Ashtakvarga
     Lessons-1") -- publishes Jupiter-from-Saturn as 3,5,6,12 and Jupiter's
     Aries bindu (3) in its Aries breakdown "3+4+3+6+3+4+5=28".

The OTHER planets' tables still differ from classical in 9 rows (Sun x5,
Moon, Mars, Mercury, Venus); see CLAUDE.md. Those are deliberately not
changed here, and this file pins that they weren't.
"""
from app.engines.bhinnashtakavarga_engine import BAV_TABLES, PLANET_KEYS, _compute_planet_bav

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def _idx(**signs):
    return {k: SIGNS.index(v) for k, v in signs.items()}


def test_jupiter_saturn_row_is_classical():
    assert BAV_TABLES["jupiter"]["saturn"] == [3, 5, 6, 12]


def test_jupiter_total_is_56_for_any_chart():
    for offset in range(12):
        idx = {k: (i * 5 + offset) % 12 for i, k in enumerate(PLANET_KEYS + ["lagna"])}
        assert sum(_compute_planet_bav("jupiter", idx)) == 56


def test_raman_standard_horoscope_jupiter_bav_per_sign():
    idx = _idx(lagna="Capricorn", sun="Virgo", moon="Aquarius", mars="Scorpio",
               mercury="Libra", jupiter="Gemini", venus="Virgo", saturn="Leo")
    assert _compute_planet_bav("jupiter", idx) == [3, 4, 7, 6, 4, 4, 6, 4, 5, 5, 4, 4]


def test_rudraprayag_1989_jupiter_bav():
    # Sidereal (Lahiri) signs computed with Swiss Ephemeris for the source's
    # birth data. Aries = 3 is published; the full row is what the classical
    # tables give -- the same tables reproduce that source's published
    # Sarvashtakavarga on all 12 signs.
    idx = _idx(lagna="Aquarius", sun="Pisces", moon="Virgo", mars="Taurus",
               mercury="Aquarius", jupiter="Taurus", venus="Pisces", saturn="Sagittarius")
    bav = _compute_planet_bav("jupiter", idx)
    assert bav[0] == 3
    assert bav == [3, 7, 5, 5, 4, 1, 4, 7, 6, 3, 5, 6]


def test_other_planets_totals_unchanged_by_this_fix():
    # Pre-fix totals: still not all classical (Moon 48 vs 49, Mars 41 vs 39),
    # but this commit must not move them.
    idx = _idx(lagna="Capricorn", sun="Virgo", moon="Aquarius", mars="Scorpio",
               mercury="Libra", jupiter="Gemini", venus="Virgo", saturn="Leo")
    totals = {p: sum(_compute_planet_bav(p, idx)) for p in PLANET_KEYS}
    assert totals == {"sun": 48, "moon": 48, "mars": 41, "mercury": 54,
                      "jupiter": 56, "venus": 52, "saturn": 39}
