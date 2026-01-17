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

# -----------------------------
# CONSTANTS
# -----------------------------

TITHI_NAMES = [
    "Prathama", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi",
    "Pournami / Amavasya"
]

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
    diff = (moon_lon - sun_lon) % 360
    tithi_index = int(diff // 12)
    paksha = "Shukla" if tithi_index < 15 else "Krishna"
    tithi_number = (tithi_index % 15) + 1

    return {
        "paksha": paksha,
        "tithi_number": tithi_number,
        "name": f"{paksha} {TITHI_NAMES[tithi_number - 1]}",
        "index": tithi_index
    }


def compute_yoga(sun_lon: float, moon_lon: float) -> Dict:
    total = (sun_lon + moon_lon) % 360
    yoga_index = int(total // (13 + 1/3))

    return {
        "name": YOGA_NAMES[yoga_index],
        "index": yoga_index
    }


def compute_karana(tithi_index: int) -> Dict:
    if tithi_index in [0, 29]:
        return {"name": "Kimstughna"}
    elif tithi_index in [14]:
        return {"name": "Shakuni"}
    elif tithi_index in [15]:
        return {"name": "Chatushpada"}
    elif tithi_index in [16]:
        return {"name": "Naga"}
    else:
        karana = KARANA_NAMES[(tithi_index - 1) % 7]
        return {"name": karana}


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
    karana = compute_karana(tithi["index"])
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
