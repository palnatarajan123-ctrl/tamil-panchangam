from typing import Dict, List


# -------------------------------------------------
# Planet Semantic Registry (EPIC-6.3 baseline)
# -------------------------------------------------

PLANET_THEMES: Dict[str, Dict[str, List[str] | str]] = {
    "Sun": {
        "themes": ["authority", "visibility", "identity"],
        "tone": "assertive",
    },
    "Moon": {
        "themes": ["emotions", "mental state", "home"],
        "tone": "sensitive",
    },
    "Mars": {
        "themes": ["action", "conflict", "drive"],
        "tone": "forceful",
    },
    "Mercury": {
        "themes": ["communication", "analysis", "learning"],
        "tone": "analytical",
    },
    "Jupiter": {
        "themes": ["growth", "learning", "guidance"],
        "tone": "expansive",
    },
    "Venus": {
        "themes": ["relationships", "comfort", "aesthetics"],
        "tone": "harmonizing",
    },
    "Saturn": {
        "themes": ["discipline", "delay", "responsibility"],
        "tone": "restrictive",
    },
    "Rahu": {
        "themes": ["ambition", "experimentation", "non-linear paths"],
        "tone": "disruptive",
    },
    "Ketu": {
        "themes": ["detachment", "introspection", "closure"],
        "tone": "withdrawn",
    },
}


# -------------------------------------------------
# House Classification (EPIC-9 dependency)
# -------------------------------------------------

SUPPORTIVE_HOUSES = {1, 4, 5, 7, 9, 10}
NEUTRAL_HOUSES = {3, 6, 11}
CHALLENGING_HOUSES = {2, 8, 12}


# -------------------------------------------------
# Phase Resolver (EPIC-6.3)
# -------------------------------------------------

def _phase_from_confidence(weight: float) -> str:
    if weight < 0.33:
        return "early"
    if weight < 0.66:
        return "mid"
    return "late"


# -------------------------------------------------
# Strength Modulation (EPIC-10)
# -------------------------------------------------

def _planet_strength(dignity: str | None) -> str:
    if dignity in {"exalted", "own"}:
        return "strong"
    if dignity in {"debilitated", "enemy"}:
        return "weak"
    return "average"


def _house_strength(house: int | None) -> str:
    if not house:
        return "neutral"
    if house in SUPPORTIVE_HOUSES:
        return "supportive"
    if house in CHALLENGING_HOUSES:
        return "challenging"
    return "neutral"


def _caution_level(planet_strength: str, house_strength: str) -> str:
    if planet_strength == "weak" and house_strength == "challenging":
        return "high"
    if planet_strength == "weak" or house_strength == "challenging":
        return "medium"
    return "low"


# -------------------------------------------------
# Remedy Generator (EPIC-10)
# -------------------------------------------------

def _build_remedies(
    *,
    planet: str,
    planet_strength: str,
    house_strength: str,
    phase: str,
) -> Dict[str, List[str]]:
    recommended: List[str] = []
    supportive: List[str] = []
    avoid: List[str] = []

    # Planet-centric base remedies
    if planet == "Saturn":
        recommended.append("Structured routines and disciplined effort")
        supportive.append("Service to the elderly or underprivileged")
        avoid.append("Avoid procrastination and shortcuts")

    elif planet == "Jupiter":
        recommended.append("Mentorship, teaching, or ethical learning")
        supportive.append("Charity on Thursdays")
        avoid.append("Avoid moral complacency or over-promising")

    elif planet == "Mars":
        recommended.append("Physical discipline and focused action")
        supportive.append("Channel anger into structured activity")
        avoid.append("Avoid impulsive confrontations")

    elif planet == "Moon":
        recommended.append("Emotional grounding and routine self-care")
        supportive.append("Time near water or nature")
        avoid.append("Avoid emotional reactivity")

    elif planet == "Venus":
        recommended.append("Cultivation of harmony in relationships")
        supportive.append("Creative or artistic expression")
        avoid.append("Avoid indulgence without balance")

    elif planet == "Mercury":
        recommended.append("Clear communication and skill refinement")
        supportive.append("Journaling or analytical exercises")
        avoid.append("Avoid overthinking or misinformation")

    elif planet == "Sun":
        recommended.append("Responsible leadership and self-clarity")
        supportive.append("Daily sunlight or reflection practices")
        avoid.append("Avoid ego conflicts")

    elif planet == "Rahu":
        recommended.append("Conscious experimentation with boundaries")
        supportive.append("Grounding practices")
        avoid.append("Avoid risky shortcuts or obsession")

    elif planet == "Ketu":
        recommended.append("Mindful detachment and introspection")
        supportive.append("Spiritual or contemplative study")
        avoid.append("Avoid isolation without purpose")

    # Strength modulation
    if planet_strength == "weak":
        recommended.append("Consistency over intensity")
    if house_strength == "challenging":
        avoid.append("Avoid forcing outcomes during sensitive periods")

    # Phase tuning
    if phase == "early":
        supportive.append("Gentle alignment and observation")
    elif phase == "mid":
        recommended.append("Active engagement with lessons")
    elif phase == "late":
        supportive.append("Consolidation and release practices")

    return {
        "recommended": list(dict.fromkeys(recommended)),
        "supportive": list(dict.fromkeys(supportive)),
        "avoid": list(dict.fromkeys(avoid)),
    }


# -------------------------------------------------
# Main Explanation Builder
# -------------------------------------------------

def build_antar_explanation(
    *,
    maha_lord: str,
    antar_lord: str,
    confidence_weight: float,
    antar_house: int | None = None,
    planet_dignity: str | None = None,
) -> Dict:
    """
    EPIC-6.3 + EPIC-9 + EPIC-10
    Contextual, NON-predictive explanation layer.
    """

    maha = PLANET_THEMES.get(maha_lord, {})
    antar = PLANET_THEMES.get(antar_lord, {})

    phase = _phase_from_confidence(confidence_weight)

    planet_strength = _planet_strength(planet_dignity)
    house_strength = _house_strength(antar_house)

    remedies = _build_remedies(
        planet=antar_lord,
        planet_strength=planet_strength,
        house_strength=house_strength,
        phase=phase,
    )

    return {
        # 🔹 EPIC-6.3 BASE
        "summary": (
            f"{antar_lord} Antar Dasha operates within "
            f"{maha_lord} Mahadasha, shaping how its results manifest."
        ),
        "themes": antar.get("themes", []),
        "modulation": (
            f"{antar_lord} introduces a {antar.get('tone', 'modifying')} "
            f"influence to {maha_lord} Mahadasha themes."
        ),
        "what_to_expect": [
            f"Greater emphasis on {t}." for t in antar.get("themes", [])
        ] + [
            {
                "early": "Themes are beginning to surface and adjust.",
                "mid": "Themes are actively shaping daily experience.",
                "late": "Themes are consolidating toward closure.",
            }[phase]
        ],
        "phase": phase,

        # 🔹 EPIC-10 ADDITIONS
        "strength_profile": {
            "planet_strength": planet_strength,
            "house_strength": house_strength,
            "phase": phase,
        },
        "remedies": remedies,
        "caution_level": _caution_level(planet_strength, house_strength),
    }
