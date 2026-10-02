# tests/engines/test_wealth_events_engine.py
"""
wealth_events_engine.py (2026-10-02): 2nd/11th house lords (from Moon) with
real Dasha windows, plus reused Dhana Yoga (yoga_engine, Lagna-based) and
KP 2nd/11th cuspal significators -- raw facts, never a verdict.
"""
from app.engines.wealth_events_engine import (
    compute_wealth_event_signals,
    format_wealth_events_compact,
    format_wealth_events_context,
)


def _payload(moon_rasi="Mesham", kp=True):
    p = {
        "ephemeris": {
            "moon": {"rasi": moon_rasi},
            "lagna": {"longitude_deg": 15.0},  # Aries Lagna
            "planets": {
                "Sun": {"longitude_deg": 10.0}, "Moon": {"longitude_deg": 5.0},
                "Mars": {"longitude_deg": 100.0}, "Mercury": {"longitude_deg": 200.0},
                "Jupiter": {"longitude_deg": 250.0}, "Venus": {"longitude_deg": 300.0},
                "Saturn": {"longitude_deg": 340.0},
            },
        },
        "dashas": {"vimshottari": {"timeline": [{
            "mahadasha": "Rahu", "start": "2020-01-01", "end": "2038-01-01",
            "antar_dashas": [
                {"antar_lord": "Saturn", "start": "2025-10-03", "end": "2028-08-08"},
                {"antar_lord": "Venus", "start": "2032-03-14", "end": "2035-03-14"},
            ],
        }]}},
    }
    if kp:
        p["kp_sublords"] = {"cuspal_significators": {"2": ["Venus", "Saturn"], "11": ["Saturn", "Jupiter"]}}
    return p


def test_second_and_eleventh_lords_from_moon_with_real_windows():
    s = compute_wealth_event_signals(_payload(), 2026, 2036)
    # Mesham Moon: 2nd = Taurus (Venus), 11th = Aquarius (Saturn)
    assert s["second_lord"] == "Venus" and s["eleventh_lord"] == "Saturn"
    assert [(d["lord"], d["level"]) for d in s["second_lord_dashas"]] == [("Venus", "antardasha")]
    assert s["eleventh_lord_dashas"][0]["lord"] == "Saturn"
    assert s["eleventh_lord_dashas"][0]["to"].startswith("2028-08-08")


def test_kp_significators_reported_per_cusp_not_merged():
    s = compute_wealth_event_signals(_payload(), 2026, 2036)
    assert s["kp_2nd_cusp_significators"] == ["Venus", "Saturn"]
    assert s["kp_11th_cusp_significators"] == ["Saturn", "Jupiter"]


def test_no_kp_data_is_explicit():
    s = compute_wealth_event_signals(_payload(kp=False), 2026, 2036)
    assert s["kp_available"] is False
    assert "KP" not in format_wealth_events_context(s)


def test_same_planet_rules_2nd_and_11th_windows_not_duplicated():
    # Simmam Moon: 2nd = Virgo (Mercury), 11th = Gemini (Mercury)
    s = compute_wealth_event_signals(_payload(moon_rasi="Simmam"), 2026, 2036)
    assert s["second_lord"] == s["eleventh_lord"] == "Mercury"
    assert s["eleventh_lord_dashas"] == []
    assert "same planet as the 2nd lord" in format_wealth_events_context(s)


def test_compact_window_is_domain_labelled():
    text = format_wealth_events_compact(compute_wealth_event_signals(_payload(), 2026, 2036))
    assert text.startswith("2nd lord Venus, 11th lord Saturn, wealth-timing window 2026-2028 (Saturn)")


def test_dhana_yoga_labelled_as_lagna_based():
    s = compute_wealth_event_signals(_payload(), 2026, 2036)
    s["dhana_yogas"] = [{"planets": ["Venus", "Jupiter"], "houses_involved": [2, 9], "type": "conjunction"}]
    assert "Venus+Jupiter (lords of houses 2/9 from Lagna, conjunction)" in format_wealth_events_context(s)
    assert "Dhana Yoga Venus+Jupiter" in format_wealth_events_compact(s)
