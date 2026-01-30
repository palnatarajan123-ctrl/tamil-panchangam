"""
Canonical PDF Report Builder - Data Loader

Loads ALL data from database/cache.
NEVER recalculates any astrological data.
Fails gracefully if required data is missing.
"""

import json
import hashlib
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import logging

from app.db.duckdb import get_conn
from app.pdf.charts.south_indian_svg import render_south_indian_chart_svg
from app.pdf.charts.chart_models import ChartSvgInput
from .models import (
    CanonicalReportData,
    BirthDetails,
    BirthReference,
    DashaContext,
    TransitContext,
    NakshatraTimingContext,
    PakshiRhythmContext,
    PredictionArea,
    SignalAttribution,
    ChartImages,
    MonthlyTheme,
    Overview,
    PracticesAndReflection,
    Closing,
)

logger = logging.getLogger(__name__)


class ReportDataNotFoundError(Exception):
    """Raised when required report data is missing."""
    pass


def _safe_json(value: Any, default: Any = None) -> Any:
    """Safely parse JSON if string, else return as-is."""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return default
    return default


def _generate_input_hash(base_chart_id: str, period_type: str, period_key: str) -> str:
    """Generate deterministic hash for caching."""
    data = f"{base_chart_id}:{period_type}:{period_key}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def load_base_chart(base_chart_id: str) -> Dict[str, Any]:
    """Load base chart from database."""
    with get_conn() as conn:
        result = conn.execute("""
            SELECT * FROM base_charts WHERE id = ?
        """, [base_chart_id]).fetchone()
        
        if not result:
            raise ReportDataNotFoundError(f"Base chart not found: {base_chart_id}")
        
        columns = [desc[0] for desc in conn.description]
        return dict(zip(columns, result))


def load_prediction(base_chart_id: str, year: int, month: int) -> Dict[str, Any]:
    """Load monthly prediction from database."""
    with get_conn() as conn:
        result = conn.execute("""
            SELECT * FROM monthly_predictions 
            WHERE base_chart_id = ? AND year = ? AND month = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, [base_chart_id, year, month]).fetchone()
        
        if not result:
            raise ReportDataNotFoundError(
                f"Prediction not found for {base_chart_id}/{year}/{month}"
            )
        
        columns = [desc[0] for desc in conn.description]
        return dict(zip(columns, result))


def load_yearly_prediction(base_chart_id: str, year: int) -> Dict[str, Any]:
    """Load yearly prediction from database."""
    with get_conn() as conn:
        result = conn.execute("""
            SELECT * FROM yearly_predictions 
            WHERE base_chart_id = ? AND year = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, [base_chart_id, year]).fetchone()
        
        if not result:
            raise ReportDataNotFoundError(
                f"Yearly prediction not found for {base_chart_id}/{year}"
            )
        
        columns = [desc[0] for desc in conn.description]
        return dict(zip(columns, result))


def load_cached_llm_interpretation(
    base_chart_id: str,
    period_type: str,
    period_key: str,
    feature_name: str = "prediction"
) -> Optional[Dict[str, Any]]:
    """Load cached LLM interpretation if available."""
    try:
        with get_conn() as conn:
            result = conn.execute("""
                SELECT content_json FROM prediction_llm_interpretation
                WHERE base_chart_id = ?
                AND period_type = ?
                AND period_key = ?
                AND feature_name = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, [base_chart_id, period_type, period_key, feature_name]).fetchone()
            
            if result and result[0]:
                return _safe_json(result[0], {})
    except Exception as e:
        logger.warning(f"Failed to load cached LLM interpretation: {e}")
    
    return None


def _convert_planet_to_sign_mapping(planet_signs: Dict[str, Any]) -> Dict[str, List[str]]:
    """Convert planet->sign mapping to sign->planets mapping for chart rendering."""
    signs_to_planets: Dict[str, list] = {}
    for planet, sign in planet_signs.items():
        if sign and isinstance(sign, str):
            if sign not in signs_to_planets:
                signs_to_planets[sign] = []
            signs_to_planets[sign].append(planet)
    return signs_to_planets


def _generate_chart_svg(planet_signs: Dict[str, Any], chart_type: str = "D1", title: str = "", lagna_sign: str = "") -> str:
    """Generate SVG chart and return as data URI."""
    try:
        signs_to_planets = _convert_planet_to_sign_mapping(planet_signs)
        
        chart_input = ChartSvgInput(
            chart_type=chart_type,
            planet_signs=signs_to_planets,
            title=title,
            lagna_sign=lagna_sign,
        )
        
        svg_content = render_south_indian_chart_svg(chart_input)
        import base64
        svg_b64 = base64.b64encode(svg_content.encode()).decode()
        return f"data:image/svg+xml;base64,{svg_b64}"
    except Exception as e:
        logger.error(f"Failed to generate chart SVG: {e}")
        return ""


def _extract_birth_reference(payload: Dict[str, Any]) -> BirthReference:
    """Extract birth reference data from parsed chart payload."""
    ephemeris = payload.get("ephemeris", {})
    moon_data = ephemeris.get("moon", {})
    lagna_data = ephemeris.get("lagna", {})
    nakshatra_data = moon_data.get("nakshatra", {})
    
    dashas = payload.get("dashas", {})
    vimshottari = dashas.get("vimshottari", {})
    current_dasha = vimshottari.get("current", {})
    
    nakshatra_lords = {
        "Ashwini": "Ketu", "Bharani": "Venus", "Krittika": "Sun",
        "Rohini": "Moon", "Mrigashira": "Mars", "Ardra": "Rahu",
        "Punarvasu": "Jupiter", "Pushya": "Saturn", "Ashlesha": "Mercury",
        "Magha": "Ketu", "Purva Phalguni": "Venus", "Uttara Phalguni": "Sun",
        "Hasta": "Moon", "Chitra": "Mars", "Swati": "Rahu",
        "Vishakha": "Jupiter", "Anuradha": "Saturn", "Jyeshtha": "Mercury",
        "Mula": "Ketu", "Purva Ashadha": "Venus", "Uttara Ashadha": "Sun",
        "Shravana": "Moon", "Dhanishta": "Mars", "Shatabhisha": "Rahu",
        "Purva Bhadrapada": "Jupiter", "Uttara Bhadrapada": "Saturn", "Revati": "Mercury",
    }
    
    nakshatra_name = nakshatra_data.get("name", "Unknown")
    nakshatra_lord = nakshatra_lords.get(nakshatra_name, "Unknown")
    
    starting_dasha = vimshottari.get("starting_dasha", "Unknown")
    
    return BirthReference(
        janma_nakshatra=nakshatra_name,
        janma_rasi=moon_data.get("rasi", "Unknown"),
        lagna=lagna_data.get("rasi", "Unknown"),
        moon_sign=moon_data.get("rasi", "Unknown"),
        nakshatra_lord=nakshatra_lord,
        birth_dasha=f"{starting_dasha} - {starting_dasha}",
        functional_role_planets={},
    )


def _extract_dasha_context(envelope: Dict[str, Any]) -> DashaContext:
    """Extract dasha context from prediction envelope."""
    dasha_ctx = envelope.get("dasha_context", {})
    active = dasha_ctx.get("active", {})
    maha = active.get("maha", {})
    antar = active.get("antar", {})
    
    maha_lord = dasha_ctx.get("maha_lord", maha.get("lord", "Unknown"))
    antar_lord = dasha_ctx.get("antar_lord", antar.get("lord", "Unknown"))
    
    maha_end = maha.get("end", "")
    balance = "Unknown"
    if maha_end:
        try:
            from datetime import datetime
            end_dt = datetime.fromisoformat(maha_end.replace("Z", "+00:00"))
            years_left = (end_dt - datetime.now(end_dt.tzinfo)).days / 365.25
            balance = f"{years_left:.1f} years remaining"
        except:
            pass
    
    functional_roles = envelope.get("functional_roles", {})
    summary = functional_roles.get("summary", {})
    benefics = summary.get("functional_benefics", [])
    malefics = summary.get("functional_malefics", [])
    
    return DashaContext(
        mahadasha=maha_lord,
        mahadasha_lord=maha_lord,
        antardasha=antar_lord,
        antardasha_lord=antar_lord,
        dasha_balance=balance,
        functional_benefics=benefics,
        functional_malefics=malefics,
    )


def _extract_transit_context(envelope: Dict[str, Any]) -> TransitContext:
    """Extract transit context from prediction envelope (gochara)."""
    gochara = envelope.get("gochara", {})
    
    jupiter = gochara.get("jupiter", {})
    saturn = gochara.get("saturn", {})
    rahu_ketu = gochara.get("rahu_ketu", {})
    
    jupiter_sign = jupiter.get("transit_rasi", "Unknown")
    saturn_sign = saturn.get("transit_rasi", "Unknown")
    rahu_sign = rahu_ketu.get("rahu_rasi", "Unknown")
    ketu_sign = rahu_ketu.get("ketu_rasi", "Unknown")
    
    return TransitContext(
        jupiter_transit=f"Jupiter in {jupiter_sign}",
        saturn_transit=f"Saturn in {saturn_sign}",
        rahu_ketu_axis=f"Rahu in {rahu_sign}, Ketu in {ketu_sign}",
    )


def _extract_nakshatra_timing(envelope: Dict[str, Any]) -> NakshatraTimingContext:
    """Extract nakshatra timing context."""
    nakshatra_ctx = envelope.get("nakshatra_context", {})
    if isinstance(nakshatra_ctx, str):
        nakshatra_ctx = {}
    
    chandra_gati = envelope.get("chandra_gati", {})
    if isinstance(chandra_gati, str):
        chandra_gati = {}
    
    tara_name = nakshatra_ctx.get("tara_name", nakshatra_ctx.get("tara_bala", "Neutral"))
    moon_nak = nakshatra_ctx.get("current_nakshatra", nakshatra_ctx.get("moon_nakshatra", "Unknown"))
    
    moods = chandra_gati.get("dominant_moods", [])
    gati_phase = ", ".join(moods[:2]) if moods else "Unknown"
    
    return NakshatraTimingContext(
        current_moon_nakshatra=moon_nak,
        tara_bala=tara_name,
        chandra_gati=gati_phase,
        favorable_window="Consult chart",
    )


def _extract_pakshi_rhythm(envelope: Dict[str, Any]) -> PakshiRhythmContext:
    """Extract pakshi rhythm context from biological_rhythm."""
    bio_rhythm = envelope.get("biological_rhythm", {})
    if isinstance(bio_rhythm, str):
        bio_rhythm = {}
    pakshi_daily = bio_rhythm.get("pancha_pakshi_daily", {})
    
    dominant = pakshi_daily.get("dominant_pakshi", "Unknown")
    activities = pakshi_daily.get("recommended_activities", [])
    activity_phase = activities[0] if activities else "Unknown"
    
    return PakshiRhythmContext(
        dominant_pakshi=dominant,
        activity_phase=activity_phase,
    )


def _extract_prediction_areas(
    interpretation: Dict[str, Any],
    llm_interpretation: Optional[Dict[str, Any]] = None
) -> Tuple[str, list, list, bool, Optional[Dict], Optional[Dict], Optional[Dict], Optional[Dict]]:
    """
    Extract prediction areas and practices from interpretation.
    
    Returns: (overview, areas, practices, is_v2, monthly_theme, overview_v2, practices_v2, closing_v2)
    """
    ai_interp = interpretation.get("ai_interpretation", {})
    
    llm_source = llm_interpretation if llm_interpretation else {}
    deterministic_source = ai_interp
    
    is_v2 = llm_source.get("engine_version") == "ai-interpretation-v2.0"
    
    if is_v2:
        overview_v2_data = llm_source.get("overview", {})
        overview = overview_v2_data.get("energy_pattern", "")
    else:
        window_summary = llm_source.get("window_summary", {})
        overview = (
            window_summary.get("overview", "") or 
            window_summary.get("summary", "") or 
            window_summary.get("narrative", "") or 
            llm_source.get("overview", "") or 
            llm_source.get("summary", "") or
            deterministic_source.get("window_summary", {}).get("overview", "")
        )
        overview_v2_data = None
    
    monthly_theme_data = llm_source.get("monthly_theme") if is_v2 else None
    practices_v2_data = llm_source.get("practices_and_reflection") if is_v2 else None
    closing_v2_data = llm_source.get("closing") if is_v2 else None
    
    llm_life_areas = llm_source.get("life_areas", {})
    det_life_areas = deterministic_source.get("life_areas", {})
    
    areas = []
    for area_name, det_area_data in det_life_areas.items():
        if not isinstance(det_area_data, dict):
            continue
        
        llm_area_data = llm_life_areas.get(area_name, {})
        if isinstance(llm_area_data, str):
            llm_area_data = {"interpretation": llm_area_data}
        
        interpretation_text = (
            llm_area_data.get("interpretation") or 
            llm_area_data.get("summary") or
            det_area_data.get("interpretation", det_area_data.get("summary", ""))
        )
        
        deeper_explanation = (
            llm_area_data.get("deeper_explanation") or
            det_area_data.get("deeper_explanation", "")
        )
        
        opportunity = llm_area_data.get("opportunity") if is_v2 else None
        watch_out = llm_area_data.get("watch_out") if is_v2 else None
        one_action = llm_area_data.get("one_action") if is_v2 else None
        
        attr_data = det_area_data.get("attribution", {})
        attribution = None
        if attr_data:
            signals_used = attr_data.get("signals_used", [])
            attribution = SignalAttribution(
                dasha=attr_data.get("dasha", ""),
                planets=attr_data.get("planets", []),
                engines=attr_data.get("engines", []),
                signals_count=len(signals_used) if isinstance(signals_used, list) else 0
            )
        
        areas.append(PredictionArea(
            area=area_name.replace("_", " ").title(),
            score=det_area_data.get("score", 50),
            outlook=det_area_data.get("outlook", "neutral"),
            interpretation=interpretation_text,
            deeper_explanation=deeper_explanation,
            guidance=llm_area_data.get("guidance") or det_area_data.get("guidance"),
            opportunity=opportunity,
            watch_out=watch_out,
            one_action=one_action,
            attribution=attribution
        ))
    
    practices = llm_source.get("practices", [])
    if not practices:
        practices = _generate_default_practices(areas)
    
    return overview, areas, practices, is_v2, monthly_theme_data, overview_v2_data, practices_v2_data, closing_v2_data


def _generate_default_practices(areas: list) -> List[str]:
    """Generate default practices based on life areas."""
    practices = []
    
    for area in areas:
        if area.score >= 65:
            if "career" in area.area.lower():
                practices.append("Leverage this favorable period for career initiatives and networking")
            elif "finance" in area.area.lower():
                practices.append("Consider strategic financial planning during this supportive window")
            elif "relationship" in area.area.lower():
                practices.append("Nurture important relationships through quality time together")
            elif "health" in area.area.lower():
                practices.append("Build on current vitality with sustainable wellness practices")
            elif "personal" in area.area.lower() or "growth" in area.area.lower():
                practices.append("Dedicate time to learning and spiritual development")
        elif area.score < 45:
            if "health" in area.area.lower():
                practices.append("Prioritize rest and stress management during this period")
    
    if not practices:
        practices = [
            "Begin each day with a moment of stillness and intention-setting",
            "Practice gratitude by noting three blessings each evening",
            "Spend time in nature to restore balance and perspective"
        ]
    
    return practices[:5]




def build_report_data(
    base_chart_id: str,
    report_type: str,
    year: int,
    month: Optional[int] = None,
) -> CanonicalReportData:
    """
    Build complete report data from database.
    
    This function ONLY reads from database.
    It NEVER recalculates any astrological data.
    """
    
    chart = load_base_chart(base_chart_id)
    
    if report_type == "monthly" and month:
        prediction = load_prediction(base_chart_id, year, month)
        period_key = f"{year}-{month:02d}"
        period_label = f"{datetime(year, month, 1).strftime('%B %Y')}"
    else:
        prediction = load_yearly_prediction(base_chart_id, year)
        period_key = str(year)
        period_label = str(year)
    
    payload = _safe_json(chart.get("payload"), {})
    envelope = _safe_json(prediction.get("envelope"), {})
    interpretation = _safe_json(prediction.get("interpretation"), {})
    
    llm_interpretation = load_cached_llm_interpretation(
        base_chart_id, report_type, period_key
    )
    
    ephemeris = payload.get("ephemeris", {})
    planets = ephemeris.get("planets", {})
    rasi_planet_signs = {planet: data.get("rasi", "") for planet, data in planets.items()}
    
    d9_data = payload.get("charts", {}).get("D9", {})
    navamsa_planet_signs = {planet: data.get("navamsa_sign", "") for planet, data in d9_data.items() if isinstance(data, dict)}
    
    lagna_data = ephemeris.get("lagna", {})
    lagna_sign = lagna_data.get("rasi", "") if isinstance(lagna_data, dict) else ""
    
    # D9 uses navamsa lagna if available, otherwise defaults to Mesham (index 0) like frontend
    d9_lagna_sign = lagna_data.get("navamsa_sign", "Mesham") if isinstance(lagna_data, dict) else "Mesham"
    
    (overview, prediction_areas, practices, is_v2, 
     monthly_theme_data, overview_v2_data, practices_v2_data, closing_v2_data) = _extract_prediction_areas(
        interpretation, llm_interpretation
    )
    
    birth_details_data = payload.get("birth_details", {})
    
    monthly_theme = None
    if monthly_theme_data:
        monthly_theme = MonthlyTheme(
            title=monthly_theme_data.get("title", ""),
            narrative=monthly_theme_data.get("narrative", "")
        )
    
    overview_v2 = None
    if overview_v2_data and isinstance(overview_v2_data, dict):
        overview_v2 = Overview(
            energy_pattern=overview_v2_data.get("energy_pattern", ""),
            key_focus=overview_v2_data.get("key_focus", []),
            avoid_or_be_mindful=overview_v2_data.get("avoid_or_be_mindful", [])
        )
    
    practices_v2 = None
    if practices_v2_data:
        practices_v2 = PracticesAndReflection(
            daily_practice=practices_v2_data.get("daily_practice"),
            weekly_practice=practices_v2_data.get("weekly_practice"),
            reflection_question=practices_v2_data.get("reflection_question")
        )
    
    closing_v2 = None
    if closing_v2_data:
        closing_v2 = Closing(
            key_takeaways=closing_v2_data.get("key_takeaways", []),
            encouragement=closing_v2_data.get("encouragement")
        )
    
    return CanonicalReportData(
        report_type=report_type.title(),
        period_label=period_label,
        generated_at=datetime.now(),
        
        birth_details=BirthDetails(
            name=birth_details_data.get("name", "Chart Holder"),
            date=birth_details_data.get("date_of_birth", "Unknown"),
            time=birth_details_data.get("time_of_birth", "Unknown"),
            place=birth_details_data.get("place_of_birth", "Unknown"),
        ),
        
        birth_reference=_extract_birth_reference(payload),
        
        chart_images=ChartImages(
            d1_rasi=_generate_chart_svg(rasi_planet_signs, "D1", "Rāsi Chart (D1)", lagna_sign),
            d9_navamsa=_generate_chart_svg(navamsa_planet_signs, "D9", "Navamsa Chart (D9)", d9_lagna_sign),
            d1_planet_signs=_convert_planet_to_sign_mapping(rasi_planet_signs),
            d9_planet_signs=_convert_planet_to_sign_mapping(navamsa_planet_signs),
            lagna_sign=lagna_sign,
        ),
        
        core_life_themes=interpretation.get("core_themes", []),
        
        dasha_context=_extract_dasha_context(envelope),
        transit_context=_extract_transit_context(envelope),
        nakshatra_timing=_extract_nakshatra_timing(envelope),
        pakshi_rhythm=_extract_pakshi_rhythm(envelope),
        
        prediction_overview=overview,
        prediction_areas=prediction_areas,
        
        practices=practices,
        
        closing_note=_generate_closing_note(prediction_areas),
        closing_affirmation=_generate_closing_affirmation(prediction_areas),
        
        llm_enhanced=llm_interpretation is not None,
        
        monthly_theme=monthly_theme,
        overview_v2=overview_v2,
        practices_v2=practices_v2,
        closing_v2=closing_v2,
        is_v2=is_v2,
    )


def _generate_closing_note(areas: list) -> str:
    """Generate contextual closing note based on prediction areas."""
    supportive_count = sum(1 for a in areas if a.score >= 65)
    watchful_count = sum(1 for a in areas if a.score < 45)
    
    if supportive_count >= 3:
        return (
            "This period carries supportive energies across multiple life areas. "
            "Trust in the flow while taking inspired action. "
            "May this guidance illuminate your path with clarity and purpose."
        )
    elif watchful_count >= 3:
        return (
            "This period invites patience and introspection. "
            "Challenges are teachers in disguise, offering opportunities for growth. "
            "May this guidance support your journey with resilience and wisdom."
        )
    else:
        return (
            "This period presents a balanced mix of opportunities and invitations for growth. "
            "Navigate with awareness, honoring both action and stillness. "
            "May this guidance illuminate your path with clarity and peace."
        )


def _generate_closing_affirmation(areas: list) -> str:
    """Generate closing affirmation."""
    return "The stars illuminate possibilities; your choices create your destiny."
