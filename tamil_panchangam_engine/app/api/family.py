# app/api/family.py
"""
Family Groups API — CRUD for family groups and members, plus Porutham matching.

Routes:
  GET    /family/groups                   List user's family groups
  POST   /family/groups                   Create a family group
  GET    /family/groups/{group_id}        Get group detail (with members)
  PUT    /family/groups/{group_id}        Rename group
  DELETE /family/groups/{group_id}        Delete group
  POST   /family/groups/{group_id}/members       Add member
  DELETE /family/groups/{group_id}/members/{id}  Remove member
  GET    /family/groups/{group_id}/porutham       Compute husband↔wife Porutham
  GET    /family/user-charts              List charts owned by user (for picker)
"""

import json
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.db.postgres import get_conn
from app.repositories.base_chart_repo import get_base_chart_by_id
from app.engines.porutham_engine import compute_porutham

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/family", tags=["Family"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class CreateGroupRequest(BaseModel):
    name: str


class RenameGroupRequest(BaseModel):
    name: str


class PatchGroupRequest(BaseModel):
    primary_chart_id: Optional[str] = None


class AddMemberRequest(BaseModel):
    chart_id: str
    role: str  # husband | wife | child | other
    display_name: Optional[str] = None
    birth_order: int = 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assert_group_owner(conn, group_id: str, user_id: str) -> dict:
    """Return group row or raise 404/403."""
    row = conn.execute(
        "SELECT id, user_id, name, primary_chart_id, created_at, updated_at FROM family_groups WHERE id = ?",
        [group_id]
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")
    if row[1] != user_id:
        raise HTTPException(status_code=403, detail="Not your group")
    return {"id": row[0], "user_id": row[1], "name": row[2],
            "primary_chart_id": row[3],
            "created_at": str(row[4]), "updated_at": str(row[5])}


def _chart_owned_by_user(conn, chart_id: str, user_id: str) -> bool:
    """Check that user owns this chart via user_charts."""
    row = conn.execute(
        "SELECT id FROM user_charts WHERE chart_id = ? AND user_id = ?",
        [chart_id, user_id]
    ).fetchone()
    return row is not None


def _extract_nak_rasi(payload: dict) -> tuple[str, str]:
    """Extract moon nakshatra name and rasi name from chart payload."""
    ephemeris = payload.get("ephemeris", {}) if isinstance(payload, dict) else {}
    moon = ephemeris.get("moon", {})
    rasi = ""
    nakshatra = ""
    if isinstance(moon, dict):
        rasi = moon.get("rasi", "")
        nak_raw = moon.get("nakshatra", {})
        if isinstance(nak_raw, dict):
            nakshatra = nak_raw.get("name", "")
        elif isinstance(nak_raw, str):
            nakshatra = nak_raw
    return nakshatra, rasi


def _member_row_to_dict(row, payload: Optional[dict] = None) -> dict:
    """Convert member DB row to dict. row: (id, group_id, chart_id, role, display_name, birth_order, created_at)"""
    d = {
        "id": str(row[0]),
        "group_id": str(row[1]),
        "chart_id": str(row[2]),
        "role": str(row[3]),
        "display_name": row[4],
        "birth_order": int(row[5] or 0),
        "created_at": str(row[6]),
    }
    if payload is not None:
        birth = payload.get("birth_details", {}) if isinstance(payload, dict) else {}
        d["chart_name"] = birth.get("name", "")
        d["date_of_birth"] = birth.get("date_of_birth", "")
        nak, rasi = _extract_nak_rasi(payload)
        d["nakshatra"] = nak
        d["rasi"] = rasi
    return d


def _resolve_primary_chart(conn, group_id: str, user_id: str,
                            explicit_id: Optional[str]) -> tuple[Optional[str], str]:
    """
    Return (chart_id, display_name) for the primary reading chart.
    Priority: explicit primary_chart_id → member chart owned by this user → None.
    """
    if explicit_id:
        chart = get_base_chart_by_id(conn, explicit_id)
        if chart:
            p = chart.get("payload")
            try:
                payload = p if isinstance(p, dict) else json.loads(p or "{}")
            except Exception:
                payload = {}
            birth = payload.get("birth_details", {}) if isinstance(payload, dict) else {}
            return explicit_id, birth.get("name", "Primary")
        # stale reference — fall through

    # Fall back: find any member chart owned by this user
    row = conn.execute("""
        SELECT fm.chart_id FROM family_members fm
        JOIN user_charts uc ON uc.chart_id = fm.chart_id AND uc.user_id = ?
        WHERE fm.group_id = ?
        LIMIT 1
    """, [user_id, group_id]).fetchone()
    if row:
        chart = get_base_chart_by_id(conn, str(row[0]))
        if chart:
            p = chart.get("payload")
            try:
                payload = p if isinstance(p, dict) else json.loads(p or "{}")
            except Exception:
                payload = {}
            birth = payload.get("birth_details", {}) if isinstance(payload, dict) else {}
            return str(row[0]), birth.get("name", "Primary")

    return None, ""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/user-charts")
def list_user_charts(user: dict = Depends(get_current_user)):
    """Return charts owned by this user (for the member picker)."""
    user_id = user["id"]
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT uc.chart_id, bc.payload
            FROM user_charts uc
            JOIN base_charts bc ON bc.id = uc.chart_id
            WHERE uc.user_id = ?
            ORDER BY uc.created_at DESC
        """, [user_id]).fetchall()

    charts = []
    for row in rows:
        try:
            payload = row[1] if isinstance(row[1], dict) else json.loads(row[1] or "{}")
        except Exception:
            payload = {}
        birth = payload.get("birth_details", {}) if isinstance(payload, dict) else {}
        nak, rasi = _extract_nak_rasi(payload)
        charts.append({
            "chart_id": str(row[0]),
            "name": birth.get("name", ""),
            "date_of_birth": birth.get("date_of_birth", ""),
            "nakshatra": nak,
            "rasi": rasi,
        })
    return {"charts": charts}


@router.get("/groups")
def list_groups(user: dict = Depends(get_current_user)):
    """List user's family groups with member count."""
    user_id = user["id"]
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT fg.id, fg.name, fg.primary_chart_id, fg.created_at, fg.updated_at,
                   COUNT(fm.id) AS member_count
            FROM family_groups fg
            LEFT JOIN family_members fm ON fm.group_id = fg.id
            WHERE fg.user_id = ?
            GROUP BY fg.id, fg.name, fg.primary_chart_id, fg.created_at, fg.updated_at
            ORDER BY fg.created_at DESC
        """, [user_id]).fetchall()

    return {"groups": [
        {
            "id": str(r[0]), "name": str(r[1]),
            "primary_chart_id": r[2],
            "created_at": str(r[3]), "updated_at": str(r[4]),
            "member_count": int(r[5]),
        }
        for r in rows
    ]}


@router.post("/groups", status_code=201)
def create_group(req: CreateGroupRequest, user: dict = Depends(get_current_user)):
    """Create a new family group."""
    user_id = user["id"]
    group_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO family_groups (id, user_id, name)
            VALUES (?, ?, ?)
        """, [group_id, user_id, req.name.strip()])
    return {"id": group_id, "name": req.name.strip(), "member_count": 0}


@router.get("/groups/{group_id}")
def get_group(group_id: str, user: dict = Depends(get_current_user)):
    """Get group detail with members and their chart info."""
    user_id = user["id"]
    with get_conn() as conn:
        group = _assert_group_owner(conn, group_id, user_id)

        member_rows = conn.execute("""
            SELECT id, group_id, chart_id, role, display_name, birth_order, created_at
            FROM family_members
            WHERE group_id = ?
            ORDER BY birth_order ASC, created_at ASC
        """, [group_id]).fetchall()

        members = []
        for row in member_rows:
            chart = get_base_chart_by_id(conn, str(row[2]))
            payload = None
            if chart:
                p = chart.get("payload")
                try:
                    payload = p if isinstance(p, dict) else json.loads(p or "{}")
                except Exception:
                    payload = {}
            members.append(_member_row_to_dict(row, payload))

        primary_id, primary_name = _resolve_primary_chart(
            conn, group_id, user_id, group.get("primary_chart_id")
        )

    group["members"] = members
    group["primary_chart_id"] = primary_id
    group["primary_chart_name"] = primary_name
    return group


@router.put("/groups/{group_id}")
def rename_group(group_id: str, req: RenameGroupRequest, user: dict = Depends(get_current_user)):
    """Rename a group."""
    user_id = user["id"]
    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)
        conn.execute("""
            UPDATE family_groups SET name = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [req.name.strip(), group_id])
    return {"ok": True}


@router.patch("/groups/{group_id}")
def patch_group(group_id: str, req: PatchGroupRequest, user: dict = Depends(get_current_user)):
    """Update primary_chart_id for a group."""
    user_id = user["id"]
    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)
        if req.primary_chart_id is not None and not _chart_owned_by_user(conn, req.primary_chart_id, user_id):
            raise HTTPException(status_code=403, detail="Chart not owned by you")
        conn.execute("""
            UPDATE family_groups SET primary_chart_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [req.primary_chart_id, group_id])
        primary_id, primary_name = _resolve_primary_chart(
            conn, group_id, user_id, req.primary_chart_id
        )
    return {"ok": True, "primary_chart_id": primary_id, "primary_chart_name": primary_name}


@router.delete("/groups/{group_id}", status_code=204)
def delete_group(group_id: str, user: dict = Depends(get_current_user)):
    """Delete a group and all its members."""
    user_id = user["id"]
    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)
        conn.execute("DELETE FROM family_groups WHERE id = ?", [group_id])


@router.post("/groups/{group_id}/members", status_code=201)
def add_member(group_id: str, req: AddMemberRequest, user: dict = Depends(get_current_user)):
    """Add a chart as a family member."""
    user_id = user["id"]
    valid_roles = {"husband", "wife", "child", "other"}
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"role must be one of {valid_roles}")

    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)

        if not _chart_owned_by_user(conn, req.chart_id, user_id):
            raise HTTPException(status_code=403, detail="Chart not owned by you")

        # Check duplicate
        existing = conn.execute(
            "SELECT id FROM family_members WHERE group_id = ? AND chart_id = ?",
            [group_id, req.chart_id]
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Chart already in this group")

        member_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO family_members (id, group_id, chart_id, role, display_name, birth_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [member_id, group_id, req.chart_id, req.role, req.display_name, req.birth_order])

        # Fetch chart for response
        chart = get_base_chart_by_id(conn, req.chart_id)
        payload = None
        if chart:
            p = chart.get("payload")
            try:
                payload = p if isinstance(p, dict) else json.loads(p or "{}")
            except Exception:
                payload = {}

        row = conn.execute(
            "SELECT id, group_id, chart_id, role, display_name, birth_order, created_at FROM family_members WHERE id = ?",
            [member_id]
        ).fetchone()

    return _member_row_to_dict(row, payload)


@router.delete("/groups/{group_id}/members/{member_id}", status_code=204)
def remove_member(group_id: str, member_id: str, user: dict = Depends(get_current_user)):
    """Remove a member from a group."""
    user_id = user["id"]
    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)
        conn.execute(
            "DELETE FROM family_members WHERE id = ? AND group_id = ?",
            [member_id, group_id]
        )


@router.get("/groups/{group_id}/porutham")
def get_porutham(group_id: str, user: dict = Depends(get_current_user)):
    """
    Compute 10-point Porutham for husband+wife pair in group.
    Returns error if group doesn't have exactly one husband and one wife.
    """
    user_id = user["id"]
    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)

        rows = conn.execute("""
            SELECT id, group_id, chart_id, role, display_name, birth_order, created_at
            FROM family_members
            WHERE group_id = ?
        """, [group_id]).fetchall()

    husband = None
    wife = None
    for row in rows:
        role = str(row[3])
        chart = None
        with get_conn() as conn:
            chart = get_base_chart_by_id(conn, str(row[2]))
        if not chart:
            continue
        p = chart.get("payload")
        try:
            payload = p if isinstance(p, dict) else json.loads(p or "{}")
        except Exception:
            payload = {}
        nak, rasi = _extract_nak_rasi(payload)
        birth = payload.get("birth_details", {}) if isinstance(payload, dict) else {}
        member_info = {
            "name": row[4] or birth.get("name", ""),
            "nakshatra": nak,
            "rasi": rasi,
        }
        if role == "husband" and husband is None:
            husband = member_info
        elif role == "wife" and wife is None:
            wife = member_info

    if not husband:
        raise HTTPException(status_code=422, detail="Group has no husband member")
    if not wife:
        raise HTTPException(status_code=422, detail="Group has no wife member")
    if not husband["nakshatra"] or not husband["rasi"]:
        raise HTTPException(status_code=422, detail="Husband chart missing nakshatra/rasi data")
    if not wife["nakshatra"] or not wife["rasi"]:
        raise HTTPException(status_code=422, detail="Wife chart missing nakshatra/rasi data")

    result = compute_porutham(
        boy_nakshatra=husband["nakshatra"], boy_rasi=husband["rasi"],
        girl_nakshatra=wife["nakshatra"], girl_rasi=wife["rasi"],
    )
    return {
        "husband": husband,
        "wife": wife,
        "porutham": result,
    }
