import json
from sqlmodel import Session, select
from datetime import datetime

from app.db.models import (
    BaseChartRow,
    ChartArtifactRow,
    MonthlyPredictionRow,
)

from app.models.report_schema import (
    PredictionReportSnapshot,
    ReportMetadata,
)

def build_prediction_report_snapshot(
    db: Session,
    base_chart_id: str,
    year: int,
    month: int,
) -> PredictionReportSnapshot:
    """
    Read-only aggregation.
    No computation. No mutation.
    """

    # ----------------------------
    # 1. Base chart (immutable)
    # ----------------------------
    base_chart = db.get(BaseChartRow, base_chart_id)
    if not base_chart:
        raise ValueError("Base chart not found")

    # ----------------------------
    # 2. Artifacts
    # ----------------------------
    artifacts = db.exec(
        ChartArtifactRow.__table__.select()
        .where(ChartArtifactRow.base_chart_id == base_chart_id)
    ).all()

    artifact_map = {
        a.chart_type: json.loads(a.payload)
        for a in artifacts
    }

    # ----------------------------
    # 3. Monthly prediction
    # ----------------------------
    pid = f"{base_chart_id}:{year}:{month}"
    prediction = db.get(MonthlyPredictionRow, pid)

    if not prediction:
        raise ValueError("Monthly prediction not found")

    # ----------------------------
    # 4. Assemble snapshot
    # ----------------------------

    return PredictionReportSnapshot(
        metadata=ReportMetadata(
            base_chart_id=base_chart_id,
            prediction_id=pid,
            generated_at=datetime.utcnow(),
            engine_versions={
                "base_chart": base_chart.engine_version,
                "prediction": prediction.engine_version,
            },
        ),
        base_chart=json.loads(base_chart.payload),
        chart_artifacts=artifact_map,
        monthly_prediction={
            "year": prediction.year,
            "month": prediction.month,
            "status": prediction.status,
            "envelope": json.loads(prediction.envelope),
            "synthesis": json.loads(prediction.synthesis),
            "interpretation": (
                json.loads(prediction.interpretation)
                if prediction.interpretation else None
            ),
        },
    )


def load_base_chart_snapshot(
    db: Session,
    base_chart_id: str,
) -> dict:
    base = db.exec(
        select(BaseChartRow).where(BaseChartRow.id == base_chart_id)
    ).first()

    if not base:
        raise ValueError("Base chart not found")

    base_payload = json.loads(base.payload)

    artifacts = db.exec(
        select(ChartArtifactRow)
        .where(ChartArtifactRow.base_chart_id == base_chart_id)
    ).all()

    artifact_map = {}
    for a in artifacts:
        artifact_map[a.chart_type] = json.loads(a.payload)

    return {
        "identity": {
            "name": base.name,
            "gender": base.gender,
            "date_of_birth": base.date_of_birth,
            "time_of_birth": base.time_of_birth,
            "place_of_birth": base.place_of_birth,
            "latitude": base.latitude,
            "longitude": base.longitude,
            "timezone": base.timezone,
        },
        "base_payload": base_payload,      # 🔑 NEW
        "artifacts": artifact_map,
    }
