from sqlmodel import Session
import json

from app.db.session import engine
from app.db.models import BaseChartRow

base_chart_id = "18b0c06a-1299-4a0e-8328-94d30c51c0f0"

with Session(engine) as db:
    row = db.get(BaseChartRow, base_chart_id)

    if not row:
        raise ValueError("Base chart not found")

    data = json.loads(row.payload)

    print("TOP KEYS:", list(data.keys()))
    print("HAS ephemeris?", "ephemeris" in data)

    if "ephemeris" in data:
        print("EPHEMERIS KEYS:", list(data["ephemeris"].keys()))

        lagna = data["ephemeris"].get("lagna", {})
        print("LAGNA:", lagna)

        planets = data["ephemeris"].get("planets", {})
        print("PLANETS:", list(planets.keys()))


