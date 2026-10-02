# tests/engines/test_bav_transit_scores.py
"""
BAV "transit scores" must score the sign a planet is TRANSITING (2026-10-02).

compute_bhinnashtakavarga() used to return "transit_scores" built from each
planet's NATAL sign, and payload_builder._build_bav_context() sent those to
the monthly/yearly LLM as "BAV bindu scores for current Saturn/Jupiter/Rahu
transits" while ignoring the gochara it was given. 69 of 82 cached reports'
"transit backing" sentence had the wrong class (e.g. f5da25da Sep 2026:
"Jupiter's transit is classically well-backed" -- natal sign 6, transit 2).
"""
from app.engines.bhinnashtakavarga_engine import compute_bav_transit_scores, compute_bhinnashtakavarga
from app.llm.payload_builder import _build_bav_context


def _bav():
    eph = {"lagna": {"longitude_deg": 285.0}, "planets": {
        "Sun": {"longitude_deg": 160.0}, "Moon": {"longitude_deg": 310.0}, "Mars": {"longitude_deg": 220.0},
        "Mercury": {"longitude_deg": 185.0}, "Jupiter": {"longitude_deg": 75.0},
        "Venus": {"longitude_deg": 165.0}, "Saturn": {"longitude_deg": 130.0}}}
    return compute_bhinnashtakavarga(eph)


def test_stored_bav_no_longer_carries_natal_transit_scores():
    assert "transit_scores" not in _bav()


def test_transit_scores_read_the_transit_sign():
    bav = _bav()
    ts = compute_bav_transit_scores(bav, {"saturn": 345.0, "jupiter": 112.0, "rahu": 304.0})
    assert ts["saturn"]["transit_sign_index"] == 11 and ts["saturn"]["bav_score"] == bav["saturn"]["bindus_per_sign"][11]
    assert ts["jupiter"]["transit_sign_index"] == 3 and ts["jupiter"]["bav_score"] == bav["jupiter"]["bindus_per_sign"][3]
    assert ts["jupiter"]["sav_score"] == bav["sarvashtakavarga"][3]
    assert ts["rahu"]["transit_sign_index"] == 10 and "bav_score" not in ts["rahu"]


def test_bav_context_uses_gochara_not_natal_sign():
    bav = _bav()
    gochara = {"saturn": {"longitude": 345.0}, "jupiter": {"longitude": 112.0},
               "rahu_ketu": {"rahu_rasi": "Aquarius", "rahu_degree_in_sign": 4.3}}
    ctx = _build_bav_context(bav, gochara)
    assert ctx["jupiter"]["bav_score"] == bav["jupiter"]["bindus_per_sign"][3]   # transit sign (Cancer)
    assert ctx["saturn"]["bav_score"] == bav["saturn"]["bindus_per_sign"][11]    # transit sign (Pisces)
    # a different month (different gochara) gives a different score source
    moved = _build_bav_context(bav, {"jupiter": {"longitude": 75.0}})
    assert moved["jupiter"]["bav_score"] == bav["jupiter"]["bindus_per_sign"][2]
    assert _build_bav_context(bav, {}) == {}
