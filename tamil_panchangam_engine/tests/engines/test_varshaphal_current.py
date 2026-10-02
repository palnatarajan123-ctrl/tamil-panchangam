# tests/engines/test_varshaphal_current.py
"""
get_varshaphal_in_force() (varshaphal_engine.py): the annual chart IN
FORCE on a date, cached per chart per solar-return year. Used by chat,
family chat and (since 2026-10-01) monthly predictive signals.
"""
from datetime import date
from unittest.mock import patch

from app.engines import varshaphal_engine as ve


def _payload(dob="1971-02-01", sun_lon=287.5, lagna_lon=15.0):
    return {
        "birth_details": {"date_of_birth": dob, "latitude": 13.08, "longitude": 80.27},
        "ephemeris": {"planets": {"Sun": {"longitude_deg": sun_lon}}, "lagna": {"longitude_deg": lagna_lon}},
        "chart_metadata": {"ayanamsa": "lahiri"},
    }


def test_birthday_already_passed_uses_this_years_return():
    vp = ve.get_varshaphal_in_force(None, _payload(), on_date=date(2026, 10, 2))
    assert vp["year"] == 2026
    assert date.fromisoformat(vp["solar_return_date"]) <= date(2026, 10, 2)


def test_birthday_still_ahead_uses_last_years_return():
    # Sun ~ late Libra sidereal -> return around mid-November.
    vp = ve.get_varshaphal_in_force(None, _payload(dob="1998-11-15", sun_lon=209.0), on_date=date(2026, 10, 2))
    assert vp["year"] == 2025
    assert vp["solar_return_date"].startswith("2025-11")


def test_muntha_from_natal_and_from_annual_lagna():
    vp = ve.get_varshaphal_in_force(None, _payload(), on_date=date(2026, 10, 2))
    age = 2026 - 1971  # 55
    natal_lagna_idx = 0  # 15 deg -> Aries
    assert ve.RASI_NAMES.index(vp["muntha"]) == (natal_lagna_idx + age) % 12  # Scorpio
    assert vp["muntha_house_from_natal_lagna"] == age % 12 + 1  # 8th from natal Lagna
    annual_idx = ve.RASI_NAMES.index(vp["lagna"])
    assert vp["muntha_house"] == (ve.RASI_NAMES.index(vp["muntha"]) - annual_idx) % 12 + 1


def test_cached_entry_is_reused_not_recomputed():
    payload = _payload()
    ve.get_varshaphal_in_force(None, payload, on_date=date(2026, 10, 2))
    assert "2026" in payload[ve._CACHE_KEY]
    with patch.object(ve, "compute_varshaphal", side_effect=AssertionError("recomputed")):
        ve.get_varshaphal_in_force(None, payload, on_date=date(2026, 10, 2))


def test_stale_cache_version_is_recomputed():
    payload = _payload()
    payload[ve._CACHE_KEY] = {"2026": {"cache_version": 0, "solar_return_date": "2026-02-01"}}
    vp = ve.get_varshaphal_in_force(None, payload, on_date=date(2026, 10, 2))
    assert vp["cache_version"] == ve._CACHE_VERSION


def test_formatters_do_not_call_it_varshesha():
    vp = ve.get_varshaphal_in_force(None, _payload(), on_date=date(2026, 10, 2))
    verbose = ve.format_varshaphal_context(vp)
    assert "Annual Lagna:" in verbose and "Muntha:" in verbose
    assert "from the annual Lagna" in verbose and "from the natal Lagna" in verbose
    assert "Varshesha" not in verbose and "year-lord" not in verbose
    assert ve.format_varshaphal_compact(vp).startswith("Annual chart (from ")
    assert ve.format_varshaphal_context({}) == "" and ve.format_varshaphal_compact({}) == ""


def test_no_varshesha_label_in_engine_output():
    vp = ve.compute_varshaphal(_payload()["ephemeris"], _payload()["birth_details"], year=2026)
    assert "varshesha" not in vp and "varshesha_house" not in vp
    assert vp["annual_lagna_lord"] == ve._RASI_LORDS[ve.RASI_NAMES.index(vp["lagna"])]


def test_monthly_predictive_signals_use_return_in_force_for_the_month():
    """Monthly reports anchor on the 15th of the prediction month. For a
    mid-November birthday, a September 2026 report must use the Nov 2025
    return, not the not-yet-happened Nov 2026 one (35 cached monthly rows
    across 13 charts had that bug before 2026-10-01)."""
    from app.engines import predictive_signals_engine as pse
    payload = _payload(dob="1998-11-15", sun_lon=209.0)
    with patch("app.db.postgres.get_conn", side_effect=RuntimeError("no db")):
        sig = pse.compute_predictive_signals(payload, None, 2026, 9)
    assert sig["varshaphal"]["year"] == 2025
    assert sig["varshaphal"]["solar_return_date"].startswith("2025-11")
