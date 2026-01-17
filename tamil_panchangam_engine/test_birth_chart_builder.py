from sqlmodel import Session
import json
from app.db.session import engine
from app.db.models import BaseChartRow
from app.services.birth_chart_builder import build_birth_chart_view_model

BASE_CHART_ID = "18b0c06a-1299-4a0e-8328-94d30c51c0f0"

with Session(engine) as db:
    row = db.get(BaseChartRow, BASE_CHART_ID)
    base_chart = json.loads(row.payload)

view = build_birth_chart_view_model(base_chart)

print("TOP LEVEL KEYS:", view.keys())

print("\nPLANETARY POSITIONS SAMPLE:")
for k, v in view["planetary_positions"].items():
    print(k, "→ house:", v["house"], "nak:", v["nakshatra"], "dasha:", v.get("dasha"))

print("\nHOUSES:")
for h in view["houses"]:
    print(h)

print("\nRASI VIEW SAMPLE:")
print(view["rasi_view"][:2])

print("\nNAKSHATRA VIEW SAMPLE:")
print(view["nakshatra_view"][:2])
