"""
KP Sub-lord Engine
Computes sub-lords for each planet and house cusp using
Krishnamurti Paddhati (KP) star-lord / sub-lord system.

Sub-lord division: each nakshatra (13°20') is divided into
9 sub-lords proportional to Vimshottari dasha periods.
Total = 120 years. Each nakshatra = 13°20' = 800'.
"""

VIMSHOTTARI_ORDER = [
    "Ketu", "Venus", "Sun", "Moon", "Mars",
    "Rahu", "Jupiter", "Saturn", "Mercury"
]

VIMSHOTTARI_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
}

TOTAL_YEARS = 120

NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury"
]

NAKSHATRA_SPAN = 13 + 1/3  # degrees


def get_star_lord(longitude: float) -> str:
    nak_index = int(longitude / NAKSHATRA_SPAN) % 27
    return NAKSHATRA_LORDS[nak_index]


def get_sub_lord(longitude: float) -> str:
    nak_index = int(longitude / NAKSHATRA_SPAN) % 27
    nak_start = nak_index * NAKSHATRA_SPAN
    pos_in_nak = longitude - nak_start
    star_lord = NAKSHATRA_LORDS[nak_index]
    star_lord_idx = VIMSHOTTARI_ORDER.index(star_lord)
    accumulated = 0.0
    for i in range(9):
        sub_lord = VIMSHOTTARI_ORDER[(star_lord_idx + i) % 9]
        sub_span = (VIMSHOTTARI_YEARS[sub_lord] / TOTAL_YEARS) * NAKSHATRA_SPAN
        accumulated += sub_span
        if pos_in_nak <= accumulated:
            return sub_lord
    return VIMSHOTTARI_ORDER[(star_lord_idx + 8) % 9]


def get_sub_sub_lord(longitude: float) -> str:
    nak_index = int(longitude / NAKSHATRA_SPAN) % 27
    nak_start = nak_index * NAKSHATRA_SPAN
    pos_in_nak = longitude - nak_start
    star_lord = NAKSHATRA_LORDS[nak_index]
    star_lord_idx = VIMSHOTTARI_ORDER.index(star_lord)
    accumulated = 0.0
    sub_lord = None
    sub_lord_idx = None
    sub_start = 0.0
    for i in range(9):
        sl = VIMSHOTTARI_ORDER[(star_lord_idx + i) % 9]
        sub_span = (VIMSHOTTARI_YEARS[sl] / TOTAL_YEARS) * NAKSHATRA_SPAN
        if pos_in_nak <= accumulated + sub_span:
            sub_lord = sl
            sub_lord_idx = VIMSHOTTARI_ORDER.index(sl)
            sub_start = accumulated
            break
        accumulated += sub_span
    if sub_lord is None:
        return VIMSHOTTARI_ORDER[(star_lord_idx + 8) % 9]
    sub_span_total = (VIMSHOTTARI_YEARS[sub_lord] / TOTAL_YEARS) * NAKSHATRA_SPAN
    pos_in_sub = pos_in_nak - sub_start
    accumulated2 = 0.0
    for i in range(9):
        ssl = VIMSHOTTARI_ORDER[(sub_lord_idx + i) % 9]
        ssl_span = (VIMSHOTTARI_YEARS[ssl] / TOTAL_YEARS) * sub_span_total
        accumulated2 += ssl_span
        if pos_in_sub <= accumulated2:
            return ssl
    return VIMSHOTTARI_ORDER[(sub_lord_idx + 8) % 9]


def compute_kp_sublords(ephemeris: dict) -> dict:
    result = {}
    planets = ephemeris.get("planets", {})
    for planet_name, planet_data in planets.items():
        lon = planet_data.get("longitude_deg", 0)
        result[planet_name] = {
            "longitude": lon,
            "star_lord": get_star_lord(lon),
            "sub_lord": get_sub_lord(lon),
            "sub_sub_lord": get_sub_sub_lord(lon),
        }
    moon = ephemeris.get("moon", {})
    if moon:
        lon = moon.get("longitude_deg", 0)
        result["Moon"] = {
            "longitude": lon,
            "star_lord": get_star_lord(lon),
            "sub_lord": get_sub_lord(lon),
            "sub_sub_lord": get_sub_sub_lord(lon),
        }
    lagna = ephemeris.get("lagna", {})
    if lagna:
        lon = lagna.get("longitude_deg", 0)
        result["Lagna"] = {
            "longitude": lon,
            "star_lord": get_star_lord(lon),
            "sub_lord": get_sub_lord(lon),
            "sub_sub_lord": get_sub_sub_lord(lon),
        }
    return result
