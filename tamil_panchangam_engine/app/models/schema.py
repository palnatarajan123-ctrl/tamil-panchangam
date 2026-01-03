"""
Pydantic models for Tamil Panchangam Engine
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PlanetaryPosition(BaseModel):
    planet: str
    longitude: float
    sign: int
    sign_name: str
    degree_in_sign: float
    nakshatra: str
    nakshatra_pada: int
    nakshatra_lord: str
    retrograde: bool = False

class DivisionalPosition(BaseModel):
    planet: str
    d1_sign: int
    d9_sign: int

class DashaPeriod(BaseModel):
    lord: str
    start_date: datetime
    end_date: datetime
    is_current: bool = False

class Panchangam(BaseModel):
    tithi: str
    tithi_number: int
    nakshatra: str
    nakshatra_pada: int
    yoga: str
    karana: str
    vara: str
    sunrise: str
    sunset: str

class BaseChart(BaseModel):
    id: str
    name: str
    date_of_birth: str
    time_of_birth: str
    place_of_birth: str
    latitude: float
    longitude: float
    timezone: str
    lagna: int
    lagna_degree: float
    moon_sign: int
    sun_sign: int
    planetary_positions: List[PlanetaryPosition]
    panchangam: Panchangam
    current_dasha: DashaPeriod
    created_at: datetime

class TransitPosition(BaseModel):
    planet: str
    current_sign: int
    current_degree: float
    from_moon: int
    effect: str

class MonthlyPrediction(BaseModel):
    base_chart_id: str
    year: int
    month: int
    transits: List[TransitPosition]
    pancha_pakshi: dict
    auspicious_dates: List[str]
    general_forecast: str
