# app/engines/porutham_engine.py
"""
10-point Jathagam Porutham (Kuta matching) engine.

Points: Dinam(3), Ganam(6), Yoni(4), Rasi(7), Rasiyathipaty(5),
        Rajju(pass/fail), Vedha(pass/fail), Mahendra(pass/fail),
        Stree Deergha(pass/fail), Nadi(8)
Total scoreable: 33 points
"""

from typing import Optional

# Nakshatra index 0-26 (Ashwini=0 ... Revati=26)
NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# Gana: 0=Deva, 1=Manushya, 2=Rakshasa
GANA = [
    0, 2, 1, 0, 1, 2, 0, 0, 2, 2, 1, 0,
    0, 2, 0, 1, 0, 2, 2, 1, 1, 0, 2, 2,
    1, 0, 0,
]

# Yoni animal index 0-13 (each animal pair shares compatibility)
YONI = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 2, 9, 6,
    10, 11, 5, 12, 4, 8, 3, 9, 0, 7, 13, 13,
    1, 12, 11,
]
# Yoni gender: M=male, F=female (alternating within pair)
YONI_GENDER = [
    "M", "M", "F", "M", "F", "F", "F", "M", "F", "M", "F", "M",
    "F", "F", "M", "M", "M", "F", "F", "F", "F", "F", "M", "F",
    "F", "F", "F",
]
# Hostile yoni pairs (animal indices)
YONI_HOSTILE_PAIRS = {(0, 3), (1, 8), (2, 12), (4, 13), (5, 6), (7, 9), (10, 11)}

# Rasi lord index (0=Aries..11=Pisces)
RASI_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4]
# 0=Mars, 1=Moon, 2=Mars, 3=Mercury, 4=Jupiter, 5=Venus, 6=Saturn

# Rajju groups (nakshatra index groups)
RAJJU_GROUPS = [
    {0, 7, 8, 17, 18, 25},   # Pada (feet)
    {1, 6, 9, 16, 19, 24},   # Kati (waist)
    {2, 5, 10, 15, 20, 23},  # Nabhi (navel)
    {3, 4, 11, 12, 21, 22},  # Kanta (neck)
    {13, 14, 26},             # Shira (head)
]

# Vedha pairs (nakshatra index pairs that cause vedha)
VEDHA_PAIRS = [
    (0, 18), (1, 17), (2, 16), (3, 15), (4, 14),
    (5, 13), (6, 12), (7, 11), (8, 10), (9, 27),  # 27 = no pair for Ashlesha/Magha
    (19, 25), (20, 24), (21, 23), (22, 26),
]
VEDHA_SET = set()
for a, b in VEDHA_PAIRS:
    VEDHA_SET.add((min(a, b), max(a, b)))

# Mahendra nakshatras (counted 4, 7, 10, 13, 16, 19, 22, 25, 28 from boy's)
MAHENDRA_OFFSETS = {4, 7, 10, 13, 16, 19, 22, 25, 28}

# Nadi: 0=Adi, 1=Madhya, 2=Antya
NADI = [
    0, 1, 2, 2, 1, 0, 0, 1, 2, 0, 1, 2,
    2, 1, 0, 0, 1, 2, 0, 1, 2, 2, 1, 0,
    0, 1, 2,
]


def _nakshatra_index(nak_name: str) -> Optional[int]:
    """Return 0-based nakshatra index from name (case-insensitive partial match)."""
    nak_lower = nak_name.lower().strip()
    for i, n in enumerate(NAKSHATRA_NAMES):
        if nak_lower in n.lower() or n.lower() in nak_lower:
            return i
    return None


def _rasi_index(rasi_name: str) -> Optional[int]:
    """Return 0-based rasi index from English or Tamil rasi name."""
    if not rasi_name:
        return None
    RASI_PAIRS = [
        ("aries",       "mesham"),
        ("taurus",      "rishabam"),
        ("gemini",      "mithunam"),
        ("cancer",      "kadakam"),
        ("leo",         "simmam"),
        ("virgo",       "kanni"),
        ("libra",       "thulam"),
        ("scorpio",     "vrischikam"),
        ("sagittarius", "dhanusu"),
        ("capricorn",   "makaram"),
        ("aquarius",    "kumbham"),
        ("pisces",      "meenam"),
    ]
    r = rasi_name.lower().strip()
    for i, (english, tamil) in enumerate(RASI_PAIRS):
        if r == english or r == tamil or r.startswith(english[:4]):
            return i
    return None


# ── Individual Kuta scorers ───────────────────────────────────────────────────

def score_dinam(boy_nak: int, girl_nak: int) -> dict:
    """Dinam (Dina): max 3 points."""
    diff = (girl_nak - boy_nak) % 27
    remainder = diff % 9
    score = 3 if remainder in {2, 4, 6, 8, 0} else 0
    return {"name": "Dinam", "score": score, "max": 3, "pass": score > 0}


def score_ganam(boy_nak: int, girl_nak: int) -> dict:
    """Ganam (Gana): max 6 points."""
    bg = GANA[boy_nak]
    gg = GANA[girl_nak]
    if bg == gg:
        score = 6
    elif bg == 0 and gg == 1:  # Deva + Manushya — intentional asymmetry: boy=Deva/girl=Manushya=5, reversed=0 (classical texts treat male Deva more favourably)
        score = 5
    elif bg == 1 and gg == 0:
        score = 0
    elif bg == 0 and gg == 2:  # Deva + Rakshasa
        score = 0
    elif bg == 1 and gg == 2:  # Manushya + Rakshasa
        score = 0
    else:
        score = 0
    return {"name": "Ganam", "score": score, "max": 6, "pass": score >= 5}


def score_yoni(boy_nak: int, girl_nak: int) -> dict:
    """Yoni: max 4 points."""
    by = YONI[boy_nak]
    gy = YONI[girl_nak]
    bg = YONI_GENDER[boy_nak]
    gg = YONI_GENDER[girl_nak]

    if by == gy:
        score = 4
    else:
        pair = (min(by, gy), max(by, gy))
        if pair in YONI_HOSTILE_PAIRS:
            score = 0
        else:
            score = 2
    return {"name": "Yoni", "score": score, "max": 4, "pass": score >= 2}


def score_rasi(boy_rasi: int, girl_rasi: int) -> dict:
    """Rasi (Rashikuta): max 7 points."""
    diff = (girl_rasi - boy_rasi) % 12
    if diff in {0}:
        score = 0
    elif diff in {1, 11}:
        score = 0
    elif diff in {2, 10}:
        score = 2
    elif diff in {3, 9}:
        score = 0
    elif diff in {4, 8}:
        score = 7
    elif diff in {5, 7}:
        score = 0
    elif diff == 6:
        score = 7
    else:
        score = 0
    return {"name": "Rasi", "score": score, "max": 7, "pass": score >= 2}


def score_rasiyathipaty(boy_rasi: int, girl_rasi: int) -> dict:
    """Rasiyathipaty (Graha Maitri): max 5 points."""
    FRIENDLY = {
        0: {3, 4, 1},  # Mars: Mercury, Jupiter, Moon
        1: {3, 4, 0},  # Moon: Mercury, Jupiter, Mars
        2: {0, 4, 5},  # Mars: Sun, Jupiter, Venus — reusing index for Sun
        3: {0, 5, 6},  # Mercury: Sun, Venus, Saturn
        4: {0, 1, 2},  # Jupiter: Sun, Moon, Mars
        5: {3, 6},     # Venus: Mercury, Saturn
        6: {5, 3},     # Saturn: Venus, Mercury
    }
    bl = RASI_LORDS[boy_rasi]
    gl = RASI_LORDS[girl_rasi]
    if bl == gl:
        score = 5
    elif gl in FRIENDLY.get(bl, set()) and bl in FRIENDLY.get(gl, set()):
        score = 4
    elif gl in FRIENDLY.get(bl, set()) or bl in FRIENDLY.get(gl, set()):
        score = 3
    else:
        score = 0
    return {"name": "Rasiyathipaty", "score": score, "max": 5, "pass": score >= 3}


def score_rajju(boy_nak: int, girl_nak: int) -> dict:
    """Rajju: pass/fail (same group = fail)."""
    same_group = False
    for group in RAJJU_GROUPS:
        if boy_nak in group and girl_nak in group:
            same_group = True
            break
    passed = not same_group
    return {"name": "Rajju", "score": 0 if not passed else 0, "max": 0, "pass": passed,
            "mandatory": True}


def score_vedha(boy_nak: int, girl_nak: int) -> dict:
    """Vedha: pass/fail (vedha pair = fail)."""
    pair = (min(boy_nak, girl_nak), max(boy_nak, girl_nak))
    passed = pair not in VEDHA_SET
    return {"name": "Vedha", "score": 0, "max": 0, "pass": passed, "mandatory": True}


def score_mahendra(boy_nak: int, girl_nak: int) -> dict:
    """Mahendra: pass/fail (girl's nak counted from boy's nak)."""
    offset = (girl_nak - boy_nak) % 27 + 1  # 1-based
    passed = offset in MAHENDRA_OFFSETS
    return {"name": "Mahendra", "score": 0, "max": 0, "pass": passed, "mandatory": False}


def score_stree_deergha(boy_nak: int, girl_nak: int) -> dict:
    """Stree Deergha: pass/fail (girl's nak must be 9+ away from boy's)."""
    diff = (girl_nak - boy_nak) % 27
    passed = diff >= 9
    return {"name": "Stree Deergha", "score": 0, "max": 0, "pass": passed, "mandatory": False}


def score_nadi(boy_nak: int, girl_nak: int) -> dict:
    """Nadi: max 8 points (different nadi = 8, same = 0)."""
    bn = NADI[boy_nak]
    gn = NADI[girl_nak]
    score = 8 if bn != gn else 0
    return {"name": "Nadi", "score": score, "max": 8, "pass": score > 0, "mandatory": True}


# ── Main entry point ──────────────────────────────────────────────────────────

def compute_porutham(
    boy_nakshatra: str, boy_rasi: str,
    girl_nakshatra: str, girl_rasi: str,
) -> dict:
    """
    Compute 10-point Porutham.

    Args:
        boy_nakshatra: nakshatra name string
        boy_rasi: rasi name string
        girl_nakshatra: nakshatra name string
        girl_rasi: rasi name string

    Returns:
        {
          "total_score": int,
          "max_score": 33,
          "percent": float,
          "grade": str,  # "Excellent" / "Good" / "Average" / "Poor"
          "mandatory_fail": bool,
          "points": [{ name, score, max, pass, mandatory? }, ...]
        }
    """
    bi = _nakshatra_index(boy_nakshatra)
    gi = _nakshatra_index(girl_nakshatra)
    br = _rasi_index(boy_rasi)
    gr = _rasi_index(girl_rasi)

    if bi is None or gi is None or br is None or gr is None:
        return {
            "error": f"Could not resolve nakshatra/rasi: boy=({boy_nakshatra},{boy_rasi}) girl=({girl_nakshatra},{girl_rasi})",
            "total_score": 0, "max_score": 33, "percent": 0.0,
            "grade": "Unknown", "mandatory_fail": False, "points": [],
        }

    points = [
        score_dinam(bi, gi),
        score_ganam(bi, gi),
        score_yoni(bi, gi),
        score_rasi(br, gr),
        score_rasiyathipaty(br, gr),
        score_rajju(bi, gi),
        score_vedha(bi, gi),
        score_mahendra(bi, gi),
        score_stree_deergha(bi, gi),
        score_nadi(bi, gi),
    ]

    total = sum(p["score"] for p in points)
    mandatory_fail = any(p.get("mandatory") and not p["pass"] for p in points)

    pct = round(total / 33 * 100, 1)
    if mandatory_fail:
        grade = "Poor"
    elif pct >= 75:
        grade = "Excellent"
    elif pct >= 55:
        grade = "Good"
    elif pct >= 36:
        grade = "Average"
    else:
        grade = "Poor"

    return {
        "total_score": total,
        "max_score": 33,
        "percent": pct,
        "grade": grade,
        "mandatory_fail": mandatory_fail,
        "points": points,
    }
