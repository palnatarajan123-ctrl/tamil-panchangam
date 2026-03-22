"""
Pydantic schemas for API I/O validation only.
Astrological truth lives in engines, not here.

EPIC-5 NOTE:
- Legacy schemas are preserved for backward compatibility
- New canonical contracts are STRICT and UI-agnostic
"""

from __future__ import annotations

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, Literal, List
from datetime import date, time, datetime
import uuid


# ============================================================
# In-memory store (v1 – temporary, EPIC-6 will replace)
# ============================================================

BASE_CHART_STORE: Dict[str, Dict[str, Any]] = {}

def generate_base_chart_id() -> str:
    return str(uuid.uuid4())


# ============================================================
# -----------------------------
# LEGACY INPUT SCHEMAS (v0)
# -----------------------------
# ❗ DO NOT EXTEND. WILL BE DEPRECATED AFTER EPIC-5
# ============================================================

class BirthInput(BaseModel):
    name: str
    sex: Optional[str] = None
    birth_date: str           # YYYY-MM-DD (legacy)
    birth_time: str           # HH:MM (legacy)
    latitude: float
    longitude: float
    timezone: Optional[str] = None
    place_name: Optional[str] = None


class PredictionRequest(BaseModel):
    base_chart_id: str
    target_month: str         # YYYY-MM (legacy)


# ============================================================
# -----------------------------
# LEGACY OUTPUT SCHEMAS (v0)
# -----------------------------
# ❗ WILL BE REMOVED AFTER UI MIGRATION
# ============================================================

class BaseChartResponse(BaseModel):
    base_chart_id: str
    base_chart: Dict[str, Any]


class PredictionResponse(BaseModel):
    base_chart_id: str
    prediction: Dict[str, Any]


# ============================================================
# ============================================================
# EPIC-5 — CANONICAL BASE CHART CONTRACTS (NEW)
# ============================================================
# ============================================================

class BaseChartCreateRequest(BaseModel):
    """
    Canonical input for base chart creation.
    This REPLACES BirthInput for all new endpoints.
    """

    name: Optional[str] = Field(default=None)

    date_of_birth: date = Field(
        ..., description="Date of birth (YYYY-MM-DD)"
    )

    time_of_birth: time = Field(
        ..., description="Time of birth (HH:MM:SS)"
    )

    place_of_birth: str = Field(
        ..., min_length=1, description="Place name (non-empty)"
    )

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

    timezone: Optional[str] = Field(
        default=None, description="IANA timezone (e.g., Asia/Kolkata)"
    )
    
    node_type: Optional[Literal["mean", "true"]] = Field(
        default="mean",
        description="Rahu/Ketu calculation method: 'mean' (traditional Tamil) or 'true' (astronomical)"
    )

    ayanamsa: Optional[Literal["lahiri", "kp"]] = Field(
        default="lahiri",
        description="Ayanamsa system: lahiri (default) or kp (Krishnamurti)"
    )

    turnstile_token: Optional[str] = Field(
        default=None, description="Cloudflare Turnstile verification token"
    )


class BaseChartCreateResponse(BaseModel):
    base_chart_id: str
    checksum: str
    locked: bool


class BaseChartSummary(BaseModel):
    base_chart_id: str
    checksum: str
    locked: bool


class BaseChartDetail(BaseModel):
    id: str
    checksum: str
    locked: bool
    created_at: datetime
    data: Dict[str, Any]


# ============================================================
# EPIC-5 — MONTHLY PREDICTION (NEW CANONICAL)
# ============================================================

class MonthlyPredictionRequest(BaseModel):
    """
    Canonical monthly prediction request.
    REPLACES target_month string.
    """

    base_chart_id: str

    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)

    @validator("month")
    def validate_month(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("month must be between 1 and 12")
        return v


class MonthlyPredictionResponse(BaseModel):
    """
    Thin orchestration response.
    Interpretation lives in EPIC-4 schemas below.
    """

    id: str
    base_chart_id: str
    year: int
    month: int
    generated_at: datetime

    status: Literal["ok", "stub"]
    summary: str
    details: Dict[str, Any]

    # EPIC-8 — derived explainability (not persisted)
    explainability: Optional[Dict[str, Any]] = None

    # True when envelope+synthesis were returned from the prediction cache
    cache_hit: bool = False

    # "pending" while LLM runs in background; "ready" or absent when done
    llm_status: Optional[str] = None


# ============================================================
# ============================================================
# EPIC-4 — PREDICTION INTERPRETATION (FROZEN)
# ============================================================
# ============================================================

class PredictionEnvironment(BaseModel):
    transits: Dict[str, Any]


class PredictionTimeRuler(BaseModel):
    vimshottari_dasha: Dict[str, Any]


class PredictionBiologicalRhythm(BaseModel):
    pancha_pakshi_daily: Dict[str, Any]


class MonthlyPrediction(BaseModel):
    reference_month: str
    environment: PredictionEnvironment
    time_ruler: PredictionTimeRuler
    biological_rhythm: PredictionBiologicalRhythm
    note: str
    schema_version: str = "prediction-v1"


class LifeAreaSynthesis(BaseModel):
    raw_score: float
    score: float
    confidence: float


class MonthlySynthesis(BaseModel):
    life_areas: Dict[str, LifeAreaSynthesis]
    engine_version: str
    generated_at: str


class MonthlyPredictionV1Response(BaseModel):
    """
    EPIC-4 FINAL OUTPUT (DO NOT MODIFY)
    """

    base_chart_id: str
    checksum: str
    prediction: MonthlyPrediction
    synthesis: MonthlySynthesis
