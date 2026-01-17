import json
import uuid
from datetime import datetime
from sqlmodel import Session

from app.db.models import ChartArtifactRow


def save_chart_artifact(
    db: Session,
    base_chart_id: str,
    chart_type: str,
    payload: dict,
    engine_version: str,
    chart_name: str | None = None,
):
    """
    Persist a render-ready chart artifact (D1, Panchangam, etc.)
    """

    row = ChartArtifactRow(
        id=str(uuid.uuid4()),
        base_chart_id=base_chart_id,
        chart_type=chart_type,
        chart_name=chart_name,
        payload=json.dumps(payload),
        engine_version=engine_version,
        created_at=datetime.utcnow(),
    )

    db.add(row)
    db.commit()
    return row
