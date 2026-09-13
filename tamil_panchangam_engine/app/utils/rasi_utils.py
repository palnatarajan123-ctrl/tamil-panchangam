"""
Shared Rasi (zodiac sign) name conversion.

Two independent naming schemes coexist in this codebase: ephemeris.py's
get_rasi() returns Tamil names ("Mesham", etc.) and that's what's stored
on every chart's payload (ephemeris.moon.rasi / ephemeris.lagna.rasi).
Several transit engines (gochara_engine.py, moon_transit_engine.py) key
their house-counting lookups in English ("Aries", etc.) instead. Passing
a Tamil rasi string into one of those English-keyed lookups silently
falls through to a default (moon_idx = 0, i.e. "as if Moon is in Aries")
rather than raising -- this is what broke Gochara house numbers for
virtually every real user's chart. See CLAUDE.md's 2026-09-12 Rahu-Ketu
peyarchi investigation for the incident this fixes.

This is the single conversion point so the mismatch isn't reintroduced
at a fourth call site the way it was independently reinvented (correctly,
this time) in app/api/realtime_context.py before this module existed.
"""
from typing import Optional

ENGLISH_TO_TAMIL_RASI = {
    "Aries": "Mesham",
    "Taurus": "Rishabam",
    "Gemini": "Mithunam",
    "Cancer": "Kadakam",
    "Leo": "Simmam",
    "Virgo": "Kanni",
    "Libra": "Thulam",
    "Scorpio": "Vrischikam",
    "Sagittarius": "Dhanusu",
    "Capricorn": "Makaram",
    "Aquarius": "Kumbham",
    "Pisces": "Meenam",
}

TAMIL_TO_ENGLISH_RASI = {tamil: english for english, tamil in ENGLISH_TO_TAMIL_RASI.items()}


def to_english_rasi(rasi: Optional[str]) -> Optional[str]:
    """
    Normalize a rasi name to English ("Aries", etc).

    Tamil names are mapped to their English equivalent; anything else
    (already-English names, None, unrecognized strings) passes through
    unchanged -- callers already using English-keyed lookups get a
    consistent answer either way instead of a silent Aries fallback.
    """
    if rasi is None:
        return None
    return TAMIL_TO_ENGLISH_RASI.get(rasi, rasi)
