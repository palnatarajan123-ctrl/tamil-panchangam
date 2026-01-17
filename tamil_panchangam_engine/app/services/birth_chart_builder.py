# app/services/birth_chart_builder.py

from typing import Dict, Any, List


# -------------------------------------------------
# CONSTANTS
# -------------------------------------------------

ZODIAC_ORDER = [
    "Mesham", "Rishabam", "Mithunam", "Kadakam",
    "Simmam", "Kanni", "Thulam", "Vrischikam",
    "Dhanusu", "Makaram", "Kumbham", "Meenam",
]

PLANET_ORDER = [
    "Sun", "Moon", "Mars", "Mercury",
    "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
]

RASI_LORDS = {
    "Mesham": "Mars",
    "Rishabam": "Venus",
    "Mithunam": "Mercury",
    "Kadakam": "Moon",
    "Simmam": "Sun",
    "Kanni": "Mercury",
    "Thulam": "Venus",
    "Vrischikam": "Mars",
    "Dhanusu": "Jupiter",
    "Makaram": "Saturn",
    "Kumbham": "Saturn",
    "Meenam": "Jupiter",
}

HOUSE_SIGNIFICATIONS = {
    1: "Self, personality, physical body",
    2: "Wealth, family, speech",
    3: "Courage, siblings, effort",
    4: "Home, mother, comfort",
    5: "Children, creativity, intelligence",
    6: "Disease, debt, service",
    7: "Marriage, partnerships",
    8: "Longevity, transformation",
    9: "Dharma, fortune, higher learning",
    10: "Career, authority",
    11: "Gains, aspirations",
    12: "Losses, isolation, moksha",
}

PLANET_FUNCTIONAL_MEANING = {
    "Sun": "Soul, vitality, authority, leadership",
    "Moon": "Mind, emotions, nourishment",
    "Mars": "Energy, courage, action",
    "Mercury": "Intellect, communication, logic",
    "Jupiter": "Wisdom, growth, fortune",
    "Venus": "Relationships, pleasure, harmony",
    "Saturn": "Discipline, karma, responsibility",
    "Rahu": "Desire, ambition, unconventional paths",
    "Ketu": "Detachment, spirituality, liberation",
}

NAKSHATRA_ORDER = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha",
    "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula",
    "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]


# -------------------------------------------------
# HELPERS
# -------------------------------------------------

def build_d1_from_planetary_positions(
    planetary_positions: dict,
) -> Dict[str, List[str]]:
    """
    Canonical D1 (Rasi) chart builder for UI.
    Output shape:
    {
      "Mesham": ["Saturn"],
      "Rishabam": ["Moon"],
      ...
    }
    """
    chart = {r: [] for r in ZODIAC_ORDER}

    for planet, data in planetary_positions.items():
        rasi = data.get("rasi")
        if rasi in chart:
            chart[rasi].append(planet)

    return chart


def derive_house_number(lagna_rasi: str, planet_rasi: str) -> int:
    lagna_index = ZODIAC_ORDER.index(lagna_rasi)
    planet_index = ZODIAC_ORDER.index(planet_rasi)
    return ((planet_index - lagna_index) % 12) + 1


def group_planets_by_house(planetary_positions: dict) -> list:
    houses = {i: [] for i in range(1, 13)}
    for planet, data in planetary_positions.items():
        houses[data["house"]].append(planet)

    return [
        {
            "house": i,
            "planets": houses[i],
            "lagna_relative": i == 1,
        }
        for i in range(1, 13)
    ]


def attach_house_lords(houses: list, lagna_rasi: str) -> list:
    lagna_index = ZODIAC_ORDER.index(lagna_rasi)
    enriched = []

    for h in houses:
        rasi = ZODIAC_ORDER[(lagna_index + h["house"] - 1) % 12]
        enriched.append({
            **h,
            "rasi": rasi,
            "lord": RASI_LORDS[rasi],
            "significations": HOUSE_SIGNIFICATIONS[h["house"]],
        })

    return enriched


def build_rasi_view(planetary_positions: dict) -> list:
    rasi_map = {r: {"rasi": r, "planets": []} for r in ZODIAC_ORDER}

    for planet, data in planetary_positions.items():
        rasi_map[data["rasi"]]["planets"].append({
            "planet": planet,
            "house": data["house"],
            "nakshatra": data["nakshatra"],
            "pada": data["pada"],
            "dasha": data.get("dasha"),
        })

    return [rasi_map[r] for r in ZODIAC_ORDER]


def build_nakshatra_view(planetary_positions: dict) -> list:
    nak_map = {n: {"nakshatra": n, "planets": []} for n in NAKSHATRA_ORDER}

    for planet, data in planetary_positions.items():
        nak = data.get("nakshatra")
        if not nak:
            continue

        nak_map[nak]["planets"].append({
            "planet": planet,
            "pada": data["pada"],
            "rasi": data["rasi"],
            "house": data["house"],
            "dasha": data.get("dasha"),
        })

    return [nak_map[n] for n in NAKSHATRA_ORDER]


# -------------------------------------------------
# DASHAS
# -------------------------------------------------

def extract_active_dasha_lords(dashas: dict) -> dict:
    """
    EPIC-5 / EPIC-6 SAFE
    Current engine exposes only `current` maha dasha.
    Antar/pratyantar will be added later.
    """
    vim = dashas.get("vimshottari", {})
    current = vim.get("current") or {}

    return {
        "maha": current.get("lord"),
        "antar": None,
    }


def build_dasha_timeline(dashas: dict) -> list:
    vim = dashas.get("vimshottari", {})
    timeline = []

    for level in ["maha", "antar", "pratyantar"]:
        d = vim.get(level)
        if not d:
            continue

        timeline.append({
            "level": level,
            "lord": d.get("lord"),
            "start": d.get("start"),
            "end": d.get("end"),
            "active": True,
        })

    return timeline


def overlay_dasha_on_planets(planetary_positions: dict, dasha_lords: dict) -> dict:
    maha = dasha_lords.get("maha")
    antar = dasha_lords.get("antar")

    enriched = {}
    for planet, data in planetary_positions.items():
        enriched[planet] = {
            **data,
            "dasha": {
                "maha": planet == maha,
                "antar": planet == antar,
                "active": planet in {maha, antar},
            },
            "house_lord_explanation": (
                f"{planet} signifies {PLANET_FUNCTIONAL_MEANING.get(planet)} "
                f"and currently influences house {data['house']}."
            ),
        }

    return enriched


def overlay_dasha_on_house_lords(houses: list, dasha_lords: dict) -> list:
    active_lords = {dasha_lords.get("maha"), dasha_lords.get("antar")}
    enriched = []

    for h in houses:
        lord = h.get("lord")
        enriched.append({
            **h,
            "lord_active": lord in active_lords,
            "lord_dasha": (
                "maha" if lord == dasha_lords.get("maha")
                else "antar" if lord == dasha_lords.get("antar")
                else None
            ),
        })

    return enriched


def derive_prediction_gates(dasha_lords: dict) -> dict:
    return {
        "high_confidence": bool(dasha_lords.get("maha")),
        "moderate_confidence": bool(dasha_lords.get("antar")),
        "explain": (
            "Predictions during Maha Dasha periods carry higher confidence. "
            "Antar Dasha adds secondary influence."
        ),
    }


# -------------------------------------------------
# MAIN VIEW BUILDER
# -------------------------------------------------

def build_birth_chart_view_model(base_chart: Dict[str, Any]) -> Dict[str, Any]:
    birth = base_chart["birth_details"]
    eph = base_chart["ephemeris"]
    lagna_rasi = eph["lagna"]["rasi"]

    # -----------------------------
    # Planetary positions
    # -----------------------------
    planetary_positions = {}

    for planet, data in eph["planets"].items():
        nak = data.get("nakshatra")
        planetary_positions[planet] = {
            **data,
            "house": derive_house_number(lagna_rasi, data["rasi"]),
            "nakshatra": nak["name"] if nak else None,
            "pada": nak.get("pada") if nak else None,
        }

    moon = eph["moon"]
    moon_nak = moon.get("nakshatra")
    planetary_positions["Moon"] = {
        **moon,
        "house": derive_house_number(lagna_rasi, moon["rasi"]),
        "nakshatra": moon_nak["name"] if moon_nak else None,
        "pada": moon_nak.get("pada") if moon_nak else None,
    }

    # -----------------------------
    # Houses
    # -----------------------------
    houses = attach_house_lords(
        group_planets_by_house(planetary_positions),
        lagna_rasi,
    )

    # -----------------------------
    # Dashas
    # -----------------------------
    dashas = base_chart.get("dashas", {})
    dasha_lords = extract_active_dasha_lords(dashas)

    planetary_positions = overlay_dasha_on_planets(
        planetary_positions,
        dasha_lords,
    )
    houses = overlay_dasha_on_house_lords(houses, dasha_lords)

    # -----------------------------
    # Views
    # -----------------------------
    rasi_view = build_rasi_view(planetary_positions)
    nakshatra_view = build_nakshatra_view(planetary_positions)
    dasha_timeline = build_dasha_timeline(dashas)
    prediction_gates = derive_prediction_gates(dasha_lords)

    # -----------------------------
    # Final payload
    # -----------------------------
    return {
        "identity": {
            "name": birth.get("name"),
            "place_of_birth": birth.get("place_of_birth"),
            "latitude": birth.get("latitude"),
            "longitude": birth.get("longitude"),
            "timezone": birth.get("timezone"),
        },
        "birth_time": {
            "date_of_birth": birth.get("date_of_birth"),
            "time_of_birth": birth.get("time_of_birth"),
            "birth_utc": base_chart.get("birth_utc"),
        },
        "panchangam": base_chart.get("panchangam_birth", {}),
        "planetary_positions": planetary_positions,
        "lagna_details": eph["lagna"],
        "charts": {
            "D1": build_d1_from_planetary_positions(planetary_positions)
        },
        "dashas": dashas,
        "dasha_timeline": dasha_timeline,
        "prediction_gates": prediction_gates,
        "pakshi": base_chart.get("pancha_pakshi_birth", {}),
        "houses": houses,
        "rasi_view": rasi_view,
        "nakshatra_view": nakshatra_view,
        "notes": [
            "Birth chart is computed using sidereal (Lahiri) calculations.",
            "All values are immutable and derived from stored ephemeris only.",
            "Dasha overlays indicate currently active planetary periods.",
            "Prediction confidence is gated by active dashas only.",
        ],
    }
