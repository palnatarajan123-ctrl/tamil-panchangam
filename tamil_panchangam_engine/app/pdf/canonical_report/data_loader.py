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

from app.db.postgres import get_conn
from app.pdf.charts.south_indian_svg import render_south_indian_chart_svg
from app.pdf.charts.chart_models import ChartSvgInput
from app.engines.corner_case_detector import assess_calculation_confidence
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
    VedaRemedy,
    MethodologyInfo,
    KpSublordsData,
    V4ExecutiveSummary,
    V4WhyThisPeriod,
    V4LifeArea,
    V4Remedy,
    V4Remedies,
    V4CautionWindow,
    NatalWhoYouAre,
    NatalWhereYouShine,
    NatalRelationships,
    NatalCurrentChapter,
    NatalDecade,
)

logger = logging.getLogger(__name__)

_AYANAMSA_LABELS = {
    "lahiri": "Lahiri (Chitrapaksha)",
    "kp": "KP (Krishnamurti)",
}


def _ayanamsa_label(raw: str) -> str:
    return _AYANAMSA_LABELS.get(str(raw).lower(), raw)


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
                SELECT content_json, reflection_text FROM prediction_llm_interpretation
                WHERE base_chart_id = ?
                AND period_type = ?
                AND period_key = ?
                AND feature_name = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, [base_chart_id, period_type, period_key, feature_name]).fetchone()
            
            if result and result[0]:
                content = _safe_json(result[0], {})
                # FIX 3: Inject stored reflection_text into response
                if result[1]:  # reflection_text column
                    # Ensure practices_and_reflection has the stored text
                    if "practices_and_reflection" not in content:
                        content["practices_and_reflection"] = {}
                    content["practices_and_reflection"]["reflection_guidance"] = result[1]
                return content
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


def _bindu_label(bindus: int) -> str:
    """Human-readable bindu strength label."""
    if bindus >= 7:
        return "Very Strong"
    if bindus >= 5:
        return "Strong"
    if bindus >= 3:
        return "Moderate"
    return "Very Weak"


def _extract_transit_context(envelope: Dict[str, Any]) -> TransitContext:
    """Extract transit context from prediction envelope (gochara)."""
    gochara = envelope.get("gochara", {})
    ashtakavarga = envelope.get("ashtakavarga", {})

    jupiter = gochara.get("jupiter", {})
    saturn = gochara.get("saturn", {})
    rahu_ketu = gochara.get("rahu_ketu", {})

    jupiter_sign = jupiter.get("transit_rasi", "Unknown")
    saturn_sign = saturn.get("transit_rasi", "Unknown")
    rahu_sign = rahu_ketu.get("rahu_rasi", "Unknown")
    ketu_sign = rahu_ketu.get("ketu_rasi", "Unknown")

    jup_av = ashtakavarga.get("jupiter", {})
    sat_av = ashtakavarga.get("saturn", {})
    jup_bindus = jup_av.get("bindus") if jup_av.get("bindus") is not None else jup_av.get("bindu")
    sat_bindus = sat_av.get("bindus") if sat_av.get("bindus") is not None else sat_av.get("bindu")
    jup_drishti_bonus = jupiter.get("drishti_aspect_bonus")
    sat_drishti_bonus = saturn.get("drishti_aspect_bonus")

    def _phase_label(d: dict, phase_key: str = "phase") -> str:
        phase = d.get(phase_key, "")
        retro = d.get("is_retrograde", False)
        suffix = ""
        if phase == "entering":
            suffix = " (Entering)"
        elif phase == "exiting":
            suffix = " (Exiting)"
        if retro:
            suffix += " [R]"
        return suffix

    def _bindu_suffix(bindus) -> str:
        if bindus is None:
            return ""
        return f" — {bindus}/8 bindus ({_bindu_label(bindus)})"

    return TransitContext(
        jupiter_transit=f"Jupiter in {jupiter_sign}{_phase_label(jupiter)}{_bindu_suffix(jup_bindus)}",
        saturn_transit=f"Saturn in {saturn_sign}{_phase_label(saturn, 'transit_phase')}{_bindu_suffix(sat_bindus)}",
        rahu_ketu_axis=f"Rahu in {rahu_sign}{_phase_label(rahu_ketu, 'rahu_phase')}, Ketu in {ketu_sign}{_phase_label(rahu_ketu, 'ketu_phase')}",
        jupiter_rasi=jupiter_sign,
        saturn_rasi=saturn_sign,
        jupiter_bindus=jup_bindus,
        saturn_bindus=sat_bindus,
        jupiter_drishti_bonus=jup_drishti_bonus,
        saturn_drishti_bonus=sat_drishti_bonus,
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
    
    Note: v3 fields (yearly_mantra, dasha_transit_synthesis, danger_windows, veda_remedy, closing_v3)
    are extracted separately in build_report_data since this function signature is preserved for v1/v2 compat.
    """
    ai_interp = interpretation.get("ai_interpretation", {})
    
    llm_source = llm_interpretation if llm_interpretation else {}
    deterministic_source = ai_interp
    
    engine_version = llm_source.get("engine_version", "")
    is_v2 = engine_version == "ai-interpretation-v2.0"
    is_v3 = engine_version == "ai-interpretation-v3.0"
    
    if is_v3:
        overview = llm_source.get("dasha_transit_synthesis", "")
        overview_v2_data = None
    elif is_v2:
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
    closing_v2_data = llm_source.get("closing") if (is_v2 and not is_v3) else None
    
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

        if area_name == "career":
            source_label = "llm" if (llm_area_data.get("interpretation") or llm_area_data.get("summary")) else "deterministic"
            logger.debug(f"PDF career text source={source_label} preview={repr(interpretation_text[:100])}")
        
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
            from .models import SignalDetail
            parsed_signals = []
            if isinstance(signals_used, list):
                for sig in signals_used:
                    if isinstance(sig, dict):
                        sig_weight = sig.get("strength") or sig.get("weight") or 0
                        parsed_signals.append(SignalDetail(
                            engine=sig.get("key") or sig.get("engine") or "Unknown",
                            direction="pos" if sig_weight >= 0 else "neg",
                            weight=sig_weight,
                            interpretive_hint=sig.get("interpretive_hint") or sig.get("rationale") or None,
                        ))
            attribution = SignalAttribution(
                dasha=attr_data.get("dasha", ""),
                planets=attr_data.get("planets", []),
                engines=attr_data.get("engines", []),
                signals_count=len(parsed_signals),
                signals=parsed_signals
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
    
    # First try cached LLM interpretation table
    llm_interpretation = load_cached_llm_interpretation(
        base_chart_id, report_type, period_key
    )
    
    # Fallback: extract from interpretation column (yearly/weekly store it there)
    if not llm_interpretation:
        llm_interpretation = interpretation.get("llm_interpretation", {})
    
    ephemeris = payload.get("ephemeris", {})
    planets = ephemeris.get("planets", {})
    rasi_planet_signs = {planet: data.get("rasi", "") for planet, data in planets.items()}
    
    d9_data = payload.get("charts", {}).get("D9", {})
    navamsa_planet_signs = {planet: data.get("navamsa_sign", "") for planet, data in d9_data.items() if isinstance(data, dict)}
    
    lagna_data = ephemeris.get("lagna", {})
    lagna_sign = lagna_data.get("rasi", "") if isinstance(lagna_data, dict) else ""
    
    # D9 uses navamsa lagna if available, otherwise defaults to Mesham (index 0) like frontend
    d9_lagna_sign = lagna_data.get("navamsa_sign", "Mesham") if isinstance(lagna_data, dict) else "Mesham"
    
    # Extract Tier-1 divisional charts (D2, D7, D10)
    divisional_charts = payload.get("divisional_charts", {})
    
    d2_data = divisional_charts.get("D2", {}).get("planets", {})
    d2_planet_signs = {planet: data.get("sign", "") for planet, data in d2_data.items() if isinstance(data, dict)}
    
    d7_data = divisional_charts.get("D7", {}).get("planets", {})
    d7_planet_signs = {planet: data.get("sign", "") for planet, data in d7_data.items() if isinstance(data, dict)}
    
    d10_data = divisional_charts.get("D10", {}).get("planets", {})
    d10_planet_signs = {planet: data.get("sign", "") for planet, data in d10_data.items() if isinstance(data, dict)}
    
    # Methodology info from chart metadata + calculation confidence
    chart_metadata = payload.get("chart_metadata", {})
    
    # Assess calculation confidence using corner case detector
    try:
        confidence_result = assess_calculation_confidence(ephemeris)
        calc_confidence = confidence_result.get("level", "high")
        cusp_cases = [
            f"{c['planet']} ({c['position']} of sign)" 
            for c in confidence_result.get("cusp_cases", [])
        ]
    except Exception as e:
        logger.warning(f"Failed to assess calculation confidence: {e}")
        calc_confidence = "high"
        cusp_cases = []
    
    methodology = MethodologyInfo(
        ephemeris_source="Swiss Ephemeris",
        ayanamsa=chart_metadata.get("ayanamsa", "Lahiri (Chitrapaksha)"),
        node_type=chart_metadata.get("node_type", "Mean Node"),
        division_method=chart_metadata.get("division_method", "Parashara"),
        calculation_confidence=calc_confidence,
        cusp_cases=cusp_cases,
    )
    
    (overview, prediction_areas, practices, is_v2, 
     monthly_theme_data, overview_v2_data, practices_v2_data, closing_v2_data) = _extract_prediction_areas(
        interpretation, llm_interpretation
    )
    
    llm_src = llm_interpretation if llm_interpretation else {}
    is_v3 = llm_src.get("engine_version") == "ai-interpretation-v3.0"
    is_v4 = llm_src.get("engine_version") == "ai-interpretation-v4.0"
    
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
            reflection_question=practices_v2_data.get("reflection_question"),
            reflection_guidance=practices_v2_data.get("reflection_guidance")
        )
    
    closing_v2 = None
    if closing_v2_data:
        closing_v2 = Closing(
            key_takeaways=closing_v2_data.get("key_takeaways", []),
            encouragement=closing_v2_data.get("encouragement")
        )
    
    # v4 fields
    v4_executive_summary_obj = None
    v4_why_this_period_obj = None
    v4_life_areas_obj = None
    v4_remedies_obj = None
    v4_caution_windows_list: List[V4CautionWindow] = []
    v4_key_takeaways_list: List[str] = []

    if is_v4:
        exec_data = llm_src.get("executive_summary")
        if exec_data and isinstance(exec_data, dict):
            v4_executive_summary_obj = V4ExecutiveSummary(
                main_theme=exec_data.get("main_theme", ""),
                one_lines=exec_data.get("one_lines", {}),
                strongest_area=exec_data.get("strongest_area"),
                watch_area=exec_data.get("watch_area"),
                best_use=exec_data.get("best_use"),
            )

        why_data = llm_src.get("why_this_period")
        if why_data and isinstance(why_data, dict):
            v4_why_this_period_obj = V4WhyThisPeriod(
                dasha_plain=why_data.get("dasha_plain"),
                transit_plain=why_data.get("transit_plain"),
                overlap_summary=why_data.get("overlap_summary"),
                supportive=why_data.get("supportive", []),
                watchouts=why_data.get("watchouts", []),
            )

        life_areas_raw = llm_src.get("life_areas")
        if life_areas_raw and isinstance(life_areas_raw, dict):
            v4_life_areas_obj = {
                area: V4LifeArea(
                    plain_english=area_data.get("plain_english", ""),
                    do=area_data.get("do", []),
                    avoid=area_data.get("avoid", []),
                    real_life_patterns=area_data.get("real_life_patterns", ""),
                    astrological_basis=area_data.get("astrological_basis"),
                )
                for area, area_data in life_areas_raw.items()
                if isinstance(area_data, dict)
            }

        remedies_raw = llm_src.get("remedies")
        if remedies_raw and isinstance(remedies_raw, dict):
            primary_raw = remedies_raw.get("primary")
            primary_obj = None
            if primary_raw and isinstance(primary_raw, dict):
                primary_obj = V4Remedy(
                    name=primary_raw.get("name", ""),
                    simple_practice=primary_raw.get("simple_practice"),
                    why=primary_raw.get("why"),
                )
            supporting_list = []
            for sup in remedies_raw.get("supporting", []):
                if isinstance(sup, dict):
                    supporting_list.append(V4Remedy(
                        name=sup.get("name", ""),
                        simple_practice=sup.get("simple_practice"),
                        why=sup.get("why"),
                    ))
            v4_remedies_obj = V4Remedies(primary=primary_obj, supporting=supporting_list)

        for cw in llm_src.get("caution_windows", []):
            if isinstance(cw, dict):
                v4_caution_windows_list.append(V4CautionWindow(
                    period=cw.get("period", ""),
                    concern=cw.get("concern"),
                    action=cw.get("action"),
                ))

        v4_key_takeaways_list = llm_src.get("key_takeaways", [])

    yearly_mantra = None
    dasha_transit_synthesis = None
    danger_windows_list: List[str] = []
    veda_remedy_obj = None
    closing_v3 = None

    if is_v3:
        yearly_mantra = llm_src.get("yearly_mantra")
        dasha_transit_synthesis = llm_src.get("dasha_transit_synthesis")
        danger_windows_list = llm_src.get("danger_windows", [])
        
        veda_data = llm_src.get("veda_remedy")
        if veda_data and isinstance(veda_data, dict):
            veda_remedy_obj = VedaRemedy(
                primary_remedy=veda_data.get("primary_remedy", ""),
                supporting_practice=veda_data.get("supporting_practice"),
                specific_remedies=veda_data.get("specific_remedies", [])
            )
        
        closing_v3_data = llm_src.get("closing")
        if closing_v3_data and isinstance(closing_v3_data, dict):
            closing_v3 = Closing(
                key_takeaways=closing_v3_data.get("key_takeaways", []),
                encouragement=closing_v3_data.get("encouragement")
            )
    
    av_raw = envelope.get("ashtakavarga", {})
    sarvashtakavarga: Optional[Dict[str, int]] = av_raw.get("sarvashtakavarga") if isinstance(av_raw, dict) else None

    # Yogas — from prediction envelope (computed at prediction time)
    yogas_raw = envelope.get("yogas")
    yogas_data = yogas_raw if isinstance(yogas_raw, dict) else None

    # Sade Sati — from prediction envelope (computed at prediction time)
    sade_sati_raw = envelope.get("sade_sati")
    sade_sati_data = sade_sati_raw if isinstance(sade_sati_raw, dict) else None

    # Shadbala — from prediction envelope (computed at prediction time)
    shadbala_raw = envelope.get("shadbala")
    shadbala_data = shadbala_raw if isinstance(shadbala_raw, dict) else None

    # KP Sub-lords (only for KP charts)
    kp_sublords_data = None
    raw_kp = payload.get("kp_sublords")
    if raw_kp and isinstance(raw_kp, dict):
        KP_ORDER = ["Lagna", "Sun", "Moon", "Mars", "Mercury",
                    "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        kp_entries = []
        for planet in KP_ORDER:
            if planet in raw_kp:
                e = raw_kp[planet]
                kp_entries.append({
                    "planet": planet,
                    "longitude": round(e.get("longitude", 0), 2),
                    "star_lord": e.get("star_lord", ""),
                    "sub_lord": e.get("sub_lord", ""),
                    "sub_sub_lord": e.get("sub_sub_lord", ""),
                })
        if kp_entries:
            kp_sublords_data = KpSublordsData(entries=kp_entries)

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
            d1_rasi=_generate_chart_svg(rasi_planet_signs, "D1", "Rasi Chart (D1)", lagna_sign),
            d9_navamsa=_generate_chart_svg(navamsa_planet_signs, "D9", "Navamsa Chart (D9)", d9_lagna_sign),
            d1_planet_signs=_convert_planet_to_sign_mapping(rasi_planet_signs),
            d9_planet_signs=_convert_planet_to_sign_mapping(navamsa_planet_signs),
            lagna_sign=lagna_sign,
            d2_hora=_generate_chart_svg(d2_planet_signs, "D2", "Hora (D2)", "") if d2_planet_signs else "",
            d7_saptamsa=_generate_chart_svg(d7_planet_signs, "D7", "Saptamsa (D7)", "") if d7_planet_signs else "",
            d10_dasamsa=_generate_chart_svg(d10_planet_signs, "D10", "Dasamsa (D10)", "") if d10_planet_signs else "",
            d2_planet_signs=_convert_planet_to_sign_mapping(d2_planet_signs),
            d7_planet_signs=_convert_planet_to_sign_mapping(d7_planet_signs),
            d10_planet_signs=_convert_planet_to_sign_mapping(d10_planet_signs),
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
        
        yearly_mantra=yearly_mantra,
        dasha_transit_synthesis=dasha_transit_synthesis,
        danger_windows=danger_windows_list,
        veda_remedy=veda_remedy_obj,
        closing_v3=closing_v3,
        is_v3=is_v3,

        is_v4=is_v4,
        v4_executive_summary=v4_executive_summary_obj,
        v4_why_this_period=v4_why_this_period_obj,
        v4_life_areas=v4_life_areas_obj,
        v4_remedies=v4_remedies_obj,
        v4_caution_windows=v4_caution_windows_list,
        v4_key_takeaways=v4_key_takeaways_list,

        methodology=methodology,
        sarvashtakavarga=sarvashtakavarga,
        yogas_data=yogas_data,
        sade_sati_data=sade_sati_data,
        shadbala_data=shadbala_data,
        kp_sublords=kp_sublords_data,
    )


def load_natal_interpretation(base_chart_id: str) -> Optional[Dict[str, Any]]:
    """Load cached natal LLM interpretation."""
    return load_cached_llm_interpretation(
        base_chart_id, "natal", "natal", "natal_interpretation"
    )


def _extract_dasha_context_from_payload(payload: Dict[str, Any]) -> DashaContext:
    """Extract current dasha context directly from chart payload (no prediction envelope needed)."""
    dashas = payload.get("dashas", {})
    vimshottari = dashas.get("vimshottari", {})
    current = vimshottari.get("current", {}) or {}

    maha_lord = current.get("lord", "Unknown")
    antar = current.get("antar", {}) or {}
    antar_lord = antar.get("lord", "Unknown")

    maha_end = current.get("end", "")
    balance = "Unknown"
    if maha_end:
        try:
            end_dt = datetime.fromisoformat(maha_end.replace("Z", "+00:00"))
            years_left = (end_dt - datetime.now(end_dt.tzinfo)).days / 365.25
            balance = f"{years_left:.1f} years remaining"
        except Exception:
            pass

    return DashaContext(
        mahadasha=maha_lord,
        mahadasha_lord=maha_lord,
        antardasha=antar_lord,
        antardasha_lord=antar_lord,
        dasha_balance=balance,
    )


def build_birth_chart_report_data(base_chart_id: str) -> CanonicalReportData:
    """
    Build report data for a birth-chart-only PDF.

    No prediction required — uses only base chart data from DB plus
    the cached natal AI interpretation (if available).
    """
    chart = load_base_chart(base_chart_id)
    payload = _safe_json(chart.get("payload"), {})

    ephemeris = payload.get("ephemeris", {})
    planets = ephemeris.get("planets", {})
    rasi_planet_signs = {planet: data.get("rasi", "") for planet, data in planets.items()}

    d9_data = payload.get("charts", {}).get("D9", {})
    navamsa_planet_signs = {
        planet: data.get("navamsa_sign", "")
        for planet, data in d9_data.items()
        if isinstance(data, dict)
    }

    lagna_data = ephemeris.get("lagna", {})
    lagna_sign = lagna_data.get("rasi", "") if isinstance(lagna_data, dict) else ""
    d9_lagna_sign = lagna_data.get("navamsa_sign", "Mesham") if isinstance(lagna_data, dict) else "Mesham"

    divisional_charts = payload.get("divisional_charts", {})
    d2_data = divisional_charts.get("D2", {}).get("planets", {})
    d2_planet_signs = {planet: data.get("sign", "") for planet, data in d2_data.items() if isinstance(data, dict)}
    d7_data = divisional_charts.get("D7", {}).get("planets", {})
    d7_planet_signs = {planet: data.get("sign", "") for planet, data in d7_data.items() if isinstance(data, dict)}
    d10_data = divisional_charts.get("D10", {}).get("planets", {})
    d10_planet_signs = {planet: data.get("sign", "") for planet, data in d10_data.items() if isinstance(data, dict)}

    # Yogas / Sade Sati / Shadbala live in the payload for birth chart context
    yogas_raw = payload.get("yogas")
    sade_sati_raw = payload.get("sade_sati")
    shadbala_raw = payload.get("shadbala")

    # KP Sub-lords (only for KP charts)
    kp_sublords_data = None
    raw_kp = payload.get("kp_sublords")
    if raw_kp and isinstance(raw_kp, dict):
        KP_ORDER = ["Lagna", "Sun", "Moon", "Mars", "Mercury",
                    "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        kp_entries = []
        for planet in KP_ORDER:
            if planet in raw_kp:
                e = raw_kp[planet]
                kp_entries.append({
                    "planet": planet,
                    "longitude": round(e.get("longitude", 0), 2),
                    "star_lord": e.get("star_lord", ""),
                    "sub_lord": e.get("sub_lord", ""),
                    "sub_sub_lord": e.get("sub_sub_lord", ""),
                })
        if kp_entries:
            kp_sublords_data = KpSublordsData(entries=kp_entries)

    birth_details_data = payload.get("birth_details", {})
    chart_metadata = payload.get("chart_metadata", {})

    # ── Live astrological context ────────────────────────────────────────────
    from app.engines.gochara_engine import compute_gochara
    from app.engines.nakshatra_engine import compute_nakshatra_context
    from app.utils.time_utils import get_month_reference_date_utc
    from datetime import datetime as dt

    ayanamsa = ephemeris.get("ayanamsa", "lahiri")
    birth_details_raw = payload.get("birth_details", {})
    latitude = birth_details_raw.get("latitude", 0.0)
    longitude_coord = birth_details_raw.get("longitude", 0.0)
    natal_moon_rasi = ephemeris.get("moon", {}).get("rasi", "")
    natal_lagna_rasi = ephemeris.get("lagna", {}).get("rasi", "")
    natal_moon_longitude = ephemeris.get("moon", {}).get("longitude_deg", 0.0)

    now = dt.utcnow()
    reference_date = get_month_reference_date_utc(now.year, now.month)

    # Gochara (transits)
    try:
        gochara = compute_gochara(
            reference_date_utc=reference_date,
            latitude=latitude,
            longitude=longitude_coord,
            natal_moon_rasi=natal_moon_rasi,
            natal_lagna_rasi=natal_lagna_rasi,
            natal_moon_longitude=natal_moon_longitude,
            ayanamsa=ayanamsa,
        )
        jup = gochara.get("jupiter", {})
        sat = gochara.get("saturn", {})
        rahu_ketu = gochara.get("rahu_ketu", {})
        jupiter_transit = f"{jup.get('transit_rasi', '')} (H{jup.get('from_moon_house', '')}) - {jup.get('effect', '')}"
        saturn_transit = f"{sat.get('transit_rasi', '')} (H{sat.get('from_moon_house', '')})"
        rahu_ketu_axis_str = f"Rahu H{rahu_ketu.get('rahu_from_moon_house', '')} / Ketu H{rahu_ketu.get('ketu_from_moon_house', '')}"
        live_transit_context = TransitContext(
            jupiter_transit=jupiter_transit,
            saturn_transit=saturn_transit,
            rahu_ketu_axis=rahu_ketu_axis_str,
            jupiter_rasi=jup.get("transit_rasi", ""),
            saturn_rasi=sat.get("transit_rasi", ""),
        )
    except Exception as e:
        logger.warning(f"Failed to compute gochara for natal PDF: {e}")
        live_transit_context = TransitContext(
            jupiter_transit="", saturn_transit="", rahu_ketu_axis=""
        )

    # Nakshatra context
    try:
        nak_context = compute_nakshatra_context(
            reference_date_utc=reference_date,
            birth_moon_longitude=natal_moon_longitude,
            ayanamsa=ayanamsa,
        )
        quality = nak_context.get("quality", "neutral")
        live_nakshatra = NakshatraTimingContext(
            current_moon_nakshatra=nak_context.get("current_nakshatra", ""),
            tara_bala=nak_context.get("tara_name", ""),
            chandra_gati=quality,
            favorable_window="Auspicious period" if quality in ("beneficial", "very_beneficial") else "Neutral / Watchful period",
        )
    except Exception as e:
        logger.warning(f"Failed to compute nakshatra context for natal PDF: {e}")
        live_nakshatra = NakshatraTimingContext(
            current_moon_nakshatra="", tara_bala="", chandra_gati="", favorable_window=""
        )

    # Pakshi context (static from birth data, no live computation needed)
    try:
        birth_pakshi = payload.get("pancha_pakshi_birth", {})
        pakshi_name = birth_pakshi.get("pakshi", "") if isinstance(birth_pakshi, dict) else ""
        pakshi_activity = birth_pakshi.get("nature", "") if isinstance(birth_pakshi, dict) else ""
        live_pakshi = PakshiRhythmContext(
            dominant_pakshi=pakshi_name,
            activity_phase=pakshi_activity,
        )
    except Exception as e:
        logger.warning(f"Failed to extract pakshi for natal PDF: {e}")
        live_pakshi = PakshiRhythmContext(dominant_pakshi="", activity_phase="")

    # ── Natal LLM interpretation ─────────────────────────────────────────────
    natal_interp = load_natal_interpretation(base_chart_id)
    natal_prediction_overview = ""
    natal_prediction_areas: List[PredictionArea] = []
    natal_closing_note = ""
    natal_llm_enhanced = False

    # natal v2 fields
    is_natal_v2 = False
    natal_who_you_are_obj = None
    natal_where_you_shine_obj = None
    natal_relationships_obj = None
    natal_current_chapter_obj = None
    natal_life_by_decade_list: List[NatalDecade] = []
    natal_dasha_life_map_list: List[dict] = []

    if natal_interp:
        natal_llm_enhanced = True
        life_theme = natal_interp.get("life_theme", {})
        chart_highlights = natal_interp.get("chart_highlights", {})

        # Overview from life_theme narrative
        if isinstance(life_theme, dict):
            natal_prediction_overview = life_theme.get("narrative", "")

        # Life area predictions
        life_areas_raw = natal_interp.get("life_areas", {})
        if isinstance(life_areas_raw, dict):
            area_label_map = {
                "career": "Career & Purpose",
                "wealth": "Wealth & Resources",
                "relationships": "Relationships",
                "health": "Health & Vitality",
                "spirituality": "Spirituality & Moksha",
            }
            for area_key, label in area_label_map.items():
                area_data = life_areas_raw.get(area_key)
                if not area_data:
                    continue
                if isinstance(area_data, str):
                    natal_prediction_areas.append(PredictionArea(
                        area=label,
                        score=50,
                        outlook="neutral",
                        interpretation=area_data,
                    ))
                elif isinstance(area_data, dict) and area_data.get("interpretation"):
                    natal_prediction_areas.append(PredictionArea(
                        area=label,
                        score=area_data.get("score", 50),
                        outlook=area_data.get("outlook", "neutral"),
                        interpretation=area_data.get("interpretation", ""),
                        deeper_explanation=area_data.get("deeper_explanation"),
                    ))

        # Closing note
        closing_wisdom = natal_interp.get("closing_wisdom")
        closing_raw = natal_interp.get("closing_blessing", natal_interp.get("closing", {}))
        if closing_wisdom and isinstance(closing_wisdom, str):
            natal_closing_note = closing_wisdom
        elif isinstance(closing_raw, dict):
            natal_closing_note = closing_raw.get("blessing", closing_raw.get("encouragement", ""))
        elif isinstance(closing_raw, str):
            natal_closing_note = closing_raw

        # natal v2 population
        natal_engine = natal_interp.get("engine_version", "")
        if natal_engine == "natal-v2.0":
            is_natal_v2 = True

            wya = natal_interp.get("who_you_are", {})
            if wya:
                natal_who_you_are_obj = NatalWhoYouAre(
                    core_identity=wya.get("core_identity", ""),
                    in_one_line=wya.get("in_one_line", ""),
                    core_strengths=wya.get("core_strengths", []),
                    growth_edges=wya.get("growth_edges", []),
                    central_tension=wya.get("central_tension", ""),
                )

            wys = natal_interp.get("where_you_shine", {})
            if wys:
                natal_where_you_shine_obj = NatalWhereYouShine(
                    natural_domains=wys.get("natural_domains", []),
                    why=wys.get("why", ""),
                    working_style=wys.get("working_style", ""),
                )

            raf = natal_interp.get("relationships_and_family", {})
            if raf:
                natal_relationships_obj = NatalRelationships(
                    partnership_nature=raf.get("partnership_nature", ""),
                    marriage_windows=raf.get("marriage_windows", ""),
                    children_indication=raf.get("children_indication", ""),
                    family_dynamics=raf.get("family_dynamics", ""),
                )

            cc = natal_interp.get("current_chapter", {})
            if cc:
                natal_current_chapter_obj = NatalCurrentChapter(
                    dasha_now=cc.get("dasha_now", ""),
                    what_this_means=cc.get("what_this_means", ""),
                    focus_for_now=cc.get("focus_for_now", ""),
                )

            for d in natal_interp.get("life_by_decade", []):
                if isinstance(d, dict):
                    natal_life_by_decade_list.append(NatalDecade(
                        age_range=d.get("age_range", ""),
                        theme=d.get("theme", ""),
                        key_focus=d.get("key_focus", ""),
                        dasha_context=d.get("dasha_context", ""),
                    ))

            dasha_map = natal_interp.get("dasha_life_map", [])
            if isinstance(dasha_map, list):
                natal_dasha_life_map_list = [
                    e for e in dasha_map
                    if isinstance(e, dict)
                ]

    try:
        confidence_result = assess_calculation_confidence(ephemeris)
        calc_confidence = confidence_result.get("level", "high")
        cusp_cases = [
            f"{c['planet']} ({c['position']} of sign)"
            for c in confidence_result.get("cusp_cases", [])
        ]
    except Exception as e:
        logger.warning(f"Failed to assess calculation confidence: {e}")
        calc_confidence = "high"
        cusp_cases = []

    return CanonicalReportData(
        report_type="Natal",
        period_label="Natal Chart",
        generated_at=datetime.now(),
        birth_details=BirthDetails(
            name=birth_details_data.get("name", "Chart Holder"),
            date=birth_details_data.get("date_of_birth", "Unknown"),
            time=birth_details_data.get("time_of_birth", "Unknown"),
            place=birth_details_data.get("place_of_birth", "Unknown"),
        ),
        birth_reference=_extract_birth_reference(payload),
        chart_images=ChartImages(
            d1_rasi=_generate_chart_svg(rasi_planet_signs, "D1", "Rasi Chart (D1)", lagna_sign),
            d9_navamsa=_generate_chart_svg(navamsa_planet_signs, "D9", "Navamsa Chart (D9)", d9_lagna_sign),
            d1_planet_signs=_convert_planet_to_sign_mapping(rasi_planet_signs),
            d9_planet_signs=_convert_planet_to_sign_mapping(navamsa_planet_signs),
            lagna_sign=lagna_sign,
            d2_hora=_generate_chart_svg(d2_planet_signs, "D2", "Hora (D2)", "") if d2_planet_signs else "",
            d7_saptamsa=_generate_chart_svg(d7_planet_signs, "D7", "Saptamsa (D7)", "") if d7_planet_signs else "",
            d10_dasamsa=_generate_chart_svg(d10_planet_signs, "D10", "Dasamsa (D10)", "") if d10_planet_signs else "",
            d2_planet_signs=_convert_planet_to_sign_mapping(d2_planet_signs),
            d7_planet_signs=_convert_planet_to_sign_mapping(d7_planet_signs),
            d10_planet_signs=_convert_planet_to_sign_mapping(d10_planet_signs),
        ),
        core_life_themes=[],
        dasha_context=_extract_dasha_context_from_payload(payload),
        transit_context=live_transit_context,
        nakshatra_timing=live_nakshatra,
        pakshi_rhythm=live_pakshi,
        prediction_overview=natal_prediction_overview,
        prediction_areas=natal_prediction_areas,
        practices=[],
        closing_note=natal_closing_note,
        llm_enhanced=natal_llm_enhanced,
        is_natal_v2=is_natal_v2,
        natal_who_you_are=natal_who_you_are_obj,
        natal_where_you_shine=natal_where_you_shine_obj,
        natal_relationships=natal_relationships_obj,
        natal_current_chapter=natal_current_chapter_obj,
        natal_life_by_decade=natal_life_by_decade_list,
        natal_dasha_life_map=natal_dasha_life_map_list,
        methodology=MethodologyInfo(
            ephemeris_source="Swiss Ephemeris",
            ayanamsa=_ayanamsa_label(chart_metadata.get("ayanamsa", "lahiri")),
            node_type=chart_metadata.get("node_type", "Mean Node"),
            division_method=chart_metadata.get("division_method", "Parashara"),
            calculation_confidence=calc_confidence,
            cusp_cases=cusp_cases,
        ),
        yogas_data=yogas_raw if isinstance(yogas_raw, dict) else None,
        sade_sati_data=sade_sati_raw if isinstance(sade_sati_raw, dict) else None,
        shadbala_data=shadbala_raw if isinstance(shadbala_raw, dict) else None,
        kp_sublords=kp_sublords_data,
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
