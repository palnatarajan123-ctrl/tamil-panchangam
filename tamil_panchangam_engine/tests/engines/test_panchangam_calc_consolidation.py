"""
Regression tests for the 2026-09-13 daily-panchangam duplication fix.

panchangam.py (birth-moment Tithi, used at chart creation) and
dinaphalam_engine.py (today's Tithi, used for daily display) used to
each independently reimplement the identical Tithi formula --
mathematically identical, but panchangam.py's 15-entry TITHI_NAMES
combined Pournami/Amavasya into one shared last entry and always
appended both regardless of paksha (e.g. "Krishna Pournami /
Amavasya", which doesn't make sense). dinaphalam_engine.py's
independently-written 30-entry table happened to get this right; it's
now the canonical shared implementation. See CLAUDE.md's 2026-09-13
entry.
"""
from app.utils.panchangam_calc import compute_tithi, GULIKA_DAYTIME_SEGMENT_1INDEXED
from app.engines.panchangam import compute_tithi as panchangam_compute_tithi
from app.engines.dinaphalam_engine import GULIKA_DAYTIME_SEGMENT_1INDEXED as dina_gulika_table
from app.engines.upagraha_engine import _MANDI_DAYTIME_SEGMENT


def test_panchangam_engine_delegates_to_shared_tithi():
    assert panchangam_compute_tithi is not compute_tithi  # wraps, doesn't shadow
    result = panchangam_compute_tithi(sun_lon=0.0, moon_lon=174.0)
    assert result == compute_tithi(0.0, 174.0)


def test_pournami_and_amavasya_correctly_distinguished_by_paksha():
    # Shukla paksha 15th tithi (index 14) -> Pournami
    shukla_15 = compute_tithi(sun_lon=0.0, moon_lon=174.0)
    assert shukla_15["paksha"] == "Shukla"
    assert shukla_15["name"] == "Pournami"

    # Krishna paksha 15th tithi (index 29) -> Amavasya
    krishna_15 = compute_tithi(sun_lon=100.0, moon_lon=100.0 + 348.0)
    assert krishna_15["paksha"] == "Krishna"
    assert krishna_15["name"] == "Amavasya"

    # Regression guard: neither name should ever contain the other
    # tithi's name or the old "Paksha TithiName" concatenation format.
    assert "Amavasya" not in shukla_15["name"]
    assert "Pournami" not in krishna_15["name"]
    assert "Shukla" not in shukla_15["name"] and "Krishna" not in shukla_15["name"]


def test_gulika_segment_table_is_single_source_shared_by_both_engines():
    assert dina_gulika_table is GULIKA_DAYTIME_SEGMENT_1INDEXED
    for weekday in range(7):
        assert _MANDI_DAYTIME_SEGMENT[weekday] == GULIKA_DAYTIME_SEGMENT_1INDEXED[weekday] - 1
