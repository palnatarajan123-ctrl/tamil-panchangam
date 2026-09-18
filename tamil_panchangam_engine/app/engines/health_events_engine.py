# app/engines/health_events_engine.py
"""
Health Events Engine.

Generalizes children_timing_engine.py's proven pattern (real,
deterministic dasha-window computation per classical significator) to
health-vulnerability windows: 6th house (disease/daily struggle) and
8th house (longevity/chronic/transformative health) lords, from Moon
rasi -- consistent with this "timing engines" family's established
convention (see children_timing_engine.py's _get_house_lord()).

Also computes a real, simple "afflicting combination" check: whether a
natural malefic (Saturn, Mars, Rahu, Ketu) natally occupies the 6th or
8th house itself -- a well-defined classical fact (a natural malefic
tenanting a dusthana/health house intensifies its significance),
computed directly from natal planetary positions rather than requiring
the full Lagna-based house_strength_engine.py machinery (a different,
inconsistent house-reference convention for this module's purpose).

Like marriage_timing_engine.py, this module returns real per-
significator facts, not a single synthesized "you will be sick in year
X" verdict -- that synthesis (and choosing gentle, non-alarming framing)
is left to the LLM narrative layer, which must cite which significator
backs any specific claim.
"""
import logging
from typing import Any, Dict, List, Optional

from app.engines.children_timing_engine import RASI_LORDS, _get_house_lord, _find_planet_dashas
from app.engines.porutham_engine import _rasi_index

logger = logging.getLogger(__name__)

_NATURAL_MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu"}
_CLASSICAL_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def _occupants_of_house(rasi_index: int, house_number: int, planets: Dict[str, Any]) -> List[str]:
    """Which planets (of the 9 grahas) natally occupy `house_number`
    counted from Moon rasi -- a plain sign-membership check, no house
    cusps involved (whole-sign houses, same convention this module's
    house-lord lookup already uses)."""
    target_sign = (rasi_index + house_number - 1) % 12
    occupants = []
    for planet in _CLASSICAL_PLANETS:
        lon = planets.get(planet, {}).get("longitude_deg")
        if lon is not None and int(lon // 30) == target_sign:
            occupants.append(planet)
    return occupants


def compute_health_event_signals(
    payload: Dict[str, Any],
    year_from: int,
    year_to: int,
) -> Dict[str, Any]:
    """
    Real, deterministic health-vulnerability signals for one chart:
    6th/8th house lords (from Moon), their real Dasha windows in the
    requested range, and whether a natural malefic natally occupies
    either house (an afflicting combination, intensifying that lord's
    significance when its dasha runs).
    """
    ephemeris = payload.get("ephemeris", {}) if isinstance(payload, dict) else {}
    moon = ephemeris.get("moon", {}) if isinstance(ephemeris, dict) else {}
    rasi_index = _rasi_index(moon.get("rasi", "")) or 0
    planets = ephemeris.get("planets", {}) if isinstance(ephemeris, dict) else {}
    vimshottari = (
        payload.get("dashas", {}).get("vimshottari", {})
        if isinstance(payload, dict) else {}
    )

    result: Dict[str, Any] = {}
    for house_number, key in ((6, "sixth"), (8, "eighth")):
        lord = _get_house_lord(rasi_index, house_number)
        dashas = _find_planet_dashas(vimshottari, lord, year_from, year_to)
        occupants = _occupants_of_house(rasi_index, house_number, planets)
        afflicting_malefics = [p for p in occupants if p in _NATURAL_MALEFICS]
        result[f"{key}_lord"] = lord
        result[f"{key}_lord_dashas"] = dashas
        result[f"{key}_house_occupants"] = occupants
        result[f"{key}_house_afflicted"] = bool(afflicting_malefics)
        result[f"{key}_house_afflicting_planets"] = afflicting_malefics

    return result


def format_health_events_context(signals: Dict[str, Any], label: str = "") -> str:
    """Render compute_health_event_signals()'s output as plain-text
    lines for an LLM prompt context, matching
    children_timing_engine.py's own text-context style."""
    prefix = f"{label} " if label else ""
    lines = []
    for key, house_label in (("sixth", "6th house (disease/daily struggle)"), ("eighth", "8th house (longevity/chronic)")):
        lines.append(f"{prefix}{house_label} lord (from Moon): {signals[f'{key}_lord']}")
        lines.append(f"{prefix}{house_label} lord Dasha windows in range: {signals[f'{key}_lord_dashas']}")
        if signals[f"{key}_house_afflicted"]:
            lines.append(
                f"{prefix}{house_label} is natally occupied by a natural malefic "
                f"({', '.join(signals[f'{key}_house_afflicting_planets'])}) -- an afflicting combination"
            )
        else:
            lines.append(f"{prefix}{house_label} has no natural malefic natally occupying it")
    return "\n".join(lines)


def format_health_events_compact(signals: Dict[str, Any]) -> str:
    """
    One-line summary for space-constrained contexts (e.g. family chat's
    per-member summary) -- names the 6th/8th lords, flags any natal
    affliction, and cites the earliest real window in range if any.
    """
    all_windows = signals["sixth_lord_dashas"] + signals["eighth_lord_dashas"]
    if all_windows:
        w = min(all_windows, key=lambda d: d["from"])
        window_bit = f", window {w['from'][:4]}-{w['to'][:4]} ({w['lord']})"
    else:
        window_bit = ", no window in analyzed range"
    afflicted_bits = []
    if signals["sixth_house_afflicted"]:
        afflicted_bits.append("6th afflicted")
    if signals["eighth_house_afflicted"]:
        afflicted_bits.append("8th afflicted")
    afflicted_bit = f", {'/'.join(afflicted_bits)}" if afflicted_bits else ""
    return f"6th lord {signals['sixth_lord']}, 8th lord {signals['eighth_lord']}{afflicted_bit}{window_bit}"
