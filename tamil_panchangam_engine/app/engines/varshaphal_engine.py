"""
Varshaphal Engine — Annual Chart (Solar Return).

Finds the moment the Sun returns to its natal longitude in the target year,
then derives Varshaphal Lagna, Varshesha, Muntha, and chart strength.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import swisseph as swe

from app.utils.swisseph_utils import compute_planet_longitude_at_jd
from app.utils.prompt_dates import fmt_date, fmt_month

logger = logging.getLogger(__name__)

RASI_NAMES = [
    "Mesham", "Rishabam", "Midhunam", "Kadagam", "Simham", "Kanni",
    "Thulam", "Vrischikam", "Dhanusu", "Makaram", "Kumbham", "Meenam",
]

_RASI_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
]

_BENEFIC_PLANETS = ["Moon", "Mercury", "Jupiter", "Venus"]


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
    jd = swe.julday(year, 1, 1, 0.0)
    jd_limit = swe.julday(year + 1, 1, 2, 0.0)

    prev_lon = None
    crossing_jd: Optional[float] = None

    while jd < jd_limit:
        cur_lon = compute_planet_longitude_at_jd("Sun", jd, ayanamsa)

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
        cur_lon = compute_planet_longitude_at_jd("Sun", mid, ayanamsa)
        diff = (cur_lon - natal_sun_lon + 180.0) % 360.0 - 180.0
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
    Compute the Varshaphal (Solar Return) chart for the solar return that
    falls in CALENDAR year `year`. That return may still be in the future
    relative to a given date (birthday later in the year) -- callers wanting
    the annual chart in force on a date must use get_varshaphal_in_force().

    Args:
        ephemeris: payload['ephemeris'].
        birth_details: payload['birth_details'].
        year: calendar year of the solar return (defaults to current year UTC).
        ayanamsa: ayanamsa name.

    Returns:
        Varshaphal dict. `annual_lagna_lord` is only the annual Lagna's lord,
        not the classical Tajika Varsheshwara (chosen among five
        office-bearers by strength), so it must not be called the year-lord.
        `muntha_house` is counted from the ANNUAL Lagna (how Tajika judges
        Muntha); `muntha_house_from_natal_lagna` is always age % 12 + 1.
    """
    if year is None:
        year = datetime.now(timezone.utc).year

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
    # Consolidated 2026-09-14 onto the single shared compute_lagna() (see
    # ephemeris.py) instead of this file's own independently-duplicated
    # swe.houses_ex() call -- compute_lagna() already sets sidereal mode
    # explicitly (same reasoning this comment used to give for doing it
    # locally: not relying on a leftover value from an earlier
    # compute_planet_longitude_at_jd() call succeeding).
    try:
        from app.engines.ephemeris import compute_lagna
        sr_lagna_lon = compute_lagna(sr_jd, latitude, longitude, ayanamsa)
    except Exception as e:
        logger.warning("SR lagna computation failed: %s", e)
        sr_lagna_lon = natal_lagna_lon

    sr_lagna_idx = _sign_idx(sr_lagna_lon)
    sr_lagna = RASI_NAMES[sr_lagna_idx]
    annual_lagna_lord = _RASI_LORDS[sr_lagna_idx]

    # ── Muntha ────────────────────────────────────────────────────────────────
    years_elapsed = year - birth_year
    muntha_idx = (natal_lagna_idx + years_elapsed) % 12
    muntha_house = (muntha_idx - sr_lagna_idx) % 12 + 1
    muntha_house_from_natal_lagna = (muntha_idx - natal_lagna_idx) % 12 + 1

    # ── Benefics in kendras of SR chart ──────────────────────────────────────
    kendras = {1, 4, 7, 10}
    benefics_in_kendra = 0
    for planet_name in _BENEFIC_PLANETS:
        try:
            plon = compute_planet_longitude_at_jd(planet_name, sr_jd, ayanamsa)
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
        "annual_lagna_lord": annual_lagna_lord,
        "muntha": RASI_NAMES[muntha_idx],
        "muntha_house": muntha_house,
        "muntha_house_from_natal_lagna": muntha_house_from_natal_lagna,
        "strength": strength,
        "benefics_in_kendra": benefics_in_kendra,
    }


# ── Annual chart in force on a date, cached per chart per solar-return year ──

_ENGLISH_RASI = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
_CACHE_KEY = "varshaphal_by_year"
# Bump to invalidate cached entries if compute_varshaphal()'s semantics change.
# 2: varshesha -> annual_lagna_lord, varshesha_house dropped, muntha_house
#    now from the annual Lagna.
_CACHE_VERSION = 2


def _cached_or_compute(chart_id: Optional[str], payload: Dict[str, Any], year: int) -> Dict[str, Any]:
    """compute_varshaphal() for `year`, read from / written to
    base_charts.payload[_CACHE_KEY][str(year)]. The annual chart only
    depends on static natal data + the year, so it never needs recomputing."""
    cached = (payload.get(_CACHE_KEY) or {}).get(str(year))
    if cached and cached.get("cache_version") == _CACHE_VERSION:
        return cached

    result = compute_varshaphal(
        ephemeris=payload.get("ephemeris", {}),
        birth_details=payload.get("birth_details", {}),
        year=year,
        ayanamsa=(payload.get("chart_metadata") or {}).get("ayanamsa", "lahiri"),
    )
    result["cache_version"] = _CACHE_VERSION
    payload.setdefault(_CACHE_KEY, {})[str(year)] = result

    if chart_id:
        try:
            import json
            from app.db.postgres import get_conn
            with get_conn() as conn:
                conn.execute(
                    "UPDATE base_charts SET payload = jsonb_set(payload, %s, "
                    "COALESCE(payload->%s, '{}'::jsonb) || %s::jsonb) WHERE id = %s",
                    ("{" + _CACHE_KEY + "}", _CACHE_KEY, json.dumps({str(year): result}), chart_id),
                )
        except Exception as e:
            logger.warning("Varshaphal cache write failed chart=%s: %s", chart_id, e)
    return result


def get_varshaphal_in_force(
    chart_id: Optional[str],
    payload: Dict[str, Any],
    on_date: Optional["date"] = None,
) -> Dict[str, Any]:
    """
    The annual chart in force on `on_date` (default today UTC): the most
    recent solar return on or before that date -- NOT simply
    compute_varshaphal(on_date.year), whose return may still be in the
    future (birthday later in the year). The single entry point for every
    consumer: chat/family (today) and monthly predictive signals (the
    prediction month's anchor date).

    Adds display fields on top of compute_varshaphal()'s output.
    Returns {} if the computation fails.
    """
    from datetime import date as _date
    on_date = on_date or datetime.now(timezone.utc).date()
    try:
        vp = _cached_or_compute(chart_id, payload, on_date.year)
        if _date.fromisoformat(vp["solar_return_date"]) > on_date:
            vp = _cached_or_compute(chart_id, payload, on_date.year - 1)
    except Exception as e:
        logger.warning("Varshaphal in force failed chart=%s: %s", chart_id, e)
        return {}

    lagna_idx = RASI_NAMES.index(vp["lagna"])
    muntha_idx = RASI_NAMES.index(vp["muntha"])
    sr = _date.fromisoformat(vp["solar_return_date"])
    return {
        **vp,
        "lagna_english": _ENGLISH_RASI[lagna_idx],
        "muntha_english": _ENGLISH_RASI[muntha_idx],
        "next_return_approx": f"{sr.year + 1}-{sr.month:02d}",
    }


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def format_varshaphal_context(vp: Dict[str, Any]) -> str:
    """Verbose rendering for chat.py's system prompt."""
    if not vp:
        return ""
    return "\n".join([
        f"- Annual year in force: from the solar return on {fmt_date(vp['solar_return_date'])} "
        f"until the next one (around {fmt_month(vp['next_return_approx'])})",
        f"- Annual Lagna: {vp['lagna_english']} ({vp['lagna']}); its lord: {vp['annual_lagna_lord']}",
        f"- Muntha: {vp['muntha_english']} ({vp['muntha']}) -- "
        f"{_ordinal(vp['muntha_house'])} house from the annual Lagna, "
        f"{_ordinal(vp['muntha_house_from_natal_lagna'])} from the natal Lagna",
        f"- Natural benefics (Moon, Mercury, Jupiter, Venus) in kendras (1/4/7/10) of the "
        f"annual chart: {vp['benefics_in_kendra']} of 4",
    ])


def format_varshaphal_compact(vp: Dict[str, Any]) -> str:
    """One-clause rendering for family.py's per-member line."""
    if not vp:
        return ""
    return (f"Annual chart (from {fmt_date(vp['solar_return_date'])}): Lagna {vp['lagna_english']}, "
            f"Muntha {vp['muntha_english']} ({_ordinal(vp['muntha_house'])} "
            f"from annual Lagna)")
