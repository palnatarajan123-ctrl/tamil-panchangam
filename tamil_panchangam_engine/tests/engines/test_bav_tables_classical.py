# tests/engines/test_bav_tables_classical.py
"""
bhinnashtakavarga_engine.BAV_TABLES must be the classical Parashari tables
(corrected 2026-10-02; 10 contributor rows across 6 planets had been wrong,
Jupiter's fixed first, the other 9 here). Verified per sign, not by totals:

  A. B.V. Raman's Standard Horoscope -- Raman's published per-sign BAVs for
     Moon, Mars, Mercury and Jupiter (vedastro.org "Mastering Ashtakavarga
     Part 2").
  B. 24 Mar 1989 04:45 IST, Rudraprayag (thevedichoroscope.com "Ashtakvarga
     Lessons-1") -- its published Sarvashtakavarga on all 12 signs, which
     needs every planet's table right at once.

BPHS Ch. 66 vv. 43-60 (Santhanam tr.) independently confirms the Sun, Mars
and Mercury Lagna rows; where that translation differs from Raman (7 cells)
its readings fail A and B, so Raman's are used.
"""
from app.engines.bhinnashtakavarga_engine import BAV_TABLES, PLANET_KEYS, _compute_planet_bav

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

RAMAN = dict(lagna="Capricorn", sun="Virgo", moon="Aquarius", mars="Scorpio",
             mercury="Libra", jupiter="Gemini", venus="Virgo", saturn="Leo")
# Sidereal (Lahiri) signs from Swiss Ephemeris for the 1989 source's birth data.
RUDRAPRAYAG_1989 = dict(lagna="Aquarius", sun="Pisces", moon="Virgo", mars="Taurus",
                        mercury="Aquarius", jupiter="Taurus", venus="Pisces", saturn="Sagittarius")


def _idx(signs):
    return {k: SIGNS.index(v) for k, v in signs.items()}


def test_classical_totals_for_any_chart():
    expected = {"sun": 48, "moon": 49, "mars": 39, "mercury": 54, "jupiter": 56, "venus": 52, "saturn": 39}
    for offset in range(12):
        idx = {k: (i * 5 + offset) % 12 for i, k in enumerate(PLANET_KEYS + ["lagna"])}
        assert {p: sum(_compute_planet_bav(p, idx)) for p in PLANET_KEYS} == expected
    assert sum(expected.values()) == 337


def test_corrected_rows():
    assert BAV_TABLES["sun"]["mars"] == [1, 2, 4, 7, 8, 9, 10, 11]
    assert BAV_TABLES["sun"]["mercury"] == [3, 5, 6, 9, 10, 11, 12]
    assert BAV_TABLES["sun"]["venus"] == [6, 7, 12]
    assert BAV_TABLES["sun"]["saturn"] == [1, 2, 4, 7, 8, 9, 10, 11]
    assert BAV_TABLES["sun"]["lagna"] == [3, 4, 6, 10, 11, 12]
    assert BAV_TABLES["moon"]["jupiter"] == [1, 4, 7, 8, 10, 11, 12]
    assert BAV_TABLES["mars"]["lagna"] == [1, 3, 6, 10, 11]
    assert BAV_TABLES["mercury"]["lagna"] == [1, 2, 4, 6, 8, 10, 11]
    assert BAV_TABLES["jupiter"]["saturn"] == [3, 5, 6, 12]
    assert BAV_TABLES["venus"]["mars"] == [3, 5, 6, 9, 11, 12]


def _per_sign(d):
    return [d[s] for s in SIGNS]


def test_raman_standard_horoscope_per_sign():
    idx = _idx(RAMAN)
    published = {
        "moon": _per_sign(dict(Aries=5, Taurus=3, Gemini=5, Cancer=5, Leo=3, Virgo=2, Libra=3, Scorpio=4,
                               Sagittarius=6, Capricorn=5, Aquarius=3, Pisces=5)),
        "mars": _per_sign(dict(Aries=4, Taurus=3, Gemini=4, Cancer=3, Leo=4, Virgo=1, Libra=1, Scorpio=5,
                               Sagittarius=3, Capricorn=2, Aquarius=5, Pisces=4)),
        "mercury": _per_sign(dict(Aries=4, Taurus=6, Gemini=4, Cancer=5, Leo=5, Virgo=5, Libra=3, Scorpio=6,
                                  Sagittarius=4, Capricorn=4, Aquarius=5, Pisces=3)),
        "jupiter": [3, 4, 7, 6, 4, 4, 6, 4, 5, 5, 4, 4],
    }
    for planet, row in published.items():
        assert _compute_planet_bav(planet, idx) == row, planet


def test_rudraprayag_1989_sarvashtakavarga_all_12_signs():
    idx = _idx(RUDRAPRAYAG_1989)
    sav = [sum(col) for col in zip(*(_compute_planet_bav(p, idx) for p in PLANET_KEYS))]
    assert sav == [28, 24, 26, 33, 20, 22, 31, 30, 35, 27, 32, 29]
    assert _compute_planet_bav("jupiter", idx)[0] == 3  # published Aries contribution
