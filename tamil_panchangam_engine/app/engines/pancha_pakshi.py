"""
This module will compute Pancha Pakshi (Five Birds) system:
- Traditional Tamil timing system
- Based on birth star and lunar phase
- Five birds: Vulture, Owl, Crow, Cock, Peacock
- Five activities: Rule, Eat, Walk, Sleep, Die

"""

from typing import Dict
from datetime import datetime

# -----------------------------
# PAKSHI MAPPINGS
# -----------------------------

PAKSHI_BY_NAKSHATRA = {
    "Ashwini": "Vulture",
    "Magha": "Vulture",
    "Mula": "Vulture",

    "Bharani": "Owl",
    "Purva Phalguni": "Owl",
    "Purva Ashada": "Owl",

    "Krittika": "Crow",
    "Uttara Phalguni": "Crow",
    "Uttara Ashada": "Crow",

    "Rohini": "Cock",
    "Hasta": "Cock",
    "Shravana": "Cock",

    "Mrigashira": "Peacock",
    "Chitra": "Peacock",
    "Dhanishta": "Peacock",

    "Ardra": "Peacock",
    "Swati": "Peacock",
    "Shatabhisha": "Peacock",

    "Punarvasu": "Cock",
    "Vishakha": "Cock",
    "Purva Bhadrapada": "Cock",

    "Pushya": "Crow",
    "Anuradha": "Crow",
    "Uttara Bhadrapada": "Crow",

    "Ashlesha": "Owl",
    "Jyeshtha": "Owl",
    "Revati": "Owl"
}

PAKSHI_NATURE = {
    "Vulture": "Slow, karmic, deep work, endurance",
    "Owl": "Strategic, secretive, planning, patience",
    "Crow": "Busy, communication, transactions, travel",
    "Cock": "Leadership, initiation, authority, action",
    "Peacock": "Creativity, visibility, beauty, performance"
}

# -----------------------------
# CORE FUNCTIONS
# -----------------------------

def get_birth_pakshi(nakshatra_name: str) -> Dict:
    """
    Determine birth Pakshi from Nakshatra.
    """
    pakshi = PAKSHI_BY_NAKSHATRA.get(nakshatra_name)

    if not pakshi:
        raise ValueError(f"No Pakshi mapping for Nakshatra: {nakshatra_name}")

    return {
        "pakshi": pakshi,
        "nature": PAKSHI_NATURE[pakshi]
    }


def get_daily_pakshi_guidance(
    birth_pakshi: str,
    date_local: datetime
) -> Dict:
    """
    v1 Daily Pakshi guidance (conservative).
    """

    return {
        "date": date_local.strftime("%Y-%m-%d"),
        "dominant_pakshi": birth_pakshi,
        "recommended_activities": [
            f"Activities aligned with {birth_pakshi} nature",
            "Important decisions during strong periods",
            "Focused work matching Pakshi strength"
        ],
        "avoid_activities": [
            "Major confrontation during weak periods",
            "Risky activities without preparation"
        ],
        "note": (
            "Pancha Pakshi guidance is for timing harmony, "
            "not deterministic outcomes."
        )
    }
