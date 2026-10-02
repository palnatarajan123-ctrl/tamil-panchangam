"""
Transit Hits Engine — degree-level transits of slow planets over natal positions.

Checks Jupiter, Saturn, Rahu, Ketu, Mars for conjunction, opposition, trine, square
(nodes: conjunction and opposition only) within a configurable day window.
"""

import logging
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional

from app.utils.swisseph_utils import compute_planet_longitude
from app.utils.prompt_dates import fmt_date

logger = logging.getLogger(__name__)

TRANSIT_PLANETS = ["Jupiter", "Saturn", "Rahu", "Ketu", "Mars"]

_FULL_ASPECTS = [
    ("conjunction", 0.0),
    ("opposition", 180.0),
    ("trine", 120.0),
    ("square", 90.0),
]
_NODE_ASPECTS = [
    ("conjunction", 0.0),
    ("opposition", 180.0),
]

_PLANET_ASPECTS = {
    "Jupiter": _FULL_ASPECTS,
    "Saturn": _FULL_ASPECTS,
    "Mars": _FULL_ASPECTS,
    "Rahu": _NODE_ASPECTS,
    "Ketu": _NODE_ASPECTS,
}

ORB = 2.0  # degrees

HOUSE_LIFE_AREA = {
    1: "self", 2: "wealth", 3: "communication", 4: "home",
    5: "creativity", 6: "health", 7: "relationships", 8: "transformation",
    9: "fortune", 10: "career", 11: "gains", 12: "spirituality",
}


def _angular_diff(transit_lon: float, natal_lon: float, aspect_angle: float) -> float:
    """Smallest angular distance between transit-natal and the target aspect."""
    raw = (transit_lon - natal_lon) % 360.0
    return min(abs(raw - aspect_angle), abs(raw - aspect_angle + 360.0), abs(raw - aspect_angle - 360.0))


def _house_of(natal_planet_lon: float, lagna_lon: float) -> int:
    return int((natal_planet_lon - lagna_lon) % 360.0 / 30.0) % 12 + 1


def compute_transit_hits(
    ephemeris: Dict[str, Any],
    reference_date: Optional[date] = None,
    ayanamsa: str = "lahiri",
    window_days: int = 45,
    node_type: str = "mean",
) -> List[Dict[str, Any]]:
    """
    Detect transit hits of slow planets over natal positions within
    [reference_date − window_days, reference_date + window_days].

    Args:
        ephemeris: payload['ephemeris']
        reference_date: center of window; defaults to today UTC.
        ayanamsa: ayanamsa name.
        window_days: half-window size (total window = 2 × window_days days).
        node_type: "mean" (traditional Tamil astrology, default) or "true"
            (astronomical) -- only affects Rahu/Ketu hits; pass the chart's
            own chart_metadata.node_type.

    Returns:
        List of transit hit dicts sorted by hit_date.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()

    lagna_lon = ephemeris.get("lagna", {}).get("longitude_deg", 0.0)
    natal_planets = ephemeris.get("planets", {})
    if not natal_planets:
        return []

    start_day = reference_date - timedelta(days=window_days)
    end_day = reference_date + timedelta(days=window_days)

    # best_hit[key] = dict with minimum orb seen so far
    best_hit: Dict[tuple, Dict[str, Any]] = {}

    for transit_planet in TRANSIT_PLANETS:
        aspects = _PLANET_ASPECTS[transit_planet]
        day = start_day
        while day <= end_day:
            dt = datetime(day.year, day.month, day.day, 12, 0, tzinfo=timezone.utc)
            try:
                transit_lon = compute_planet_longitude(transit_planet, dt, ayanamsa, node_type=node_type)
            except Exception as e:
                logger.debug("Transit lon %s %s: %s", transit_planet, day, e)
                day += timedelta(days=1)
                continue

            for natal_name, natal_data in natal_planets.items():
                natal_lon = natal_data.get("longitude_deg")
                if natal_lon is None:
                    continue

                for aspect_name, aspect_angle in aspects:
                    orb = _angular_diff(transit_lon, natal_lon, aspect_angle)
                    if orb > ORB:
                        continue

                    key = (transit_planet, natal_name, aspect_name)
                    prev = best_hit.get(key)
                    if prev is None or orb < prev["orb"]:
                        house = _house_of(natal_lon, lagna_lon)
                        best_hit[key] = {
                            "transit_planet": transit_planet,
                            "natal_planet": natal_name,
                            "natal_degree": round(natal_lon, 2),
                            "transit_degree": round(transit_lon, 2),
                            "hit_date": day.isoformat(),
                            "aspect_type": aspect_name,
                            "orb": round(orb, 2),
                            "house": house,
                            "life_area_hint": HOUSE_LIFE_AREA.get(house, "unknown"),
                        }
            day += timedelta(days=1)

    hits = sorted(best_hit.values(), key=lambda h: h["hit_date"])
    return hits


# ── Chat-facing selection (2026-10-02) ───────────────────────────────────────
#
# Framing decision: chat speaks classical Vedic, and trine/square are
# Western aspects. Only relationships with an EXACT classical counterpart
# are surfaced, named in Vedic terms:
#   conjunction -> transiting over the natal planet
#   opposition  -> 7th-house aspect (the full aspect every planet casts)
#   trine/square only where they coincide with that planet's own special
#   drishti, counted forward from the transiting planet: Jupiter 5th
#   (~120) / 9th (~240), Mars 4th (~90), Saturn 10th (~270).
# All other trines/squares are dropped rather than relabelled -- a
# "nearest classical name" would misstate what was computed. The `house`/
# `life_area_hint` fields are never surfaced: _house_of() is Equal House,
# not the whole-sign system used everywhere else (open backlog item).

_SPECIAL_DRISHTI = {
    "Jupiter": {120: "5th", 240: "9th"},
    "Mars": {90: "4th"},
    "Saturn": {270: "10th"},
}


def _vedic_relation(hit: Dict[str, Any]) -> Optional[str]:
    tp, aspect = hit["transit_planet"], hit["aspect_type"]
    if aspect == "conjunction":
        return f"transiting over your natal {hit['natal_planet']}"
    if aspect == "opposition":
        return f"exactly opposite your natal {hit['natal_planet']} (its 7th-house aspect)"
    forward = (hit["natal_degree"] - hit["transit_degree"]) % 360.0
    for angle, nth in _SPECIAL_DRISHTI.get(tp, {}).items():
        if abs(forward - angle) <= ORB + 0.5:
            return f"casting its special {nth}-house aspect exactly onto your natal {hit['natal_planet']}"
    return None


def select_chat_transit_hits(
    hits: List[Dict[str, Any]],
    reference_date: date,
    window_days: int = 45,
) -> List[Dict[str, Any]]:
    """Filter compute_transit_hits() output to Vedic-meaningful relations and
    mark window-edge hits: compute_transit_hits() keeps the closest day
    WITHIN the window, so a hit on the first/last day is still approaching
    (or already separating) beyond the scan -- that day is not the exact date."""
    start = (reference_date - timedelta(days=window_days)).isoformat()
    end = (reference_date + timedelta(days=window_days)).isoformat()
    out = []
    for h in hits:
        relation = _vedic_relation(h)
        if not relation:
            continue
        if h["hit_date"] == end:
            when = f"tightening; becomes exact after {fmt_date(end)} (beyond the {window_days}-day scan)"
        elif h["hit_date"] == start:
            when = f"was exact before {fmt_date(start)} (beyond the {window_days}-day scan), now separating"
        elif h["hit_date"] < reference_date.isoformat():
            when = f"exact on {fmt_date(h['hit_date'])} (past, now separating)"
        else:
            when = f"exact on {fmt_date(h['hit_date'])}"
        out.append({
            "transit_planet": h["transit_planet"],
            "natal_planet": h["natal_planet"],
            "relation": relation,
            "when": when,
            "hit_date": h["hit_date"],
            "orb": h["orb"],
        })
    return out


def format_chat_transit_hits(selected: List[Dict[str, Any]]) -> str:
    """Verbose rendering for chat.py."""
    return "\n".join(f"- Transiting {s['transit_planet']} {s['relation']}: {s['when']}" for s in selected)


def format_chat_transit_hits_compact(selected: List[Dict[str, Any]], reference_date: date, limit: int = 3) -> str:
    """The `limit` hits nearest to reference_date, one clause, for family.py."""
    if not selected:
        return ""
    nearest = sorted(selected, key=lambda s: abs((date.fromisoformat(s["hit_date"]) - reference_date).days))[:limit]
    return "Exact-degree transits: " + "; ".join(
        f"{s['transit_planet']} {s['relation'].replace('your natal', 'natal')} ({s['when']})" for s in nearest
    )
