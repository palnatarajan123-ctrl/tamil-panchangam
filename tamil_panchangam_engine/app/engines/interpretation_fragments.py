"""
Pre-generated interpretation fragments for planet-house-life area combinations.
Used by interpretation_builder to assemble dynamic, personalized predictions.
"""

PLANET_GENERAL = {
    "Sun": "authority, vitality, and recognition",
    "Moon": "emotions, mental peace, and intuition",
    "Mars": "energy, action, and courage",
    "Mercury": "communication, intellect, and adaptability",
    "Jupiter": "wisdom, growth, and opportunities",
    "Venus": "harmony, relationships, and comforts",
    "Saturn": "discipline, patience, and karmic lessons",
    "Rahu": "ambition, unconventional paths, and transformation",
    "Ketu": "spirituality, detachment, and past karma",
}

PLANET_INFLUENCE_POSITIVE = {
    "Sun": "brings clarity and confidence",
    "Moon": "enhances emotional intelligence and receptivity",
    "Mars": "provides drive and initiative",
    "Mercury": "sharpens thinking and communication",
    "Jupiter": "expands possibilities and brings blessings",
    "Venus": "attracts harmony and pleasant experiences",
    "Saturn": "rewards disciplined effort with stability",
    "Rahu": "opens doors to new opportunities",
    "Ketu": "brings spiritual insights and liberation",
}

PLANET_INFLUENCE_NEGATIVE = {
    "Sun": "may create ego conflicts or authority issues",
    "Moon": "could bring emotional fluctuations or anxiety",
    "Mars": "might trigger impatience or conflicts",
    "Mercury": "may cause miscommunication or nervous tension",
    "Jupiter": "could lead to overconfidence or missed details",
    "Venus": "might bring indulgence or relationship complications",
    "Saturn": "introduces delays, obstacles, or extra responsibilities",
    "Rahu": "may create confusion or unrealistic expectations",
    "Ketu": "could cause detachment or lack of focus",
}

HOUSE_LIFE_AREA_MAP = {
    1: ["health", "personal_growth"],
    2: ["finance"],
    3: ["career", "personal_growth"],
    4: ["relationships", "health"],
    5: ["personal_growth", "relationships"],
    6: ["health", "career"],
    7: ["relationships"],
    8: ["health", "finance"],
    9: ["personal_growth", "career"],
    10: ["career"],
    11: ["finance", "career"],
    12: ["health", "personal_growth"],
}

HOUSE_THEMES = {
    1: "self-expression and physical vitality",
    2: "wealth, speech, and family resources",
    3: "courage, skills, and short journeys",
    4: "home, emotional security, and inner peace",
    5: "creativity, children, and speculative gains",
    6: "daily routines, health challenges, and service",
    7: "partnerships, marriage, and business alliances",
    8: "transformation, shared resources, and longevity",
    9: "higher learning, fortune, and spiritual growth",
    10: "career, reputation, and public standing",
    11: "gains, aspirations, and social networks",
    12: "expenses, spirituality, and foreign connections",
}

LIFE_AREA_OPENING = {
    "career": {
        "strong_positive": "Career prospects are exceptionally favorable this period.",
        "positive": "Professional matters show positive momentum.",
        "mixed": "Career shows a balanced outlook requiring mindful navigation.",
        "challenging": "Professional sphere requires patience and careful attention.",
    },
    "finance": {
        "strong_positive": "Financial prospects are highly auspicious this period.",
        "positive": "Money matters trend favorably with steady growth potential.",
        "mixed": "Finances require balanced management this period.",
        "challenging": "Financial caution is advisable during this phase.",
    },
    "relationships": {
        "strong_positive": "Relationships flourish with exceptional harmony this period.",
        "positive": "Personal connections are well-supported and harmonious.",
        "mixed": "Relationships show mixed currents requiring understanding.",
        "challenging": "Interpersonal matters need extra care and patience.",
    },
    "health": {
        "strong_positive": "Health and vitality are strongly supported this period.",
        "positive": "Physical and mental wellbeing show favorable trends.",
        "mixed": "Health requires mindful attention to maintain balance.",
        "challenging": "Wellness matters need proactive care this period.",
    },
    "personal_growth": {
        "strong_positive": "Personal evolution is powerfully supported this period.",
        "positive": "Growth and learning opportunities are favorable.",
        "mixed": "Self-development proceeds at a steady, measured pace.",
        "challenging": "Inner growth requires patience and self-compassion.",
    },
}

LIFE_AREA_CLOSING = {
    "career": {
        "strong_positive": "Strategic initiatives and leadership roles are particularly favored.",
        "positive": "Consistent effort brings recognition and advancement.",
        "mixed": "Focus on skill-building rather than major transitions.",
        "challenging": "Consolidate current position and await clearer timing.",
    },
    "finance": {
        "strong_positive": "Investment decisions and new income sources are well-timed.",
        "positive": "Budgeting and moderate investments yield good returns.",
        "mixed": "Maintain conservative spending and avoid speculation.",
        "challenging": "Prioritize savings and defer major financial commitments.",
    },
    "relationships": {
        "strong_positive": "New connections and deepening bonds are highly favored.",
        "positive": "Quality time with loved ones strengthens connections.",
        "mixed": "Clear communication prevents misunderstandings.",
        "challenging": "Give space where needed and practice patience.",
    },
    "health": {
        "strong_positive": "New fitness regimes and health practices take root easily.",
        "positive": "Maintain current routines for sustained wellness.",
        "mixed": "Prioritize rest and stress management practices.",
        "challenging": "Avoid overexertion and address concerns promptly.",
    },
    "personal_growth": {
        "strong_positive": "Spiritual practices and new learning bring profound insights.",
        "positive": "Study and reflection yield meaningful progress.",
        "mixed": "Integration of past lessons serves better than new pursuits.",
        "challenging": "Rest and contemplation prepare ground for future growth.",
    },
}


def get_planet_house_fragment(planet: str, house: int, valence: str) -> str:
    """Generate a fragment describing planet's influence on a house."""
    house_theme = HOUSE_THEMES.get(house, "general life matters")
    
    if valence == "pos":
        influence = PLANET_INFLUENCE_POSITIVE.get(planet, "brings supportive energy")
        return f"{planet}'s activation of the {_ordinal(house)} house {influence} in matters of {house_theme}."
    else:
        influence = PLANET_INFLUENCE_NEGATIVE.get(planet, "requires careful handling")
        return f"{planet}'s influence on the {_ordinal(house)} house {influence} regarding {house_theme}."


def get_dasha_context_fragment(maha_lord: str, antar_lord: str = None) -> str:
    """Generate a fragment describing the current dasha period."""
    maha_quality = PLANET_GENERAL.get(maha_lord, "planetary influence")
    
    if antar_lord and antar_lord != maha_lord:
        antar_quality = PLANET_GENERAL.get(antar_lord, "additional energy")
        return (
            f"The current {maha_lord} Mahadasha emphasizes {maha_quality}, "
            f"while {antar_lord} Antardasha adds themes of {antar_quality}."
        )
    return f"The {maha_lord} Mahadasha period emphasizes themes of {maha_quality}."


def _ordinal(n: int) -> str:
    """Convert number to ordinal (1st, 2nd, 3rd, etc.)"""
    if 11 <= n <= 13:
        return f"{n}th"
    return f"{n}{['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]}"
