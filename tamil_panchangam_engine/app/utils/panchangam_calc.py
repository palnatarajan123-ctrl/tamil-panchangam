"""
Shared Tithi (lunar day) calculation.

Single source of truth: app.engines.panchangam.compute_tithi() (used at
chart-creation time, for the birth-moment Tithi) and
app.engines.dinaphalam_engine.compute_dinaphalam() (used for "today"'s
display) used to each independently reimplement the identical formula.
The formula was never wrong (verified identical), but panchangam.py's
15-entry TITHI_NAMES combined Pournami/Amavasya into one shared last
entry ("Pournami / Amavasya") and always appended both regardless of
paksha -- so a Krishna-paksha 15th tithi rendered as "Krishna Pournami
/ Amavasya", which doesn't make sense (Pournami only occurs in Shukla
paksha, Amavasya only in Krishna). dinaphalam_engine.py's independently
written 30-entry table happened to get this right. This module keeps
the correct (30-entry) version as canonical. See CLAUDE.md's
2026-09-13 entry.
"""
from typing import Dict

TITHI_NAMES = [
    "Prathama", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Pournami",
    "Prathama", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]


# Gulika (daytime) segment by Python weekday (Mon=0), 1-indexed (segment
# 1 = first of 8 daylight segments after sunrise). Verified against
# published reference tables (templesinindiainfo.com, anytimeastro.com):
# Sun=7th, Mon=6th, Tue=5th, Wed=4th, Thu=3rd, Fri=2nd, Sat=1st.
#
# Single source of truth: upagraha_engine.py (natal Gulika/Mandi) and
# dinaphalam_engine.py (today's Gulika Kaalam window) used to each hand-copy
# this same table independently -- upagraha_engine.py's own comment already
# noted they matched, but as two separately-maintained copies (one 0-indexed,
# one 1-indexed) rather than one shared source. See CLAUDE.md's 2026-09-13
# entry.
GULIKA_DAYTIME_SEGMENT_1INDEXED: Dict[int, int] = {
    0: 6,  # Monday
    1: 5,  # Tuesday
    2: 4,  # Wednesday
    3: 3,  # Thursday
    4: 2,  # Friday
    5: 1,  # Saturday
    6: 7,  # Sunday
}


def compute_tithi(sun_lon: float, moon_lon: float) -> Dict:
    """
    Compute Tithi (lunar day) from Sun and Moon sidereal longitudes.

    Returns:
        {"paksha": "Shukla"|"Krishna", "tithi_number": 1-15,
         "name": e.g. "Ashtami" or "Pournami"/"Amavasya" (unprefixed --
         paksha is reported separately, not concatenated into name),
         "index": 0-29}
    """
    diff = (moon_lon - sun_lon) % 360
    tithi_index = int(diff // 12)
    paksha = "Shukla" if tithi_index < 15 else "Krishna"
    tithi_number = (tithi_index % 15) + 1

    return {
        "paksha": paksha,
        "tithi_number": tithi_number,
        "name": TITHI_NAMES[tithi_index],
        "index": tithi_index,
    }
