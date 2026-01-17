"""
UI-facing prediction schemas.

IMPORTANT:
- These are presentation models
- They do NOT drive computation
- Safe to evolve independently
"""

from typing import List, Optional
from pydantic import BaseModel


class LifeAreaUI(BaseModel):
    name: str
    score: int
    confidence: float
    text: str


class PredictionUIResponse(BaseModel):
    period: str
    maha_dasha: Optional[str] = None
    antar_dasha: Optional[str] = None
    life_areas: List[LifeAreaUI]
