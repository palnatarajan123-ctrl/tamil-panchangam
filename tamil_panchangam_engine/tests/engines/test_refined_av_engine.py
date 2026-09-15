"""
Regression test for refined_av_engine.py's Ekadhipatya Shodhana fix
(2026-09-14).

The pre-fix version used bindu-count > 0 as a proxy for "sign is occupied
by a natal planet" -- a proxy that has no basis in the classical rule and
was confirmed wrong by concrete counter-example: an equal 5/5 bindu pair
should both go to zero if genuinely unoccupied (this file's old code left
it at (5, 0), matching neither the "both occupied" nor "both unoccupied"
outcome), and an unequal 5/3 unoccupied pair should both become 3 (old
code gave (5, 2), an arbitrary "a - b" calculation from neither rule).

This fix takes real natal-planet occupancy (from longitude_deg // 30,
not from matching a 'rasi' string -- see compute_refined_av()'s
docstring for the separate spelling-mismatch reason) and implements the
three real sub-cases.
"""
from app.engines.refined_av_engine import (
    _ekadhipatya_shodhana,
    compute_refined_av,
    _EKADHIPATYA_PAIRS,
)


def _bindus(overrides: dict) -> list:
    arr = [0.0] * 12
    for i, v in overrides.items():
        arr[i] = v
    return arr


class TestEkadhipatyaShodhanaSubCases:
    """All 4 cases use the Venus pair (1, 6) = Rishabam/Thulam."""

    def test_both_occupied_no_reduction(self):
        result = _ekadhipatya_shodhana(_bindus({1: 5, 6: 3}), occupied_signs={1, 6})
        assert result[1] == 5
        assert result[6] == 3

    def test_both_unoccupied_unequal_reduces_higher_to_lower(self):
        result = _ekadhipatya_shodhana(_bindus({1: 5, 6: 3}), occupied_signs=set())
        assert result[1] == 3
        assert result[6] == 3

    def test_both_unoccupied_equal_is_a_noop(self):
        result = _ekadhipatya_shodhana(_bindus({1: 5, 6: 5}), occupied_signs=set())
        assert result[1] == 5
        assert result[6] == 5

    def test_one_occupied_empty_sign_goes_to_zero_regardless_of_bindu_count(self):
        # Unoccupied sign (6) has MORE bindus than the occupied one (1) --
        # old bindu>0-proxy code would have treated 6 as "occupied" (since
        # 7 > 0) and reduced 1 instead. Real rule only cares about
        # occupancy, not bindu count.
        result = _ekadhipatya_shodhana(_bindus({1: 4, 6: 7}), occupied_signs={1})
        assert result[1] == 4
        assert result[6] == 0

    def test_all_pairs_processed(self):
        bindus = _bindus({i: 5 for pair in _EKADHIPATYA_PAIRS for i in pair})
        result = _ekadhipatya_shodhana(bindus, occupied_signs=set())
        for i, j in _EKADHIPATYA_PAIRS:
            assert result[i] == 5
            assert result[j] == 5


class TestComputeRefinedAvOccupancy:
    def _bav(self, bindus_by_planet: dict) -> dict:
        return {
            planet: {"bindus_per_sign": bindus}
            for planet, bindus in bindus_by_planet.items()
        }

    def test_occupancy_derived_from_longitude_not_rasi_string(self):
        # Mercury natal planet at 35 deg -> sign index 1 (Rishabam/Taurus).
        # If this were matched by rasi-string against this file's own
        # (differently-spelled) RASI_NAMES instead of longitude, a
        # spelling mismatch could silently fail to register occupancy.
        natal_planets = {"Mercury": {"longitude_deg": 35.0}}
        bav = self._bav({"mercury": _bindus({1: 5, 6: 3})})
        result = compute_refined_av(bav, natal_planets=natal_planets)
        scores = result["refined_scores"]["Mercury"]
        # sign 1 = Rishabam (occupied), sign 6 = Thulam (unoccupied) ->
        # one-occupied sub-case: Thulam (unoccupied) goes to 0.
        assert scores["Rishabam"] == 5.0
        assert scores["Thulam"] == 0.0

    def test_missing_natal_planets_skips_ekadhipatya_but_keeps_trikona(self):
        bav = self._bav({"mercury": _bindus({1: 5, 6: 3})})
        result_with_skip = compute_refined_av(bav, natal_planets=None)
        # No Ekadhipatya reduction applied -- Trikona-only result stands
        # (Trikona groups here don't touch indices 1/6, so bindus pass through).
        scores = result_with_skip["refined_scores"]["Mercury"]
        assert scores["Rishabam"] == 5.0
        assert scores["Thulam"] == 3.0

    def test_empty_natal_planets_dict_treated_as_no_occupancy_info(self):
        bav = self._bav({"mercury": _bindus({1: 5, 6: 3})})
        result = compute_refined_av(bav, natal_planets={})
        scores = result["refined_scores"]["Mercury"]
        assert scores["Rishabam"] == 5.0
        assert scores["Thulam"] == 3.0
