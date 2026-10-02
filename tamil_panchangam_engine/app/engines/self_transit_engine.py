# app/engines/self_transit_engine.py
"""
Self-relative transits: when does a transiting planet next return to, or
cast an exact classical aspect onto, its OWN natal degree -- beyond the
+/-45-day window transit_hits_engine.py already covers.

Search shape reused from ingress_engine.find_next_ingress(): sample real
positions coarse-then-refine (one forward sweep per planet, every target
degree checked per sample, bisection once a crossing is bracketed),
retargeted from a sign boundary to a specific degree. Because it samples
real positions, retrograde passes are caught, not assumed away: Jupiter/
Saturn/Mars can cross a degree up to three times, and all passes of one
event are returned together.

Framing matches transit_hits_engine.select_chat_transit_hits(): return
(conjunction), opposition (7th aspect), and the planet's own classical
special drishti, counted forward from the transiting planet. Rahu/Ketu:
nodal return and half-return (Rahu over natal Ketu) -- Ketu is always
Rahu + 180, so Rahu alone determines both.

Cached per chart in base_charts.payload["self_transits"]; valid until the
earliest cached future date comes within the +/-45-day window (then that
event belongs to transit_hits_engine.py, and the next one is needed).
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.utils.swisseph_utils import compute_planet_longitude_with_speed

logger = logging.getLogger(__name__)

TRANSIT_HITS_WINDOW_DAYS = 45  # transit_hits_engine.compute_transit_hits() default
_CACHE_KEY = "self_transits"
_CACHE_VERSION = 1
_PASS_SPAN_DAYS = 400  # retrograde re-crossings of one event fall within this

# planet -> (sweep step days, search horizon years, [(event label, forward angle)])
# Forward angle = how far the NATAL point lies ahead of the transiting planet.
_EVENTS: Dict[str, Tuple[float, float, List[Tuple[str, float]]]] = {
    "Jupiter": (1, 13, [("return", 0), ("opposition (7th aspect)", 180),
                        ("5th-house aspect", 120), ("9th-house aspect", 240)]),
    "Saturn": (1, 31, [("return", 0), ("opposition (7th aspect)", 180),
                       ("3rd-house aspect", 60), ("10th-house aspect", 270)]),
    "Mars": (1, 3, [("return", 0), ("opposition (7th aspect)", 180),
                    ("4th-house aspect", 90), ("8th-house aspect", 210)]),
    "Rahu": (2, 20, [("nodal return (Rahu over natal Rahu, Ketu over natal Ketu)", 0),
                     ("nodal half-return (Rahu over natal Ketu, Ketu over natal Rahu)", 180)]),
}


def _signed_diff(lon: float, target: float) -> float:
    return (lon - target + 540.0) % 360.0 - 180.0


def _to_dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc)


def _bisect(planet: str, lo: datetime, hi: datetime, target: float, ayanamsa: str, node_type: str) -> datetime:
    f_lo = _signed_diff(compute_planet_longitude_with_speed(planet, lo, ayanamsa, node_type)[0], target)
    for _ in range(30):
        mid = lo + (hi - lo) / 2
        f_mid = _signed_diff(compute_planet_longitude_with_speed(planet, mid, ayanamsa, node_type)[0], target)
        if (f_mid < 0) == (f_lo < 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
        if hi - lo < timedelta(hours=1):
            break
    return lo + (hi - lo) / 2


def _sweep(planet: str, natal_lon: float, start: date, direction: int,
           ayanamsa: str, node_type: str, events: List[Tuple[str, float]]) -> Dict[str, List[str]]:
    """First pass (all retrograde re-crossings) of each event, sweeping from
    `start` forward (direction=1) or backward (-1). Returns label -> dates."""
    step, horizon_years, _ = _EVENTS[planet]
    targets = {label: (natal_lon - angle) % 360.0 for label, angle in events}
    found: Dict[str, List[str]] = {}
    first_at: Dict[str, datetime] = {}
    t = _to_dt(start)
    end = t + direction * timedelta(days=horizon_years * 365.25)
    prev_t, prev_lon = t, compute_planet_longitude_with_speed(planet, t, ayanamsa, node_type)[0]
    while (t < end) if direction > 0 else (t > end):
        t = prev_t + direction * timedelta(days=step)
        lon = compute_planet_longitude_with_speed(planet, t, ayanamsa, node_type)[0]
        for label, target in targets.items():
            if label in first_at and abs((t - first_at[label]).days) > _PASS_SPAN_DAYS:
                continue  # that event's pass is complete
            f0, f1 = _signed_diff(prev_lon, target), _signed_diff(lon, target)
            if (f0 < 0) != (f1 < 0) and abs(f0) < 90 and abs(f1) < 90:  # real crossing, not the 180 wrap
                lo, hi = (prev_t, t) if direction > 0 else (t, prev_t)
                exact = _bisect(planet, lo, hi, target, ayanamsa, node_type)
                first_at.setdefault(label, exact)
                found.setdefault(label, []).append(exact.date().isoformat())
        if len(first_at) == len(targets) and all(abs((t - v).days) > _PASS_SPAN_DAYS for v in first_at.values()):
            break
        prev_t, prev_lon = t, lon
    return {k: sorted(v) for k, v in found.items()}


def compute_self_transits(payload: Dict[str, Any], today: Optional[date] = None) -> Dict[str, Any]:
    """Next (beyond today+45d) occurrence of every self-relative event, and
    the most recent past return (before today-45d), for each planet."""
    today = today or datetime.now(timezone.utc).date()
    meta = payload.get("chart_metadata") or {}
    ayanamsa, node_type = meta.get("ayanamsa", "lahiri"), meta.get("node_type", "mean")
    planets = (payload.get("ephemeris") or {}).get("planets", {})
    future_start = today + timedelta(days=TRANSIT_HITS_WINDOW_DAYS + 1)
    past_start = today - timedelta(days=TRANSIT_HITS_WINDOW_DAYS + 1)

    events: List[Dict[str, Any]] = []
    for planet, (_, _, planet_events) in _EVENTS.items():
        natal_lon = (planets.get(planet) or {}).get("longitude_deg")
        if natal_lon is None:
            continue
        nxt = _sweep(planet, natal_lon, future_start, 1, ayanamsa, node_type, planet_events)
        prev = _sweep(planet, natal_lon, past_start, -1, ayanamsa, node_type, planet_events[:1])
        for label, _angle in planet_events:
            events.append({
                "planet": planet,
                "event": label,
                "next_dates": nxt.get(label, []),
                "last_date": (prev.get(label) or [None])[-1] if label == planet_events[0][0] else None,
            })
    return {"computed_on": today.isoformat(), "cache_version": _CACHE_VERSION, "events": events}


def get_self_transits(chart_id: Optional[str], payload: Dict[str, Any], today: Optional[date] = None) -> Dict[str, Any]:
    """compute_self_transits(), cached in the chart payload while still valid."""
    today = today or datetime.now(timezone.utc).date()
    horizon = (today + timedelta(days=TRANSIT_HITS_WINDOW_DAYS)).isoformat()
    cached = payload.get(_CACHE_KEY)
    if cached and cached.get("cache_version") == _CACHE_VERSION and cached.get("computed_on", "") <= today.isoformat():
        nexts = [d for e in cached["events"] for d in e["next_dates"][:1]]
        if nexts and min(nexts) > horizon:
            return cached

    try:
        result = compute_self_transits(payload, today)
    except Exception as e:
        logger.warning("Self-transit computation failed chart=%s: %s", chart_id, e)
        return {}
    payload[_CACHE_KEY] = result
    if chart_id:
        try:
            import json
            from app.db.postgres import get_conn
            with get_conn() as conn:
                conn.execute(
                    "UPDATE base_charts SET payload = payload || %s::jsonb WHERE id = %s",
                    (json.dumps({_CACHE_KEY: result}), chart_id),
                )
        except Exception as e:
            logger.warning("Self-transit cache write failed chart=%s: %s", chart_id, e)
    return result


def _human(iso: str) -> str:
    # "22 May 2029", not "2029-05-22": with ISO dates the model was observed
    # (2/3 live runs) restating 2029-05-22 as "29 May 2029" -- the year's
    # "29" bleeding into the day.
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B')} {d.year}"


def _fmt_next(e: Dict[str, Any]) -> str:
    d = [_human(x) for x in e["next_dates"]]
    if not d:
        return "not within the search horizon"
    if len(d) == 1:
        return f"next exact {d[0]}"
    return f"next exact {d[0]} (retrograde motion makes it exact {len(d)} times: {'; '.join(d)})"


def format_self_transits_context(st: Dict[str, Any]) -> str:
    """Verbose rendering for chat.py."""
    if not st or not st.get("events"):
        return ""
    lines = []
    for e in st["events"]:
        if e["planet"] == "Rahu":
            line = f"- Rahu/Ketu {e['event']}: {_fmt_next(e)}"
        else:
            line = f"- {e['planet']} {e['event']} to its own natal degree: {_fmt_next(e)}"
        if e.get("last_date"):
            line += f"; most recent {_human(e['last_date'])}"
        lines.append(line)
    return "\n".join(lines)


def format_self_transits_compact(st: Dict[str, Any]) -> str:
    """Returns only (Jupiter/Saturn/nodal), next date each, for family.py."""
    if not st or not st.get("events"):
        return ""
    bits = []
    for e in st["events"]:
        is_return = e["event"] == "return" or e["event"].startswith("nodal return")
        if is_return and e["planet"] in ("Jupiter", "Saturn", "Rahu") and e["next_dates"]:
            name = "Nodal" if e["planet"] == "Rahu" else e["planet"]
            bits.append(f"{name} return {_human(e['next_dates'][0])}")
    return "Next returns to natal degree: " + ", ".join(bits) if bits else ""
