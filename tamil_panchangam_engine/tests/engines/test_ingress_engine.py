"""
Tests for ingress_engine.py -- the coarse-then-refine peyarchi (sign
change) date computation, and the planet_ingress_events cache.

Real astronomical values pinned here were verified during this
feature's build against a 264-call exhaustive day-by-day scan (Rahu,
Jupiter) and cross-checked against external Tamil peyarchi sources
(Rahu into Capricorn Dec 5 2026 mean node; Jupiter into Cancer ~June
2026, confirmed via a coarser sample sweep) -- see CLAUDE.md's
2026-09-13 entry.
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
    # Cross-check against the June 2026 Jupiter-into-Cancer date already
    # reviewed via external PDF content earlier in this project.
    result = find_next_ingress("Jupiter", datetime(2026, 1, 1))
    assert result["to_sign"] == "Cancer"
    assert result["ingress_date_utc"].month == 6
    assert result["ingress_date_utc"].year == 2026


def test_saturn_ingress_detects_real_retrograde_return():
    # Saturn's real 2027 Pisces->Aries entry, followed by a retrograde
    # return to Pisces later the same year -- a genuine astronomical
    # event (not synthesized), found while validating this algorithm
    # against real ephemeris data.
    result = find_next_ingress("Saturn", datetime(2026, 9, 13))
    assert result["from_sign"] == "Pisces"
    assert result["to_sign"] == "Aries"
    assert result["ingress_date_utc"].date() == datetime(2027, 6, 3).date()
    assert result["retrograde_return_date_utc"] is not None
    assert result["retrograde_return_date_utc"] > result["ingress_date_utc"]
    assert result["retrograde_return_date_utc"] < result["ingress_date_utc"] + timedelta(days=300)


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
