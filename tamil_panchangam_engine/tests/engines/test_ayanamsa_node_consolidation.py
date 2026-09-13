"""
Regression tests for the 2026-09-13 ayanamsa/node_type constant
consolidation. AYANAMSA_MODES and NODE_TYPES used to be independently
redefined in ephemeris.py (in addition to swisseph_utils.py, the now-sole
canonical source), and 4 more engines (varshaphal_engine.py,
special_lagnas_engine.py, upagraha_engine.py, dinaphalam_engine.py)
called swe.calc_ut()/swe.set_sid_mode() directly instead of through a
shared wrapper. See CLAUDE.md's 2026-09-13 entry.
"""
from datetime import datetime

from app.utils.swisseph_utils import (
    compute_planet_longitude,
    compute_planet_longitude_at_jd,
    to_julian_day,
    AYANAMSA_MODES,
    NODE_TYPES,
)
from app.engines.ephemeris import AYANAMSA_MODES as ephemeris_ayanamsa_modes
from app.engines.ephemeris import NODE_TYPES as ephemeris_node_types
from app.engines.ephemeris import PLANETS as ephemeris_planets
from app.utils.swisseph_utils import PLANETS as swisseph_utils_planets


def test_ephemeris_imports_shared_constants_not_local_copies():
    assert ephemeris_ayanamsa_modes is AYANAMSA_MODES
    assert ephemeris_node_types is NODE_TYPES
    assert ephemeris_planets is swisseph_utils_planets


def test_compute_planet_longitude_at_jd_matches_datetime_variant():
    dt = datetime(2026, 9, 13, 12, 0, 0)
    jd = to_julian_day(dt)
    for planet in ("Sun", "Moon", "Rahu", "Ketu"):
        via_datetime = compute_planet_longitude(planet, dt)
        via_jd = compute_planet_longitude_at_jd(planet, jd)
        assert via_datetime == via_jd


def test_compute_planet_longitude_at_jd_respects_node_type():
    dt = datetime(2026, 11, 30)
    jd = to_julian_day(dt)
    mean = compute_planet_longitude_at_jd("Rahu", jd, node_type="mean")
    true = compute_planet_longitude_at_jd("Rahu", jd, node_type="true")
    assert mean != true
