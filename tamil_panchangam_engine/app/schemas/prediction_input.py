# app/schemas/prediction_input.py

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import date


# -------------------------------------------------
# CORE ENUMS
# -------------------------------------------------

PredictionMode = Literal["monthly", "event"]
PredictionHorizon = Literal["short", "medium", "long"]

AstroLever = Literal[
    "transit",
    "dasha",
    "nakshatra",
]

LifeArea = Literal[
    "career",
    "finance",
    "relationships",
    "health",
    "education",
    "spirituality",
    "family",
]


# -------------------------------------------------
# TIMEFRAME
# -------------------------------------------------

class PredictionTimeframe(BaseModel):
    """
    Defines the time window for prediction.

    - Monthly: month + year
    - Event-based: explicit start/end dates
    """

    mode: PredictionMode

    # monthly
    year: Optional[int] = Field(
        None, description="Calendar year for monthly prediction"
    )
    month: Optional[int] = Field(
        None, ge=1, le=12, description="Calendar month (1–12)"
    )

    # event-based
    start_date: Optional[date] = None
    end_date: Optional[date] = None


# -------------------------------------------------
# TRIGGERS
# -------------------------------------------------

class PredictionTriggers(BaseModel):
    """
    What causes a prediction to be evaluated.
    Read-only flags — no computation here.
    """

    include_transits: bool = True
    include_dasha: bool = True
    include_nakshatra: bool = True


# -------------------------------------------------
# ASTRO LEVERS
# -------------------------------------------------

class PredictionLevers(BaseModel):
    """
    Controls which astrological mechanisms are emphasized.
    """

    enabled: List[AstroLever] = Field(
        default_factory=lambda: ["transit", "dasha"]
    )

    horizon: PredictionHorizon = "short"


# -------------------------------------------------
# CONSTRAINTS
# -------------------------------------------------

class PredictionConstraints(BaseModel):
    """
    Guardrails to prevent overreach.
    """

    max_events: int = Field(
        5, ge=1, le=20, description="Maximum number of surfaced events"
    )

    confidence_threshold: float = Field(
        0.6, ge=0.0, le=1.0,
        description="Minimum confidence for surfaced predictions"
    )


# -------------------------------------------------
# OUTPUT PREFERENCES
# -------------------------------------------------

class PredictionOutputPreferences(BaseModel):
    """
    How the prediction should be rendered.
    """

    include_explanations: bool = True
    include_remedies: bool = False
    include_confidence_score: bool = True
    include_house_context: bool = True


# -------------------------------------------------
# ROOT PREDICTION REQUEST
# -------------------------------------------------

class PredictionRequest(BaseModel):
    """
    EPIC-10
    Canonical prediction input schema.

    RULES:
    - Birth chart is immutable and referenced by ID
    - No raw birth data allowed
    - No computation happens here
    """

    schema_version: str = Field(
        "1.0",
        description="Prediction schema version"
    )

    base_chart_id: str = Field(
        ..., description="Immutable birth chart ID"
    )

    timeframe: PredictionTimeframe

    triggers: PredictionTriggers = Field(
        default_factory=PredictionTriggers
    )

    levers: PredictionLevers = Field(
        default_factory=PredictionLevers
    )

    focus_areas: Optional[List[LifeArea]] = Field(
        None,
        description="Optional life areas to emphasize"
    )

    constraints: PredictionConstraints = Field(
        default_factory=PredictionConstraints
    )

    output: PredictionOutputPreferences = Field(
        default_factory=PredictionOutputPreferences
    )

    class Config:
        extra = "forbid"

# app/schemas/prediction_input.py (ADD AT BOTTOM)

class Epic6Defaults:
    """
    EPIC-6 deterministic defaults.
    Used when schema_version < 1.0
    """

    @staticmethod
    def normalize_for_epic6(req: "PredictionRequest"):
        """
        Enforce EPIC-6 guardrails:
        - Only dasha-based predictions
        - Monthly or explicit date windows
        - No interpretation flags
        """
        req.triggers.include_transits = False
        req.triggers.include_nakshatra = False

        req.levers.enabled = ["dasha"]
        req.levers.horizon = "short"

        req.output.include_explanations = False
        req.output.include_remedies = False
        req.output.include_house_context = False

        return req

# --- EPIC-6 NORMALIZATION (ADDITIVE) ---

class Epic6Defaults:
    """
    Enforces EPIC-6 deterministic behavior.
    Does NOT change schema shape.
    """

    @staticmethod
    def normalize(req: "PredictionRequest") -> "PredictionRequest":
        # EPIC-6 = dasha-only, no interpretation
        req.triggers.include_transits = False
        req.triggers.include_nakshatra = False
        req.triggers.include_dasha = True

        req.levers.enabled = ["dasha"]
        req.levers.horizon = "short"

        req.output.include_explanations = False
        req.output.include_remedies = False
        req.output.include_house_context = False

        return req
