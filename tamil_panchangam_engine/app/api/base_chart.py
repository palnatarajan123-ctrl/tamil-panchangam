# app/api/base_chart.py

import logging
import hashlib
import os
import httpx
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from typing import List, Optional
from app.core.limiter import limiter

logger = logging.getLogger(__name__)


def _compute_birth_fingerprint(
    date_of_birth: str,
    time_of_birth: str,
    latitude: float,
    longitude: float,
    node_type: str = "mean",
) -> str:
    """
    Compute a deterministic fingerprint for birth data.
    Same birth data + node_type = same fingerprint = same chart (for cache sharing).
    """
    data = f"{date_of_birth}|{time_of_birth}|{latitude:.4f}|{longitude:.4f}|{node_type}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def _find_existing_chart_by_fingerprint(fingerprint: str) -> Optional[str]:
    """
    Check if a chart with this birth fingerprint already exists.
    Returns chart_id if found, None otherwise.
    """
    for chart_id, chart in BASE_CHART_STORE.items():
        stored_fp = chart.get("fingerprint")
        if stored_fp == fingerprint:
            logger.info(f"Found existing chart {chart_id} for fingerprint {fingerprint}")
            return chart_id
    return None

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

# ✅ Navamsa engine (legacy import for compatibility)
from app.engines.navamsa_engine import build_navamsa_chart

# ✅ Tier-1 Divisional Charts
from app.engines.divisional_charts import (
    build_hora_chart,
    build_saptamsa_chart,
    build_navamsa_chart as build_d9_chart,
    build_dasamsa_chart,
)

# ✅ Functional Role engine
from app.engines.functional_role_engine import compute_functional_roles

from app.utils.time_utils import (
    normalize_birth_time_to_utc,
    get_timezone_from_coordinates,
)
from app.utils.checksum import compute_chart_checksum
from app.services.birth_chart_builder import build_birth_chart_view_model
from app.db.duckdb import get_conn
from app.repositories.base_chart_repo import insert_base_chart
from app.repositories.base_chart_repo import get_base_chart_by_id


router = APIRouter(prefix="/base-chart", tags=["Base Chart"])


def _verify_turnstile(token: str) -> bool:
    """Verify Cloudflare Turnstile token. Returns True if valid."""
    secret = os.getenv("TURNSTILE_SECRET_KEY", "1x0000000000000000000000000000000AA")
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={"secret": secret, "response": token},
            )
            return resp.json().get("success", False)
    except Exception:
        return False


def load_charts_from_db():
    """Load all charts from DuckDB into in-memory store on startup."""
    import json
    try:
        with get_conn() as conn:
            results = conn.execute(
                "SELECT id, locked, payload FROM base_charts"
            ).fetchall()
            
            loaded_count = 0
            for row in results:
                chart_id = row[0]
                locked = row[1]
                raw_payload = row[2]
                
                if isinstance(raw_payload, str):
                    try:
                        payload = json.loads(raw_payload)
                    except json.JSONDecodeError:
                        print(f"⚠️ Failed to parse payload for chart {chart_id}")
                        continue
                elif isinstance(raw_payload, dict):
                    payload = raw_payload
                else:
                    continue
                
                # Compute fingerprint for deduplication
                # Birth data is in 'birth_details', not 'reference'
                birth_details = payload.get("birth_details", {})
                fingerprint = _compute_birth_fingerprint(
                    date_of_birth=birth_details.get("date_of_birth", ""),
                    time_of_birth=birth_details.get("time_of_birth", ""),
                    latitude=birth_details.get("latitude", 0) or 0,
                    longitude=birth_details.get("longitude", 0) or 0,
                )
                
                BASE_CHART_STORE[chart_id] = {
                    "id": chart_id,
                    "checksum": compute_chart_checksum(payload),
                    "locked": locked,
                    "created_at": datetime.utcnow().isoformat(),
                    "data": payload,
                    "fingerprint": fingerprint,
                }
                loaded_count += 1
            
            print(f"📂 Loaded {loaded_count} charts from DuckDB into memory")
    except Exception as e:
        print(f"⚠️ Failed to load charts from DB: {e}")


# ============================================================
# UI VIEW (D1 + Panchangam)
# ============================================================

@router.get("/birth-chart")
def get_birth_chart_ui(base_chart_id: str):
    with get_conn() as conn:
        record = get_base_chart_by_id(conn, base_chart_id)

    if not record:
        raise HTTPException(404, "Base chart not found")

    import json
    payload = json.loads(record["payload"])

    ui_view = build_birth_chart_view_model(payload)
    return {"view": ui_view}


# ============================================================
# CREATE BASE CHART (EPIC-5 / 6.3)
# ============================================================

@limiter.limit("5/hour")
@router.post("/create", response_model=BaseChartCreateResponse)
def create_base_chart(request: Request, payload: BaseChartCreateRequest, force_recalculate: bool = False):
    """
    Immutable birth chart creation with deduplication.

    Guarantees:
    - Deterministic
    - Contract-safe
    - Deduplicated (same birth data = same chart_id for LLM cache sharing)
    
    Args:
        force_recalculate: If True, bypasses cache and recalculates ephemeris
    """

    # -------------------------------------------------
    # 0a. Turnstile verification
    # -------------------------------------------------
    token = payload.turnstile_token
    if token and not _verify_turnstile(token):
        raise HTTPException(status_code=403, detail="CAPTCHA verification failed. Please try again.")

    # -------------------------------------------------
    # 0. Check for existing chart with same birth data
    # -------------------------------------------------
    node_type = payload.node_type or "mean"
    fingerprint = _compute_birth_fingerprint(
        date_of_birth=payload.date_of_birth.isoformat(),
        time_of_birth=payload.time_of_birth.strftime("%H:%M:%S"),
        latitude=payload.latitude,
        longitude=payload.longitude,
        node_type=node_type,
    )
    
    if not force_recalculate:
        existing_chart_id = _find_existing_chart_by_fingerprint(fingerprint)
        if existing_chart_id:
            existing = BASE_CHART_STORE[existing_chart_id]
            logger.info(f"Returning existing chart {existing_chart_id} (fingerprint match)")
            return BaseChartCreateResponse(
                base_chart_id=existing_chart_id,
                checksum=existing["checksum"],
                locked=existing["locked"],
            )

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
        node_type=node_type,
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
    # 7. Tier-1 Divisional Charts — IMMUTABLE
    # -------------------------------------------------
    # D2: Hora (Wealth)
    d2_hora = build_hora_chart(ephemeris)
    
    # D7: Saptamsa (Creativity/Children)
    d7_saptamsa = build_saptamsa_chart(ephemeris)
    
    # D9: Navamsa (Dharma/Maturity) - using new standardized builder
    d9_navamsa = build_d9_chart(ephemeris)
    
    # D10: Dasamsa (Career/Authority)
    d10_dasamsa = build_dasamsa_chart(ephemeris)
    
    # Legacy navamsa for backward compatibility
    navamsa_legacy = build_navamsa_chart(ephemeris)

    # -------------------------------------------------
    # 7b. Functional Roles (yogakaraka/benefic/malefic)
    # -------------------------------------------------
    functional_roles = compute_functional_roles(
        ephemeris=ephemeris,
        houses={}  # Houses extracted from ephemeris internally
    )

    # -------------------------------------------------
    # 8. Assemble immutable base chart
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

        # ✅ Legacy format for backward compatibility
        "charts": {
            "D9": navamsa_legacy,
        },

        # ✅ Tier-1 Divisional Charts (standardized format)
        "divisional_charts": {
            "D2": d2_hora,
            "D7": d7_saptamsa,
            "D9": d9_navamsa,
            "D10": d10_dasamsa,
        },
        
        # ✅ Metadata for audit
        "chart_metadata": {
            "ayanamsa": "lahiri",
            "division_method": "parashara",
            "precision": "arc-second",
            "node_type": node_type,
        },

        "dashas": {
            "vimshottari": dasha,
        },
        "pancha_pakshi_birth": pakshi,
        "functional_roles": functional_roles,
    }

    # -------------------------------------------------
    # 9. Persist (DuckDB = source of truth)
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
        conn.commit()

    # Optional: keep in-memory copy for UI endpoints
    BASE_CHART_STORE[base_chart_id] = {
        "id": base_chart_id,
        "checksum": checksum,
        "locked": True,
        "created_at": datetime.utcnow(),
        "data": base_chart,
        "fingerprint": fingerprint,
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

    # Compute functional_roles on-the-fly if missing (for charts loaded from DuckDB)
    chart_data = chart["data"]
    if not chart_data.get("functional_roles"):
        ephemeris = chart_data.get("ephemeris", {})
        if ephemeris:
            try:
                computed_roles = compute_functional_roles(ephemeris=ephemeris, houses={})
                chart_data["functional_roles"] = computed_roles
            except Exception as e:
                logger.warning(f"Failed to compute functional_roles: {e}")
                chart_data["functional_roles"] = {}

    return BaseChartDetail(
        id=chart["id"],
        checksum=chart["checksum"],
        locked=chart["locked"],
        created_at=chart["created_at"],
        data=chart_data,
    )
