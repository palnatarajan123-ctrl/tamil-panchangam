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

# Sign order, index 0 = Aries. TAMIL_RASI_ORDER uses the payload's own
# spelling (ephemeris.py's RASI_NAMES / get_rasi()), so anything keyed by it
# matches a rasi read straight off a chart.
ENGLISH_RASI_ORDER = list(ENGLISH_TO_TAMIL_RASI)
TAMIL_RASI_ORDER = [ENGLISH_TO_TAMIL_RASI[e] for e in ENGLISH_RASI_ORDER]

# Alternate Tamil transliterations that some engines' own sign lists use
# (refined_av_engine.py before 2026-10-02, varshaphal_engine.py,
# special_lagnas_engine.py). Without these, to_english_rasi("Kadagam")
# passed through unchanged and an English-keyed lookup silently missed.
_TAMIL_VARIANTS_TO_ENGLISH = {
    "Midhunam": "Gemini",
    "Kadagam": "Cancer",
    "Simham": "Leo",
}


def to_english_rasi(rasi: Optional[str]) -> Optional[str]:
    """
    Normalize a rasi name to English ("Aries", etc).

    Tamil names (payload spelling or a known variant, e.g. "Kadagam") are
    mapped to their English equivalent; anything else
    (already-English names, None, unrecognized strings) passes through
    unchanged -- callers already using English-keyed lookups get a
    consistent answer either way instead of a silent Aries fallback.
    """
    if rasi is None:
        return None
    return TAMIL_TO_ENGLISH_RASI.get(rasi) or _TAMIL_VARIANTS_TO_ENGLISH.get(rasi, rasi)


def to_payload_rasi(rasi: Optional[str]) -> Optional[str]:
    """Normalize any spelling (English, payload Tamil, or a known variant)
    to the payload's Tamil spelling ("Kadagam" -> "Kadakam"). Unrecognized
    strings and None pass through unchanged."""
    english = to_english_rasi(rasi)
    return ENGLISH_TO_TAMIL_RASI.get(english, english) if english else english
