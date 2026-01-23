# app/adapters/birth_chart_adapter.py

def build_birth_chart_view_model(base_chart: dict) -> dict:
    """
    Canonical adapter for birth chart data.
    Produces a normalized, synthesis-safe view.
    """

    birth_chart = base_chart.get("birth_chart", {})
    houses_raw = birth_chart.get("houses", {})

    houses = {}

    for h, data in houses_raw.items():
        try:
            house_num = int(h)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        houses[house_num] = {
            "house": house_num,
            "rasi": data.get("rasi"),
            "lord": data.get("lord"),
            "planets": data.get("planets", []),
        }

    return {
        "houses": houses,
    }
