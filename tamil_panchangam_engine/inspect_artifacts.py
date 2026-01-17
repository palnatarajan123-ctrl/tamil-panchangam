from sqlmodel import Session, select
import json

from app.db.session import engine
from app.db.models import ChartArtifactRow

base_chart_id = "18b0c06a-1299-4a0e-8328-94d30c51c0f0"

with Session(engine) as db:
    artifacts = db.exec(
        select(ChartArtifactRow)
        .where(ChartArtifactRow.base_chart_id == base_chart_id)
    ).all()

    print(f"Found {len(artifacts)} artifacts")

    for a in artifacts:
        print("\n====================")
        print("TYPE:", a.chart_type)
        print(json.dumps(json.loads(a.payload), indent=2))
