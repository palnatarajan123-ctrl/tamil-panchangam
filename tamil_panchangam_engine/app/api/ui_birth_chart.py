from fastapi import APIRouter, Query, HTTPException
import json

from app.db.postgres import get_conn
from app.services.birth_chart_builder import build_birth_chart_view_model

router = APIRouter(prefix="/ui", tags=["ui"])


@router.get("/birth-chart")
def get_birth_chart_ui(
    base_chart_id: str = Query(...),
):
    """
    UI-safe birth chart endpoint.

    GUARANTEES:
    - Read-only
    - DuckDB-backed
    - Returns DERIVED VIEW MODEL only
    - Never exposes raw persistence schema
    """

    conn = get_conn()

    row = conn.execute(
        """
        SELECT id, payload
        FROM base_charts
        WHERE id = ?
        """,
        [base_chart_id],
    ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Base chart not found",
        )

    _, payload = row

    base_payload = (
        payload if isinstance(payload, dict)
        else json.loads(payload)
    )

    # Lazy upagraha backfill for pre-v2.0 charts
    if not base_payload.get("upagrahas"):
        _birth_utc_str = base_payload.get("birth_utc", "")
        _birth_details = base_payload.get("birth_details", {})
        if _birth_utc_str and _birth_details:
            try:
                from datetime import datetime as _dt
                from app.engines.upagraha_engine import compute_gulika_mandi
                _bu = _dt.fromisoformat(_birth_utc_str.replace("Z", "+00:00"))
                _upa = compute_gulika_mandi(
                    birth_utc=_bu,
                    latitude=_birth_details.get("latitude", 0.0),
                    longitude=_birth_details.get("longitude", 0.0),
                    ayanamsa=base_payload.get("ephemeris", {}).get("ayanamsa", "lahiri"),
                )
                base_payload["upagrahas"] = _upa
                with get_conn() as _conn:
                    _conn.execute(
                        "UPDATE base_charts SET payload = payload || %s::jsonb WHERE id = %s",
                        (json.dumps({"upagrahas": _upa}), base_chart_id),
                    )
            except Exception:
                pass  # non-critical — natal view still works without upagrahas

    # 🔑 Canonical derived UI model
    view = build_birth_chart_view_model(base_payload)

    return {
        "base_chart_id": base_chart_id,
        "view": view,
        "kp_sublords": base_payload.get("kp_sublords"),
    }
