"""
This module computes Vimshottari Dasha:
- Mahadasha (major period)
- Antardasha (sub-period) [future]
- Pratyantar Dasha (sub-sub-period) [future]

Based on Moon's Nakshatra at birth.

Time handling:
- ALL datetimes are UTC
- ALL datetimes are timezone-aware
"""

from datetime import datetime, timedelta, timezone
from typing import Dict

# -----------------------------
# CONSTANTS
# -----------------------------

DASHA_SEQUENCE = [
    ("Ketu", 7),
    ("Venus", 20),
    ("Sun", 6),
    ("Moon", 10),
    ("Mars", 7),
    ("Rahu", 18),
    ("Jupiter", 16),
    ("Saturn", 19),
    ("Mercury", 17),
]

NAKSHATRA_SPAN = 13 + 1 / 3  # degrees


# -----------------------------
# CORE FUNCTIONS
# -----------------------------

def get_starting_dasha(nakshatra_index: int) -> int:
    """
    Returns index in DASHA_SEQUENCE for starting Mahadasha.
    """
    return nakshatra_index % 9


def compute_dasha_balance(
    moon_longitude: float,
    nakshatra_index: int,
    dasha_years: int
) -> float:
    """
    Compute remaining Mahadasha years at birth.
    """
    nak_start = nakshatra_index * NAKSHATRA_SPAN
    elapsed = moon_longitude - nak_start
    remaining_fraction = 1 - (elapsed / NAKSHATRA_SPAN)
    return remaining_fraction * dasha_years


def add_years(dt: datetime, years: float) -> datetime:
    """
    Add years to a datetime using astronomical year length.
    Preserves timezone awareness.
    """
    days = int(years * 365.2425)
    return dt + timedelta(days=days)


def compute_vimshottari_dasha(
    birth_datetime_utc: datetime,
    moon_longitude: float,
    nakshatra_index: int
) -> Dict:
    """
    Compute full Vimshottari Dasha timeline
    AND resolve the currently active Mahadasha.
    """

    # -----------------------------
    # Setup
    # -----------------------------

    start_idx = get_starting_dasha(nakshatra_index)
    start_planet, total_years = DASHA_SEQUENCE[start_idx]

    balance_years = compute_dasha_balance(
        moon_longitude,
        nakshatra_index,
        total_years
    )

    timeline = []
    current_start = birth_datetime_utc

    # -----------------------------
    # First (partial) Mahadasha
    # -----------------------------

    first_end = add_years(current_start, balance_years)

    timeline.append({
        "mahadasha": start_planet,
        "start": current_start.isoformat(),
        "end": first_end.isoformat(),
        "is_partial": True
    })

    current_start = first_end

    # -----------------------------
    # Remaining Mahadashas
    # -----------------------------

    for i in range(1, len(DASHA_SEQUENCE)):
        idx = (start_idx + i) % len(DASHA_SEQUENCE)
        planet, years = DASHA_SEQUENCE[idx]

        end = add_years(current_start, years)

        timeline.append({
            "mahadasha": planet,
            "start": current_start.isoformat(),
            "end": end.isoformat(),
            "is_partial": False
        })

        current_start = end

    # --------------------------------------------------
    # STEP 3 — Resolve CURRENT active Mahadasha
    # --------------------------------------------------

    now = datetime.now(timezone.utc)
    current_dasha = None

    for entry in timeline:
        start = datetime.fromisoformat(entry["start"])
        end = datetime.fromisoformat(entry["end"])

        # SAFE: all datetimes are UTC + tz-aware
        if start <= now <= end:
            current_dasha = {
                "lord": entry["mahadasha"],
                "start": entry["start"],
                "end": entry["end"],
                "is_partial": entry["is_partial"]
            }
            break

    # Absolute safety fallback (should never trigger)
    if current_dasha is None:
        first = timeline[0]
        current_dasha = {
            "lord": first["mahadasha"],
            "start": first["start"],
            "end": first["end"],
            "is_partial": first["is_partial"]
        }

    # -----------------------------
    # Final output
    # -----------------------------

    return {
        "starting_dasha": start_planet,
        "balance_years": round(balance_years, 2),
        "timeline": timeline,
        "current": current_dasha  # ✅ REQUIRED by prediction engine
    }
