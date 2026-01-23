# app/api/realtime_context.py
"""
Real-time Astrological Context API

Provides current-moment astrological context for a birth chart.
This is separate from cached predictions - computed fresh on each request.
"""

from fastapi import APIRouter, HTTPException, Query
import json

from app.db.duckdb import get_conn
from app.repositories.base_chart_repo import get_base_chart_by_id
from app.engines.realtime_context_engine import compute_realtime_context


router = APIRouter(prefix="/realtime", tags=["Realtime Context"])


ENGLISH_TO_TAMIL_RASI = {
    "Aries": "Mesham",
    "Taurus": "Rishabam",
    "Gemini": "Mithunam",
    "Cancer": "Kadakam",
    "Leo": "Simmam",
    "Virgo": "Kanni",
    "Libra": "Thulam",
    "Scorpio": "Vrischikam",
    "Sagittarius": "Dhanusu",
    "Capricorn": "Makaram",
    "Aquarius": "Kumbham",
    "Pisces": "Meenam",
}


@router.get("/context/{base_chart_id}")
def get_realtime_context(base_chart_id: str):
    """
    Get real-time astrological context for a birth chart.
    
    Returns current transit positions, Tara Bala, Pakshi status.
    Computed fresh on each request (not cached).
    """
    
    with get_conn() as conn:
        base_chart = get_base_chart_by_id(conn, base_chart_id)
    
    if base_chart is None:
        raise HTTPException(
            status_code=404,
            detail=f"Base chart not found: {base_chart_id}",
        )
    
    payload = (
        base_chart["payload"]
        if isinstance(base_chart["payload"], dict)
        else json.loads(base_chart["payload"])
    )
    
    ephemeris = payload.get("ephemeris", {})
    moon_data = ephemeris.get("moon", {})
    birth_moon_longitude = moon_data.get("longitude_deg", 0.0)
    birth_moon_rasi = moon_data.get("rasi", "Aries")
    
    if birth_moon_rasi in ENGLISH_TO_TAMIL_RASI.values():
        for eng, tam in ENGLISH_TO_TAMIL_RASI.items():
            if tam == birth_moon_rasi:
                birth_moon_rasi = eng
                break
    
    panchangam = payload.get("panchangam_birth", {})
    nakshatra_data = panchangam.get("nakshatra", {})
    birth_nakshatra = nakshatra_data.get("name", "Ashwini")
    if not birth_nakshatra:
        moon_nak = moon_data.get("nakshatra", {})
        birth_nakshatra = moon_nak.get("name", "Ashwini") if isinstance(moon_nak, dict) else "Ashwini"
    
    lagna = ephemeris.get("lagna", {})
    birth_lagna_rasi = lagna.get("rasi", None)
    if birth_lagna_rasi in ENGLISH_TO_TAMIL_RASI.values():
        for eng, tam in ENGLISH_TO_TAMIL_RASI.items():
            if tam == birth_lagna_rasi:
                birth_lagna_rasi = eng
                break
    
    birth_details = payload.get("birth_details", {})
    latitude = birth_details.get("latitude", 13.0827)
    longitude = birth_details.get("longitude", 80.2707)
    
    context = compute_realtime_context(
        birth_moon_longitude=birth_moon_longitude,
        birth_moon_rasi=birth_moon_rasi,
        birth_nakshatra=birth_nakshatra,
        birth_lagna_rasi=birth_lagna_rasi,
        latitude=latitude,
        longitude=longitude,
    )
    
    return {
        "base_chart_id": base_chart_id,
        "context": context,
    }
