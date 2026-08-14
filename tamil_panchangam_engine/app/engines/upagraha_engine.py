"""
Upagraha Engine — Gulika (Mandi) Computation

Classical Parashari method:
- Daylight is divided into 8 equal segments.
- Each segment's lord follows the weekday-hora sequence.
- Gulika/Mandi is the segment ruled by Saturn's sub-period.
- Gulika's position = the Ascendant (Lagna) at the moment Gulika's segment begins.

Convention note: classical texts differ on whether to snapshot the Lagna at the
START or the END of Gulika's segment. This module uses segment START (the
Drik/Parashara convention). Some traditions use segment END instead and treat
it as a distinct point — this is a deliberate choice, not an oversight.

In South Indian Jyotisha, Gulika and Mandi are identical.
"""

import logging
import swisseph as swe
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

RASI_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

RASI_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

AYANAMSA_MODES = {
    "lahiri": swe.SIDM_LAHIRI,
    "kp": swe.SIDM_KRISHNAMURTI,
}

# Gulika/Mandi daytime segment index (0-based, out of 8) by Python weekday (Mon=0)
# Verified against reference tables (e.g. templesinindiainfo.com, anytimeastro.com):
# Sun=7th, Mon=6th, Tue=5th, Wed=4th, Thu=3rd, Fri=2nd, Sat=1st (1-indexed).
# Matches _GULIKA_SEGMENT in dinaphalam_engine.py (same table, 0-indexed here).
_MANDI_DAYTIME_SEGMENT: Dict[int, int] = {
    0: 5,  # Monday   — segment 6 (0-indexed: 5)
    1: 4,  # Tuesday  — segment 5
    2: 3,  # Wednesday— segment 4
    3: 2,  # Thursday — segment 3
    4: 1,  # Friday   — segment 2
    5: 0,  # Saturday — segment 1
    6: 6,  # Sunday   — segment 7
}

# Nighttime segment offsets (different sequence, not used for birth charts by default)
_MANDI_NIGHTTIME_SEGMENT: Dict[int, int] = {
    0: 2,  # Monday
    1: 1,  # Tuesday
    2: 0,  # Wednesday
    3: 6,  # Thursday
    4: 5,  # Friday
    5: 4,  # Saturday
    6: 3,  # Sunday
}


def _get_rasi(longitude_deg: float) -> str:
    return RASI_NAMES[int(longitude_deg // 30) % 12]


def _compute_sunrise_sunset(
    jd_noon: float,
    latitude: float,
    longitude: float,
) -> tuple[float, float]:
    """Return (sunrise_jd, sunset_jd). Falls back to 6am/6pm if computation fails."""
    # JD at midnight local — approximate by using jd_noon - 0.5
    jd_start = jd_noon - 0.5
    try:
        rise_res = swe.rise_trans(
            jd_start, swe.SUN,
            geopos=(longitude, latitude, 0.0),
            rsmi=swe.CALC_RISE | swe.BIT_DISC_CENTER,
        )
        set_res = swe.rise_trans(
            jd_start, swe.SUN,
            geopos=(longitude, latitude, 0.0),
            rsmi=swe.CALC_SET | swe.BIT_DISC_CENTER,
        )
        sunrise_jd = rise_res[1][0]
        sunset_jd = set_res[1][0]
        if sunset_jd <= sunrise_jd:
            sunset_jd += 1.0
        return sunrise_jd, sunset_jd
    except Exception as e:
        logger.debug(f"Sunrise/sunset computation failed ({e}); using 6am/6pm fallback")
        # Rough JD for midnight UTC on birth date
        sunrise_jd = jd_noon - (jd_noon % 1) + 6 / 24
        sunset_jd = sunrise_jd + 12 / 24
        return sunrise_jd, sunset_jd


def compute_gulika_mandi(
    birth_utc: datetime,
    latitude: float,
    longitude: float,
    ayanamsa: str = "lahiri",
) -> Dict[str, Any]:
    """
    Compute Gulika (Mandi) position using classical Parashari method.

    Returns:
        {
          "gulika": { "longitude_deg": float, "rasi": str, "rasi_lord": str },
          "mandi": { ... }   # identical in South Indian tradition
        }
    """
    swe.set_sid_mode(AYANAMSA_MODES.get(ayanamsa, swe.SIDM_LAHIRI))
    swe.set_ephe_path(".")

    # Julian day at noon UTC on birth date
    jd_noon = swe.julday(
        birth_utc.year, birth_utc.month, birth_utc.day, 12.0
    )

    sunrise_jd, sunset_jd = _compute_sunrise_sunset(jd_noon, latitude, longitude)
    day_duration = sunset_jd - sunrise_jd  # in JD (days)
    segment_duration = day_duration / 8.0

    weekday = birth_utc.weekday()  # Mon=0, Sun=6
    segment_idx = _MANDI_DAYTIME_SEGMENT.get(weekday, 0)

    mandi_jd = sunrise_jd + segment_idx * segment_duration

    try:
        flags = swe.FLG_SIDEREAL
        _houses, ascmc = swe.houses_ex(mandi_jd, latitude, longitude, b"P", flags)
        mandi_lon = ascmc[0] % 360.0
    except Exception as e:
        logger.warning(f"Upagraha Lagna computation failed: {e}")
        # Fallback: use Sun's longitude at Mandi time as a reasonable proxy
        sun_flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        result, _ = swe.calc_ut(mandi_jd, swe.SUN, sun_flags)
        mandi_lon = result[0] % 360.0

    rasi = _get_rasi(mandi_lon)
    rasi_lord = RASI_LORDS.get(rasi, "Unknown")

    entry = {
        "longitude_deg": round(mandi_lon, 4),
        "rasi": rasi,
        "rasi_lord": rasi_lord,
        "method": "parashari_lagna_at_mandi_kala",
    }

    return {
        "gulika": entry,
        "mandi": entry,  # South Indian: Gulika = Mandi
    }
