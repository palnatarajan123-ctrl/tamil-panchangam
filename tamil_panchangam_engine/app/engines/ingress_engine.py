"""
Planet Ingress (Peyarchi) Engine

Computes exact future sign-change ("peyarchi") dates for slow-moving
planets: Rahu, Ketu, Jupiter, Saturn -- the same four gochara_engine.py
already tracks for transits.

Key design point: an ingress date is a GLOBAL astronomical fact, not a
per-user one ("Rahu enters Capricorn on Dec 5, 2026" is true for every
user simultaneously). Only the resulting house number is personal. So
this module computes each ingress ONCE via find_next_ingress() and
get_upcoming_ingresses() caches the result in planet_ingress_events --
chat-time lookups are a cheap indexed SELECT, never a live ephemeris
call in the request hot path. See CLAUDE.md's 2026-09-13 entry for the
incident this closes (Ask Jyotishi correctly refusing to answer "when"
questions after the earlier chat-grounding fix, rather than the
ungrounded fabrication that fix replaced -- this closes the remaining
gap by giving it a real, cached answer to give instead of a refusal).
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.utils.swisseph_utils import compute_planet_longitude_with_speed

logger = logging.getLogger(__name__)

RASI_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
RASI_TO_INDEX = {rasi: i for i, rasi in enumerate(RASI_ORDER)}

INGRESS_PLANETS = ["Rahu", "Ketu", "Jupiter", "Saturn"]

# Jupiter/Saturn can station retrograde and retreat back into the sign
# they just entered before finally settling -- a real, well-documented
# phenomenon (e.g. Saturn's 2017 Sagittarius/Capricorn back-and-forth,
# and its 2027 Pisces/Aries one verified during this feature's build).
# 300 days comfortably covers a full retrograde cycle for both planets
# (Saturn's retrograde period is ~140 days/year, Jupiter's ~120).
# Rahu/Ketu are always retrograde by convention and move in one
# direction continuously -- they never station, so this check is
# skipped for them.
_RETROGRADE_RETURN_CHECK_DAYS = 300
_RETROGRADE_RETURN_SAMPLE_STEP_DAYS = 10

# Placeholder used instead of NULL for node_type on Jupiter/Saturn rows.
# Postgres treats NULL != NULL under UNIQUE constraints, so two NULL
# node_type rows for the same planet/to_sign/date wouldn't be caught by
# ON CONFLICT DO NOTHING -- a real footgun for a lazy-backfill table
# that can be written from concurrent requests. Using a real value
# avoids it entirely.
NODE_TYPE_NOT_APPLICABLE = "n/a"


def _sign_idx(longitude: float) -> int:
    return int(longitude // 30) % 12


def find_next_ingress(
    planet: str,
    start_date_utc: datetime,
    node_type: str = "mean",
    ayanamsa: str = "lahiri",
    max_iters: int = 80,
) -> Dict:
    """
    Find the next sign-change (ingress) date for `planet` strictly after
    `start_date_utc`.

    Coarse-then-refine, not a day-by-day scan: estimates an adaptive
    step toward the next 30-degree boundary from the planet's current
    speed (re-estimated after every step, so it naturally shrinks as
    the planet slows near a station -- this is what makes it safe near
    a retrograde station rather than assuming monotonic motion), then
    bisects the bracketing interval once an actual sampled sign change
    is observed. Because it's sampling real positions rather than
    extrapolating, a genuine station-and-reverse is caught by the
    stepping itself; it isn't assumed away.

    Returns:
        {
            "planet": str, "from_sign": str, "to_sign": str,
            "ingress_date_utc": datetime,
            "retrograde_return_date_utc": datetime | None,
        }
    """
    lon, speed = compute_planet_longitude_with_speed(planet, start_date_utc, ayanamsa=ayanamsa, node_type=node_type)
    prev_date, prev_sign = start_date_utc, _sign_idx(lon)

    d = start_date_utc
    bracket = None
    for _ in range(max_iters):
        deg_in_sign = lon % 30
        if speed > 1e-6:
            remaining_deg = 30.0 - deg_in_sign
        elif speed < -1e-6:
            remaining_deg = deg_in_sign
        else:
            remaining_deg = None

        step_days = 5 if remaining_deg is None else max(1, min(remaining_deg / abs(speed), 15))
        d = d + timedelta(days=step_days)
        lon, speed = compute_planet_longitude_with_speed(planet, d, ayanamsa=ayanamsa, node_type=node_type)
        cur_sign = _sign_idx(lon)

        if cur_sign != prev_sign:
            bracket = (prev_date, d, prev_sign, cur_sign)
            break
        prev_date, prev_sign = d, cur_sign

    if bracket is None:
        raise RuntimeError(f"No ingress found for {planet} within {max_iters} adaptive steps from {start_date_utc}")

    lo, hi, from_idx, to_idx = bracket
    for _ in range(24):
        mid = lo + (hi - lo) / 2
        mlon, _ = compute_planet_longitude_with_speed(planet, mid, ayanamsa=ayanamsa, node_type=node_type)
        if _sign_idx(mlon) == from_idx:
            lo = mid
        else:
            hi = mid
        if (hi - lo) < timedelta(minutes=30):
            break
    ingress_date = hi

    retro_return = _find_retrograde_return(planet, ingress_date, from_idx, to_idx, node_type, ayanamsa)

    return {
        "planet": planet,
        "from_sign": RASI_ORDER[from_idx],
        "to_sign": RASI_ORDER[to_idx],
        "ingress_date_utc": ingress_date,
        "retrograde_return_date_utc": retro_return,
    }


def _find_retrograde_return(
    planet: str, ingress_date: datetime, from_idx: int, to_idx: int, node_type: str, ayanamsa: str
) -> Optional[datetime]:
    """Check whether `planet` retreats back into `from_idx`'s sign within
    _RETROGRADE_RETURN_CHECK_DAYS of ingress_date -- Jupiter/Saturn only."""
    if planet in ("Rahu", "Ketu"):
        return None

    prev_date, prev_sign = ingress_date, to_idx
    for days in range(_RETROGRADE_RETURN_SAMPLE_STEP_DAYS, _RETROGRADE_RETURN_CHECK_DAYS, _RETROGRADE_RETURN_SAMPLE_STEP_DAYS):
        d = ingress_date + timedelta(days=days)
        lon, _ = compute_planet_longitude_with_speed(planet, d, ayanamsa=ayanamsa, node_type=node_type)
        cur_sign = _sign_idx(lon)

        if cur_sign == from_idx:
            lo, hi = prev_date, d
            for _ in range(20):
                mid = lo + (hi - lo) / 2
                mlon, _ = compute_planet_longitude_with_speed(planet, mid, ayanamsa=ayanamsa, node_type=node_type)
                if _sign_idx(mlon) == to_idx:
                    lo = mid
                else:
                    hi = mid
                if (hi - lo) < timedelta(minutes=30):
                    break
            return hi

        if cur_sign != to_idx:
            # Moved on into a third sign without reverting -- no
            # retrograde return within the check window.
            return None

        prev_date, prev_sign = d, cur_sign

    return None


def get_upcoming_ingresses(
    conn,
    planet: str,
    node_type: str,
    now_utc: datetime,
    count: int = 2,
    ayanamsa: str = "lahiri",
) -> List[Dict]:
    """
    Return the next `count` upcoming ingresses for `planet` (and, for
    Rahu/Ketu, `node_type`), reading from the planet_ingress_events
    cache and lazily backfilling via find_next_ingress() if fewer than
    `count` future rows exist. This is the only function chat.py (or
    any other caller) should use -- never call find_next_ingress()
    directly from a request path.
    """
    lookup_node_type = node_type if planet in ("Rahu", "Ketu") else NODE_TYPE_NOT_APPLICABLE

    def _query():
        rows = conn.execute(
            "SELECT to_sign, ingress_date_utc, retrograde_return_date_utc "
            "FROM planet_ingress_events "
            "WHERE planet = ? AND node_type = ? AND ingress_date_utc > ? "
            "ORDER BY ingress_date_utc ASC LIMIT ?",
            [planet, lookup_node_type, now_utc, count],
        ).fetchall()
        return [
            {"to_sign": r[0], "ingress_date_utc": r[1], "retrograde_return_date_utc": r[2]}
            for r in rows
        ]

    rows = _query()
    if len(rows) < count:
        start_from = rows[-1]["ingress_date_utc"] if rows else now_utc
        needed = count - len(rows)
        for _ in range(needed):
            try:
                result = find_next_ingress(
                    planet, start_from + timedelta(days=1), node_type=lookup_node_type, ayanamsa=ayanamsa
                )
            except Exception as e:
                logger.warning(f"find_next_ingress failed for {planet}/{lookup_node_type}: {e}")
                break
            conn.execute(
                "INSERT INTO planet_ingress_events "
                "(planet, node_type, from_sign, to_sign, ingress_date_utc, retrograde_return_date_utc) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (planet, node_type, to_sign, ingress_date_utc) DO NOTHING",
                [
                    planet, lookup_node_type, result["from_sign"], result["to_sign"],
                    result["ingress_date_utc"], result["retrograde_return_date_utc"],
                ],
            )
            start_from = result["ingress_date_utc"]
        rows = _query()

    return rows


def house_from_sign(target_sign: str, reference_sign: str) -> int:
    """1-indexed house of `target_sign` counted from `reference_sign`."""
    return ((RASI_TO_INDEX[target_sign] - RASI_TO_INDEX[reference_sign]) % 12) + 1
