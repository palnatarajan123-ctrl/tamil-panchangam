"""
Special Lagnas Engine — Arudha, Hora, Ghati, and Upapada Lagna.

All four are derived from the birth lagna, birth time, sunrise, and planet positions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import swisseph as swe

logger = logging.getLogger(__name__)

RASI_NAMES = [
    "Mesham", "Rishabam", "Midhunam", "Kadagam", "Simham", "Kanni",
    "Thulam", "Vrischikam", "Dhanusu", "Makaram", "Kumbham", "Meenam",
]

# Traditional sign lords by index (0=Mesham … 11=Meenam)
_RASI_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
]

_AYANAMSA_MODES = {
    "lahiri": swe.SIDM_LAHIRI,
    "kp": swe.SIDM_KRISHNAMURTI,
}


def _sign_idx(lon: float) -> int:
    return int(lon / 30.0) % 12


def _house_from_lagna(sign_idx: int, lagna_sign_idx: int) -> int:
    return (sign_idx - lagna_sign_idx) % 12 + 1


def _compute_sunrise_jd(date_str: str, latitude: float, longitude: float) -> float:
    """Return Julian Day of sunrise. Falls back to 6am local if computation fails."""
    y, m, d = (int(x) for x in date_str.split("-"))
    jd_start = swe.julday(y, m, d, 0.0)
    try:
        res = swe.rise_trans(
            jd_start, swe.SUN,
            geopos=(longitude, latitude, 0.0),
            rsmi=swe.CALC_RISE | swe.BIT_DISC_CENTER,
        )
        return res[1][0]
    except Exception as e:
        logger.debug("Sunrise failed %s: %s — using 6am fallback", date_str, e)
        return jd_start + 6.0 / 24.0


def _compute_arudha(
    lagna_lon: float,
    planets: Dict[str, Any],
    house_offset: int,
    lagna_sign_idx: int,
) -> Dict[str, Any]:
    """
    Compute Arudha for any house (house_offset=0 → 1st house Arudha,
    house_offset=11 → 12th house Upapada).
    """
    target_sign_idx = (lagna_sign_idx + house_offset) % 12
    house_lord = _RASI_LORDS[target_sign_idx]

    lord_data = planets.get(house_lord, {})
    lord_lon = lord_data.get("longitude_deg")
    if lord_lon is None:
        # Lord not found — return lagna itself as safe fallback
        return {"rasi": RASI_NAMES[lagna_sign_idx], "house_from_lagna": 1}

    lord_sign_idx = _sign_idx(lord_lon)
    # N = how many signs the lord is from the target house (1-indexed)
    n = (lord_sign_idx - target_sign_idx) % 12 + 1
    # Count N more from the lord's sign
    arudha_sign_idx = (lord_sign_idx + n - 1) % 12

    # Exception: if result equals lagna or 7th from lagna, add 10
    seventh = (lagna_sign_idx + 6) % 12
    if arudha_sign_idx == lagna_sign_idx or arudha_sign_idx == seventh:
        arudha_sign_idx = (arudha_sign_idx + 10) % 12

    return {
        "rasi": RASI_NAMES[arudha_sign_idx],
        "house_from_lagna": _house_from_lagna(arudha_sign_idx, lagna_sign_idx),
    }


def compute_special_lagnas(
    ephemeris: Dict[str, Any],
    birth_details: Dict[str, Any],
    ayanamsa: str = "lahiri",
) -> Dict[str, Any]:
    """
    Compute Arudha, Hora, Ghati, and Upapada Lagnas.

    Args:
        ephemeris: payload['ephemeris'] (needs lagna and planets).
        birth_details: payload['birth_details'].
        ayanamsa: ayanamsa name.

    Returns:
        {"arudha": {...}, "hora": {...}, "ghati": {...}, "upapada": {...}}
    """
    swe.set_sid_mode(_AYANAMSA_MODES.get(ayanamsa, swe.SIDM_LAHIRI))
    swe.set_ephe_path(".")

    lagna_lon = ephemeris.get("lagna", {}).get("longitude_deg", 0.0)
    lagna_sign_idx = _sign_idx(lagna_lon)
    planets = ephemeris.get("planets", {})

    date_str = birth_details.get("date_of_birth", "")
    time_str = birth_details.get("time_of_birth", "00:00:00")
    latitude = birth_details.get("latitude", 13.0)
    longitude = birth_details.get("longitude", 80.0)
    timezone_str = birth_details.get("timezone", "UTC")

    # ── Arudha Lagna (1st house) ──────────────────────────────────────────────
    arudha = _compute_arudha(lagna_lon, planets, 0, lagna_sign_idx)

    # ── Upapada Lagna (12th house Arudha) ────────────────────────────────────
    upapada = _compute_arudha(lagna_lon, planets, 11, lagna_sign_idx)

    # ── Elapsed time since sunrise ────────────────────────────────────────────
    elapsed_hours = 0.0
    if date_str:
        try:
            sunrise_jd = _compute_sunrise_jd(date_str, latitude, longitude)
            y, m, d = (int(x) for x in date_str.split("-"))
            h, mi, s = (int(x) for x in time_str.split(":"))

            try:
                from zoneinfo import ZoneInfo
                local_dt = datetime(y, m, d, h, mi, s, tzinfo=ZoneInfo(timezone_str))
                utc_offset_hours = local_dt.utcoffset().total_seconds() / 3600.0
            except Exception:
                utc_offset_hours = 5.5  # IST fallback

            birth_ut_hours = h + mi / 60.0 + s / 3600.0 - utc_offset_hours
            birth_jd = swe.julday(y, m, d, birth_ut_hours)
            elapsed_hours = max(0.0, (birth_jd - sunrise_jd) * 24.0)
        except Exception as e:
            logger.warning("Elapsed-time computation failed: %s", e)

    elapsed_ghatis = elapsed_hours * 2.5  # 1 hour = 2.5 ghatis

    # ── Hora Lagna ───────────────────────────────────────────────────────────
    hora_lon = (elapsed_hours * 30.0 + lagna_lon) % 360.0
    hora_sign_idx = _sign_idx(hora_lon)

    # ── Ghati Lagna ──────────────────────────────────────────────────────────
    ghati_lon = (elapsed_ghatis * 5.0 + lagna_lon) % 360.0
    ghati_sign_idx = _sign_idx(ghati_lon)

    return {
        "arudha": arudha,
        "hora": {
            "rasi": RASI_NAMES[hora_sign_idx],
            "house_from_lagna": _house_from_lagna(hora_sign_idx, lagna_sign_idx),
        },
        "ghati": {
            "rasi": RASI_NAMES[ghati_sign_idx],
            "house_from_lagna": _house_from_lagna(ghati_sign_idx, lagna_sign_idx),
        },
        "upapada": upapada,
    }
