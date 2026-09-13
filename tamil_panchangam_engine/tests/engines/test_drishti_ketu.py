"""
Regression tests for Ketu's drishti (aspect) being fully excluded.

compute_drishti()'s main loop used to unconditionally skip Ketu
("if planet_name in ["Ketu"]: continue"), so Ketu cast zero aspects in
practice regardless of PARASHARA_SPECIAL_ASPECTS already listing its
5th/9th special aspects correctly -- that entry was dead. Decided
doctrine (2026-09-13): default to NODAL_DRISHTI_MODE="SYMMETRIC_NODES"
(Ketu aspects the same as Rahu), specifically validated for Tamil/South
Indian practice -- see CLAUDE.md's 2026-09-13 entry for sourcing.
"""
from app.engines.drishti_engine import compute_drishti, NODAL_DRISHTI_MODE


def _ephemeris_with_ketu(ketu_longitude=15.0):
    # Ketu at 15deg Aries (house 1 if lagna=0) -> should cast 5th/7th/9th
    # special+regular aspects onto houses 5, 7, 9 (0-indexed lagna).
    return {
        "planets": {
            "Ketu": {"longitude_deg": ketu_longitude},
        },
        "lagna": {"longitude_deg": 0.0},
    }


def test_default_mode_is_symmetric_nodes():
    assert NODAL_DRISHTI_MODE == "SYMMETRIC_NODES"


def test_ketu_casts_aspects_under_default_symmetric_mode():
    eph = _ephemeris_with_ketu()
    result = compute_drishti(ephemeris=eph, houses={}, lagna_longitude=0.0)
    ketu_aspects = [a for a in result["aspects"] if a["planet"] == "Ketu"]
    assert len(ketu_aspects) == 3  # 5th, 7th, 9th from its house
    aspected_houses = {a["aspected_house"] for a in ketu_aspects}
    assert aspected_houses == {5, 7, 9}


def test_ketu_casts_no_aspects_when_mode_overridden():
    eph = _ephemeris_with_ketu()
    result = compute_drishti(
        ephemeris=eph, houses={}, lagna_longitude=0.0, nodal_drishti_mode="RAHU_ONLY"
    )
    ketu_aspects = [a for a in result["aspects"] if a["planet"] == "Ketu"]
    assert ketu_aspects == []


def test_ketu_included_in_significant_aspects_filter():
    eph = _ephemeris_with_ketu()
    result = compute_drishti(ephemeris=eph, houses={}, lagna_longitude=0.0)
    ketu_significant = [a for a in result["significant_aspects"] if a["planet"] == "Ketu"]
    assert len(ketu_significant) > 0
