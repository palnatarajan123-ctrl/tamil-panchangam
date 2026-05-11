"""
Nakshatra Canonical Lookup Module

Tamil primary names as canonical. Accepts any spelling variant (Sanskrit,
alternate Tamil romanizations) and normalizes to the canonical form.
"""

from typing import Optional, List

# 27 Nakshatras — Tamil primary names as canonical, in sidereal order
CANONICAL_NAMES: List[str] = [
    "Aswini",           # 0
    "Bharani",          # 1
    "Karthigai",        # 2
    "Rohini",           # 3
    "Mirugashirisham",  # 4
    "Thiruvadirai",     # 5
    "Punarpoosam",      # 6
    "Poosam",           # 7
    "Ayilyam",          # 8
    "Magam",            # 9
    "Pooram",           # 10
    "Uthiram",          # 11
    "Hastham",          # 12
    "Chittirai",        # 13
    "Swathi",           # 14
    "Visakam",          # 15
    "Anusham",          # 16
    "Kettai",           # 17
    "Moolam",           # 18
    "Pooradam",         # 19
    "Uthiradam",        # 20
    "Thiruvonam",       # 21
    "Avittam",          # 22
    "Sadayam",          # 23
    "Poorattadhi",      # 24
    "Uthirattadhi",     # 25
    "Revathi",          # 26
]

# All known spellings (lowercased) → index into CANONICAL_NAMES
_VARIANT_MAP: dict[str, int] = {
    # 0 — Aswini
    "aswini": 0, "ashwini": 0, "ashvini": 0, "asvini": 0, "aswinee": 0,
    # 1 — Bharani
    "bharani": 1, "bharathi": 1,
    # 2 — Karthigai
    "karthigai": 2, "karthikai": 2, "krittika": 2, "krithika": 2,
    "karthika": 2, "kritika": 2, "krittikaa": 2,
    # 3 — Rohini
    "rohini": 3, "rohani": 3,
    # 4 — Mirugashirisham
    "mirugashirisham": 4, "mrigashira": 4, "mrigashirsha": 4,
    "mrigazhirisham": 4, "mrigasirisham": 4, "mrugasiras": 4,
    "mrigashiras": 4, "mrugashira": 4,
    # 5 — Thiruvadirai
    "thiruvadirai": 5, "thiruvathirai": 5, "ardra": 5, "arudra": 5,
    # 6 — Punarpoosam
    "punarpoosam": 6, "punarvasu": 6, "punarvashu": 6, "punarpusam": 6,
    # 7 — Poosam
    "poosam": 7, "pushya": 7, "pooshyam": 7, "pusyam": 7,
    # 8 — Ayilyam
    "ayilyam": 8, "ashlesha": 8, "ashleysha": 8, "aayilyam": 8,
    "aslesha": 8, "aayilya": 8,
    # 9 — Magam
    "magam": 9, "magha": 9, "maham": 9, "maka": 9,
    # 10 — Pooram
    "pooram": 10, "purva phalguni": 10, "purva_phalguni": 10,
    "puram": 10, "purvaphalguni": 10,
    # 11 — Uthiram
    "uthiram": 11, "uttara phalguni": 11, "uttara_phalguni": 11,
    "utharam": 11, "uttaraphalguni": 11,
    # 12 — Hastham
    "hastham": 12, "hasta": 12, "hastam": 12,
    # 13 — Chittirai
    "chittirai": 13, "chitra": 13, "chitirai": 13, "chitta": 13,
    # 14 — Swathi
    "swathi": 14, "swati": 14, "swathy": 14,
    # 15 — Visakam
    "visakam": 15, "vishakha": 15, "visakha": 15, "vizakam": 15,
    "vishaka": 15,
    # 16 — Anusham
    "anusham": 16, "anuradha": 16, "anizham": 16, "anusha": 16,
    # 17 — Kettai
    "kettai": 17, "jyeshtha": 17, "jyestha": 17, "ketai": 17,
    "jyestham": 17,
    # 18 — Moolam
    "moolam": 18, "mula": 18, "moola": 18, "moolam": 18, "mulam": 18,
    # 19 — Pooradam
    "pooradam": 19, "purva ashadha": 19, "purva ashada": 19,
    "purva_ashadha": 19, "purva_ashada": 19, "pooraadam": 19,
    "purvashada": 19, "purvashadha": 19,
    # 20 — Uthiradam
    "uthiradam": 20, "uttara ashadha": 20, "uttara ashada": 20,
    "uttara_ashadha": 20, "uttara_ashada": 20, "uttarashadha": 20,
    "uttarashada": 20,
    # 21 — Thiruvonam
    "thiruvonam": 21, "shravana": 21, "sravana": 21, "thiruvonaam": 21,
    "shravan": 21,
    # 22 — Avittam
    "avittam": 22, "dhanishta": 22, "dhanista": 22, "dhanishtha": 22,
    "avittom": 22,
    # 23 — Sadayam
    "sadayam": 23, "shatabhisha": 23, "sadhayam": 23, "satabhisha": 23,
    "shatayam": 23,
    # 24 — Poorattadhi
    "poorattadhi": 24, "purva bhadrapada": 24, "purva_bhadrapada": 24,
    "pooratathi": 24, "purvabhadrapada": 24,
    # 25 — Uthirattadhi
    "uthirattadhi": 25, "uttara bhadrapada": 25, "uttara_bhadrapada": 25,
    "uthiratathi": 25, "uttarabhadrapada": 25,
    # 26 — Revathi
    "revathi": 26, "revati": 26, "revathy": 26,
}


def nakshatra_index(name: str) -> Optional[int]:
    """
    Return 0-based nakshatra index from any spelling variant.
    Returns None if name is unrecognized.
    """
    if not name:
        return None
    key = name.strip().lower().replace("-", " ").replace("_", " ")
    idx = _VARIANT_MAP.get(key)
    if idx is not None:
        return idx
    # Prefix match fallback
    for variant, i in _VARIANT_MAP.items():
        if key.startswith(variant) or variant.startswith(key):
            if abs(len(key) - len(variant)) <= 3:
                return i
    return None


def normalize_nakshatra(name: str) -> str:
    """
    Return canonical Tamil nakshatra name for any input spelling.
    Returns the input unchanged if unrecognized.
    """
    idx = nakshatra_index(name)
    if idx is not None:
        return CANONICAL_NAMES[idx]
    return name


def canonical_nakshatra_list() -> List[str]:
    """Return the 27-element list of Tamil canonical nakshatra names."""
    return list(CANONICAL_NAMES)
