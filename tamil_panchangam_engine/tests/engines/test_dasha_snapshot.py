# tests/engines/test_dasha_snapshot.py
"""
compute_dasha_snapshot() (pratyantar_dasha_engine.py, 2026-10-02): live
current/next Mahadasha/Antardasha/Pratyantar with dates, for chat. Must
resolve from the timeline for the given date -- never from the
creation-time vimshottari["current"] field, which was stale for 6/41 real
charts on 2026-10-01.
"""
from datetime import date

from app.engines.pratyantar_dasha_engine import (
    compute_dasha_snapshot,
    compute_pratyantar,
    format_dasha_snapshot_compact,
    format_dasha_snapshot_context,
)


def _vim():
    # Rahu MD with real-proportion ADs (Rahu 18y: Saturn AD = 18*19/120 y).
    return {
        "current": {"lord": "Rahu", "antar": {"lord": "Jupiter"}},  # deliberately stale
        "timeline": [
            {
                "mahadasha": "Rahu", "start": "2020-08-28T00:00:00+00:00", "end": "2038-08-28T00:00:00+00:00",
                "antar_dashas": [
                    {"antar_lord": "Jupiter", "start": "2023-05-10T00:00:00+00:00", "end": "2025-10-03T00:00:00+00:00"},
                    {"antar_lord": "Saturn", "start": "2025-10-03T00:00:00+00:00", "end": "2028-08-08T00:00:00+00:00"},
                    {"antar_lord": "Mercury", "start": "2028-08-08T00:00:00+00:00", "end": "2031-02-25T00:00:00+00:00"},
                ],
            },
            {
                "mahadasha": "Jupiter", "start": "2038-08-28T00:00:00+00:00", "end": "2054-08-28T00:00:00+00:00",
                "antar_dashas": [
                    {"antar_lord": "Jupiter", "start": "2038-08-28T00:00:00+00:00", "end": "2040-10-15T00:00:00+00:00"},
                ],
            },
        ],
    }


def test_resolves_live_not_from_stale_current_field():
    snap = compute_dasha_snapshot(_vim(), date(2026, 10, 1))
    assert snap["mahadasha"]["lord"] == "Rahu"
    assert snap["antardasha"] == {"lord": "Saturn", "start": "2025-10-03", "end": "2028-08-08",
                                  "duration_days": snap["antardasha"]["duration_days"]}


def test_pratyantar_matches_existing_engine():
    snap = compute_dasha_snapshot(_vim(), date(2026, 10, 1))
    ref = compute_pratyantar(_vim(), date(2026, 10, 1))
    assert snap["pratyantar"] == ref["pratyantar"]
    # Saturn AD's sequence starts at Saturn: Saturn, Mercury, Ketu, ...
    assert snap["pratyantar"]["lord"] == "Ketu"


def test_next_periods():
    snap = compute_dasha_snapshot(_vim(), date(2026, 10, 1))
    assert snap["next_antardasha"]["lord"] == "Mercury"
    assert snap["next_antardasha"]["start"] == "2028-08-08"
    assert snap["next_pratyantar"]["lord"] == "Venus"
    assert snap["next_pratyantar"]["start"] == snap["pratyantar"]["end"]
    assert snap["next_mahadasha"]["lord"] == "Jupiter"
    assert snap["next_mahadasha"]["start"] == "2038-08-28"


def test_next_pratyantar_rolls_into_next_antardasha():
    # Last PD of the Saturn AD -> next PD is the first PD of Mercury AD (lord Mercury).
    snap = compute_dasha_snapshot(_vim(), date(2028, 8, 1))
    assert snap["antardasha"]["lord"] == "Saturn"
    assert snap["next_pratyantar"]["lord"] == "Mercury"
    assert snap["next_pratyantar"]["start"] == "2028-08-08"


def test_uncovered_date_returns_empty():
    assert compute_dasha_snapshot(_vim(), date(1990, 1, 1)) == {}
    assert format_dasha_snapshot_context({}) == ""
    assert format_dasha_snapshot_compact({}) == ""


def test_formatters():
    snap = compute_dasha_snapshot(_vim(), date(2026, 10, 1))
    verbose = format_dasha_snapshot_context(snap)
    assert "Current Antardasha (sub-period): Saturn, 2025-10-03 to 2028-08-08" in verbose
    assert "Next Antardasha: Mercury, 2028-08-08 to 2031-02-25" in verbose
    compact = format_dasha_snapshot_compact(snap)
    assert compact == (
        "Dasha Rahu›Saturn›Ketu (Saturn sub-period Oct 2025–Aug 2028; "
        "next sub-period Mercury Aug 2028–Feb 2031; Ketu sub-sub-period Aug 2026–Oct 2026; "
        "next sub-sub-period Venus Oct 2026–Apr 2027)"
    )
