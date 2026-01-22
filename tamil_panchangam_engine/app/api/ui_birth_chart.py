from fastapi import APIRouter, Query, HTTPException
import json

from app.db.duckdb import get_conn
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

    # 🔑 Canonical derived UI model
    view = build_birth_chart_view_model(base_payload)

    return {
        "base_chart_id": base_chart_id,
        "view": view,
    }
