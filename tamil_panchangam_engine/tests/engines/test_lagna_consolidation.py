"""
Regression test for the 2026-09-14 Lagna call-site consolidation.

3 independent swe.houses_ex() call sites computed the same 2-line
Ascendant formula: ephemeris.py's compute_lagna() (natal chart, the only
one previously independently validated -- see the Southern Hemisphere
audit), upagraha_engine.py's Gulika/Mandi-at-segment-start Lagna, and
varshaphal_engine.py's solar-return Lagna. All three now call the one
shared compute_lagna(). This pins two things: the shared function
produces byte-identical output to the old inlined formula, and the other
two engines now genuinely import and call it (not a second independent
copy reintroduced later).
"""
import inspect

import swisseph as swe

from app.engines.ephemeris import compute_lagna
from app.utils.swisseph_utils import AYANAMSA_MODES

swe.set_ephe_path(".")


def _old_inline_formula(jd: float, lat: float, lon: float, ayanamsa: str) -> float:
    """Replica of what each of the 3 call sites did independently before
    consolidation: caller sets sid_mode, then calls houses_ex directly."""
    swe.set_sid_mode(AYANAMSA_MODES.get(ayanamsa, swe.SIDM_LAHIRI))
    _houses, ascmc = swe.houses_ex(jd, lat, lon, b"P", swe.FLG_SIDEREAL)
    return ascmc[0] % 360


class TestComputeLagnaMatchesOldInlineFormula:
    def test_chennai_j2000(self):
        assert compute_lagna(2451545.0, 13.0827, 80.2707, "lahiri") == \
            _old_inline_formula(2451545.0, 13.0827, 80.2707, "lahiri")

    def test_southern_hemisphere(self):
        jd = 2461212.5
        assert compute_lagna(jd, -33.8688, 151.2093, "lahiri") == \
            _old_inline_formula(jd, -33.8688, 151.2093, "lahiri")

    def test_kp_ayanamsa(self):
        jd = 2459950.75
        assert compute_lagna(jd, 13.0827, 80.2707, "kp") == \
            _old_inline_formula(jd, 13.0827, 80.2707, "kp")

    def test_default_ayanamsa_is_lahiri(self):
        jd = 2451545.0
        assert compute_lagna(jd, 13.0827, 80.2707) == \
            compute_lagna(jd, 13.0827, 80.2707, "lahiri")


class TestOtherEnginesUseSharedComputeLagna:
    """Structural guard: upagraha_engine.py and varshaphal_engine.py must
    import ephemeris.compute_lagna, not reimplement swe.houses_ex()
    themselves -- verified by source inspection so a future edit that
    reintroduces an inline swe.houses_ex() call shows up here."""

    def test_upagraha_engine_source_has_no_inline_houses_ex(self):
        import app.engines.upagraha_engine as mod
        source = inspect.getsource(mod)
        assert "= swe.houses_ex(" not in source
        assert "from app.engines.ephemeris import compute_lagna" in source

    def test_varshaphal_engine_source_has_no_inline_houses_ex(self):
        import app.engines.varshaphal_engine as mod
        source = inspect.getsource(mod)
        assert "= swe.houses_ex(" not in source
        assert "from app.engines.ephemeris import compute_lagna" in source
