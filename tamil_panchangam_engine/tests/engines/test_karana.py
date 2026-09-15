"""
Regression test for compute_karana() (2026-09-14 fix).

Karana is HALF a tithi (60 half-tithi slots per lunar month, not 30).
compute_karana() used to be called with the 0-29 whole-tithi index
instead of a real 0-59 half-tithi index, so it could never represent two
different karanas within one tithi, and it placed the 4 fixed karanas
(Kimstughna, Shakuni, Chatushpada, Naga) at indices 0/14/15/16 --
the middle of the month -- instead of their real position at the very
start (Kimstughna) and very end (Shakuni/Chatushpada/Naga) of the lunar
month. Confirmed wrong on 3/3 real dates cross-checked against a
published Panchangam (DrikPanchang) before the fix; this test pins the
fixed formula against the same 3 dates plus the fixed-karana boundaries.
"""
from datetime import datetime, timezone, timedelta

from app.engines.panchangam import compute_karana, KARANA_NAMES
from app.utils.swisseph_utils import compute_planet_longitude

IST = timezone(timedelta(hours=5, minutes=30))


class TestKaranaFixedBoundaries:
    def test_index_0_is_kimstughna(self):
        assert compute_karana(0)["name"] == "Kimstughna"

    def test_index_57_is_shakuni(self):
        assert compute_karana(57)["name"] == "Shakuni"

    def test_index_58_is_chatushpada(self):
        assert compute_karana(58)["name"] == "Chatushpada"

    def test_index_59_is_naga(self):
        assert compute_karana(59)["name"] == "Naga"


class TestKaranaMovableCycle:
    def test_first_movable_karana_is_bava(self):
        assert compute_karana(1)["name"] == "Bava"

    def test_seventh_movable_karana_is_vishti(self):
        assert compute_karana(7)["name"] == "Vishti"

    def test_cycle_repeats_eight_times_across_56_slots(self):
        # indices 1-56 must be exactly 8 full cycles of the 7 chara karanas
        names = [compute_karana(i)["name"] for i in range(1, 57)]
        assert names == KARANA_NAMES * 8

    def test_index_56_is_last_of_eighth_cycle(self):
        assert compute_karana(56)["name"] == "Vishti"


class TestKaranaAgainstRealPanchangam:
    """Cross-checked against DrikPanchang for these exact 3 dates --
    see CLAUDE.md's Karana finding. All 3 were WRONG before this fix."""

    def _karana_index_at(self, local_dt: datetime) -> int:
        utc_dt = local_dt.astimezone(timezone.utc)
        sun_lon = compute_planet_longitude("Sun", utc_dt)
        moon_lon = compute_planet_longitude("Moon", utc_dt)
        diff = (moon_lon - sun_lon) % 360
        return int(diff // 6)

    def test_2026_09_14_noon_ist_is_vanija(self):
        idx = self._karana_index_at(datetime(2026, 9, 14, 12, 0, tzinfo=IST))
        assert compute_karana(idx)["name"] == "Vanija"

    def test_2026_01_01_noon_ist_is_kaulava(self):
        idx = self._karana_index_at(datetime(2026, 1, 1, 12, 0, tzinfo=IST))
        assert compute_karana(idx)["name"] == "Kaulava"

    def test_2026_03_15_noon_ist_is_kaulava(self):
        idx = self._karana_index_at(datetime(2026, 3, 15, 12, 0, tzinfo=IST))
        assert compute_karana(idx)["name"] == "Kaulava"
