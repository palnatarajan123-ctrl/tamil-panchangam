# app/engines/porutham_engine.py
"""
10-point Jathagam Porutham (Kuta matching) engine.

Points: Dinam(3), Ganam(6), Yoni(4), Rasi(7), Rasiyathipaty(5),
        Rajju(pass/fail), Vedha(pass/fail), Mahendra(pass/fail),
        Stree Deergha(pass/fail), Nadi(8)
Total scoreable: 33 points
"""

from typing import Optional
from app.engines.nakshatra_names import canonical_nakshatra_list, nakshatra_index as _canonical_nakshatra_index

# Nakshatra index 0-26 (canonical Tamil names)
NAKSHATRA_NAMES = canonical_nakshatra_list()

# Gana: 0=Deva, 1=Manushya, 2=Rakshasa
#
# Corrected 2026-08-17 (Porutham correctness audit, Phase 1): the prior
# table had 8 of 27 nakshatras misclassified -- Bharani, Karthigai,
# Rohini, Mirugashirisham, Thiruvadirai, Uthiram, Visakam, Uthirattadhi --
# cross-checked against 3+ independent sources this session. Verify
# against tests/engines/test_porutham_engine.py's full 27-nakshatra table
# test before ever touching this array again.
GANA = [
    0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1,
    0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2,
    1, 1, 0,
]

# Yoni animal index 0-13: 0=Horse, 1=Elephant, 2=Goat, 3=Serpent, 4=Dog,
# 5=Cat, 6=Rat, 7=Cow, 8=Buffalo, 9=Tiger, 10=Deer, 11=Monkey,
# 12=Mongoose (only 1 nakshatra, no pair), 13=Lion.
#
# Corrected 2026-08-17 (Porutham audit, Phase 5): the prior table was
# almost totally scrambled -- 13 of 14 reference animal-pairs were split
# across different codes (mechanically verified, not estimated).
# Cross-checked against 3 independent sources this session, including
# resolving a genuine Purva/Uttara Phalguni Rat-vs-Cow ambiguity between
# 2 of them with a 3rd (astroanuradha.com): Magha+Purva Phalguni=Rat,
# Uttara Phalguni+Uttara Bhadrapada=Cow.
YONI = [
    0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7,
    8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0,
    13, 7, 1,
]
# Yoni gender: M=male, F=female (alternating within pair). NOT currently
# read by score_yoni() -- left as-is (unused, not re-derived) since
# gender-based scoring nuance was explicitly out of scope for this phase;
# see the audit's Phase 5 gate discussion before ever wiring this in.
YONI_GENDER = [
    "M", "M", "F", "M", "F", "F", "F", "M", "F", "M", "F", "M",
    "F", "F", "M", "M", "M", "F", "F", "F", "F", "F", "M", "F",
    "F", "F", "F",
]
# Sworn-enemy yoni pairs (animal indices) -- score 0. 7 pairs, confirmed
# across 2+ independent sources, cleanly covering all 14 animals with no
# leftovers (a useful structural sanity check that the list is complete).
# The middle tiers (Friendly=3, Neutral=2, Rival=1) that a fully-sourced
# 5-tier gradient would need are NOT implemented -- no source found this
# session reproduces the complete 14x14 friend/neutral/rival grid despite
# several being referenced as containing one. Per the Phase 5 decision:
# every non-same, non-sworn-enemy pair collapses to Neutral (2) until
# that grid is sourced -- this is a deliberate, flagged gap, not a bug.
YONI_HOSTILE_PAIRS = {(5, 6), (4, 10), (3, 12), (1, 13), (7, 9), (0, 8), (2, 11)}

# Rasi lord index (0=Aries..11=Pisces)
RASI_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4]
# Corrected 2026-08-17 (Porutham audit, Phase 6): this comment previously
# mislabeled index 0 as "Mars" (a duplicate of index 2's real label) and
# never mentioned Sun at all. Leo(4) is the only sign mapping to index 0,
# and Leo is Sun-ruled, not Mars-ruled -- the underlying RASI_LORDS data
# was already correct, only this comment was wrong.
# 0=Sun, 1=Moon, 2=Mars, 3=Mercury, 4=Jupiter, 5=Venus, 6=Saturn

# Rajju groups (nakshatra index groups)
# Corrected 2026-08-17 (Porutham audit, Phase 3): every one of the 5
# groups below was previously scrambled -- each reference group was split
# across 2-3 different engine groups, essentially a total mismatch, not
# isolated errors. Rajju is a mandatory dosha category (same group =
# automatic fail), so this was the highest-stakes fix in the whole audit.
# Cross-checked against 3 independent sources this session, all agreeing
# exactly (one of them Tamil-context specific). Verify against
# tests/engines/test_porutham_engine.py's full 27-nakshatra table test
# before ever touching this array again.
RAJJU_GROUPS = [
    {0, 8, 9, 17, 18, 26},    # Pada (feet)
    {1, 7, 10, 16, 19, 25},   # Kati (waist)
    {2, 6, 11, 15, 20, 24},   # Nabhi (navel)
    {3, 5, 12, 14, 21, 23},   # Kantha (neck)
    {4, 13, 22},               # Siro (head)
]

# Vedha pairs (nakshatra index pairs that cause vedha)
# Corrected 2026-08-17 (Porutham audit, Phase 4): every one of the prior
# pairs was wrong -- none of the 13 original pairs (plus the dead,
# out-of-range (9,27) placeholder) survived. That placeholder's comment
# claimed "no pair for Ashlesha/Magha," but 2 independent sources this
# session confirmed BOTH have a real clash partner (Ashlesha-Mula,
# Magha-Revati) -- so the old code meant Magha could never fail Vedha
# against anyone, regardless of partner. Vedha is a mandatory dosha
# category, so this mattered. 12 pairs cover 24 of 27 nakshatras;
# Mirugashirisham, Chittirai, and Avittam have no documented clash
# partner in either source and are intentionally absent here (not a
# bug -- they simply never appear in VEDHA_SET, so any pairing
# involving them correctly evaluates as "not vedha"). Verify against
# tests/engines/test_porutham_engine.py's full pair-list test before
# ever touching this array again.
VEDHA_PAIRS = [
    (2, 15),   # Karthigai - Visakam
    (0, 17),   # Aswini - Kettai
    (3, 14),   # Rohini - Swathi
    (1, 16),   # Bharani - Anusham
    (5, 21),   # Thiruvadirai - Thiruvonam
    (6, 20),   # Punarpoosam - Uthiradam
    (7, 19),   # Poosam - Pooradam
    (8, 18),   # Ayilyam - Moolam
    (9, 26),   # Magam - Revathi
    (10, 25),  # Pooram - Uthirattadhi
    (11, 24),  # Uthiram - Poorattadhi
    (12, 23),  # Hastham - Sadayam
]
VEDHA_SET = set()
for a, b in VEDHA_PAIRS:
    VEDHA_SET.add((min(a, b), max(a, b)))

# Mahendra nakshatras (counted 4, 7, 10, 13, 16, 19, 22, 25, 28 from boy's)
# Confirmed correct 2026-08-17 (Porutham audit, Phase 9) -- no fix. The
# 8 reachable offsets {4,7,10,13,16,19,22,25} match 2 independent
# sources exactly, and the direction (girl-to-boy count) matches too.
# "28" here is unreachable dead code, not a bug: the formula below
# (% 27 + 1) can only ever produce 1-27, so 28 never fires either way.
MAHENDRA_OFFSETS = {4, 7, 10, 13, 16, 19, 22, 25, 28}

# Nadi: 0=Adi, 1=Madhya, 2=Antya
#
# Corrected 2026-08-17 (Porutham audit, Phase 2): 6 of 27 nakshatras were
# misclassified (Magam, Uthiram, Hastham, Swathi, Visakam, Kettai),
# cross-checked against 4+ independent sources. Nadi is a mandatory
# dosha category, so this mattered more than most tables here. The
# correct pattern repeats [Adi,Madhya,Antya,Antya,Madhya,Adi,Adi,Madhya,
# Antya] every 9 nakshatras -- verify against
# tests/engines/test_porutham_engine.py's full 27-nakshatra table test
# before ever touching this array again.
NADI = [
    0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0,
    0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0,
    0, 1, 2,
]


def _nakshatra_index(nak_name: str) -> Optional[int]:
    """Return 0-based nakshatra index from any known name spelling."""
    return _canonical_nakshatra_index(nak_name)


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
    """
    Ganam (Gana): max 6 points.

    Corrected 2026-08-17 (Porutham audit, Phase 1) to a fully symmetric
    grid: same=6, Deva+Manushya=5, Deva+Rakshasa=0, Manushya+Rakshasa=1 --
    each regardless of which side is boy vs girl. The previous version
    had an "intentional asymmetry" for Deva+Manushya (boy=Deva/girl=
    Manushya=5, reversed=0) that a fresh 2-source check this session
    could not corroborate: one numeric source gave a symmetric grid, and
    a second (Tamil-context, prokerala.com's dedicated Gana Porutham
    page) was internally inconsistent about Manushya<->Rakshasa
    directionality within its own text. Per this session's contested-
    finding tiebreak rule (don't encode asymmetry on single-source
    confidence), this is scored symmetrically. If you find a citable
    classical Tamil source that establishes genuine directionality here,
    this is the place to revisit it.
    """
    bg = GANA[boy_nak]
    gg = GANA[girl_nak]
    pair = {bg, gg}
    if bg == gg:
        score = 6
    elif pair == {0, 1}:  # Deva + Manushya
        score = 5
    elif pair == {1, 2}:  # Manushya + Rakshasa
        score = 1
    else:  # Deva + Rakshasa
        score = 0
    return {"name": "Ganam", "score": score, "max": 6, "pass": score >= 5}


def score_yoni(boy_nak: int, girl_nak: int) -> dict:
    """
    Yoni: max 4 points.

    3-tier scoring (same=4, sworn-enemy=0, else=2) is a deliberate,
    flagged decision as of the 2026-08-17 audit's Phase 5, not the full
    classical 5-tier gradient (Friendly=3, Neutral=2, Rival=1 as
    distinct tiers) -- see YONI_HOSTILE_PAIRS's comment for why the
    middle tiers aren't split out.
    """
    by = YONI[boy_nak]
    gy = YONI[girl_nak]

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
    """
    Rasi (Rashikuta): max 7 points.

    Corrected 2026-08-17 (Porutham audit, Phase 7): the 4th/10th
    positional relationship (diff=3,9) was scored 0 (unfavorable); fixed
    to 7 (favorable, full marks) -- 3 of 4 sources found this session
    place it in the same "auspicious" tier as 1/7 and 3/11, including
    one clean, unhedged explicit source (astroyogi.com) giving it 7, and
    a Tamil-context source (dineshcheramastro.com) listing it among
    "1,3,4,5,7,9,11 acceptable" positions. Only one source dissented, and
    even that source hedged its own number ("some texts accept, others
    reject").

    The 5th/9th relationship (diff=4,8) was flagged in the audit as
    possibly wrong (scored 7, but 2 of 3 generic sources suggested
    unfavorable) -- resolved as NO CHANGE after finding a Tamil-context
    source (dineshcheramastro.com) explicitly calling 5-9 "very good...
    one of the most favorable combinations," directly matching this
    engine's existing treatment. Per this session's tiebreak rule
    (prefer Tamil/South-Indian-tradition sources over generic ones), the
    engine was already right here.

    Two additional exception mechanisms surfaced during this research --
    an "Eka Rasi" same-sign exception (8 specific nakshatra pairs treated
    as favorable despite same-sign) and a 6th/8th cancellation tied to
    Rasiyathipaty friendship -- deliberately NOT implemented here. Both
    are new capabilities, not table corrections, and were explicitly out
    of scope for this phase pending a separate go-ahead.
    """
    diff = (girl_rasi - boy_rasi) % 12
    if diff in {0}:
        score = 0
    elif diff in {1, 11}:
        score = 0
    elif diff in {2, 10}:
        score = 2
    elif diff in {3, 9}:
        score = 7
    elif diff in {4, 8}:
        score = 7
    elif diff in {5, 7}:
        score = 0
    elif diff == 6:
        score = 7
    else:
        score = 0
    return {"name": "Rasi", "score": score, "max": 7, "pass": score >= 2}


# Naisargika (natural) Graha Maitri table, keyed by RASI_LORDS's planet
# index (0=Sun, 1=Moon, 2=Mars, 3=Mercury, 4=Jupiter, 5=Venus, 6=Saturn).
#
# Corrected 2026-08-17 (Porutham audit, Phase 6): the prior FRIENDLY dict
# had Sun, Moon, and Mars each with one wrong friend (and no concept of
# "neutral" at all -- everything not explicitly friend fell through to
# the same bucket as enemy). Cross-checked against 3 independent
# sources, including a genuine classical Tamil-language text that
# resolved a contested point (see RASIYATHIPATY_ENEMY's Mercury entry).
# This table is intentionally asymmetric: e.g. Moon considers Mercury a
# friend, but Mercury considers Moon an enemy -- that's correct, not a
# bug, and score_rasiyathipaty() below handles the asymmetry explicitly
# rather than assuming symmetry.
RASIYATHIPATY_FRIENDLY = {
    0: {1, 2, 4},  # Sun: Moon, Mars, Jupiter
    1: {0, 3},     # Moon: Sun, Mercury
    2: {0, 1, 4},  # Mars: Sun, Moon, Jupiter
    3: {0, 5},     # Mercury: Sun, Venus
    4: {0, 1, 2},  # Jupiter: Sun, Moon, Mars
    5: {3, 6},     # Venus: Mercury, Saturn
    6: {3, 5},     # Saturn: Mercury, Venus
}
RASIYATHIPATY_ENEMY = {
    0: {5, 6},     # Sun: Venus, Saturn
    1: set(),      # Moon: none
    2: {3},        # Mars: Mercury
    3: {1},        # Mercury: Moon -- NOT Saturn, resolved via a genuine
                   # classical Tamil source after 2 sources disagreed on
                   # whether Saturn is a Mercury friend (it's neutral).
    4: {3, 5},     # Jupiter: Mercury, Venus
    5: {0, 1},     # Venus: Sun, Moon
    6: {0, 1, 2},  # Saturn: Sun, Moon, Mars
}
# Anything not in FRIENDLY or ENEMY for a given planet is neutral to it
# (each planet's 3 categories exactly partition the other 6 planets).


def _rasiyathipaty_relation(from_planet: int, to_planet: int) -> str:
    if to_planet in RASIYATHIPATY_FRIENDLY[from_planet]:
        return "friend"
    if to_planet in RASIYATHIPATY_ENEMY[from_planet]:
        return "enemy"
    return "neutral"


def score_rasiyathipaty(boy_rasi: int, girl_rasi: int) -> dict:
    """
    Rasiyathipaty (Graha Maitri): max 5 points.

    7-tier gradient, corrected 2026-08-17 (Porutham audit, Phase 6):
    same lord=5, mutual friends (different lords)=5, one friend + one
    neutral=4, mutual neutral=3, one friend + one enemy=1, one neutral +
    one enemy=0.5, mutual enemies=0. 6 of these 7 tiers were confirmed
    by 2 independent sources; "mutual friends, different lords=5" had
    only 1 explicit source (a 2nd source's gradient list simply didn't
    name this case, not contradicted it) -- scored 5 per an explicit
    product decision, treating mutual friendship as equal to same-lord
    since it's the strongest non-identical relationship the table can
    express.
    """
    bl = RASI_LORDS[boy_rasi]
    gl = RASI_LORDS[girl_rasi]
    if bl == gl:
        score = 5
    else:
        relations = {
            _rasiyathipaty_relation(bl, gl),
            _rasiyathipaty_relation(gl, bl),
        }
        if relations == {"friend"}:
            score = 5
        elif relations == {"friend", "neutral"}:
            score = 4
        elif relations == {"neutral"}:
            score = 3
        elif relations == {"friend", "enemy"}:
            score = 1
        elif relations == {"neutral", "enemy"}:
            score = 0.5
        else:  # {"enemy"}
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
    """
    Stree Deergha: pass/fail (girl's nak must be 9+ away from boy's).

    Reviewed 2026-08-17 (Porutham audit, Phase 8) -- no fix, deliberate
    convention. This is the least-documented Kuta researched this
    session: sources genuinely disagree with each other, not just with
    this engine. Direction (count girl-to-boy) is unanimous across every
    source that addresses it -- high confidence, matches this code.
    The threshold and pass/fail-vs-graduated shape are NOT settled:
    - One source: flat pass/fail at diff>=9 (matches this code exactly).
    - Three sources (near-identical wording, possibly one shared
      upstream origin rather than fully independent): two-tier graduated
      (diff>13="Uttamam"/excellent, diff>7="Madhyamam"/acceptable).
    - One source: same two-tier shape but diff>15, not diff>13.
    - One source: continuous "further is always better" framing across
      the full 27-star cycle, no real upper cap.
    None of the graduated-shape sources state whether "Madhyamam" counts
    as a full pass, a partial pass, or a family's discretionary call in
    the standard 10-Porutham tally -- that distinction is itself
    unresolved in the source material, not just unimplemented here.
    Given no clean classical Tamil-language source was found to break
    this tie (unlike Rajju, Vedha, and the Rasi 5th/9th question, all
    resolved this session with one), diff>=9 flat pass/fail stands as
    this engine's deliberate, documented choice -- not a confirmed bug,
    and not silently guessed at either.
    """
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
