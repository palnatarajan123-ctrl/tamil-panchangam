from typing import List, Literal, Dict, Any
from pydantic import BaseModel, Field


ExplainabilityDriverType = Literal[
    "DASHA_OVERLAP",
    "DASHA_TRANSITION",
    "DASHA_STABILITY",
    "PERIOD_GRANULARITY",
    "CONFLICT_FLAG",
]


class ExplainabilityDriver(BaseModel):
    """
    Single deterministic explainability driver.

    No interpretation.
    No scoring.
    Evidence-only.
    """
    type: ExplainabilityDriverType
    label: str
    evidence: Dict[str, Any]


class ExplainabilityBlock(BaseModel):
    """
    EPIC-8 Explainability output schema.

    - Deterministic
    - Period-aware
    - UI-safe
    """
    summary: str
    dominant_dasha: str
    drivers: List[ExplainabilityDriver]
    transit_highlights: List[str] = Field(default_factory=list)
