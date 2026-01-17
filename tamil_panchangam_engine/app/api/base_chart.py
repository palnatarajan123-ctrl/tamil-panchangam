# app/api/base_chart.py

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import List

from app.models.schema import (
    BASE_CHART_STORE,
    generate_base_chart_id,
    BaseChartCreateRequest,
    BaseChartCreateResponse,
    BaseChartSummary,
    BaseChartDetail,
)

from app.engines.ephemeris import compute_sidereal_positions
from app.engines.panchangam import compute_panchangam
from app.engines.dasha_vimshottari import compute_vimshottari_dasha
from app.engines.pancha_pakshi import get_birth_pakshi

from app.utils.time_utils import (
    normalize_birth_time_to_utc,
    get_timezone_from_coordinates,
)
from app.utils.checksum import compute_chart_checksum
from app.services.birth_chart_builder import build_birth_chart_view_model
from app.db.duckdb import get_conn
from app.repositories.base_chart_repo import insert_base_chart

router = APIRouter(prefix="/api/base-chart", tags=["Base Chart"])


# ============================================================
# UI VIEW (D1 + Panchangam)
# ============================================================

@router.get("/birth-chart")
def get_birth_chart_ui(base_chart_id: str):
    chart = BASE_CHART_STORE.get(base_chart_id)
    if not chart:
        raise HTTPException(404, "Base chart not found")

    ui_view = build_birth_chart_view_model(chart["data"])
    return {"view": ui_view}


# ============================================================
# CREATE BASE CHART (EPIC-5 / 6.3)
# ============================================================

@router.post("/create", response_model=BaseChartCreateResponse)
def create_base_chart(payload: BaseChartCreateRequest):
    """
    Immutable birth chart creation.

    Guarantees:
    - Deterministic
    - Contract-safe
    - In-memory (by design)
    """

    # -------------------------------------------------
    # 1. Resolve timezone
    # -------------------------------------------------
    timezone = payload.timezone
    if not timezone:
        timezone = get_timezone_from_coordinates(
            payload.latitude,
            payload.longitude,
        )

    # -------------------------------------------------
    # 2. Normalize birth datetime → UTC
    # -------------------------------------------------
    try:
        birth_utc = normalize_birth_time_to_utc(
            birth_date=payload.date_of_birth.isoformat(),
            birth_time=payload.time_of_birth.strftime("%H:%M:%S"),
            latitude=payload.latitude,
            longitude=payload.longitude,
            timezone_str=timezone,
        )
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Birth time normalization failed: {str(e)}",
        )

    # -------------------------------------------------
    # 3. Ephemeris (Sidereal – Lahiri)
    # -------------------------------------------------
    ephemeris = compute_sidereal_positions(
        birth_utc,
        payload.latitude,
        payload.longitude,
    )

    # -------------------------------------------------
    # 4. Panchangam at birth
    # -------------------------------------------------
    panchangam = compute_panchangam(
        dt_local=birth_utc,
        sun_lon=ephemeris["planets"]["Sun"]["longitude_deg"],
        moon_lon=ephemeris["moon"]["longitude_deg"],
        nakshatra=ephemeris["moon"]["nakshatra"],
    )

    # -------------------------------------------------
    # 5. Vimshottari Dasha
    # -------------------------------------------------
    dasha = compute_vimshottari_dasha(
        birth_datetime_utc=birth_utc,
        moon_longitude=ephemeris["moon"]["longitude_deg"],
        nakshatra_index=ephemeris["moon"]["nakshatra"]["index"],
    )

    # -------------------------------------------------
    # 6. Pancha Pakshi
    # -------------------------------------------------
    pakshi = get_birth_pakshi(
        ephemeris["moon"]["nakshatra"]["name"]
    )

    # -------------------------------------------------
    # 7. Assemble immutable base chart
    # -------------------------------------------------
    base_chart = {
        "birth_details": {
            "name": payload.name,
            "place_of_birth": payload.place_of_birth,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "timezone": timezone,
            "date_of_birth": payload.date_of_birth.isoformat(),
            "time_of_birth": payload.time_of_birth.strftime("%H:%M:%S"),
        },
        "birth_utc": birth_utc.isoformat(),
        "ephemeris": ephemeris,
        "panchangam_birth": panchangam,
        "charts": {},
        "dashas": {
            "vimshottari": dasha,
        },
        "pancha_pakshi_birth": pakshi,
    }

    # -------------------------------------------------
    # 8. Persist (DuckDB = source of truth)
    # -------------------------------------------------
    base_chart_id = generate_base_chart_id()
    checksum = compute_chart_checksum(base_chart)

    with get_conn() as conn:
        insert_base_chart(
            conn,
            chart_id=base_chart_id,
            payload=base_chart,
            locked=True,
        )

    # Optional: keep in-memory copy for UI endpoints
    BASE_CHART_STORE[base_chart_id] = {
        "id": base_chart_id,
        "checksum": checksum,
        "locked": True,
        "created_at": datetime.utcnow(),
        "data": base_chart,
    }

    return BaseChartCreateResponse(
        base_chart_id=base_chart_id,
        checksum=checksum,
        locked=True,
    )


# ============================================================
# LIST BASE CHARTS
# ============================================================

@router.get("/list", response_model=List[BaseChartSummary])
def list_base_charts():
    return [
        BaseChartSummary(
            base_chart_id=chart["id"],
            checksum=chart["checksum"],
            locked=chart["locked"],
        )
        for chart in BASE_CHART_STORE.values()
    ]


# ============================================================
# FETCH BASE CHART (FULL)
# ============================================================

@router.get("/{base_chart_id}", response_model=BaseChartDetail)
def get_base_chart(base_chart_id: str):
    chart = BASE_CHART_STORE.get(base_chart_id)

    if chart is None:
        raise HTTPException(
            status_code=404,
            detail=f"Base chart not found: {base_chart_id}",
        )

    return BaseChartDetail(
        id=chart["id"],
        checksum=chart["checksum"],
        locked=chart["locked"],
        created_at=chart["created_at"],
        data=chart["data"],
    )
