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
    functional_benefics: List[str] = []
    functional_malefics: List[str] = []


class TransitContext(BaseModel):
    """Transit/Gochara context."""
    jupiter_transit: str
    saturn_transit: str
    rahu_ketu_axis: str
    jupiter_rasi: str = ""
    saturn_rasi: str = ""
    jupiter_bindus: Optional[int] = None
    saturn_bindus: Optional[int] = None
    jupiter_drishti_bonus: Optional[float] = None
    saturn_drishti_bonus: Optional[float] = None


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


class SignalDetail(BaseModel):
    """Individual signal with full details."""
    engine: str
    direction: str  # "pos" or "neg"
    weight: float
    interpretive_hint: Optional[str] = None


class SignalAttribution(BaseModel):
    """Attribution data for a life area prediction."""
    dasha: str = ""
    planets: List[str] = []
    engines: List[str] = []
    signals_count: int = 0
    signals: List[SignalDetail] = []


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
    reflection_guidance: Optional[str] = None  # Guidance for the reflection question


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
    
    # Tier-1 divisional charts
    d2_hora: str = ""
    d7_saptamsa: str = ""
    d10_dasamsa: str = ""
    d2_planet_signs: Dict[str, List[str]] = {}
    d7_planet_signs: Dict[str, List[str]] = {}
    d10_planet_signs: Dict[str, List[str]] = {}


class MethodologyInfo(BaseModel):
    """Methodology and calculation confidence info."""
    ephemeris_source: str = "Swiss Ephemeris"
    ayanamsa: str = "Lahiri (Chitrapaksha)"
    node_type: str = "Mean Node"
    division_method: str = "Parashara"
    calculation_confidence: str = "high"
    cusp_cases: List[str] = []


class VedaRemedy(BaseModel):
    """V3 veda remedy / pariharam section."""
    primary_remedy: str
    supporting_practice: Optional[str] = None
    specific_remedies: List[str] = []


class V4Remedy(BaseModel):
    """Single v4 remedy entry."""
    name: str
    simple_practice: Optional[str] = None
    why: Optional[str] = None


class V4Remedies(BaseModel):
    """V4 remedies section."""
    primary: Optional[V4Remedy] = None
    supporting: List[V4Remedy] = []


class V4LifeArea(BaseModel):
    """V4 life area with plain-English content."""
    plain_english: str = ""
    do: List[str] = []
    avoid: List[str] = []
    real_life_patterns: List[str] = []
    astrological_basis: Optional[str] = None


class V4ExecutiveSummary(BaseModel):
    """V4 executive summary."""
    main_theme: str = ""
    one_lines: Dict[str, str] = {}
    strongest_area: Optional[str] = None
    watch_area: Optional[str] = None
    best_use: Optional[str] = None


class V4WhyThisPeriod(BaseModel):
    """V4 explanation of why this period feels the way it does."""
    dasha_plain: Optional[str] = None
    transit_plain: Optional[str] = None
    overlap_summary: Optional[str] = None
    supportive: List[str] = []
    watchouts: List[str] = []


class V4CautionWindow(BaseModel):
    """V4 caution window."""
    period: str = ""
    concern: Optional[str] = None
    action: Optional[str] = None


class KpSublordsData(BaseModel):
    """KP Sub-lord data for PDF rendering. Only present for KP charts."""
    entries: List[Dict[str, Any]] = []  # list of {planet, longitude, star_lord, sub_lord, sub_sub_lord}


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
    
    yearly_mantra: Optional[str] = None
    dasha_transit_synthesis: Optional[str] = None
    danger_windows: List[str] = []
    veda_remedy: Optional[VedaRemedy] = None
    closing_v3: Optional[Closing] = None
    is_v3: bool = False
    
    methodology: Optional[MethodologyInfo] = None
    sarvashtakavarga: Optional[Dict[str, int]] = None
    yogas_data: Optional[Dict[str, Any]] = None
    sade_sati_data: Optional[Dict[str, Any]] = None
    shadbala_data: Optional[Dict[str, Any]] = None
    kp_sublords: Optional[KpSublordsData] = None

    is_v4: bool = False
    v4_executive_summary: Optional[V4ExecutiveSummary] = None
    v4_why_this_period: Optional[V4WhyThisPeriod] = None
    v4_life_areas: Optional[Dict[str, V4LifeArea]] = None
    v4_remedies: Optional[V4Remedies] = None
    v4_caution_windows: List[V4CautionWindow] = []
    v4_key_takeaways: List[str] = []
