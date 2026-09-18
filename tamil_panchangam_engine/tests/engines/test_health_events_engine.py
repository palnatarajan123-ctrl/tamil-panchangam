# tests/engines/test_health_events_engine.py
"""
Tests for health_events_engine.py (2026-09-19) -- generalizes
children_timing_engine.py's proven pattern to health-vulnerability
windows: 6th/8th house lords (from Moon) with real Dasha windows, plus
a real natal-affliction check (a natural malefic occupying the house).
"""
from app.engines.health_events_engine import compute_health_event_signals, format_health_events_compact


class TestComputeHealthEventSignals:
    def _payload(self, mars_lon=100.0):
        return {
            "ephemeris": {
                "moon": {"rasi": "Mesham"},  # index 0
                "planets": {
                    "Sun": {"longitude_deg": 10.0},
                    "Moon": {"longitude_deg": 65.0},
                    "Mars": {"longitude_deg": mars_lon},
                    "Mercury": {"longitude_deg": 200.0},
                    "Jupiter": {"longitude_deg": 250.0},
                    "Venus": {"longitude_deg": 300.0},
                    "Saturn": {"longitude_deg": 340.0},
                },
            },
            "dashas": {"vimshottari": {"timeline": [
                {
                    "mahadasha": "Mars", "start": "2020-01-01", "end": "2027-01-01",
                    "antar_dashas": [],
                },
            ]}},
        }

    def test_sixth_and_eighth_lords_computed_from_moon(self):
        result = compute_health_event_signals(self._payload(), 2026, 2030)
        # Moon rasi Mesham (index 0): 6th house sign = Virgo (index 5) -> lord Mercury
        # 8th house sign = Scorpio (index 7) -> lord Mars
        assert result["sixth_lord"] == "Mercury"
        assert result["eighth_lord"] == "Mars"

    def test_eighth_lord_dasha_window_is_real_and_bounded(self):
        result = compute_health_event_signals(self._payload(), 2026, 2030)
        assert len(result["eighth_lord_dashas"]) == 1
        assert result["eighth_lord_dashas"][0]["from"] == "2026-01-01"
        assert result["eighth_lord_dashas"][0]["to"] == "2027-01-01"

    def test_afflicting_malefic_detected_when_occupying_house(self):
        # Mars at 220 deg -> sign index 7 (Scorpio) -> the 8th house from Mesham
        result = compute_health_event_signals(self._payload(mars_lon=220.0), 2026, 2030)
        assert result["eighth_house_afflicted"] is True
        assert "Mars" in result["eighth_house_afflicting_planets"]

    def test_no_affliction_when_no_malefic_occupies_house(self):
        result = compute_health_event_signals(self._payload(mars_lon=100.0), 2026, 2030)
        assert result["eighth_house_afflicted"] is False
        assert result["eighth_house_afflicting_planets"] == []

    def test_benefic_occupant_alone_is_not_flagged_as_afflicting(self):
        # Jupiter (benefic) occupying the 8th house should not set afflicted=True
        payload = self._payload()
        payload["ephemeris"]["planets"]["Jupiter"] = {"longitude_deg": 220.0}
        payload["ephemeris"]["planets"]["Mars"] = {"longitude_deg": 10.0}
        result = compute_health_event_signals(payload, 2026, 2030)
        assert "Jupiter" in result["eighth_house_occupants"]
        assert result["eighth_house_afflicted"] is False


class TestFormatHealthEventsCompact:
    _payload = TestComputeHealthEventSignals._payload

    def test_names_lords_flags_affliction_and_earliest_window(self):
        result = format_health_events_compact(compute_health_event_signals(self._payload(mars_lon=220.0), 2026, 2030))
        assert "6th lord Mercury" in result
        assert "8th lord Mars" in result
        assert "8th afflicted" in result
        assert "6th afflicted" not in result

    def test_no_affliction_bit_omitted_when_neither_house_afflicted(self):
        result = format_health_events_compact(compute_health_event_signals(self._payload(mars_lon=100.0), 2026, 2030))
        assert "afflicted" not in result
