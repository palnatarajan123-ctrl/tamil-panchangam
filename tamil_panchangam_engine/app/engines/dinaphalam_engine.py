"""
Dinaphalam Engine — Daily Timing + Panchangam

Computes for a given date and birth chart:
- Rahu Kaalam (inauspicious window ruled by Rahu)
- Yamagandam (inauspicious window ruled by Yama)
- Gulika Kaalam (inauspicious window ruled by Gulika)
- Today's Nakshatra and Tara Bala (relative to birth nakshatra)
- Tithi (lunar day)

All inauspicious windows are 1/8 of daylight, at fixed weekday offsets.
"""

import logging
import swisseph as swe
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Rahu Kaalam segment (1-indexed, 1=first daylight segment) by Python weekday Mon=0
_RAHU_SEGMENT: Dict[int, int] = {
    0: 2,  # Monday    — 2nd segment
    1: 7,  # Tuesday   — 7th
    2: 5,  # Wednesday — 5th
    3: 6,  # Thursday  — 6th
    4: 4,  # Friday    — 4th
    5: 3,  # Saturday  — 3rd
    6: 8,  # Sunday    — 8th
}

# Yamagandam segment by weekday
# Verified against reference tables (e.g. templesinindiainfo.com, anytimeastro.com):
# Sun=5th, Mon=4th, Tue=3rd, Wed=2nd, Thu=1st, Fri=7th, Sat=6th.
_YAMA_SEGMENT: Dict[int, int] = {
    0: 4,  # Monday    — 4th
    1: 3,  # Tuesday   — 3rd
    2: 2,  # Wednesday — 2nd
    3: 1,  # Thursday  — 1st
    4: 7,  # Friday    — 7th
    5: 6,  # Saturday  — 6th
    6: 5,  # Sunday    — 5th
}

# Gulika Kaalam segment by weekday (daytime table)
# Verified against reference tables (e.g. templesinindiainfo.com, anytimeastro.com):
# Sun=7th, Mon=6th, Tue=5th, Wed=4th, Thu=3rd, Fri=2nd, Sat=1st.
_GULIKA_SEGMENT: Dict[int, int] = {
    0: 6,  # Monday    — 6th
    1: 5,  # Tuesday   — 5th
    2: 4,  # Wednesday — 4th
    3: 3,  # Thursday  — 3rd
    4: 2,  # Friday    — 2nd
    5: 1,  # Saturday  — 1st
    6: 7,  # Sunday    — 7th
}

AYANAMSA_MODES = {
    "lahiri": swe.SIDM_LAHIRI,
    "kp": swe.SIDM_KRISHNAMURTI,
}

TITHI_NAMES = [
    "Prathama", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Pournami",
    "Prathama", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

from app.engines.nakshatra_names import canonical_nakshatra_list as _canonical_nakshatra_list
NAKSHATRA_NAMES = _canonical_nakshatra_list()

TARA_BALA_CYCLE = [
    ("janma", "Janma Tara", "neutral"),
    ("sampat", "Sampat Tara", "favorable"),
    ("vipat", "Vipat Tara", "challenging"),
    ("kshemam", "Kshemam Tara", "favorable"),
    ("pratyak", "Pratyak Tara", "challenging"),
    ("sadhana", "Sadhana Tara", "favorable"),
    ("naidhana", "Naidhana Tara", "challenging"),
    ("mitra", "Mitra Tara", "favorable"),
    ("parama_mitra", "Parama Mitra Tara", "favorable"),
]


def _compute_sunrise_sunset(
    year: int, month: int, day: int,
    latitude: float, longitude: float,
) -> Tuple[float, float]:
    """Return (sunrise_jd, sunset_jd). Falls back to 6am/6pm on failure."""
    jd_start = swe.julday(year, month, day, 0.0)
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
        logger.debug(f"Sunrise computation failed ({e}); using 6am/6pm fallback")
        jd_6am = jd_start + 6 / 24
        return jd_6am, jd_6am + 12 / 24


def _jd_to_local_time(jd: float, utc_offset_hours: float) -> str:
    """Convert Julian Day to local HH:MM string."""
    jd_epoch = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    delta_days = jd - 2451545.0
    dt_utc = jd_epoch + timedelta(days=delta_days)
    dt_local = dt_utc + timedelta(hours=utc_offset_hours)
    return dt_local.strftime("%H:%M")


def _window_times(
    sunrise_jd: float, segment_duration: float, segment_1indexed: int, utc_offset: float
) -> Dict[str, str]:
    start_jd = sunrise_jd + (segment_1indexed - 1) * segment_duration
    end_jd = start_jd + segment_duration
    return {
        "start": _jd_to_local_time(start_jd, utc_offset),
        "end": _jd_to_local_time(end_jd, utc_offset),
    }


def compute_dinaphalam(
    date_utc: datetime,
    latitude: float,
    longitude: float,
    birth_nakshatra_index: int,
    utc_offset_hours: float = 5.5,
    ayanamsa: str = "lahiri",
) -> Dict[str, Any]:
    """
    Compute daily Panchangam and inauspicious windows.

    Args:
        date_utc: Date to compute for (UTC midnight or near it is fine)
        latitude, longitude: Location coordinates
        birth_nakshatra_index: 0-based index of the birth nakshatra (for Tara Bala)
        utc_offset_hours: Local timezone offset (IST = 5.5)
        ayanamsa: "lahiri" or "kp"

    Returns dict with keys:
        rahu_kaalam, yamagandam, gulika_kaalam, nakshatra, tara_bala, tithi
    """
    swe.set_sid_mode(AYANAMSA_MODES.get(ayanamsa, swe.SIDM_LAHIRI))
    swe.set_ephe_path(".")

    y, m, d = date_utc.year, date_utc.month, date_utc.day
    sunrise_jd, sunset_jd = _compute_sunrise_sunset(y, m, d, latitude, longitude)
    day_duration = sunset_jd - sunrise_jd
    segment_duration = day_duration / 8.0

    weekday = date_utc.weekday()  # Mon=0

    rahu_seg = _RAHU_SEGMENT[weekday]
    yama_seg = _YAMA_SEGMENT[weekday]
    gulika_seg = _GULIKA_SEGMENT[weekday]

    rahu_window = _window_times(sunrise_jd, segment_duration, rahu_seg, utc_offset_hours)
    yama_window = _window_times(sunrise_jd, segment_duration, yama_seg, utc_offset_hours)
    gulika_window = _window_times(sunrise_jd, segment_duration, gulika_seg, utc_offset_hours)

    # Compute Moon longitude at local noon
    jd_noon = swe.julday(y, m, d, 12.0 - utc_offset_hours)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    moon_result, _ = swe.calc_ut(jd_noon, swe.MOON, flags)
    moon_lon = moon_result[0] % 360.0

    sun_result, _ = swe.calc_ut(jd_noon, swe.SUN, flags)
    sun_lon = sun_result[0] % 360.0

    # Nakshatra
    nak_idx = int(moon_lon / (360 / 27)) % 27
    nakshatra_name = NAKSHATRA_NAMES[nak_idx]
    nak_pada = int((moon_lon % (360 / 27)) / (360 / 27 / 4)) + 1

    # Tara Bala
    distance = (nak_idx - birth_nakshatra_index) % 27
    tara_idx = distance % 9
    tara_key, tara_name, tara_quality = TARA_BALA_CYCLE[tara_idx]

    # Tithi
    diff = (moon_lon - sun_lon) % 360
    tithi_idx = int(diff / 12)
    paksha = "Shukla" if tithi_idx < 15 else "Krishna"
    tithi_name = TITHI_NAMES[tithi_idx]

    return {
        "date": date_utc.strftime("%Y-%m-%d"),
        "rahu_kaalam": {
            "start": rahu_window["start"],
            "end": rahu_window["end"],
            "segment": rahu_seg,
        },
        "yamagandam": {
            "start": yama_window["start"],
            "end": yama_window["end"],
            "segment": yama_seg,
        },
        "gulika_kaalam": {
            "start": gulika_window["start"],
            "end": gulika_window["end"],
            "segment": gulika_seg,
        },
        "nakshatra": {
            "name": nakshatra_name,
            "index": nak_idx,
            "pada": nak_pada,
            "longitude_deg": round(moon_lon, 4),
        },
        "tara_bala": {
            "key": tara_key,
            "name": tara_name,
            "quality": tara_quality,
            "distance": distance,
        },
        "tithi": {
            "name": tithi_name,
            "paksha": paksha,
            "number": (tithi_idx % 15) + 1,
        },
        "sunrise": _jd_to_local_time(sunrise_jd, utc_offset_hours),
        "sunset": _jd_to_local_time(sunset_jd, utc_offset_hours),
    }
