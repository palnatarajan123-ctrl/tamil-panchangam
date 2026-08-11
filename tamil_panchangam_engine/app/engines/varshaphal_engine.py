"""
Varshaphal Engine — Annual Chart (Solar Return).

Finds the moment the Sun returns to its natal longitude in the target year,
then derives Varshaphal Lagna, Varshesha, Muntha, and chart strength.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import swisseph as swe

logger = logging.getLogger(__name__)

RASI_NAMES = [
    "Mesham", "Rishabam", "Midhunam", "Kadagam", "Simham", "Kanni",
    "Thulam", "Vrischikam", "Dhanusu", "Makaram", "Kumbham", "Meenam",
]

_RASI_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
]

_BENEFIC_IDS = {
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
}

_AYANAMSA_MODES = {
    "lahiri": swe.SIDM_LAHIRI,
    "kp": swe.SIDM_KRISHNAMURTI,
}

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL


def _sign_idx(lon: float) -> int:
    return int(lon / 30.0) % 12


def _find_solar_return_jd(
    natal_sun_lon: float,
    year: int,
    ayanamsa: str,
) -> float:
    """
    Walk day by day from Jan 1 of `year` to find when the Sun crosses natal_sun_lon,
    then binary-search for the exact Julian Day.
    """
    swe.set_sid_mode(_AYANAMSA_MODES.get(ayanamsa, swe.SIDM_LAHIRI))

    jd = swe.julday(year, 1, 1, 0.0)
    jd_limit = swe.julday(year + 1, 1, 2, 0.0)

    prev_lon = None
    crossing_jd: Optional[float] = None

    while jd < jd_limit:
        res, _ = swe.calc_ut(jd, swe.SUN, _FLAGS)
        cur_lon = res[0] % 360.0

        if prev_lon is not None:
            delta = (cur_lon - prev_lon) % 360.0
            dist = (natal_sun_lon - prev_lon) % 360.0
            if 0 < dist <= delta:
                crossing_jd = jd - 1.0 + dist / max(delta, 1e-9)
                break

        prev_lon = cur_lon
        jd += 1.0

    if crossing_jd is None:
        # Fallback: approximate from natal sun longitude (degrees → day of year)
        crossing_jd = swe.julday(year, 1, 1, 0.0) + natal_sun_lon / 360.0 * 365.25

    # Binary-search to refine to < 1-second accuracy
    lo, hi = crossing_jd - 1.0, crossing_jd + 1.0
    for _ in range(48):
        mid = (lo + hi) / 2.0
        res, _ = swe.calc_ut(mid, swe.SUN, _FLAGS)
        diff = (res[0] % 360.0 - natal_sun_lon + 180.0) % 360.0 - 180.0
        if abs(diff) < 1e-7:
            break
        if diff < 0:
            lo = mid
        else:
            hi = mid

    return mid


def compute_varshaphal(
    ephemeris: Dict[str, Any],
    birth_details: Dict[str, Any],
    year: Optional[int] = None,
    ayanamsa: str = "lahiri",
) -> Dict[str, Any]:
    """
    Compute the Varshaphal (Solar Return) chart for `year`.

    Args:
        ephemeris: payload['ephemeris'].
        birth_details: payload['birth_details'].
        year: target year (defaults to current year UTC).
        ayanamsa: ayanamsa name.

    Returns:
        Varshaphal dict.
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    swe.set_sid_mode(_AYANAMSA_MODES.get(ayanamsa, swe.SIDM_LAHIRI))
    swe.set_ephe_path(".")

    natal_sun_lon = ephemeris.get("planets", {}).get("Sun", {}).get("longitude_deg", 0.0)
    natal_lagna_lon = ephemeris.get("lagna", {}).get("longitude_deg", 0.0)
    natal_lagna_idx = _sign_idx(natal_lagna_lon)

    latitude = birth_details.get("latitude", 13.0)
    longitude = birth_details.get("longitude", 80.0)
    dob = birth_details.get("date_of_birth", "")
    birth_year = int(dob.split("-")[0]) if dob else year - 30

    # ── Solar return Julian Day ───────────────────────────────────────────────
    try:
        sr_jd = _find_solar_return_jd(natal_sun_lon, year, ayanamsa)
    except Exception as e:
        logger.warning("Solar return search failed: %s", e)
        sr_jd = swe.julday(year, 10, 11, 12.0)

    # ── Convert to calendar date ──────────────────────────────────────────────
    try:
        sr_parts = swe.revjul(sr_jd)
        sr_date = f"{int(sr_parts[0]):04d}-{int(sr_parts[1]):02d}-{int(sr_parts[2]):02d}"
    except Exception:
        sr_date = f"{year}-10-11"

    # ── Varshaphal Lagna ─────────────────────────────────────────────────────
    try:
        _, ascmc = swe.houses_ex(sr_jd, latitude, longitude, b"P", swe.FLG_SIDEREAL)
        sr_lagna_lon = ascmc[0] % 360.0
    except Exception as e:
        logger.warning("SR lagna computation failed: %s", e)
        sr_lagna_lon = natal_lagna_lon

    sr_lagna_idx = _sign_idx(sr_lagna_lon)
    sr_lagna = RASI_NAMES[sr_lagna_idx]
    varshesha = _RASI_LORDS[sr_lagna_idx]

    # House of varshesha from natal lagna (use first owned sign)
    vh = next(
        ((i - natal_lagna_idx) % 12 + 1
         for i, lord in enumerate(_RASI_LORDS) if lord == varshesha),
        1,
    )

    # ── Muntha ────────────────────────────────────────────────────────────────
    years_elapsed = year - birth_year
    muntha_idx = (natal_lagna_idx + years_elapsed) % 12
    muntha_house = (muntha_idx - natal_lagna_idx) % 12 + 1

    # ── Benefics in kendras of SR chart ──────────────────────────────────────
    kendras = {1, 4, 7, 10}
    benefics_in_kendra = 0
    for pid in _BENEFIC_IDS.values():
        try:
            res, _ = swe.calc_ut(sr_jd, pid, _FLAGS)
            plon = res[0] % 360.0
            house = (_sign_idx(plon) - sr_lagna_idx) % 12 + 1
            if house in kendras:
                benefics_in_kendra += 1
        except Exception:
            pass

    if benefics_in_kendra >= 3:
        strength = "strong"
    elif benefics_in_kendra == 2:
        strength = "moderate"
    elif benefics_in_kendra == 1:
        strength = "weak"
    else:
        strength = "minimal"

    return {
        "year": year,
        "solar_return_date": sr_date,
        "lagna": sr_lagna,
        "varshesha": varshesha,
        "varshesha_house": vh,
        "muntha": RASI_NAMES[muntha_idx],
        "muntha_house": muntha_house,
        "strength": strength,
        "benefics_in_kendra": benefics_in_kendra,
    }
