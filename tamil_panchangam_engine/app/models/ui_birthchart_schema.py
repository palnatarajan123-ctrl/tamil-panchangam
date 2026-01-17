from datetime import date, time
from typing import List, Dict, Optional
from pydantic import BaseModel


# -------------------------------------------------
# CORE IDENTITY
# -------------------------------------------------

class BirthIdentity(BaseModel):
    name: str
    gender: Optional[str]
    date_of_birth: date
    time_of_birth: time
    place_of_birth: str
    latitude: float
    longitude: float
    timezone: str


# -------------------------------------------------
# PANCHANGAM ELEMENTS (AT BIRTH)
# -------------------------------------------------

class PanchangamAtBirth(BaseModel):
    tithi: str
    nakshatra: str
    yoga: str
    karana: str
    weekday: str


# -------------------------------------------------
# PLANETARY POSITION
# -------------------------------------------------

class PlanetPosition(BaseModel):
    planet: str

    longitude: Optional[float] = None
    degree: Optional[float] = None

    sign: Optional[str] = None
    nakshatra: Optional[str] = None
    pada: Optional[int] = None

    house: Optional[int] = None
    retrograde: Optional[bool] = None



# -------------------------------------------------
# HOUSE DETAILS
# -------------------------------------------------

class HouseDetail(BaseModel):
    house: int
    sign: str
    lord: str
    planets: List[str]


# -------------------------------------------------
# DASA SNAPSHOT (STATIC)
# -------------------------------------------------

class DashaSnapshot(BaseModel):
    maha_dasha: Optional[str] = None
    antar_dasha: Optional[str] = None

    start_date: Optional[date] = None
    end_date: Optional[date] = None


# -------------------------------------------------
# CHART METADATA
# -------------------------------------------------


class ChartMetadata(BaseModel):
    sun_sign: Optional[str] = None
    moon_sign: Optional[str] = None

    ayanamsa: Optional[str] = None
    calculation_method: Optional[str] = None

    house_system: Optional[str] = None
    zodiac_type: Optional[str] = None



# -------------------------------------------------
# FINAL VIEW MODEL
# -------------------------------------------------

class BirthChartView(BaseModel):
    identity: BirthIdentity
    panchangam: PanchangamAtBirth
    chart_metadata: ChartMetadata
    planets: List[PlanetPosition]
    houses: List[HouseDetail]
    dasha: DashaSnapshot
