# app/api/daily.py
"""
Daily Dinaphalam API

GET /api/prediction/daily?base_chart_id=<id>&date=YYYY-MM-DD

Returns daily Panchangam + inauspicious windows for a given chart and date.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from app.db.postgres import get_conn
from app.engines.dinaphalam_engine import compute_dinaphalam
from app.utils.time_utils import get_timezone_from_coordinates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prediction", tags=["Prediction"])


def _get_base_chart_payload(base_chart_id: str) -> dict:
    """Fetch base chart payload from DB."""
    import json
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT payload FROM base_charts WHERE id = ?",
                [base_chart_id],
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Base chart not found")
            raw = row[0]
            if isinstance(raw, str):
                return json.loads(raw)
            return raw
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB error fetching chart {base_chart_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load base chart")


@router.get("/daily")
def get_daily_prediction(
    base_chart_id: str = Query(..., description="Base chart ID"),
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD (defaults to today UTC)"),
):
    """
    Return daily Panchangam and inauspicious windows for a base chart.

    Response includes:
    - rahu_kaalam, yamagandam, gulika_kaalam (start/end local time)
    - nakshatra (today's Moon nakshatra + pada)
    - tara_bala (quality relative to birth nakshatra)
    - tithi (lunar day + paksha)
    - sunrise / sunset (local time)
    """
    payload = _get_base_chart_payload(base_chart_id)

    # Parse target date
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    else:
        today = datetime.now(timezone.utc)
        target_date = today.replace(hour=0, minute=0, second=0, microsecond=0)

    # Extract chart coordinates
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    if latitude is None or longitude is None:
        raise HTTPException(status_code=422, detail="Chart missing latitude/longitude")

    # Determine birth nakshatra index from stored nakshatra data
    nakshatra_context = payload.get("nakshatra_context", {})
    birth_nak_index = nakshatra_context.get("janma_nakshatra_index")
    if birth_nak_index is None:
        planets = payload.get("planets", {})
        moon = planets.get("Moon", {})
        moon_lon = moon.get("longitude", 0.0)
        birth_nak_index = int(moon_lon / (360 / 27)) % 27

    # Determine UTC offset from chart coordinates
    try:
        tz_name = get_timezone_from_coordinates(latitude, longitude)
        import pytz
        from datetime import timedelta
        tz = pytz.timezone(tz_name)
        aware = target_date.astimezone(tz)
        utc_offset = aware.utcoffset().total_seconds() / 3600
    except Exception:
        utc_offset = 5.5  # fallback to IST

    ayanamsa = payload.get("reference", {}).get("ayanamsa", "lahiri")

    result = compute_dinaphalam(
        date_utc=target_date,
        latitude=latitude,
        longitude=longitude,
        birth_nakshatra_index=int(birth_nak_index),
        utc_offset_hours=utc_offset,
        ayanamsa=ayanamsa,
    )

    return {
        "base_chart_id": base_chart_id,
        **result,
    }
