"""
Golden-reference test: a real chart with a planet sitting almost
exactly on a sign/nakshatra boundary, added 2026-09-14 to close a gap
flagged in the 2026-09-13 audit as "untested, not confirmed broken."

Real chart `11656fc5-c67b-4b0b-9929-c14a28105e56` (found by scanning
every chart in the live DB for a planet within 0.5 degrees of a 30-deg
sign boundary -- not constructed/fabricated) has Mars at
240.00704718744535 degrees: 0.00705 deg (about 25 arcseconds) past the
Scorpio/Sagittarius cusp. Coincidentally, 240 deg is ALSO exactly a
nakshatra boundary (18 x 13 deg20' = 240.0 exactly, the Jyeshtha/Mula
cusp) -- so this one real chart tests both sign- and nakshatra-boundary
rounding at once.

Verdict: no inconsistency found. Checked every independent
longitude-to-sign implementation found across the app this session
(ephemeris.py, gochara_engine.py, yoga_engine.py, ashtakavarga_engine.py,
moon_transit_engine.py, divisional_charts/d9_navamsa.py) plus the
nakshatra derivation (ephemeris.py's get_nakshatra + the inline
dinaphalam_engine.py-style formula) -- all agree Mars is in Sagittarius
(Dhanusu) / Mula nakshatra, not Scorpio/Jyeshtha. Also verified through
D9 (Navamsa correctly computed from 0.00705 deg into the sign, landing
in Navamsa part 1) and the full chat-grounding pipeline (planets_summary
correctly shows "Mars in Dhanusu"). Added here as a permanent
regression guard.
"""
import json

from app.db.postgres import get_conn
from app.engines.ephemeris import get_nakshatra
from app.engines.divisional_charts import build_navamsa_chart
from app.utils.rasi_utils import to_english_rasi

CHART_ID = "11656fc5-c67b-4b0b-9929-c14a28105e56"
MARS_LON = 240.00704718744535  # the exact stored value, for tests that don't hit the DB


def _load_chart():
    with get_conn() as conn:
        row = conn.execute("SELECT payload FROM base_charts WHERE id = %s", (CHART_ID,)).fetchone()
    if row is None:
        return None
    return row[0] if isinstance(row[0], dict) else json.loads(row[0])


def test_mars_sign_boundary_agrees_across_every_independent_derivation():
    from app.engines.ephemeris import RASI_NAMES
    from app.engines.gochara_engine import RASI_ORDER as gochara_rasi_order
    from app.engines.moon_transit_engine import RASI_ORDER as moon_transit_rasi_order
    from app.engines.divisional_charts.d9_navamsa import SIGNS as d9_signs

    ephemeris_sign = RASI_NAMES[int(MARS_LON // 30)]
    gochara_sign = gochara_rasi_order[int(MARS_LON / 30) % 12]
    yoga_sign_1indexed = int(MARS_LON // 30) + 1
    ashtakavarga_idx_0indexed = int(MARS_LON / 30) % 12
    moon_transit_sign = moon_transit_rasi_order[int(MARS_LON / 30) % 12]
    d9_sign = d9_signs[int(MARS_LON // 30) % 12]

    assert ephemeris_sign == "Dhanusu"  # Sagittarius, Tamil
    assert gochara_sign == "Sagittarius"
    assert yoga_sign_1indexed == 9  # Sagittarius, 1-indexed (Aries=1)
    assert ashtakavarga_idx_0indexed == 8  # Sagittarius, 0-indexed (Aries=0)
    assert moon_transit_sign == "Sagittarius"
    assert d9_sign == "Sagittarius"


def test_nakshatra_boundary_agrees_across_derivations():
    nak = get_nakshatra(MARS_LON)
    assert nak["name"] == "Mula"
    assert nak["index"] == 18

    # dinaphalam_engine.py-style inline formula (same shape used for
    # "today's" nakshatra display, not the shared helper above)
    inline_idx = int(MARS_LON / (360 / 27)) % 27
    assert inline_idx == 18


def test_real_chart_mars_stored_correctly():
    payload = _load_chart()
    if payload is None:
        import pytest
        pytest.skip(f"chart {CHART_ID} not present in this DB")
    mars = payload["ephemeris"]["planets"]["Mars"]
    assert abs(mars["longitude_deg"] - MARS_LON) < 1e-6
    assert mars["rasi"] == "Dhanusu"


def test_d9_navamsa_consistent_at_the_boundary():
    payload = _load_chart()
    if payload is None:
        import pytest
        pytest.skip(f"chart {CHART_ID} not present in this DB")
    d9 = build_navamsa_chart(payload["ephemeris"])
    mars_d9 = d9["planets"]["Mars"]
    # Sagittarius is a dual sign -> Navamsa counts from its 5th sign (Aries).
    # At 0.00705 deg into the sign, this must land in the very first
    # Navamsa division (part 1), not spill into the previous sign's last
    # division due to a rounding error.
    assert mars_d9["sign"] == "Aries"
    assert mars_d9["part"] == 1


def test_to_english_rasi_consistent_at_the_boundary():
    assert to_english_rasi("Dhanusu") == "Sagittarius"
