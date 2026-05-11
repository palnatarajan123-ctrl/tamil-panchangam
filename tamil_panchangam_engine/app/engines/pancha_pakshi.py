"""
This module will compute Pancha Pakshi (Five Birds) system:
- Traditional Tamil timing system
- Based on birth star and lunar phase
- Five birds: Vulture, Owl, Crow, Cock, Peacock
- Five activities: Rule, Eat, Walk, Sleep, Die

"""

from typing import Dict
from datetime import datetime
from app.engines.nakshatra_names import nakshatra_index as _nakshatra_index

# -----------------------------
# PAKSHI MAPPINGS
# -----------------------------

# Index-based mapping (0–26, sidereal order) — replaces fragile Sanskrit name dict.
# Derived from classical Pancha Pakshi assignment, verified against PAKSHI_BY_NAKSHATRA.
_PAKSHI_BY_INDEX = [
    "Vulture",  # 0  Aswini
    "Owl",      # 1  Bharani
    "Crow",     # 2  Karthigai
    "Cock",     # 3  Rohini
    "Peacock",  # 4  Mirugashirisham
    "Peacock",  # 5  Thiruvadirai
    "Cock",     # 6  Punarpoosam
    "Crow",     # 7  Poosam
    "Owl",      # 8  Ayilyam
    "Vulture",  # 9  Magam
    "Owl",      # 10 Pooram
    "Crow",     # 11 Uthiram
    "Cock",     # 12 Hastham
    "Peacock",  # 13 Chittirai
    "Peacock",  # 14 Swathi
    "Cock",     # 15 Visakam
    "Crow",     # 16 Anusham
    "Owl",      # 17 Kettai
    "Vulture",  # 18 Moolam
    "Owl",      # 19 Pooradam
    "Crow",     # 20 Uthiradam
    "Cock",     # 21 Thiruvonam
    "Peacock",  # 22 Avittam
    "Peacock",  # 23 Sadayam
    "Cock",     # 24 Poorattadhi
    "Crow",     # 25 Uthirattadhi
    "Owl",      # 26 Revathi
]

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
    Accepts any spelling variant (Tamil or Sanskrit) via normalize_nakshatra.
    """
    idx = _nakshatra_index(nakshatra_name)
    if idx is None:
        raise ValueError(f"No Pakshi mapping for Nakshatra: {nakshatra_name}")
    pakshi = _PAKSHI_BY_INDEX[idx]
    return {
        "pakshi": pakshi,
        "nature": PAKSHI_NATURE[pakshi],
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
