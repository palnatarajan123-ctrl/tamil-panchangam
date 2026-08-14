# tests/engines/test_upagraha_engine.py
"""
Tests for upagraha_engine.compute_gulika_mandi — natal Gulika (Mandi) point.

Segment table cross-checked against the same reference used in
test_dinaphalam_engine.py (Gulika column): Sun=7th, Mon=6th, Tue=5th,
Wed=4th, Thu=3rd, Fri=2nd, Sat=1st (1-indexed daylight segment).
"""

from datetime import datetime, timezone

from app.engines.upagraha_engine import compute_gulika_mandi, _MANDI_DAYTIME_SEGMENT
from app.engines.dinaphalam_engine import _GULIKA_SEGMENT

CHENNAI_LAT = 13.0827
CHENNAI_LON = 80.2707


class TestGulikaMandiComputation:
    def test_monday_birth_returns_valid_point(self):
        # 2026-08-10 is a Monday, birth at 10:00 UTC (daytime in Chennai)
        result = compute_gulika_mandi(
            datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc), CHENNAI_LAT, CHENNAI_LON,
        )
        gulika = result["gulika"]
        assert 0.0 <= gulika["longitude_deg"] < 360.0
        assert gulika["rasi"]
        assert gulika["rasi_lord"]
        assert gulika["method"] == "parashari_lagna_at_mandi_kala"

    def test_gulika_and_mandi_are_identical(self):
        result = compute_gulika_mandi(
            datetime(2026, 8, 16, 10, 0, tzinfo=timezone.utc), CHENNAI_LAT, CHENNAI_LON,
        )
        assert result["gulika"] == result["mandi"]

    def test_different_weekdays_give_different_segments(self):
        # Monday and Sunday births should generally land in different rasis
        # since they use different daylight segments (6th vs 7th).
        monday = compute_gulika_mandi(
            datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc), CHENNAI_LAT, CHENNAI_LON,
        )
        sunday = compute_gulika_mandi(
            datetime(2026, 8, 16, 10, 0, tzinfo=timezone.utc), CHENNAI_LAT, CHENNAI_LON,
        )
        assert monday["gulika"]["longitude_deg"] != sunday["gulika"]["longitude_deg"]

    def test_segment_table_matches_dinaphalam_gulika_table(self):
        """
        The natal (upagraha_engine) and daily (dinaphalam_engine) Gulika
        segment tables must stay in sync — both derive from the same
        classical rule and were fixed together after an off-by-one weekday
        bug was found (each day was using the previous day's segment).
        """
        for weekday_0indexed in range(7):
            natal_1indexed = _MANDI_DAYTIME_SEGMENT[weekday_0indexed] + 1
            daily_1indexed = _GULIKA_SEGMENT[weekday_0indexed]
            assert natal_1indexed == daily_1indexed, (
                f"weekday {weekday_0indexed}: natal={natal_1indexed} "
                f"daily={daily_1indexed}"
            )


class TestNightBirthKnownLimitation:
    """
    KNOWN LIMITATION (flagged, not silently handled): compute_gulika_mandi()
    always divides sunrise-to-sunset into 8 segments and applies the daytime
    segment table, regardless of whether birth_utc actually falls at night.
    Classical Parashari method uses a *different* segment order for night
    births (sunset-to-next-sunrise) — a nighttime table already exists as
    _MANDI_NIGHTTIME_SEGMENT in upagraha_engine.py but is not wired in.

    This test documents current behavior so a future change to add real
    night-birth support shows up as an intentional diff here, not a silent
    regression.
    """

    def test_night_birth_still_uses_daytime_segment_table(self):
        # 2026-08-10 (Monday), birth at 20:00 UTC == 01:30 IST next day —
        # well after sunset in Chennai.
        night_result = compute_gulika_mandi(
            datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc), CHENNAI_LAT, CHENNAI_LON,
        )
        day_result = compute_gulika_mandi(
            datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc), CHENNAI_LAT, CHENNAI_LON,
        )
        # Same calendar date -> same weekday -> same (daytime) segment table
        # is applied for both, i.e. night birth is NOT yet treated specially.
        assert night_result["gulika"]["longitude_deg"] == day_result["gulika"]["longitude_deg"]
