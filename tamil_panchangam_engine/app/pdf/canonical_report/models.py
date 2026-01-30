"""
Canonical PDF Report Builder - Data Models

These models define the structure of data passed to the PDF renderer.
All data is READ-ONLY from database - no recalculation.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime


class BirthDetails(BaseModel):
    """Birth details for cover page."""
    name: str
    date: str
    time: str
    place: str


class BirthReference(BaseModel):
    """Static birth reference data (never changes)."""
    janma_nakshatra: str
    janma_rasi: str
    lagna: str
    moon_sign: str
    nakshatra_lord: str
    birth_dasha: str
    functional_role_planets: Dict[str, str]
    sun_sign: Optional[str] = None
    ayanamsa: Optional[str] = None


class DashaContext(BaseModel):
    """Active dasha context for current period."""
    mahadasha: str
    mahadasha_lord: str
    antardasha: str
    antardasha_lord: str
    dasha_balance: str


class TransitContext(BaseModel):
    """Transit/Gochara context."""
    jupiter_transit: str
    saturn_transit: str
    rahu_ketu_axis: str


class NakshatraTimingContext(BaseModel):
    """Nakshatra and timing context."""
    current_moon_nakshatra: str
    tara_bala: str
    chandra_gati: str
    favorable_window: str


class PakshiRhythmContext(BaseModel):
    """Pakshi rhythm context."""
    dominant_pakshi: str
    activity_phase: str


class SignalAttribution(BaseModel):
    """Attribution data for a life area prediction."""
    dasha: str = ""
    planets: List[str] = []
    engines: List[str] = []
    signals_count: int = 0


class PredictionArea(BaseModel):
    """Single prediction life area with full details."""
    area: str
    score: int = 50
    outlook: str = "neutral"
    interpretation: str
    deeper_explanation: Optional[str] = None
    guidance: Optional[str] = None
    opportunity: Optional[str] = None
    watch_out: Optional[str] = None
    one_action: Optional[str] = None
    attribution: Optional[SignalAttribution] = None


class MonthlyTheme(BaseModel):
    """V2 monthly theme."""
    title: str
    narrative: str


class Overview(BaseModel):
    """V2 overview with focus areas."""
    energy_pattern: str
    key_focus: List[str] = []
    avoid_or_be_mindful: List[str] = []


class PracticesAndReflection(BaseModel):
    """V2 practices and reflection."""
    daily_practice: Optional[str] = None
    weekly_practice: Optional[str] = None
    reflection_question: Optional[str] = None


class Closing(BaseModel):
    """V2 closing section."""
    key_takeaways: List[str] = []
    encouragement: Optional[str] = None


class ChartImages(BaseModel):
    """Chart data for rendering."""
    d1_rasi: str
    d9_navamsa: str
    d1_planet_signs: Dict[str, List[str]] = {}
    d9_planet_signs: Dict[str, List[str]] = {}
    lagna_sign: str = ""


class CanonicalReportData(BaseModel):
    """Complete data model for canonical PDF report."""
    
    report_type: str
    period_label: str
    generated_at: datetime
    
    birth_details: BirthDetails
    birth_reference: BirthReference
    
    chart_images: ChartImages
    
    core_life_themes: List[str]
    
    dasha_context: DashaContext
    transit_context: TransitContext
    nakshatra_timing: NakshatraTimingContext
    pakshi_rhythm: PakshiRhythmContext
    
    prediction_overview: str
    prediction_areas: List[PredictionArea]
    
    practices: List[str]
    
    closing_note: str
    closing_affirmation: Optional[str] = None
    
    llm_enhanced: bool = False
    
    monthly_theme: Optional[MonthlyTheme] = None
    overview_v2: Optional[Overview] = None
    practices_v2: Optional[PracticesAndReflection] = None
    closing_v2: Optional[Closing] = None
    is_v2: bool = False
