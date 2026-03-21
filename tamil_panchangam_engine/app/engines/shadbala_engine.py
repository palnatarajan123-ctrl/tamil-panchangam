"""
Shadbala Engine — Classical 6-fold Planetary Strength
Implements Sthana, Dig, Chesta, Naisargika, and Drik Bala.
Scores are in Rupas (1 Rupa = 60 Shashtiamsas).
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ── Natural strength (Naisargika Bala) ─────────────────────────────
# Fixed values in Shashtiamsas (out of 60)
NAISARGIKA_BALA = {
    "Sun":     60.0,
    "Moon":    51.43,
    "Venus":   45.0,
    "Jupiter": 34.29,
    "Mercury": 25.71,
    "Mars":    17.14,
    "Saturn":  8.57,
    "Rahu":    0.0,
    "Ketu":    0.0,
}

# ── Exaltation / Debilitation / Own signs ──────────────────────────
# Sign numbers 1=Aries to 12=Pisces
EXALTATION_SIGN = {
    "Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6,
    "Jupiter": 4, "Venus": 12, "Saturn": 7
}
DEBILITATION_SIGN = {
    "Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12,
    "Jupiter": 10, "Venus": 6, "Saturn": 1
}
OWN_SIGNS = {
    "Sun": [5], "Moon": [4], "Mars": [1, 8],
    "Mercury": [3, 6], "Jupiter": [9, 12],
    "Venus": [2, 7], "Saturn": [10, 11]
}
FRIENDLY_SIGNS = {
    "Sun":     [1, 4, 9, 10, 11],
    "Moon":    [2, 3, 4, 6, 11],
    "Mars":    [1, 3, 4, 8, 10],
    "Mercury": [3, 5, 6, 10, 11],
    "Jupiter": [1, 4, 5, 9, 10],
    "Venus":   [2, 3, 7, 9, 12],
    "Saturn":  [2, 7, 10, 11, 12],
}

# ── Dig Bala directional strength ──────────────────────────────────
# Planet is strongest in this house (from Lagna)
DIG_BALA_HOUSE = {
    "Sun":     10,  # 10th house (Midheaven)
    "Moon":    4,   # 4th house
    "Mars":    10,  # 10th house
    "Mercury": 1,   # 1st house (Lagna)
    "Jupiter": 1,   # 1st house
    "Venus":   4,   # 4th house
    "Saturn":  7,   # 7th house
}

# ── Mean daily motions (degrees/day) for Chesta Bala ───────────────
MEAN_DAILY_MOTION = {
    "Sun":     0.9856,
    "Moon":    13.1764,
    "Mars":    0.5240,
    "Mercury": 1.3833,
    "Jupiter": 0.0831,
    "Venus":   1.2000,
    "Saturn":  0.0335,
}

# ── Aspect strengths (for Drik Bala) ───────────────────────────────
# Positive = benefic aspect, Negative = malefic aspect (Shashtiamsas)
ASPECT_STRENGTH = {
    "Jupiter": 15.0,   # natural benefic — strong positive
    "Venus":   12.0,
    "Mercury": 8.0,    # neutral benefic
    "Moon":    7.0,
    "Sun":     -8.0,   # natural malefic
    "Mars":    -10.0,
    "Saturn":  -12.0,
}


def _get_sign(longitude: float) -> int:
    """Get sign number 1-12 from longitude."""
    return int(longitude // 30) + 1


def _get_house(planet_lon: float, lagna_lon: float) -> int:
    """Get house number 1-12 from lagna."""
    planet_sign = _get_sign(planet_lon)
    lagna_sign = _get_sign(lagna_lon)
    return ((planet_sign - lagna_sign + 12) % 12) + 1


def compute_sthana_bala(
    planet: str,
    longitude: float,
    lagna_lon: float
) -> Dict[str, Any]:
    """
    Sthana Bala — Positional Strength (0-60 Shashtiamsas)
    Based on sign placement quality.
    """
    sign = _get_sign(longitude)
    house = _get_house(longitude, lagna_lon)

    # Exaltation = 60, Own = 45, Friendly = 30, Neutral = 15, Debilitation = 0
    if planet in EXALTATION_SIGN and sign == EXALTATION_SIGN[planet]:
        score = 60.0
        placement = "exaltation"
    elif planet in DEBILITATION_SIGN and sign == DEBILITATION_SIGN[planet]:
        score = 0.0
        placement = "debilitation"
    elif planet in OWN_SIGNS and sign in OWN_SIGNS[planet]:
        score = 45.0
        placement = "own_sign"
    elif planet in FRIENDLY_SIGNS and sign in FRIENDLY_SIGNS[planet]:
        score = 30.0
        placement = "friendly_sign"
    else:
        score = 15.0
        placement = "neutral_sign"

    # Kendra bonus (+5) for planets in houses 1,4,7,10
    kendra_bonus = 5.0 if house in [1, 4, 7, 10] else 0.0
    # Trikona bonus (+3) for houses 5,9 (house 1 already gets kendra)
    trikona_bonus = 3.0 if house in [5, 9] else 0.0

    total = min(60.0, score + kendra_bonus + trikona_bonus)

    return {
        "score": round(total, 2),
        "placement": placement,
        "sign": sign,
        "house": house,
        "kendra_bonus": kendra_bonus,
        "trikona_bonus": trikona_bonus,
    }


def compute_dig_bala(
    planet: str,
    longitude: float,
    lagna_lon: float
) -> Dict[str, Any]:
    """
    Dig Bala — Directional Strength (0-60 Shashtiamsas)
    Planet is strongest in its preferred house, weakest in opposite.
    """
    if planet not in DIG_BALA_HOUSE:
        return {"score": 30.0, "house": 0, "peak_house": 0}

    house = _get_house(longitude, lagna_lon)
    peak_house = DIG_BALA_HOUSE[planet]

    # Distance from peak house (0 = strongest, 6 = weakest)
    distance = abs(house - peak_house)
    if distance > 6:
        distance = 12 - distance

    score = round(60.0 - (distance * 10.0), 2)
    score = max(0.0, min(60.0, score))

    return {
        "score": score,
        "house": house,
        "peak_house": peak_house,
        "distance_from_peak": distance,
    }


def compute_chesta_bala(
    planet: str,
    speed: float
) -> Dict[str, Any]:
    """
    Chesta Bala — Motional Strength (0-60 Shashtiamsas)
    Based on actual speed vs mean speed.
    Retrograde planets get reduced strength.
    Rahu/Ketu always retrograde — get fixed moderate score.
    """
    if planet in ["Rahu", "Ketu"]:
        return {"score": 15.0, "motion": "always_retrograde", "speed": 0.0}

    if planet not in MEAN_DAILY_MOTION:
        return {"score": 30.0, "motion": "unknown", "speed": speed}

    mean_speed = MEAN_DAILY_MOTION[planet]

    if speed < 0:
        # Retrograde — score based on how slowly retrograde
        score = 15.0 + min(15.0, abs(speed) / mean_speed * 10.0)
        motion = "retrograde"
    else:
        # Direct — score based on speed vs mean
        ratio = speed / mean_speed if mean_speed > 0 else 1.0
        score = min(60.0, ratio * 45.0)
        motion = "fast" if ratio > 1.2 else "mean" if ratio > 0.8 else "slow"

    return {
        "score": round(score, 2),
        "motion": motion,
        "speed": round(speed, 4),
        "mean_speed": mean_speed,
    }


def compute_drik_bala(
    planet: str,
    longitude: float,
    planets_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Drik Bala — Aspectual Strength (-30 to +30 Shashtiamsas)
    Net strength from aspects received from other planets.
    7th house aspect = full, 4th/8th = 3/4, 5th/9th = 1/2, others = 1/4
    """
    planet_sign = _get_sign(longitude)
    net_score = 0.0
    aspects_received = []

    for other_planet, other_data in planets_data.items():
        if other_planet == planet:
            continue
        if other_planet not in ASPECT_STRENGTH:
            continue

        other_lon = other_data.get("longitude_deg", 0)
        other_sign = _get_sign(other_lon)

        # House distance from other planet to this planet
        distance = ((planet_sign - other_sign + 12) % 12) + 1

        # Aspect multiplier
        if distance == 7:
            multiplier = 1.0    # Full aspect
        elif distance in [4, 8]:
            multiplier = 0.75   # 3/4 aspect (Mars special)
        elif distance in [5, 9]:
            multiplier = 0.5    # 1/2 aspect (Jupiter special)
        elif distance in [3, 10]:
            multiplier = 0.25   # 1/4 aspect (Saturn special)
        else:
            multiplier = 0.0

        if multiplier > 0:
            raw = ASPECT_STRENGTH[other_planet] * multiplier
            net_score += raw
            aspects_received.append({
                "from": other_planet,
                "strength": round(raw, 2),
                "aspect_type": f"H{distance}"
            })

    # Normalize to 0-60 range (net can be negative -> map to 0)
    normalized = max(0.0, min(60.0, 30.0 + net_score))

    return {
        "score": round(normalized, 2),
        "net_raw": round(net_score, 2),
        "aspects_received": aspects_received,
    }


def compute_shadbala(
    planets_data: Dict[str, Any],
    lagna_lon: float
) -> Dict[str, Any]:
    """
    Master function: compute Shadbala for all 7 planets.
    Returns per-planet scores and rankings.

    Args:
        planets_data: From ephemeris["planets"] — needs longitude_deg,
                      speed_deg_per_day
        lagna_lon: Lagna longitude in degrees

    Returns:
        Dict with per-planet Shadbala scores and overall ranking
    """
    try:
        SHADBALA_PLANETS = [
            "Sun", "Moon", "Mars", "Mercury",
            "Jupiter", "Venus", "Saturn"
        ]

        results = {}

        for planet in SHADBALA_PLANETS:
            if planet not in planets_data:
                continue

            pdata = planets_data[planet]
            lon   = pdata.get("longitude_deg", 0.0)
            speed = pdata.get("speed_deg_per_day", 0.0)

            sthana = compute_sthana_bala(planet, lon, lagna_lon)
            dig    = compute_dig_bala(planet, lon, lagna_lon)
            chesta = compute_chesta_bala(planet, speed)
            naisargika_score = NAISARGIKA_BALA.get(planet, 0.0)
            drik   = compute_drik_bala(planet, lon, planets_data)

            # Total Shadbala (out of 300 Shashtiamsas for 5 components)
            total = (
                sthana["score"] +
                dig["score"] +
                chesta["score"] +
                naisargika_score +
                drik["score"]
            )

            # Convert to Rupas (1 Rupa = 60 Shashtiamsas)
            rupas = round(total / 60.0, 3)

            # Percentage of maximum possible (300 Shashtiamsas)
            percent = round((total / 300.0) * 100, 1)

            results[planet] = {
                "total_shashtiamsas": round(total, 2),
                "rupas": rupas,
                "percent_strength": percent,
                "strength_label": (
                    "Very Strong" if percent >= 75 else
                    "Strong"      if percent >= 55 else
                    "Moderate"    if percent >= 35 else
                    "Weak"
                ),
                "components": {
                    "sthana_bala": sthana,
                    "dig_bala": dig,
                    "chesta_bala": chesta,
                    "naisargika_bala": {
                        "score": naisargika_score,
                        "note": "Fixed natural strength"
                    },
                    "drik_bala": drik,
                },
                "is_retrograde": speed < 0,
                "sign": _get_sign(lon),
                "house": _get_house(lon, lagna_lon),
            }

        # Rank planets by total strength
        ranked = sorted(
            results.items(),
            key=lambda x: x[1]["total_shashtiamsas"],
            reverse=True
        )

        strongest = ranked[0][0] if ranked else None
        weakest   = ranked[-1][0] if ranked else None

        return {
            "planets": results,
            "ranking": [p for p, _ in ranked],
            "strongest_planet": strongest,
            "weakest_planet": weakest,
            "summary": {
                "strongest": strongest,
                "weakest": weakest,
                "very_strong_count": sum(
                    1 for _, v in results.items()
                    if v["strength_label"] == "Very Strong"
                ),
                "weak_count": sum(
                    1 for _, v in results.items()
                    if v["strength_label"] == "Weak"
                ),
            },
            "error": None
        }

    except Exception as e:
        logger.error(f"Shadbala computation error: {e}")
        return {
            "planets": {},
            "ranking": [],
            "strongest_planet": None,
            "weakest_planet": None,
            "summary": {},
            "error": str(e)
        }
