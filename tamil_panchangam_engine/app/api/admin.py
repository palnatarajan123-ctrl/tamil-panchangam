# app/api/admin.py
"""
Admin endpoints — stats, user management, audit log, chart listing.
All routes require admin role.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import require_admin
from app.db.postgres import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Models ───────────────────────────────────────────────────────────────────

class UpdateUserRequest(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(_admin: dict = Depends(require_admin)):
    """Return platform usage stats."""
    with get_conn() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE").fetchone()[0]
        total_charts = conn.execute("SELECT COUNT(*) FROM base_charts").fetchone()[0]
        total_saved = conn.execute("SELECT COUNT(*) FROM user_charts").fetchone()[0]
        total_predictions = conn.execute("SELECT COUNT(*) FROM monthly_predictions").fetchone()[0]

        # Token usage this month
        token_rows = conn.execute(
            """SELECT feature_name, SUM(total_tokens)
               FROM llm_token_usage
               WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
               GROUP BY feature_name"""
        ).fetchall()
        token_usage = {row[0]: row[1] for row in token_rows}

        # Recent registrations (last 7 days)
        new_users_7d = conn.execute(
            """SELECT COUNT(*) FROM users
               WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'"""
        ).fetchone()[0]

    return {
        "users": {"total": total_users, "active": active_users, "new_7d": new_users_7d},
        "charts": {"total": total_charts, "saved": total_saved},
        "predictions": {"total": total_predictions},
        "token_usage_this_month": token_usage,
    }


@router.get("/users")
def list_users(
    offset: int = 0,
    limit: int = 50,
    _admin: dict = Depends(require_admin),
):
    """List all users with pagination."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, email, name, role, is_active, created_at, last_login_at
               FROM users
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            [limit, offset],
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    users = [
        {
            "id": r[0], "email": r[1], "name": r[2], "role": r[3],
            "is_active": r[4], "created_at": str(r[5]),
            "last_login_at": str(r[6]) if r[6] else None,
        }
        for r in rows
    ]
    return {"users": users, "total": total, "offset": offset, "limit": limit}


@router.put("/users/{user_id}")
def update_user(
    user_id: str,
    body: UpdateUserRequest,
    admin: dict = Depends(require_admin),
):
    """Toggle user active status or change role."""
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot modify your own account")

    with get_conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = ?", [user_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        if body.is_active is not None:
            conn.execute(
                "UPDATE users SET is_active = ? WHERE id = ?", [body.is_active, user_id]
            )
        if body.role is not None:
            if body.role not in ("user", "admin"):
                raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")
            conn.execute("UPDATE users SET role = ? WHERE id = ?", [body.role, user_id])

    return {"ok": True}


@router.get("/audit-log")
def get_audit_log(
    offset: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    _admin: dict = Depends(require_admin),
):
    """Paginated audit log, optionally filtered by user."""
    with get_conn() as conn:
        if user_id:
            rows = conn.execute(
                """SELECT id, user_id, action, resource_type, resource_id,
                          ip_address, details, created_at
                   FROM audit_log WHERE user_id = ?
                   ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                [user_id, limit, offset],
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE user_id = ?", [user_id]
            ).fetchone()[0]
        else:
            rows = conn.execute(
                """SELECT id, user_id, action, resource_type, resource_id,
                          ip_address, details, created_at
                   FROM audit_log
                   ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                [limit, offset],
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]

    entries = [
        {
            "id": r[0], "user_id": r[1], "action": r[2], "resource_type": r[3],
            "resource_id": r[4], "ip_address": r[5],
            "details": r[6] if isinstance(r[6], dict) else (json.loads(r[6]) if r[6] else None),
            "created_at": str(r[7]),
        }
        for r in rows
    ]
    return {"entries": entries, "total": total, "offset": offset, "limit": limit}


@router.get("/charts")
def list_all_charts(
    offset: int = 0,
    limit: int = 50,
    _admin: dict = Depends(require_admin),
):
    """List all base charts with optional user association."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT bc.id, bc.locked,
                      uc.user_id, u.email, u.name, uc.nickname, uc.created_at
               FROM base_charts bc
               LEFT JOIN user_charts uc ON uc.base_chart_id = bc.id
               LEFT JOIN users u ON u.id = uc.user_id
               ORDER BY uc.created_at DESC NULLS LAST
               LIMIT ? OFFSET ?""",
            [limit, offset],
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM base_charts").fetchone()[0]

    charts = [
        {
            "id": r[0], "locked": r[1],
            "user_id": r[2], "user_email": r[3], "user_name": r[4],
            "nickname": r[5], "saved_at": str(r[6]) if r[6] else None,
        }
        for r in rows
    ]
    return {"charts": charts, "total": total, "offset": offset, "limit": limit}
