# app/engines/wealth_events_engine.py
"""
Wealth Events Engine.

Generalizes children_timing_engine.py's pattern (real, deterministic
dasha-window computation per classical significator, handed to the LLM as
citable facts -- never a synthesized verdict), same as
marriage_timing_engine.py / health_events_engine.py:

  - 2nd house lord (accumulated wealth, family resources) and 11th house
    lord (income, gains), counted from Moon rasi -- this timing-engine
    family's convention (children_timing_engine._get_house_lord()) -- each
    with its real Dasha/Antardasha windows in the requested range.

Plus two already-computed natal facts, reused rather than recomputed:
  - Dhana Yoga, via yoga_engine.check_dhana_yoga(). NOTE: that detector is
    LAGNA-based (lords of 2/5/9/11 from Lagna), unlike the Moon-based lords
    above -- labelled as such in the formatted output, not silently mixed.
  - KP cuspal significators of the 2nd and 11th cusps
    (payload["kp_sublords"]["cuspal_significators"]), when the chart has
    KP data -- reported separately per cusp.

No window is synthesized from Dhana Yoga or KP significators: only the 2nd/
11th lords' real dasha windows are dated facts.
"""
import logging
from typing import Any, Dict, List

from app.engines.children_timing_engine import _find_planet_dashas, _get_house_lord
from app.engines.porutham_engine import _rasi_index

logger = logging.getLogger(__name__)


def _dhana_yogas(ephemeris: Dict[str, Any]) -> List[Dict[str, Any]]:
    from app.engines.yoga_engine import check_dhana_yoga
    planets = ephemeris.get("planets", {})
    lagna_lon = (ephemeris.get("lagna") or {}).get("longitude_deg")
    if not planets or lagna_lon is None:
        return []
    return [
        {"planets": y["planets"], "houses_involved": y["houses_involved"], "type": y["type"]}
        for y in check_dhana_yoga(planets, lagna_lon)
    ]


def compute_wealth_event_signals(
    payload: Dict[str, Any],
    year_from: int,
    year_to: int,
) -> Dict[str, Any]:
    """Real, deterministic wealth-timing facts for one chart -- per
    significator, never a single verdict."""
    ephemeris = payload.get("ephemeris", {}) if isinstance(payload, dict) else {}
    moon = ephemeris.get("moon", {}) if isinstance(ephemeris, dict) else {}
    rasi_index = _rasi_index(moon.get("rasi", "")) or 0
    vimshottari = (payload.get("dashas") or {}).get("vimshottari", {}) if isinstance(payload, dict) else {}

    second_lord = _get_house_lord(rasi_index, 2)
    eleventh_lord = _get_house_lord(rasi_index, 11)

    try:
        dhana = _dhana_yogas(ephemeris)
    except Exception as e:
        logger.warning("Dhana Yoga check failed: %s", e)
        dhana = []

    cuspal = ((payload.get("kp_sublords") or {}).get("cuspal_significators") or {}) if isinstance(payload, dict) else {}

    return {
        "second_lord": second_lord,
        "second_lord_dashas": _find_planet_dashas(vimshottari, second_lord, year_from, year_to),
        "eleventh_lord": eleventh_lord,
        "eleventh_lord_dashas": (
            [] if eleventh_lord == second_lord  # same planet -> windows already listed once
            else _find_planet_dashas(vimshottari, eleventh_lord, year_from, year_to)
        ),
        "dhana_yogas": dhana,
        "kp_available": bool(cuspal),
        "kp_2nd_cusp_significators": list(cuspal.get("2", [])),
        "kp_11th_cusp_significators": list(cuspal.get("11", [])),
    }


def _dhana_text(signals: Dict[str, Any]) -> str:
    return "; ".join(
        f"{'+'.join(y['planets'])} (lords of houses {'/'.join(str(h) for h in y['houses_involved'])} "
        f"from Lagna, {y['type'].replace('_', ' ')})"
        for y in signals["dhana_yogas"]
    )


def format_wealth_events_context(signals: Dict[str, Any], label: str = "") -> str:
    """Verbose rendering for chat.py, matching the marriage/health formatters."""
    prefix = f"{label} " if label else ""
    same = signals["second_lord"] == signals["eleventh_lord"]
    lines = [
        f"{prefix}2nd house (accumulated wealth) lord (from Moon): {signals['second_lord']}",
        f"{prefix}2nd lord Dasha windows in range: {signals['second_lord_dashas']}",
        f"{prefix}11th house (income/gains) lord (from Moon): {signals['eleventh_lord']}"
        + (" (same planet as the 2nd lord -- its windows are listed above)" if same else ""),
    ]
    if not same:
        lines.append(f"{prefix}11th lord Dasha windows in range: {signals['eleventh_lord_dashas']}")
    lines.append(
        f"{prefix}Dhana Yoga (natal): {_dhana_text(signals)}" if signals["dhana_yogas"]
        else f"{prefix}Dhana Yoga (natal): none detected"
    )
    if signals["kp_available"]:
        lines.append(
            f"{prefix}KP significators -- 2nd cusp: {', '.join(signals['kp_2nd_cusp_significators']) or 'none'}; "
            f"11th cusp: {', '.join(signals['kp_11th_cusp_significators']) or 'none'}"
        )
    return "\n".join(lines)


def format_wealth_events_compact(signals: Dict[str, Any]) -> str:
    """One clause for family.py's per-member line. Window is labelled by
    domain so it can't be re-presented as another life area's window."""
    all_windows = signals["second_lord_dashas"] + signals["eleventh_lord_dashas"]
    if all_windows:
        w = min(all_windows, key=lambda d: d["from"])
        window_bit = f", wealth-timing window {w['from'][:4]}-{w['to'][:4]} ({w['lord']})"
    else:
        window_bit = ", no wealth-timing window in analyzed range"
    dhana_bit = f", Dhana Yoga {', '.join('+'.join(y['planets']) for y in signals['dhana_yogas'])}" \
        if signals["dhana_yogas"] else ""
    return f"2nd lord {signals['second_lord']}, 11th lord {signals['eleventh_lord']}{window_bit}{dhana_bit}"
