# app/engines/marriage_timing_engine.py
"""
Marriage Timing Engine.

Generalizes children_timing_engine.py's proven pattern (real,
deterministic dasha-window computation per classical significator,
handed to a consumer as grounded facts -- not a single LLM-invented
verdict) to marriage timing.

Three classical significators, each with a real natal basis:
  - 7th house lord (from Moon rasi, consistent with this "timing
    engines" family's established convention -- see
    children_timing_engine.py's _get_house_lord()).
  - Darakaraka (Jaimini): among the 7 classical grahas (Sun through
    Saturn -- Rahu/Ketu excluded, consistent with this app's other
    classical-graha sets, e.g. shadbala_engine.py's dignity tables),
    the one with the LOWEST degree within its own sign.
  - Kalatra Karaka (Parashari): Venus for a male native (wife-
    significator), Jupiter for a female native (husband-significator).
    Requires gender -- confirmed 2026-09-19 that this app's data model
    does not collect gender anywhere (no field on base_charts,
    family_members, or birth_details for any real chart checked).
    Only inferable today for family members with role='husband'/'wife'.
    Returns None (and is simply omitted) when gender is unknown -- e.g.
    for role='child' members, exactly child_prediction_engine.py's use
    case. This is a real, reported data-model gap, not silently
    defaulted or guessed.

This module does NOT synthesize a single "you will marry in year X"
verdict -- like children_timing_engine.py's own "combined_windows", that
judgment (weighing possibly-disagreeing significators) is left to the
LLM narrative layer, which is required to cite which significator(s)
back any specific claim it makes. This module's job is only to compute
the real facts.
"""
import logging
from datetime import date
from typing import Any, Dict, List, Optional

from app.engines.children_timing_engine import RASI_LORDS, _get_house_lord, _find_planet_dashas
from app.engines.porutham_engine import _rasi_index

logger = logging.getLogger(__name__)

_CLASSICAL_GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def compute_darakaraka(ephemeris_planets: Dict[str, Any]) -> Optional[str]:
    """
    Jaimini Darakaraka: among the 7 classical grahas, the one with the
    lowest degree within its own sign (0-30 deg). Ties broken by fixed
    planet order (Sun..Saturn) for determinism -- true exact-degree ties
    are vanishingly rare with real ephemeris precision.
    """
    candidates: List[tuple] = []
    for planet in _CLASSICAL_GRAHAS:
        lon = ephemeris_planets.get(planet, {}).get("longitude_deg")
        if lon is not None:
            candidates.append((round(lon % 30, 6), _CLASSICAL_GRAHAS.index(planet), planet))
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], c[1]))
    return candidates[0][2]


def compute_kalatra_karaka(gender: Optional[str]) -> Optional[str]:
    """
    Parashari convention: Venus (wife-significator) for a male native,
    Jupiter (husband-significator) for a female native. Returns None
    when gender is unknown rather than guessing -- see module docstring.
    """
    if gender == "male":
        return "Venus"
    if gender == "female":
        return "Jupiter"
    return None


def compute_marriage_timing_signals(
    payload: Dict[str, Any],
    year_from: int,
    year_to: int,
    gender: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Real, deterministic marriage-timing signals for one chart. Returns
    per-significator data (lord/karaka identity + real dasha windows in
    the requested year range) -- never a single synthesized verdict.

    gender: "male" | "female" | None. Only affects whether
        kalatra_karaka can be computed at all (see compute_kalatra_karaka).
    """
    ephemeris = payload.get("ephemeris", {}) if isinstance(payload, dict) else {}
    moon = ephemeris.get("moon", {}) if isinstance(ephemeris, dict) else {}
    rasi_index = _rasi_index(moon.get("rasi", "")) or 0
    planets = ephemeris.get("planets", {}) if isinstance(ephemeris, dict) else {}
    vimshottari = (
        payload.get("dashas", {}).get("vimshottari", {})
        if isinstance(payload, dict) else {}
    )

    seventh_lord = _get_house_lord(rasi_index, 7)
    seventh_lord_dashas = _find_planet_dashas(vimshottari, seventh_lord, year_from, year_to)

    darakaraka = compute_darakaraka(planets)
    darakaraka_dashas = (
        _find_planet_dashas(vimshottari, darakaraka, year_from, year_to)
        if darakaraka else []
    )

    kalatra_karaka = compute_kalatra_karaka(gender)
    kalatra_karaka_dashas = (
        _find_planet_dashas(vimshottari, kalatra_karaka, year_from, year_to)
        if kalatra_karaka else []
    )

    return {
        "seventh_lord": seventh_lord,
        "seventh_lord_dashas": seventh_lord_dashas,
        "darakaraka": darakaraka,
        "darakaraka_dashas": darakaraka_dashas,
        "kalatra_karaka": kalatra_karaka,
        "kalatra_karaka_dashas": kalatra_karaka_dashas,
        "gender_known": gender is not None,
    }


def format_marriage_timing_context(signals: Dict[str, Any], label: str = "") -> str:
    """Render compute_marriage_timing_signals()'s output as plain-text
    lines for an LLM prompt context, matching
    children_timing_engine.py's own text-context style."""
    prefix = f"{label} " if label else ""
    lines = [
        f"{prefix}7th house lord (from Moon): {signals['seventh_lord']}",
        f"{prefix}7th lord Dasha windows in range: {signals['seventh_lord_dashas']}",
        f"{prefix}Darakaraka (Jaimini, lowest-degree graha): {signals['darakaraka']}",
        f"{prefix}Darakaraka Dasha windows in range: {signals['darakaraka_dashas']}",
    ]
    if signals["gender_known"]:
        lines.append(f"{prefix}Kalatra Karaka: {signals['kalatra_karaka']}")
        lines.append(f"{prefix}Kalatra Karaka Dasha windows in range: {signals['kalatra_karaka_dashas']}")
    else:
        lines.append(
            f"{prefix}Kalatra Karaka: not available (gender not recorded for this chart)"
        )
    return "\n".join(lines)


def format_marriage_timing_compact(signals: Dict[str, Any]) -> str:
    """
    One-line summary for space-constrained contexts (e.g. family chat's
    per-member summary, which is deliberately kept compact -- see
    family.py's _build_member_summary()'s own cost-consciousness note).
    Names the significators and, if any real window exists in the
    analyzed range, its date span -- omits the full window-list detail
    the verbose formatter includes.
    """
    all_windows = signals["seventh_lord_dashas"] + signals["darakaraka_dashas"] + signals["kalatra_karaka_dashas"]
    if all_windows:
        w = min(all_windows, key=lambda d: d["from"])
        window_bit = f", window {w['from'][:4]}-{w['to'][:4]} ({w['lord']})"
    else:
        window_bit = ", no window in analyzed range"
    karaka_bit = f", Kalatra Karaka {signals['kalatra_karaka']}" if signals["gender_known"] else ""
    return f"7th lord {signals['seventh_lord']}, Darakaraka {signals['darakaraka']}{karaka_bit}{window_bit}"
