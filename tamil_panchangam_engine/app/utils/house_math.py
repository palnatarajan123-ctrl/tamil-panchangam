"""
Shared whole-sign house-from-longitude arithmetic.

house_from_longitude(target_lon, reference_lon) -> 1-12: the classical
whole-sign house number of `target_lon` counted from whichever sign
`reference_lon` (Lagna, natal Moon, etc.) falls in. This exact formula
used to be hand-copied independently in ~9 engine files (yoga_engine.py,
house_strength_engine.py, shadbala_engine.py, sade_sati_engine.py,
ashtakavarga_engine.py, drishti_engine.py, transit_hits_engine.py,
functional_role_engine.py, varshaphal_engine.py) -- all verified
formula-equivalent before this consolidation, so this was a real "N
independent copies, currently in sync" risk rather than an active bug.
See CLAUDE.md's 2026-09-13 entry.

kp_engine.py deliberately does NOT use this -- it works from real
Placidus house cusps (swe.houses_ex), not whole-sign houses, a
genuinely different (and correct, for KP) system. Don't route it
through here.
"""


def house_from_longitude(target_lon: float, reference_lon: float) -> int:
    """1-indexed whole-sign house of target_lon counted from reference_lon's sign."""
    return ((int(target_lon // 30) - int(reference_lon // 30) + 12) % 12) + 1


def house_from_sign_number(target_sign: int, reference_sign: int) -> int:
    """1-indexed whole-sign house of target_sign (1-12) counted from
    reference_sign (1-12) -- for callers that already have sign numbers
    rather than raw longitudes (e.g. sade_sati_engine.py)."""
    return ((target_sign - reference_sign + 12) % 12) + 1
