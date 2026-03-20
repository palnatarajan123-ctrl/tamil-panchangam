"""
app/engines/sade_sati_engine.py

Sade Sati & Ashtama Shani Engine
=================================
Sade Sati = Saturn transiting the 12th, 1st, and 2nd signs from natal Moon.
Duration  = ~7.5 years total (3 phases × ~2.5 years each).

Also detects:
- Ashtama Shani: Saturn in 8th from natal Moon (~2.5 years) – challenging sub-period
- Ardha Sade Sati (Kantaka Shani): Saturn in 4th from natal Moon

Classical Tamil / Jyotish tradition.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Approximate Saturn ingress dates per sign (Lahiri / Nirayana)
# Format: (sign_number_1_to_12, entry_date, exit_date)
# Sign 1=Aries, 2=Taurus, ... 10=Capricorn, 11=Aquarius, 12=Pisces
SATURN_SIGN_TRANSITS = [
    (10, "2020-01-24", "2022-04-29"),  # Capricorn
    (11, "2022-04-29", "2025-03-29"),  # Aquarius
    (12, "2025-03-29", "2027-06-05"),  # Pisces
    (1,  "2027-06-05", "2029-08-08"),  # Aries
    (2,  "2029-08-08", "2032-01-01"),  # Taurus (approx)
]

SIGN_NAMES = {
    1: "Mesha (Aries)",    2: "Rishabam (Taurus)", 3: "Mithunam (Gemini)",
    4: "Kadakam (Cancer)", 5: "Simmam (Leo)",       6: "Kanni (Virgo)",
    7: "Thulam (Libra)",   8: "Vrischikam (Scorpio)", 9: "Dhanusu (Sagittarius)",
    10: "Makaram (Capricorn)", 11: "Kumbam (Aquarius)", 12: "Meenam (Pisces)"
}

PHASE_NAMES = {
    -1: "Rising Phase (12th from Moon)",   # Saturn in 12th from Moon
     0: "Peak Phase (1st – Moon sign)",    # Saturn in Moon sign
     1: "Setting Phase (2nd from Moon)",   # Saturn in 2nd from Moon
}

PHASE_EFFECTS = {
    -1: [
        "Expenses and hidden losses may increase",
        "Sleep disturbances and mental restlessness",
        "Foreign travel or separation from home",
        "Spiritual seeking and introspection intensify",
        "Past karma surfaces for resolution"
    ],
    0: [
        "Maximum intensity of Sade Sati – greatest challenges",
        "Health requires careful attention",
        "Career and relationships face testing",
        "Deep karmic lessons in personal identity",
        "Transformation through surrender"
    ],
    1: [
        "Financial pressures and family tensions",
        "Speech and communication require care",
        "Gradual easing as Saturn moves forward",
        "Wealth-related karmic clearing",
        "Recovery and rebuilding begins"
    ],
}

ASHTAMA_EFFECTS = [
    "Sudden obstacles and unexpected challenges",
    "Health vulnerabilities – routine check-ups advised",
    "Avoid major financial risks and speculation",
    "Relationship friction may intensify",
    "Inner resilience and discipline are tested"
]

KANTAKA_EFFECTS = [
    "Domestic disruptions and property-related stress",
    "Emotional discomfort and mental fatigue",
    "Mother's health may require attention",
    "Career changes or relocation possible",
    "Patience and grounding practices are essential"
]

REMEDIES_BY_PHASE = {
    -1: [
        "Light sesame oil lamp at Shani/Ayyappan shrine every Saturday",
        "Chant 'Om Sham Shanaishcharaya Namah' 108 times on Saturdays",
        "Donate black sesame seeds and iron to the needy",
        "Avoid major new ventures during this phase"
    ],
    0: [
        "Visit Thirunallar Shani temple (most powerful Sade Sati remedy)",
        "Offer black cloth and sesame at Shani shrine on Saturdays",
        "Chant Hanuman Chalisa or Shani Stotram daily",
        "Practice discipline, service, and humility consistently",
        "Wear blue sapphire only after consulting a qualified astrologer"
    ],
    1: [
        "Continue Saturday Shani worship with sesame oil lamp",
        "Chant 'Om Sham Shanaishcharaya Namah' 108 times",
        "Donate food to the elderly and underprivileged",
        "Focus on completing existing commitments rather than new starts"
    ],
}

ASHTAMA_REMEDIES = [
    "Light sesame oil lamp at Shani shrine every Saturday",
    "Chant 'Om Sham Shanaishcharaya Namah' 108 times on Saturdays",
    "Avoid risky financial decisions during this period",
    "Donate black sesame and iron items on Saturdays"
]


def _get_sign_from_longitude(longitude: float) -> int:
    """Get sign number (1-12) from longitude."""
    return int(longitude // 30) + 1


def _get_house_from_moon(saturn_sign: int, moon_sign: int) -> int:
    """Get house number of Saturn from Moon sign."""
    return ((saturn_sign - moon_sign + 12) % 12) + 1


def _get_current_saturn_sign(reference_date: Optional[datetime] = None) -> Optional[int]:
    """
    Get Saturn's current sign from the hardcoded transit table.
    Returns sign number (1-12) or None if outside table range.
    """
    if reference_date is None:
        reference_date = datetime.utcnow()

    for sign, entry, exit_ in SATURN_SIGN_TRANSITS:
        entry_dt = datetime.strptime(entry, "%Y-%m-%d")
        exit_dt  = datetime.strptime(exit_,  "%Y-%m-%d")
        if entry_dt <= reference_date <= exit_dt:
            return sign
    return None


def _find_sade_sati_windows(moon_sign: int) -> list:
    """
    Find all Sade Sati windows (past, current, upcoming) from the transit table.
    Returns list of dicts describing each phase window.
    """
    sade_sati_signs = {
        (moon_sign - 2) % 12 + 1: -1,  # 12th from Moon
        moon_sign: 0,                   # Moon sign
        moon_sign % 12 + 1: 1,          # 2nd from Moon
    }

    windows = []
    for sign, entry, exit_ in SATURN_SIGN_TRANSITS:
        if sign in sade_sati_signs:
            phase = sade_sati_signs[sign]
            windows.append({
                "phase": phase,
                "phase_name": PHASE_NAMES[phase],
                "saturn_sign": sign,
                "saturn_sign_name": SIGN_NAMES.get(sign, str(sign)),
                "start_date": entry,
                "end_date": exit_,
            })

    return sorted(windows, key=lambda w: w["start_date"])


def compute_sade_sati(
    natal_moon_longitude: float,
    reference_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Compute Sade Sati status for a natal Moon position.

    Args:
        natal_moon_longitude: Moon's longitude in degrees (0-360, sidereal/Lahiri)
        reference_date: Date to check against (defaults to today)

    Returns:
        Full Sade Sati analysis dict
    """
    if reference_date is None:
        reference_date = datetime.utcnow()

    try:
        moon_sign = _get_sign_from_longitude(natal_moon_longitude)
        moon_sign_name = SIGN_NAMES.get(moon_sign, str(moon_sign))

        current_saturn_sign = _get_current_saturn_sign(reference_date)
        if current_saturn_sign is None:
            return _empty_result(moon_sign, moon_sign_name, "Saturn sign not found in transit table")

        house_from_moon = _get_house_from_moon(current_saturn_sign, moon_sign)

        # — Sade Sati check ————————————————————————————————
        in_sade_sati = house_from_moon in [12, 1, 2]
        phase = None
        if house_from_moon == 12:
            phase = -1
        elif house_from_moon == 1:
            phase = 0
        elif house_from_moon == 2:
            phase = 1

        # — Ashtama Shani check —————————————————————————————
        in_ashtama = house_from_moon == 8

        # — Kantaka Shani check —————————————————————————————
        in_kantaka = house_from_moon == 4

        # — Find current window end date ————————————————————
        current_window_end = None
        for sign, entry, exit_ in SATURN_SIGN_TRANSITS:
            if sign == current_saturn_sign:
                current_window_end = exit_
                break

        # — All Sade Sati windows from table —————————————————
        all_windows = _find_sade_sati_windows(moon_sign)

        # — Build result ————————————————————————————————————
        result = {
            "moon_sign": moon_sign,
            "moon_sign_name": moon_sign_name,
            "current_saturn_sign": current_saturn_sign,
            "current_saturn_sign_name": SIGN_NAMES.get(current_saturn_sign, str(current_saturn_sign)),
            "saturn_house_from_moon": house_from_moon,
            "reference_date": reference_date.strftime("%Y-%m-%d"),

            # Sade Sati
            "sade_sati": {
                "active": in_sade_sati,
                "phase": phase,
                "phase_name": PHASE_NAMES.get(phase) if phase is not None else None,
                "effects": PHASE_EFFECTS.get(phase, []) if in_sade_sati else [],
                "remedies": REMEDIES_BY_PHASE.get(phase, []) if in_sade_sati else [],
                "current_phase_ends": current_window_end if in_sade_sati else None,
                "all_windows": all_windows,
                "summary": (
                    f"Active – {PHASE_NAMES[phase]}" if in_sade_sati
                    else f"Not active (Saturn in H{house_from_moon} from Moon)"
                ),
            },

            # Ashtama Shani
            "ashtama_shani": {
                "active": in_ashtama,
                "effects": ASHTAMA_EFFECTS if in_ashtama else [],
                "remedies": ASHTAMA_REMEDIES if in_ashtama else [],
                "ends": current_window_end if in_ashtama else None,
                "summary": (
                    "Active – Saturn in 8th from Moon. Proceed with caution."
                    if in_ashtama else "Not active"
                ),
            },

            # Kantaka Shani
            "kantaka_shani": {
                "active": in_kantaka,
                "effects": KANTAKA_EFFECTS if in_kantaka else [],
                "ends": current_window_end if in_kantaka else None,
                "summary": (
                    "Active – Saturn in 4th from Moon. Domestic care needed."
                    if in_kantaka else "Not active"
                ),
            },

            # Overall alert level
            "alert_level": (
                "high"   if (in_sade_sati and phase == 0) or in_ashtama else
                "medium" if in_sade_sati or in_kantaka else
                "low"
            ),

            "error": None
        }

        logger.info(
            f"Sade Sati computed: Moon={moon_sign_name}, Saturn H{house_from_moon}, "
            f"active={in_sade_sati}, ashtama={in_ashtama}"
        )
        return result

    except Exception as e:
        logger.error(f"Sade Sati computation error: {e}")
        return _empty_result(0, "Unknown", str(e))


def _empty_result(moon_sign: int, moon_sign_name: str, error: str) -> Dict[str, Any]:
    return {
        "moon_sign": moon_sign,
        "moon_sign_name": moon_sign_name,
        "current_saturn_sign": None,
        "saturn_house_from_moon": None,
        "sade_sati": {"active": False, "phase": None, "effects": [], "remedies": [], "summary": "Unknown"},
        "ashtama_shani": {"active": False, "effects": [], "remedies": [], "summary": "Unknown"},
        "kantaka_shani": {"active": False, "effects": [], "summary": "Unknown"},
        "alert_level": "unknown",
        "error": error
    }
