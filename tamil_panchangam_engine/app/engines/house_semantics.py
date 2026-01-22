# app/engines/house_semantics.py

HOUSE_MEANINGS = {
    1: "Self, identity, physical vitality",
    2: "Wealth, speech, family",
    3: "Effort, courage, communication",
    4: "Home, peace, mother",
    5: "Creativity, intelligence, children",
    6: "Health, competition, debts",
    7: "Relationships, partnerships",
    8: "Transformation, longevity",
    9: "Dharma, fortune, higher learning",
    10: "Career, authority, public life",
    11: "Gains, networks, ambitions",
    12: "Loss, isolation, liberation",
}


def build_antar_house_interpretation(
    *,
    antar_lord: str,
    activated_house: int,
    planet_semantics: dict,
) -> dict:
    return {
        "antar_lord": antar_lord,
        "activated_house": activated_house,
        "house_theme": HOUSE_MEANINGS.get(activated_house, "Life matters"),
        "what_to_expect": [
            *planet_semantics.get("supports", []),
            f"Focus on {HOUSE_MEANINGS.get(activated_house)}",
        ],
        "watch_out_for": planet_semantics.get("watch_out", []),
    }
