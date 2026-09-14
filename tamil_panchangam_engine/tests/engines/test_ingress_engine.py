"""
Tests for ingress_engine.py -- the coarse-then-refine peyarchi (sign
change) date computation, and the planet_ingress_events cache.

Real astronomical values pinned here were verified during this
feature's build against a 264-call exhaustive day-by-day scan (Rahu,
Jupiter) and cross-checked against external Tamil peyarchi sources
(Rahu into Capricorn Dec 5 2026 mean node; Jupiter into Cancer ~June
2026, confirmed via a coarser sample sweep) -- see CLAUDE.md's
2026-09-13 entry.

2026-09-14: added permanent Jupiter/Saturn confirmations, matching the
same external-source rigor -- Saturn's dates cross-checked against
multiple independent sites, one explicitly citing "Drik Siddhantam
method... verified against published almanacs"; Jupiter's dates
cross-checked with a noted ~1-day source variance (normal tolerance for
this kind of published date) for the retrograde-return date only.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.engines.ingress_engine import (
    find_next_ingress,
    get_upcoming_ingresses,
    house_from_sign,
    NODE_TYPE_NOT_APPLICABLE,
)


def test_rahu_mean_node_ingress_matches_external_source():
    result = find_next_ingress("Rahu", datetime(2026, 9, 13), node_type="mean")
    assert result["to_sign"] == "Capricorn"
    assert result["from_sign"] == "Aquarius"
    assert result["ingress_date_utc"].date() == datetime(2026, 12, 5).date()
    assert result["retrograde_return_date_utc"] is None  # Rahu never stations


def test_rahu_true_node_ingress_differs_from_mean():
    mean_result = find_next_ingress("Rahu", datetime(2026, 9, 13), node_type="mean")
    true_result = find_next_ingress("Rahu", datetime(2026, 9, 13), node_type="true")
    assert mean_result["ingress_date_utc"].date() != true_result["ingress_date_utc"].date()
    assert true_result["ingress_date_utc"].date() == datetime(2026, 11, 25).date()


def test_ketu_ingress_is_exactly_opposite_rahu():
    rahu = find_next_ingress("Rahu", datetime(2026, 9, 13), node_type="mean")
    ketu = find_next_ingress("Ketu", datetime(2026, 9, 13), node_type="mean")
    # Astronomically simultaneous (Ketu is always 180 deg from Rahu);
    # allow slack matching each independent bisection's own 30-minute
    # convergence cutoff rather than asserting sub-minute exactness the
    # algorithm was never tuned to guarantee.
    assert abs((ketu["ingress_date_utc"] - rahu["ingress_date_utc"]).total_seconds()) < 3600
    from app.engines.ingress_engine import RASI_TO_INDEX
    assert (RASI_TO_INDEX[ketu["to_sign"]] - RASI_TO_INDEX[rahu["to_sign"]]) % 12 == 6


def test_jupiter_cancer_entry_matches_known_external_date():
    # External source: Jupiter into Cancer June 2, 2026 -- that date is
    # in IST. The engine returns UTC by design (matching the rest of
    # this app's convention); this app's computed instant, 2026-06-01
    # 20:35 UTC, is 2026-06-02 02:05 IST (+5:30) -- the same real moment,
    # not a discrepancy. Asserting the UTC calendar date the engine
    # actually returns, with the IST correspondence noted here so a
    # future reader doesn't "fix" this to 06-02 and silently reintroduce
    # a real, if small, error.
    result = find_next_ingress("Jupiter", datetime(2026, 1, 1))
    assert result["from_sign"] == "Gemini"
    assert result["to_sign"] == "Cancer"
    assert result["ingress_date_utc"].date() == datetime(2026, 6, 1).date()


def test_jupiter_leo_entry_matches_known_external_date():
    # External source: Jupiter into Leo October 31, 2026.
    result = find_next_ingress("Jupiter", datetime(2026, 9, 13))
    assert result["from_sign"] == "Cancer"
    assert result["to_sign"] == "Leo"
    assert result["ingress_date_utc"].date() == datetime(2026, 10, 31).date()


def test_jupiter_retrograde_return_to_cancer_matches_known_external_date():
    # External source: Jupiter retrogrades back into Cancer around
    # 2027-01-24/25 (external sources vary by ~1 day, normal tolerance
    # for this kind of published date) before finally settling in Leo.
    result = find_next_ingress("Jupiter", datetime(2026, 9, 13))
    assert result["retrograde_return_date_utc"] is not None
    assert result["retrograde_return_date_utc"].date() in (
        datetime(2027, 1, 24).date(), datetime(2027, 1, 25).date(),
    )


def test_saturn_ingress_detects_real_retrograde_return():
    # Saturn's real 2027 Pisces->Aries entry, followed by a retrograde
    # return to Pisces later the same year -- a genuine astronomical
    # event (not synthesized), found while validating this algorithm
    # against real ephemeris data. External source (2026-09-14):
    # multiple independent sites, one explicitly citing "Drik
    # Siddhantam method... verified against published almanacs" --
    # retrograde return to Pisces October 20, 2027.
    result = find_next_ingress("Saturn", datetime(2026, 9, 13))
    assert result["from_sign"] == "Pisces"
    assert result["to_sign"] == "Aries"
    assert result["ingress_date_utc"].date() == datetime(2027, 6, 3).date()
    assert result["retrograde_return_date_utc"] is not None
    assert result["retrograde_return_date_utc"].date() == datetime(2027, 10, 20).date()


def test_saturn_pisces_entry_matches_known_external_date():
    # External source: Saturn into Pisces March 29, 2025 -- the ingress
    # immediately before the one covered by
    # test_saturn_ingress_detects_real_retrograde_return above. Search
    # starts well before this date since it's in the past relative to
    # "today" elsewhere in this file.
    result = find_next_ingress("Saturn", datetime(2025, 1, 1))
    assert result["from_sign"] == "Aquarius"
    assert result["to_sign"] == "Pisces"
    assert result["ingress_date_utc"].date() == datetime(2025, 3, 29).date()


def test_saturn_aries_reentry_after_retrograde_return_matches_known_external_date():
    # External source: after retrograding back into Pisces (Oct 20
    # 2027, tested above), Saturn re-enters Aries for good in February
    # 2028. This is the THIRD ingress out from "today" (Pisces->Aries,
    # ->Pisces retrograde, ->Aries again), found by searching forward
    # from just after the retrograde-return date.
    first = find_next_ingress("Saturn", datetime(2026, 9, 13))
    reentry = find_next_ingress(
        "Saturn", first["retrograde_return_date_utc"] + timedelta(days=1)
    )
    assert reentry["from_sign"] == "Pisces"
    assert reentry["to_sign"] == "Aries"
    assert reentry["ingress_date_utc"].year == 2028
    assert reentry["ingress_date_utc"].month == 2


def test_coarse_then_refine_uses_far_fewer_calls_than_day_by_day():
    """Not a hard call-count assertion (that's an implementation
    accident) -- but confirms the algorithm terminates well under a
    day-by-day scan's iteration count for a multi-month-out ingress,
    proving it isn't secretly looping daily internally."""
    from app.utils import swisseph_utils
    call_count = {"n": 0}
    orig = swisseph_utils.compute_planet_longitude_with_speed

    def counting_wrapper(*args, **kwargs):
        call_count["n"] += 1
        return orig(*args, **kwargs)

    swisseph_utils.compute_planet_longitude_with_speed = counting_wrapper
    try:
        result = find_next_ingress("Saturn", datetime(2026, 9, 13))
    finally:
        swisseph_utils.compute_planet_longitude_with_speed = orig

    # Saturn's real ingress here is ~263 days out; a day-by-day scan
    # would need ~263+ calls just to find the crossing, before any
    # retrograde-return check. This should need well under 100.
    assert call_count["n"] < 100
    assert result["to_sign"] == "Aries"


def test_house_from_sign_arithmetic():
    assert house_from_sign("Capricorn", "Aries") == 10
    assert house_from_sign("Aries", "Aries") == 1
    assert house_from_sign("Aquarius", "Taurus") == 10


class _FakeConn:
    """Minimal in-memory stand-in for the app's _ConnWrapper, enough to
    exercise get_upcoming_ingresses()'s query + lazy-backfill-insert +
    re-query flow without touching a real database."""

    def __init__(self):
        self.rows = []  # list of dicts matching planet_ingress_events columns

    def execute(self, sql, params=None):
        sql_stripped = sql.strip()
        if sql_stripped.startswith("SELECT"):
            planet, node_type, now_utc, count = params
            matched = [
                r for r in self.rows
                if r["planet"] == planet and r["node_type"] == node_type and r["ingress_date_utc"] > now_utc
            ]
            matched.sort(key=lambda r: r["ingress_date_utc"])
            self._last_result = [
                (r["to_sign"], r["ingress_date_utc"], r["retrograde_return_date_utc"]) for r in matched[:count]
            ]
        elif sql_stripped.startswith("INSERT"):
            planet, node_type, from_sign, to_sign, ingress_date_utc, retro = params
            exists = any(
                r["planet"] == planet and r["node_type"] == node_type
                and r["to_sign"] == to_sign and r["ingress_date_utc"] == ingress_date_utc
                for r in self.rows
            )
            if not exists:
                self.rows.append({
                    "planet": planet, "node_type": node_type, "from_sign": from_sign,
                    "to_sign": to_sign, "ingress_date_utc": ingress_date_utc,
                    "retrograde_return_date_utc": retro,
                })
        return self

    def fetchall(self):
        return self._last_result


def test_get_upcoming_ingresses_backfills_when_cache_empty():
    conn = _FakeConn()
    now = datetime(2026, 9, 13, tzinfo=timezone.utc)
    rows = get_upcoming_ingresses(conn, "Rahu", node_type="mean", now_utc=now, count=2)
    assert len(rows) == 2
    assert rows[0]["to_sign"] == "Capricorn"
    assert rows[0]["ingress_date_utc"].date() == datetime(2026, 12, 5).date()
    # Backfill actually wrote rows to the cache, not just returned values in memory.
    assert len(conn.rows) == 2


def test_get_upcoming_ingresses_uses_cache_without_recomputing():
    conn = _FakeConn()
    now = datetime(2026, 9, 13, tzinfo=timezone.utc)
    get_upcoming_ingresses(conn, "Rahu", node_type="mean", now_utc=now, count=2)
    cached_row_count = len(conn.rows)

    from app.engines import ingress_engine
    orig = ingress_engine.find_next_ingress
    ingress_engine.find_next_ingress = MagicMock(side_effect=AssertionError("should not recompute"))
    try:
        rows = get_upcoming_ingresses(conn, "Rahu", node_type="mean", now_utc=now, count=2)
    finally:
        ingress_engine.find_next_ingress = orig

    assert len(rows) == 2
    assert len(conn.rows) == cached_row_count  # no new rows written


def test_get_upcoming_ingresses_backfills_only_the_missing_count():
    conn = _FakeConn()
    now = datetime(2026, 9, 13, tzinfo=timezone.utc)
    get_upcoming_ingresses(conn, "Rahu", node_type="mean", now_utc=now, count=1)
    assert len(conn.rows) == 1

    rows = get_upcoming_ingresses(conn, "Rahu", node_type="mean", now_utc=now, count=2)
    assert len(rows) == 2
    assert len(conn.rows) == 2


def test_jupiter_saturn_use_placeholder_node_type_not_null():
    conn = _FakeConn()
    now = datetime(2026, 9, 13, tzinfo=timezone.utc)
    get_upcoming_ingresses(conn, "Jupiter", node_type="mean", now_utc=now, count=1)
    assert conn.rows[0]["node_type"] == NODE_TYPE_NOT_APPLICABLE
    assert conn.rows[0]["node_type"] != "mean"
