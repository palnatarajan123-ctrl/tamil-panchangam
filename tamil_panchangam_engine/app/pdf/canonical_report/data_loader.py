"""
Canonical PDF Report Builder - Data Loader

Loads ALL data from database/cache.
NEVER recalculates any astrological data.
Fails gracefully if required data is missing.
"""

import json
import hashlib
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from app.db.duckdb_store import get_conn
from app.pdf.charts.south_indian_svg import render_south_indian_chart
from .models import (
    CanonicalReportData,
    BirthDetails,
    BirthReference,
    DashaContext,
    TransitContext,
    NakshatraTimingContext,
    PakshiRhythmContext,
    PredictionArea,
    ChartImages,
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
            SELECT * FROM base_chart WHERE id = ?
        """, [base_chart_id]).fetchone()
        
        if not result:
            raise ReportDataNotFoundError(f"Base chart not found: {base_chart_id}")
        
        columns = [desc[0] for desc in conn.description]
        return dict(zip(columns, result))


def load_prediction(base_chart_id: str, year: int, month: int) -> Dict[str, Any]:
    """Load monthly prediction from database."""
    with get_conn() as conn:
        result = conn.execute("""
            SELECT * FROM predictions 
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
            SELECT * FROM predictions 
            WHERE base_chart_id = ? AND year = ? AND period_type = 'yearly'
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
    feature_name: str = "interpretation"
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


def _generate_chart_svg(planet_signs: Dict[str, str], title: str = "") -> str:
    """Generate SVG chart and return as data URI."""
    try:
        svg_content = render_south_indian_chart(planet_signs)
        import base64
        svg_b64 = base64.b64encode(svg_content.encode()).decode()
        return f"data:image/svg+xml;base64,{svg_b64}"
    except Exception as e:
        logger.error(f"Failed to generate chart SVG: {e}")
        return ""


def _extract_birth_reference(chart: Dict[str, Any]) -> BirthReference:
    """Extract birth reference data from chart payload."""
    payload = _safe_json(chart.get("payload"), {})
    birth_interp = _safe_json(chart.get("birth_interpretation"), {})
    
    vimshottari = payload.get("vimshottari", {})
    
    return BirthReference(
        janma_nakshatra=payload.get("nakshatra", {}).get("name", "Unknown"),
        janma_rasi=payload.get("moon_sign", "Unknown"),
        lagna=payload.get("lagna", "Unknown"),
        moon_sign=payload.get("moon_sign", "Unknown"),
        nakshatra_lord=payload.get("nakshatra", {}).get("lord", "Unknown"),
        birth_dasha=f"{vimshottari.get('mahadasha', 'Unknown')} - {vimshottari.get('antardasha', 'Unknown')}",
        functional_role_planets=birth_interp.get("functional_roles", {}),
    )


def _extract_dasha_context(envelope: Dict[str, Any]) -> DashaContext:
    """Extract dasha context from prediction envelope."""
    vimshottari = envelope.get("vimshottari", {})
    
    return DashaContext(
        mahadasha=vimshottari.get("mahadasha", "Unknown"),
        mahadasha_lord=vimshottari.get("mahadasha_lord", "Unknown"),
        antardasha=vimshottari.get("antardasha", "Unknown"),
        antardasha_lord=vimshottari.get("antardasha_lord", "Unknown"),
        dasha_balance=vimshottari.get("balance", "Unknown"),
    )


def _extract_transit_context(envelope: Dict[str, Any]) -> TransitContext:
    """Extract transit context from prediction envelope."""
    transits = envelope.get("transits", {})
    
    jupiter_sign = transits.get("jupiter", {}).get("sign", "Unknown")
    saturn_sign = transits.get("saturn", {}).get("sign", "Unknown")
    rahu = transits.get("rahu", {}).get("sign", "Unknown")
    ketu = transits.get("ketu", {}).get("sign", "Unknown")
    
    return TransitContext(
        jupiter_transit=f"Jupiter in {jupiter_sign}",
        saturn_transit=f"Saturn in {saturn_sign}",
        rahu_ketu_axis=f"Rahu in {rahu}, Ketu in {ketu}",
    )


def _extract_nakshatra_timing(envelope: Dict[str, Any]) -> NakshatraTimingContext:
    """Extract nakshatra timing context."""
    tara_bala = envelope.get("tara_bala", {})
    timing = envelope.get("timing", {})
    
    return NakshatraTimingContext(
        current_moon_nakshatra=timing.get("moon_nakshatra", "Unknown"),
        tara_bala=tara_bala.get("rating", "Neutral"),
        chandra_gati=timing.get("chandra_gati", "Unknown"),
        favorable_window=timing.get("favorable_window", "Consult chart"),
    )


def _extract_pakshi_rhythm(envelope: Dict[str, Any]) -> PakshiRhythmContext:
    """Extract pakshi rhythm context."""
    pakshi = envelope.get("pakshi", {})
    
    return PakshiRhythmContext(
        dominant_pakshi=pakshi.get("bird", "Unknown"),
        activity_phase=pakshi.get("activity", "Unknown"),
    )


def _extract_prediction_areas(
    interpretation: Dict[str, Any],
    llm_interpretation: Optional[Dict[str, Any]] = None
) -> Tuple[str, list]:
    """Extract prediction areas from interpretation."""
    
    source = llm_interpretation if llm_interpretation else interpretation
    
    overview = source.get("overview") or source.get("summary", "")
    
    life_areas = source.get("life_areas", {})
    
    areas = []
    for area_name, area_data in life_areas.items():
        if isinstance(area_data, dict):
            areas.append(PredictionArea(
                area=area_name.replace("_", " ").title(),
                interpretation=area_data.get("interpretation", area_data.get("summary", "")),
                guidance=area_data.get("guidance"),
            ))
        elif isinstance(area_data, str):
            areas.append(PredictionArea(
                area=area_name.replace("_", " ").title(),
                interpretation=area_data,
            ))
    
    return overview, areas


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
    
    rasi = payload.get("rasi", {}).get("planet_signs", {})
    navamsa = payload.get("navamsa", {}).get("planet_signs", {})
    
    overview, prediction_areas = _extract_prediction_areas(
        interpretation, llm_interpretation
    )
    
    birth_meta = chart.get("birth_data", {})
    if isinstance(birth_meta, str):
        birth_meta = _safe_json(birth_meta, {})
    
    return CanonicalReportData(
        report_type=report_type.title(),
        period_label=period_label,
        generated_at=datetime.now(),
        
        birth_details=BirthDetails(
            name=birth_meta.get("name", "Chart Holder"),
            date=birth_meta.get("date", "Unknown"),
            time=birth_meta.get("time", "Unknown"),
            place=birth_meta.get("place", "Unknown"),
        ),
        
        birth_reference=_extract_birth_reference(chart),
        
        chart_images=ChartImages(
            d1_rasi=_generate_chart_svg(rasi, "Rasi (D1)"),
            d9_navamsa=_generate_chart_svg(navamsa, "Navamsa (D9)"),
        ),
        
        core_life_themes=interpretation.get("core_themes", []),
        
        dasha_context=_extract_dasha_context(envelope),
        transit_context=_extract_transit_context(envelope),
        nakshatra_timing=_extract_nakshatra_timing(envelope),
        pakshi_rhythm=_extract_pakshi_rhythm(envelope),
        
        prediction_overview=overview,
        prediction_areas=prediction_areas,
        
        practices=interpretation.get("practices", []),
        reflection_prompts=interpretation.get("reflections", []),
        
        closing_note=interpretation.get("closing", 
            "May this guidance support your journey with awareness and wisdom."),
        
        llm_enhanced=llm_interpretation is not None,
    )
