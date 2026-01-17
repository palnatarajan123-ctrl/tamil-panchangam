from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


# =====================================================
# BASE CHARTS (IMMUTABLE TRUTH)
# =====================================================

class BaseChartRow(SQLModel, table=True):
    __tablename__ = "base_charts"

    id: str = Field(primary_key=True)
    checksum: str
    locked: bool
    created_at: datetime
    payload: str              # JSON stored as TEXT
    engine_version: str


# =====================================================
# CHART ARTIFACTS (D1, PANCHANGAM, ETC.)
# =====================================================

class ChartArtifactRow(SQLModel, table=True):
    __tablename__ = "chart_artifacts"

    id: str = Field(primary_key=True)
    base_chart_id: str = Field(foreign_key="base_charts.id")
    chart_type: str
    chart_name: Optional[str] = None
    payload: str              # JSON
    engine_version: str
    created_at: datetime


# =====================================================
# MONTHLY PREDICTIONS
# =====================================================

class MonthlyPredictionRow(SQLModel, table=True):
    __tablename__ = "monthly_predictions"

    id: str = Field(primary_key=True)
    base_chart_id: str = Field(foreign_key="base_charts.id")
    year: int
    month: int
    status: str
    created_at: datetime

    envelope: str             # JSON
    synthesis: str             # JSON
    interpretation: Optional[str] = None

    engine_version: str


# =====================================================
# ENGINE RUNS (OPTIONAL)
# =====================================================

class EngineRunRow(SQLModel, table=True):
    __tablename__ = "engine_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    engine: str
    version: str
    run_at: datetime
    notes: Optional[str] = None
