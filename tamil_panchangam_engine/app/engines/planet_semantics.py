# app/engines/planet_semantics.py

PLANET_SEMANTICS = {
    "Sun": {
        "themes": ["Authority", "Identity", "Leadership"],
        "supports": ["Recognition", "Confidence", "Visibility"],
        "watch_out": ["Ego clashes", "Rigidity"],
    },
    "Moon": {
        "themes": ["Mind", "Emotions", "Comfort"],
        "supports": ["Emotional balance", "Intuition"],
        "watch_out": ["Mood swings", "Over-attachment"],
    },
    "Mars": {
        "themes": ["Action", "Courage", "Conflict"],
        "supports": ["Decisiveness", "Energy"],
        "watch_out": ["Impulsiveness", "Aggression"],
    },
    "Mercury": {
        "themes": ["Communication", "Analysis", "Trade"],
        "supports": ["Negotiation", "Learning"],
        "watch_out": ["Overthinking", "Nervousness"],
    },
    "Jupiter": {
        "themes": ["Growth", "Wisdom", "Expansion"],
        "supports": ["Mentorship", "Ethics", "Learning"],
        "watch_out": ["Overconfidence", "Excess optimism"],
    },
    "Venus": {
        "themes": ["Relationships", "Comfort", "Art"],
        "supports": ["Harmony", "Attraction"],
        "watch_out": ["Indulgence", "Dependency"],
    },
    "Saturn": {
        "themes": ["Discipline", "Responsibility", "Structure"],
        "supports": ["Stability", "Long-term gains"],
        "watch_out": ["Delays", "Pessimism"],
    },
    "Rahu": {
        "themes": ["Ambition", "Innovation", "Disruption"],
        "supports": ["Unconventional success"],
        "watch_out": ["Obsession", "Illusion"],
    },
    "Ketu": {
        "themes": ["Detachment", "Insight", "Spirituality"],
        "supports": ["Liberation", "Introspection"],
        "watch_out": ["Isolation", "Confusion"],
    },
}


def get_planet_semantics(planet: str) -> dict:
    return PLANET_SEMANTICS.get(
        planet,
        {"themes": [], "supports": [], "watch_out": []},
    )
