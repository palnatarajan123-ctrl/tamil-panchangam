# app/engines/navamsa_engine.py

from typing import Any, Dict, Optional

# -------------------------------------------------
# Canonical Sign Order (English)
# -------------------------------------------------

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}

# -------------------------------------------------
# Tamil/Sanskrit/Variant → English normalization
# NOTE: include ALL variants used across your codebase
# -------------------------------------------------

RASI_NORMALIZATION = {
    # --- Tamil/Sanskrit (common in your codebase) ---
    "mesham": "Aries",
    "rishabam": "Taurus",
    "mithunam": "Gemini",

    # Cancer variants
    "kadakam": "Cancer",
    "katakam": "Cancer",

    # Leo variants
    "simmam": "Leo",
    "simham": "Leo",

    "kanni": "Virgo",
    "thulam": "Libra",

    # Scorpio variants (this caused your error)
    "vrischikam": "Scorpio",
    "vrischigam": "Scorpio",
    "viruchigam": "Scorpio",
    "viruchikam": "Scorpio",

    # Sagittarius variants
    "dhanusu": "Sagittarius",
    "dhanus": "Sagittarius",
    "dhanush": "Sagittarius",

    "makaram": "Capricorn",
    "kumbham": "Aquarius",
    "meenam": "Pisces",

    # --- English passthrough (safe) ---
    "aries": "Aries",
    "taurus": "Taurus",
    "gemini": "Gemini",
    "cancer": "Cancer",
    "leo": "Leo",
    "virgo": "Virgo",
    "libra": "Libra",
    "scorpio": "Scorpio",
    "sagittarius": "Sagittarius",
    "capricorn": "Capricorn",
    "aquarius": "Aquarius",
    "pisces": "Pisces",
}

# -------------------------------------------------
# Dignity mappings (English canonical)
# -------------------------------------------------

EXALTATION_SIGNS = {
    "Sun": "Aries",
    "Moon": "Taurus",
    "Mars": "Capricorn",
    "Mercury": "Virgo",
    "Jupiter": "Cancer",
    "Venus": "Pisces",
    "Saturn": "Libra",
}

DEBILITATION_SIGNS = {
    "Sun": "Libra",
    "Moon": "Scorpio",
    "Mars": "Cancer",
    "Mercury": "Pisces",
    "Jupiter": "Capricorn",
    "Venus": "Virgo",
    "Saturn": "Aries",
}


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def _normalize_rasi(rasi: Any) -> Optional[str]:
    """
    Normalize Tamil/Sanskrit/English sign strings → canonical English.
    Returns None if it cannot be normalized.
    """
    if not rasi or not isinstance(rasi, str):
        return None
    key = rasi.strip().casefold()
    return RASI_NORMALIZATION.get(key)


def _extract_longitude_deg(data: Dict[str, Any]) -> Optional[float]:
    """
    Prefer longitude_deg; fall back to degree if present.
    """
    lon = data.get("longitude_deg")
    if isinstance(lon, (int, float)):
        return float(lon)

    deg = data.get("degree")
    if isinstance(deg, (int, float)):
        return float(deg)

    return None


# -------------------------------------------------
# Core Navamsa Logic
# -------------------------------------------------

def compute_navamsa_sign(rasi: str, degree_in_rasi: float) -> str:
    """
    Compute Navamsa (D9) sign using Parashara method.
    Uses canonical English sign for indexing.
    """
    canonical_rasi = _normalize_rasi(rasi)
    if canonical_rasi is None:
        raise ValueError(f"Unknown rasi sign: {rasi}")

    rasi_index = SIGN_INDEX[canonical_rasi]
    navamsa_part = int(degree_in_rasi // (30 / 9))  # 0–8
    navamsa_index = (rasi_index * 9 + navamsa_part) % 12
    return SIGNS[navamsa_index]


def assess_navamsa_dignity(planet: str, navamsa_sign: str) -> str:
    if EXALTATION_SIGNS.get(planet) == navamsa_sign:
        return "exalted"
    if DEBILITATION_SIGNS.get(planet) == navamsa_sign:
        return "debilitated"
    return "neutral"


# -------------------------------------------------
# Public API
# -------------------------------------------------

def build_navamsa_chart(ephemeris: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Build Navamsa (D9) chart from birth ephemeris.

    Expected ephemeris shape:
    {
      "planets": { "Sun": {...}, ... },
      "moon": {...},  # optional separate moon
      "lagna": {...},
      ...
    }
    """
    navamsa: Dict[str, Dict[str, Any]] = {}

    planets = ephemeris.get("planets", {})
    if isinstance(planets, dict):
        for planet, data in planets.items():
            if not isinstance(data, dict):
                continue

            rasi = data.get("rasi")
            lon = _extract_longitude_deg(data)
            if not rasi or lon is None:
                continue

            degree_in_rasi = lon % 30.0
            navamsa_sign = compute_navamsa_sign(rasi, degree_in_rasi)
            dignity = assess_navamsa_dignity(planet, navamsa_sign)

            navamsa[planet] = {
                "navamsa_sign": navamsa_sign,
                "dignity": dignity,
            }

    # Optional: include Moon if your ephemeris stores Moon outside "planets"
    moon = ephemeris.get("moon")
    if isinstance(moon, dict) and "Moon" not in navamsa:
        rasi = moon.get("rasi")
        lon = _extract_longitude_deg(moon)
        if rasi and lon is not None:
            degree_in_rasi = lon % 30.0
            navamsa_sign = compute_navamsa_sign(rasi, degree_in_rasi)
            dignity = assess_navamsa_dignity("Moon", navamsa_sign)
            navamsa["Moon"] = {
                "navamsa_sign": navamsa_sign,
                "dignity": dignity,
            }

    return navamsa
