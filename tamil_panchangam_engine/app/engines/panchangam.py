"""
This module will compute Tamil Panchangam elements:
- Tithi (lunar day)
- Nakshatra (lunar mansion)
- Yoga (luni-solar combination)
- Karana (half tithi)
- Vara (weekday)

"""

from datetime import datetime
from typing import Dict

from app.utils.panchangam_calc import compute_tithi as _compute_tithi_shared

# -----------------------------
# CONSTANTS
# -----------------------------

YOGA_NAMES = [
    "Vishkumbha", "Preeti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shoola", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti"
]

KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti"
]

WEEKDAY_TAMIL = {
    0: "Thingal",   # Monday
    1: "Sevvai",
    2: "Budhan",
    3: "Viyazhan",
    4: "Velli",
    5: "Sani",
    6: "Nyayiru"    # Sunday
}

TAMIL_MONTHS = [
    "Chithirai", "Vaikasi", "Aani", "Aadi",
    "Aavani", "Purattasi", "Aippasi", "Karthigai",
    "Margazhi", "Thai", "Maasi", "Panguni"
]

# -----------------------------
# CORE FUNCTIONS
# -----------------------------

def compute_tithi(sun_lon: float, moon_lon: float) -> Dict:
    """Delegates to app.utils.panchangam_calc (the single canonical
    implementation, shared with dinaphalam_engine.py's "today" display --
    see CLAUDE.md's 2026-09-13 entry). "name" is now the bare tithi name
    (e.g. "Ashtami", or "Pournami"/"Amavasya" correctly distinguished by
    paksha) rather than a "Paksha TithiName" concatenated string --
    "paksha" is still reported as its own field, matching the shape
    dinaphalam_engine.py's version already used."""
    return _compute_tithi_shared(sun_lon, moon_lon)


def compute_yoga(sun_lon: float, moon_lon: float) -> Dict:
    total = (sun_lon + moon_lon) % 360
    yoga_index = int(total // (13 + 1/3))

    return {
        "name": YOGA_NAMES[yoga_index],
        "index": yoga_index
    }


def compute_karana(karana_index: int) -> Dict:
    """
    Karana is HALF a tithi (30 tithis x 2 karanas = 60 slots per lunar
    month), not one karana per tithi -- karana_index must be
    int(diff // 6) where diff = (moon_lon - sun_lon) % 360, NOT the
    0-29 whole-tithi index. Passing a 0-29 tithi index here (the
    pre-2026-09-14 bug) collapses two real karanas into one and
    misplaces all 4 fixed karanas into the middle of the month instead
    of its boundaries -- confirmed wrong on 3/3 real dates cross-checked
    against a published Panchangam (DrikPanchang), see CLAUDE.md.

    Of the 11 real karana names: Kimstughna occurs ONCE, only in the
    first half of Shukla Pratipada (karana_index 0). Shakuni,
    Chatushpada, and Naga occur ONCE EACH, only at the very end of the
    month (karana_index 57, 58, 59 -- spanning Krishna Chaturdashi into
    Amavasya). The remaining 7 "chara" (movable) karanas
    (KARANA_NAMES) cycle continuously 8 times across the other 56 slots
    (karana_index 1-56).
    """
    if karana_index == 0:
        return {"name": "Kimstughna", "index": karana_index}
    elif karana_index == 57:
        return {"name": "Shakuni", "index": karana_index}
    elif karana_index == 58:
        return {"name": "Chatushpada", "index": karana_index}
    elif karana_index == 59:
        return {"name": "Naga", "index": karana_index}
    else:
        karana = KARANA_NAMES[(karana_index - 1) % 7]
        return {"name": karana, "index": karana_index}


def compute_tamil_weekday(dt_local: datetime) -> Dict:
    weekday_index = dt_local.weekday()
    return {
        "english": dt_local.strftime("%A"),
        "tamil": WEEKDAY_TAMIL[weekday_index]
    }


def compute_tamil_month(sun_lon: float) -> Dict:
    month_index = int(sun_lon // 30)
    return {
        "name": TAMIL_MONTHS[month_index],
        "number": month_index + 1
    }


def compute_panchangam(
    dt_local: datetime,
    sun_lon: float,
    moon_lon: float,
    nakshatra: Dict
) -> Dict:
    tithi = compute_tithi(sun_lon, moon_lon)
    yoga = compute_yoga(sun_lon, moon_lon)
    karana_index = int(((moon_lon - sun_lon) % 360) // 6)
    karana = compute_karana(karana_index)
    weekday = compute_tamil_weekday(dt_local)
    tamil_month = compute_tamil_month(sun_lon)

    return {
        "tithi": tithi,
        "nakshatra": nakshatra,
        "yoga": yoga,
        "karana": karana,
        "weekday": weekday,
        "tamil_month": tamil_month
    }
