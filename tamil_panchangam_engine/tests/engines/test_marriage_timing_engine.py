# tests/engines/test_marriage_timing_engine.py
"""
Tests for marriage_timing_engine.py (2026-09-19) -- generalizes
children_timing_engine.py's proven pattern (real Dasha-window
computation per classical significator) to marriage timing: 7th house
lord (from Moon), Darakaraka (Jaimini lowest-degree graha), and Kalatra
Karaka (Parashari, gender-dependent).
"""
from app.engines.marriage_timing_engine import (
    compute_darakaraka,
    compute_kalatra_karaka,
    compute_marriage_timing_signals,
    format_marriage_timing_compact,
)


class TestComputeDarakaraka:
    def test_lowest_degree_graha_wins(self):
        planets = {
            "Sun": {"longitude_deg": 40.0},      # 10 deg in sign
            "Moon": {"longitude_deg": 65.0},     # 5 deg in sign
            "Mars": {"longitude_deg": 100.0},    # 10 deg in sign
            "Mercury": {"longitude_deg": 200.0},  # 20 deg
            "Jupiter": {"longitude_deg": 250.0},  # 10 deg
            "Venus": {"longitude_deg": 300.0},   # 0 deg -- exactly on the cusp, lowest
            "Saturn": {"longitude_deg": 340.0},  # 10 deg
        }
        assert compute_darakaraka(planets) == "Venus"

    def test_excludes_rahu_ketu(self):
        planets = {
            "Rahu": {"longitude_deg": 1.0},    # 1 deg -- lowest overall, but not a classical graha
            "Ketu": {"longitude_deg": 181.0},  # 1 deg -- same
            "Sun": {"longitude_deg": 15.0},    # 15 deg
            "Moon": {"longitude_deg": 42.0},   # 12 deg
            "Mars": {"longitude_deg": 63.0},   # 3 deg
            "Mercury": {"longitude_deg": 94.0},  # 4 deg
            "Jupiter": {"longitude_deg": 125.0},  # 5 deg
            "Venus": {"longitude_deg": 2.0},   # 2 deg -- lowest among the 7 classical grahas
            "Saturn": {"longitude_deg": 156.0},  # 6 deg
        }
        assert compute_darakaraka(planets) == "Venus"

    def test_missing_data_returns_none(self):
        assert compute_darakaraka({}) is None


class TestComputeKalatraKaraka:
    def test_male_gets_venus(self):
        assert compute_kalatra_karaka("male") == "Venus"

    def test_female_gets_jupiter(self):
        assert compute_kalatra_karaka("female") == "Jupiter"

    def test_unknown_gender_returns_none_not_a_guess(self):
        assert compute_kalatra_karaka(None) is None
        assert compute_kalatra_karaka("unspecified") is None


class TestComputeMarriageTimingSignals:
    def _payload(self):
        return {
            "ephemeris": {
                "moon": {"rasi": "Mesham"},
                "planets": {
                    "Sun": {"longitude_deg": 10.0},
                    "Moon": {"longitude_deg": 65.0},
                    "Mars": {"longitude_deg": 100.0},
                    "Mercury": {"longitude_deg": 200.0},
                    "Jupiter": {"longitude_deg": 250.0},
                    "Venus": {"longitude_deg": 300.0},
                    "Saturn": {"longitude_deg": 340.0},
                },
            },
            "dashas": {"vimshottari": {"timeline": [
                {
                    "mahadasha": "Venus", "start": "2020-01-01", "end": "2040-01-01",
                    "antar_dashas": [
                        {"antar_lord": "Venus", "start": "2026-01-01", "end": "2027-01-01"},
                    ],
                },
            ]}},
        }

    def test_gender_known_includes_kalatra_karaka(self):
        result = compute_marriage_timing_signals(self._payload(), 2026, 2030, gender="male")
        assert result["gender_known"] is True
        assert result["kalatra_karaka"] == "Venus"

    def test_gender_unknown_omits_kalatra_karaka(self):
        result = compute_marriage_timing_signals(self._payload(), 2026, 2030, gender=None)
        assert result["gender_known"] is False
        assert result["kalatra_karaka"] is None
        assert result["kalatra_karaka_dashas"] == []

    def test_seventh_lord_dasha_windows_are_real_and_bounded_to_range(self):
        result = compute_marriage_timing_signals(self._payload(), 2026, 2030, gender=None)
        # Moon rasi Mesham (index 0) -> 7th house sign = Libra (index 6) -> lord Venus
        assert result["seventh_lord"] == "Venus"
        # Test fixture's Venus Mahadasha (2020-2040, truncated to the
        # 2026-2030 search range) AND Venus Antardasha (2026-2027) both
        # match -- _find_planet_dashas() reports both levels separately.
        assert len(result["seventh_lord_dashas"]) == 2
        levels = {d["level"] for d in result["seventh_lord_dashas"]}
        assert levels == {"mahadasha", "antardasha"}


class TestFormatMarriageTimingCompact:
    def test_gender_known_separates_darakaraka_and_kalatra_karaka_labels(self):
        """Regression for an ambiguous-label bug: the two significators
        must each carry their own name, not be joined as if one value
        (e.g. the old 'Darakaraka Moon/Venus' read as a single combined
        field instead of Darakaraka=Moon, Kalatra Karaka=Venus)."""
        signals = {
            "seventh_lord": "Venus",
            "seventh_lord_dashas": [{"from": "2032-01-01", "to": "2035-01-01", "lord": "Venus", "level": "mahadasha"}],
            "darakaraka": "Moon",
            "darakaraka_dashas": [],
            "kalatra_karaka": "Venus",
            "kalatra_karaka_dashas": [],
            "gender_known": True,
        }
        result = format_marriage_timing_compact(signals)
        assert "Darakaraka Moon" in result
        assert "Kalatra Karaka Venus" in result
        assert "Moon/Venus" not in result
        assert "window 2032-2035 (Venus)" in result

    def test_gender_unknown_omits_kalatra_karaka_entirely(self):
        signals = {
            "seventh_lord": "Venus",
            "seventh_lord_dashas": [],
            "darakaraka": "Moon",
            "darakaraka_dashas": [],
            "kalatra_karaka": None,
            "kalatra_karaka_dashas": [],
            "gender_known": False,
        }
        result = format_marriage_timing_compact(signals)
        assert "Kalatra Karaka" not in result
        assert "no window in analyzed range" in result
