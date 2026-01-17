# app/engines/house_weights.py

from app.engines.house_mappings import HOUSE_LIFE_AREA_MAP

def compute_house_weight_multiplier(
    planet_name: str,
    planet_house: int,
    life_area: str
) -> float:
    """
    Returns a multiplier based on natal house relevance.
    """

    relevant_areas = HOUSE_LIFE_AREA_MAP.get(planet_house, [])

    # Strong relevance
    if life_area in relevant_areas:
        return 1.3

    # Dusthana houses reduce stability
    if planet_house in (6, 8, 12):
        return 0.85

    # Neutral
    return 1.0
