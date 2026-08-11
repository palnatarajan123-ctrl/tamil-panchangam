"""
Yoga Activation Engine — detect which natal yogas are currently firing.

A yoga fires when its key planet(s) are the active MD, AD, or Pratyantar lord.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# For yogas that lack an explicit 'planets' list, derive the key planet(s) by name.
_YOGA_PLANET_MAP: Dict[str, List[str]] = {
    "Gaja Kesari Yoga": ["Jupiter"],
    "Chandra Mangala Yoga": ["Moon", "Mars"],
    "Budh-Aditya Yoga": ["Sun", "Mercury"],
    "Saraswati Yoga": ["Jupiter", "Venus", "Mercury"],
    "Hamsa Yoga": ["Jupiter"],
    "Malavya Yoga": ["Venus"],
    "Ruchaka Yoga": ["Mars"],
    "Bhadra Yoga": ["Mercury"],
    "Sasa Yoga": ["Saturn"],
    "Shasha Yoga": ["Saturn"],
    "Amala Yoga": ["Jupiter", "Venus"],
}

_ALL_PLANETS = {
    "Sun", "Moon", "Mars", "Mercury", "Jupiter",
    "Venus", "Saturn", "Rahu", "Ketu",
}

# Yoga type → life area it primarily activates
YOGA_TYPE_AREA: Dict[str, str] = {
    "dhana": "wealth",
    "raja": "career",
    "dharma": "fortune",
    "moksha": "spirituality",
    "general": "self",
    "conjunction": "self",
}


def _extract_yoga_planets(yoga: Dict[str, Any]) -> List[str]:
    """Return the key planets for this yoga (from 'planets' list or name-based map)."""
    explicit = [p for p in yoga.get("planets", []) if p in _ALL_PLANETS]
    if explicit:
        return explicit
    return _YOGA_PLANET_MAP.get(yoga.get("name", ""), [])


def compute_yoga_activation(
    yogas_payload: Dict[str, Any],
    md_lord: Optional[str],
    ad_lord: Optional[str],
    pt_lord: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Check which natal yogas are activated by the active dasha lords.

    Args:
        yogas_payload: payload['yogas'] dict (contains 'yogas' list).
        md_lord: current Mahadasha lord.
        ad_lord: current Antardasha lord.
        pt_lord: current Pratyantar lord (may be None).

    Returns:
        List of activated yoga dicts, sorted strongest first.
    """
    yoga_list = yogas_payload.get("yogas", [])
    if not yoga_list:
        return []

    results: List[Dict[str, Any]] = []

    for yoga in yoga_list:
        if not yoga.get("present", False):
            continue

        planets = _extract_yoga_planets(yoga)
        if not planets:
            continue

        pt_match = bool(pt_lord and pt_lord in planets)
        ad_match = bool(ad_lord and ad_lord in planets)
        md_match = bool(md_lord and md_lord in planets)

        if pt_match:
            level = "peak"
            reason = f"{pt_lord} is current Pratyantar lord"
        elif ad_match:
            level = "moderate"
            reason = f"{ad_lord} is current Antardasha lord"
        elif md_match:
            level = "strong"
            reason = f"{md_lord} is current Mahadasha lord"
        else:
            continue

        yoga_type = yoga.get("type", "general")
        results.append({
            "name": yoga.get("name", "Unknown Yoga"),
            "type": yoga_type,
            "planets": planets,
            "houses": yoga.get("houses_involved", []),
            "strength": yoga.get("strength", "moderate"),
            "activation_level": level,
            "activation_reason": reason,
            "life_area": YOGA_TYPE_AREA.get(yoga_type, "self"),
            "currently_active": True,
        })

    # Sort: peak > strong > moderate
    _order = {"peak": 0, "strong": 1, "moderate": 2}
    results.sort(key=lambda y: _order.get(y["activation_level"], 3))
    return results
