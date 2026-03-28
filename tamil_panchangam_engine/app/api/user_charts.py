# app/api/user_charts.py
"""
User chart management — save, list, rename, delete.
Max 10 charts per user.
"""

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.db.postgres import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["User Charts"])

MAX_CHARTS_PER_USER = 10
MAX_CHARTS_ADMIN = None  # unlimited


# ── Models ───────────────────────────────────────────────────────────────────

class SaveChartRequest(BaseModel):
    base_chart_id: str
    nickname: Optional[str] = None


class RenameChartRequest(BaseModel):
    nickname: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/charts")
def list_user_charts(user: dict = Depends(get_current_user)):
    """List all charts saved by the current user."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT uc.id, uc.base_chart_id, uc.nickname, uc.created_at,
                      bc.payload
               FROM user_charts uc
               JOIN base_charts bc ON bc.id = uc.base_chart_id
               WHERE uc.user_id = ?
               ORDER BY uc.created_at DESC""",
            [user["id"]],
        ).fetchall()

    charts = []
    for row in rows:
        uc_id, base_chart_id, nickname, created_at, payload_raw = row
        # Extract birth details for display
        birth = {}
        try:
            payload = payload_raw if isinstance(payload_raw, dict) else json.loads(payload_raw)
            birth = payload.get("birth_details", {})
        except Exception:
            pass
        charts.append({
            "id": uc_id,
            "base_chart_id": base_chart_id,
            "nickname": nickname or birth.get("name", "Unnamed"),
            "name": birth.get("name", ""),
            "date_of_birth": birth.get("date_of_birth", ""),
            "place_of_birth": birth.get("place_of_birth", ""),
            "created_at": str(created_at),
        })
    return {"charts": charts}


@router.post("/charts", status_code=status.HTTP_201_CREATED)
def save_chart(body: SaveChartRequest, user: dict = Depends(get_current_user)):
    """Save a chart to the current user's collection."""
    with get_conn() as conn:
        # Check chart exists
        bc = conn.execute(
            "SELECT id FROM base_charts WHERE id = ?", [body.base_chart_id]
        ).fetchone()
        if not bc:
            raise HTTPException(status_code=404, detail="Base chart not found")

        # Check if already saved
        existing = conn.execute(
            "SELECT id FROM user_charts WHERE user_id = ? AND base_chart_id = ?",
            [user["id"], body.base_chart_id],
        ).fetchone()
        if existing:
            return {"id": existing[0], "already_saved": True}

        # Enforce max charts (admin = unlimited)
        if user.get("role") != "admin":
            count = conn.execute(
                "SELECT COUNT(*) FROM user_charts WHERE user_id = ?", [user["id"]]
            ).fetchone()[0]
            if count >= MAX_CHARTS_PER_USER:
                raise HTTPException(
                    status_code=400,
                    detail=f"Maximum of {MAX_CHARTS_PER_USER} saved charts reached. Delete one to save more.",
                )

        uc_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO user_charts (id, user_id, base_chart_id, nickname, created_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            [uc_id, user["id"], body.base_chart_id, body.nickname],
        )
    return {"id": uc_id, "already_saved": False}


@router.put("/charts/{chart_id}/nickname")
def rename_chart(chart_id: str, body: RenameChartRequest, user: dict = Depends(get_current_user)):
    """Rename (update nickname of) a saved chart."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM user_charts WHERE id = ? AND user_id = ?",
            [chart_id, user["id"]],
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Chart not found")
        conn.execute(
            "UPDATE user_charts SET nickname = ? WHERE id = ?",
            [body.nickname, chart_id],
        )
    return {"ok": True}


@router.delete("/charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chart(chart_id: str, user: dict = Depends(get_current_user)):
    """Remove a chart from the current user's saved collection."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM user_charts WHERE id = ? AND user_id = ?",
            [chart_id, user["id"]],
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Chart not found")
        conn.execute("DELETE FROM user_charts WHERE id = ?", [chart_id])
