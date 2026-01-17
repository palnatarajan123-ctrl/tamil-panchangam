from typing import List, Literal, Dict, Any
from pydantic import BaseModel

ExplainabilityDriverType = Literal[
    "DASHA_OVERLAP",
    "DASHA_TRANSITION",
    "DASHA_STABILITY",
    "PERIOD_GRANULARITY",
    "CONFLICT_FLAG",
]


class ExplainabilityDriver(BaseModel):
    type: ExplainabilityDriverType
    label: str
    evidence: Dict[str, Any]


class ExplainabilityBlock(BaseModel):
    summary: str
    dominant_dasha: str
    drivers: List[ExplainabilityDriver]
    transit_highlights: List[str] = []
