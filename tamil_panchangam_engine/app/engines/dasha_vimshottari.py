"""
This module computes Vimshottari Dasha:
- Mahadasha (major period)
- Antardasha (sub-period)
- Pratyantar Dasha (future)

Based on Moon's Nakshatra at birth.

Time handling:
- ALL datetimes are UTC
- ALL datetimes are timezone-aware
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List

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

TOTAL_DASHA_YEARS = 120
NAKSHATRA_SPAN = 13 + 1 / 3  # degrees


# -----------------------------
# HELPERS
# -----------------------------

def add_years(dt: datetime, years: float) -> datetime:
    days = int(years * 365.2425)
    return dt + timedelta(days=days)


def get_starting_dasha(nakshatra_index: int) -> int:
    return nakshatra_index % 9


def compute_dasha_balance(
    moon_longitude: float,
    nakshatra_index: int,
    dasha_years: int
) -> float:
    nak_start = nakshatra_index * NAKSHATRA_SPAN
    elapsed = moon_longitude - nak_start
    remaining_fraction = 1 - (elapsed / NAKSHATRA_SPAN)
    return remaining_fraction * dasha_years


def compute_antar_dashas(
    maha_lord: str,
    maha_start: datetime,
    maha_years: float
) -> List[Dict]:
    """
    Compute Antar Dashas within a Mahadasha.
    """
    antar_list = []
    current_start = maha_start

    start_idx = next(
        i for i, (p, _) in enumerate(DASHA_SEQUENCE) if p == maha_lord
    )

    for i in range(len(DASHA_SEQUENCE)):
        planet, planet_years = DASHA_SEQUENCE[(start_idx + i) % len(DASHA_SEQUENCE)]
        antar_years = (maha_years * planet_years) / TOTAL_DASHA_YEARS
        antar_end = add_years(current_start, antar_years)

        antar_list.append({
            "antar_lord": planet,
            "start": current_start.isoformat(),
            "end": antar_end.isoformat(),
        })

        current_start = antar_end

    return antar_list


# -----------------------------
# CORE
# -----------------------------

def compute_vimshottari_dasha(
    birth_datetime_utc: datetime,
    moon_longitude: float,
    nakshatra_index: int
) -> Dict:
    """
    Compute full Vimshottari Dasha timeline
    including Antar Dashas.
    """

    start_idx = get_starting_dasha(nakshatra_index)
    start_planet, total_years = DASHA_SEQUENCE[start_idx]

    balance_years = compute_dasha_balance(
        moon_longitude,
        nakshatra_index,
        total_years
    )

    timeline: List[Dict] = []
    current_start = birth_datetime_utc

    # -----------------------------
    # First (partial) Mahadasha
    # -----------------------------

    first_end = add_years(current_start, balance_years)

    timeline.append({
        "mahadasha": start_planet,
        "start": current_start.isoformat(),
        "end": first_end.isoformat(),
        "is_partial": True,
        "antar_dashas": compute_antar_dashas(
            start_planet, current_start, balance_years
        ),
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
            "is_partial": False,
            "antar_dashas": compute_antar_dashas(
                planet, current_start, years
            ),
        })

        current_start = end

    # -----------------------------
    # Resolve CURRENT Mahadasha + Antardasha
    # -----------------------------

    now = datetime.now(timezone.utc)
    current_dasha = None
    current_antar = None

    for entry in timeline:
        start = datetime.fromisoformat(entry["start"])
        end = datetime.fromisoformat(entry["end"])

        if start <= now <= end:
            current_dasha = {
                "lord": entry["mahadasha"],
                "start": entry["start"],
                "end": entry["end"],
                "is_partial": entry["is_partial"],
            }
            
            # Find current Antardasha within this Mahadasha
            for antar in entry.get("antar_dashas", []):
                antar_start = datetime.fromisoformat(antar["start"])
                antar_end = datetime.fromisoformat(antar["end"])
                
                if antar_start <= now <= antar_end:
                    # Calculate confidence weight (peaks mid-period)
                    duration = (antar_end - antar_start).total_seconds()
                    elapsed = (now - antar_start).total_seconds()
                    progress = elapsed / duration if duration > 0 else 0.5
                    confidence_weight = round(1.0 - abs(0.5 - progress), 2)
                    
                    current_antar = {
                        "lord": antar["antar_lord"],
                        "start": antar["start"],
                        "end": antar["end"],
                        "confidence_weight": confidence_weight,
                    }
                    break
            break

    if current_dasha is None:
        first = timeline[0]
        current_dasha = {
            "lord": first["mahadasha"],
            "start": first["start"],
            "end": first["end"],
            "is_partial": first["is_partial"],
        }
        
        # Also get first antar for fallback
        if first.get("antar_dashas"):
            first_antar = first["antar_dashas"][0]
            current_antar = {
                "lord": first_antar["antar_lord"],
                "start": first_antar["start"],
                "end": first_antar["end"],
                "confidence_weight": 0.5,
            }
    
    # Add antar to current dasha object
    current_dasha["antar"] = current_antar

    # 🔑 CRITICAL FIX: expose BOTH keys
    # timeline → Birth Chart UI
    # periods  → resolver / prediction (legacy, locked)

    return {
        "starting_dasha": start_planet,
        "balance_years": round(balance_years, 2),
        "timeline": timeline,     # ✅ UI expects this
        "periods": timeline,      # ✅ resolver already uses this
        "current": current_dasha,
    }
