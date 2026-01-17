from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime


class UIMeta(BaseModel):
    generated_at: datetime
    engine_version: str
    period_label: str


class UIIdentity(BaseModel):
    name: str
    place_of_birth: str
    birth_date: str
    moon_sign: str
    lagna: str


class UILifeArea(BaseModel):
    key: str
    label: str
    score: int
    confidence: float
    sentiment: str
    summary: str
    detail: str


class UITiming(BaseModel):
    dominant_pakshi: str
    recommended: List[str]
    avoid: List[str]


class UIChartMeta(BaseModel):
    type: str
    label: str
    available: bool


class MonthlyPredictionUIModel(BaseModel):
    meta: UIMeta
    identity: UIIdentity
    overview: Dict
    life_areas: List[UILifeArea]
    timing: UITiming
    charts: List[UIChartMeta]
    disclaimers: List[str]
