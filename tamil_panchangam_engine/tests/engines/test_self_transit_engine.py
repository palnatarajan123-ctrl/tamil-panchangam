# tests/engines/test_self_transit_engine.py
"""
self_transit_engine.py (2026-10-02): next/last dates a transiting planet
returns to, opposes, or casts its own classical aspect onto its OWN natal
degree, beyond transit_hits_engine.py's +/-45-day window. Verified against
real ephemeris positions, not against the engine's own arithmetic.
"""
import re
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from app.engines import self_transit_engine as ste
from app.utils.swisseph_utils import compute_planet_longitude_with_speed

TODAY = date(2026, 10, 2)
NATAL = {"Jupiter": 219.41, "Saturn": 22.54, "Mars": 222.41, "Rahu": 300.95}


def _payload():
    return {
        "chart_metadata": {"ayanamsa": "kp", "node_type": "mean"},
        "ephemeris": {"planets": {p: {"longitude_deg": lon} for p, lon in NATAL.items()}},
    }


def _lon(planet, iso):
    dt = datetime.fromisoformat(iso).replace(hour=12, tzinfo=timezone.utc)
    return compute_planet_longitude_with_speed(planet, dt, "kp", "mean")[0]


def test_every_reported_date_puts_the_planet_on_its_target_degree():
    st = ste.compute_self_transits(_payload(), TODAY)
    angles = {label: a for _, (_, _, ev) in ste._EVENTS.items() for label, a in ev}
    checked = 0
    for e in st["events"]:
        target = (NATAL[e["planet"]] - angles[e["event"]]) % 360
        for d in e["next_dates"] + ([e["last_date"]] if e["last_date"] else []):
            assert abs(ste._signed_diff(_lon(e["planet"], d), target)) < 1.0, (e, d)
            checked += 1
    assert checked >= 15


def test_known_milestones():
    st = {(e["planet"], e["event"]): e for e in ste.compute_self_transits(_payload(), TODAY)["events"]}
    nodal = st[("Rahu", "nodal return (Rahu over natal Rahu, Ketu over natal Ketu)")]
    # Just past the +/-45-day window: transit_hits flags it only as "exact after 2026-11-16".
    assert nodal["next_dates"][0].startswith("2026-11")
    assert nodal["next_dates"][0] > "2026-11-16"
    assert st[("Saturn", "return")]["last_date"].startswith("2000")
    assert st[("Saturn", "return")]["next_dates"][0].startswith("2029")


def test_nothing_reported_inside_the_transit_hits_window():
    st = ste.compute_self_transits(_payload(), TODAY)
    lo = (TODAY - timedelta(days=45)).isoformat()
    hi = (TODAY + timedelta(days=45)).isoformat()
    for e in st["events"]:
        for d in e["next_dates"]:
            assert d > hi
        if e["last_date"]:
            assert e["last_date"] < lo


def test_retrograde_passes_grouped_into_one_event():
    st = ste.compute_self_transits(_payload(), TODAY)
    multi = [e for e in st["events"] if len(e["next_dates"]) > 1]
    assert multi, "expected at least one triple-pass event for Jupiter/Saturn/Mars"
    for e in multi:
        span = (date.fromisoformat(e["next_dates"][-1]) - date.fromisoformat(e["next_dates"][0])).days
        assert span <= ste._PASS_SPAN_DAYS


def test_cache_reused_until_earliest_next_date_enters_window():
    payload = _payload()
    first = ste.get_self_transits(None, payload, TODAY)
    with patch.object(ste, "compute_self_transits", side_effect=AssertionError("recomputed")):
        assert ste.get_self_transits(None, payload, TODAY) is first
    # Once the earliest cached date is within 45 days, recompute.
    earliest = min(d for e in first["events"] for d in e["next_dates"][:1])
    later = date.fromisoformat(earliest) - timedelta(days=10)
    with patch.object(ste, "compute_self_transits", return_value={"recomputed": True}) as m:
        assert ste.get_self_transits(None, payload, later) == {"recomputed": True}
        m.assert_called_once()


def test_formatters():
    st = ste.compute_self_transits(_payload(), TODAY)
    verbose = ste.format_self_transits_context(st)
    # Human-readable "D Month YYYY", never ISO (ISO 2029-05-22 was misread as "29 May").
    assert re.search(r"Saturn return to its own natal degree: next exact \d{1,2} May 2029", verbose)
    assert not re.search(r"\d{4}-\d{2}-\d{2}", verbose)
    assert "Rahu/Ketu nodal return" in verbose and "to its own natal degree" not in verbose.split("Rahu/Ketu")[1]
    compact = ste.format_self_transits_compact(st)
    assert compact.startswith("Next returns to natal degree: Jupiter return ")
    assert re.search(r"Nodal return \d{1,2} November 2026", compact)
    assert ste.format_self_transits_context({}) == "" and ste.format_self_transits_compact({}) == ""
