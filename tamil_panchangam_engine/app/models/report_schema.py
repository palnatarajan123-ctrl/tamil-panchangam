from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, List, Optional


class ReportMetadata(BaseModel):
    base_chart_id: str
    prediction_id: Optional[str] = None
    generated_at: datetime
    engine_versions: dict


class PredictionReportSnapshot(BaseModel):
    metadata: ReportMetadata
    base_chart: Dict
    chart_artifacts: Dict
    monthly_prediction: Optional[Dict] = None
