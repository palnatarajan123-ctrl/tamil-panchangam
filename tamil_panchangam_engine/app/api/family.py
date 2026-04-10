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
  GET    /family/groups/{group_id}/overview       Dasha + Sade Sati per member
  GET    /family/user-charts              List charts owned by user (for picker)
"""

import json
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.db.postgres import get_conn
from app.repositories.base_chart_repo import get_base_chart_by_id
from app.engines.porutham_engine import compute_porutham
from app.engines.sade_sati_engine import compute_sade_sati
from app.engines.dasha_resolver import resolve_antar_dasha
from app.engines.family_prediction_engine import run_family_prediction
from app.engines.children_timing_engine import run_children_timing
from app.engines.timeline_aggregator import build_timeline
from app.engines.child_prediction_engine import run_child_prediction
from app.pdf.family_report.family_pdf_renderer import render_family_pdf

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
        "SELECT id FROM user_charts WHERE base_chart_id = ? AND user_id = ?",
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
        JOIN user_charts uc ON uc.base_chart_id = fm.chart_id AND uc.user_id = ?
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
            SELECT uc.base_chart_id, uc.nickname, bc.payload
            FROM user_charts uc
            JOIN base_charts bc ON bc.id = uc.base_chart_id
            WHERE uc.user_id = ?
            ORDER BY uc.created_at DESC
        """, [user_id]).fetchall()

    charts = []
    for row in rows:
        base_chart_id, nickname, payload_raw = row[0], row[1], row[2]
        try:
            payload = payload_raw if isinstance(payload_raw, dict) else json.loads(payload_raw or "{}")
        except Exception:
            payload = {}
        birth = payload.get("birth_details", {}) if isinstance(payload, dict) else {}
        nak, rasi = _extract_nak_rasi(payload)
        charts.append({
            "chart_id": str(base_chart_id),
            "nickname": nickname or birth.get("name", ""),
            "name": birth.get("name", ""),
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


@router.get("/groups/{group_id}/overview")
def get_group_overview(group_id: str, user: dict = Depends(get_current_user)):
    """Dasha + Sade Sati summary for each member in the group."""
    user_id = user["id"]
    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)
        member_rows = conn.execute("""
            SELECT id, group_id, chart_id, role, display_name, birth_order, created_at
            FROM family_members
            WHERE group_id = ?
            ORDER BY birth_order ASC, created_at ASC
        """, [group_id]).fetchall()

    now = datetime.now(timezone.utc)
    members_overview = []

    for row in member_rows:
        member_id = str(row[0])
        chart_id = str(row[2])
        role = str(row[3])
        display_name = row[4]

        with get_conn() as conn:
            chart = get_base_chart_by_id(conn, chart_id)

        payload = None
        if chart:
            p = chart.get("payload")
            try:
                payload = p if isinstance(p, dict) else json.loads(p or "{}")
            except Exception:
                payload = {}

        # ── Dasha resolution (same pattern as prediction_envelope.py) ──
        dasha_info = {"mahadasha": None, "antardasha": None, "end_date": None}
        if payload:
            try:
                vimshottari = payload.get("dashas", {}).get("vimshottari", {})
                resolved = resolve_antar_dasha(
                    vimshottari=vimshottari,
                    reference_date=now,
                )
                if resolved:
                    dasha_info["mahadasha"] = resolved["maha"]["lord"]
                    dasha_info["antardasha"] = resolved["antar"]["lord"]
                    dasha_info["end_date"] = resolved["antar"]["end"]
            except Exception as e:
                logger.warning(f"Dasha resolution failed for member {member_id}: {e}")

        # ── Sade Sati (same pattern as chat.py _build_chat_context) ──
        sade_sati_info = {"is_active": False, "phase": None, "start_date": None, "end_date": None}
        if payload:
            try:
                ss_result = compute_sade_sati(payload)
                if isinstance(ss_result, dict):
                    ss = ss_result.get("sade_sati", {})
                    if isinstance(ss, dict) and ss.get("active"):
                        sade_sati_info["is_active"] = True
                        sade_sati_info["phase"] = ss.get("phase")
                        sade_sati_info["start_date"] = None  # not available per-phase; use end_date
                        sade_sati_info["end_date"] = ss.get("current_phase_ends")
            except Exception as e:
                logger.warning(f"Sade Sati computation failed for member {member_id}: {e}")

        members_overview.append({
            "member_id": member_id,
            "chart_id": chart_id,
            "role": role,
            "display_name": display_name,
            "dasha": dasha_info,
            "sade_sati": sade_sati_info,
        })

    return {"members": members_overview}


# ── Family Predictions ────────────────────────────────────────────────────────

def _load_members_with_charts(conn, group_id: str) -> list:
    """Shared helper: fetch members + parsed chart payloads for a group."""
    member_rows = conn.execute("""
        SELECT id, group_id, chart_id, role, display_name, birth_order, created_at
        FROM family_members
        WHERE group_id = ?
        ORDER BY birth_order ASC, created_at ASC
    """, [group_id]).fetchall()

    result = []
    for row in member_rows:
        chart = get_base_chart_by_id(conn, str(row[2]))
        if not chart:
            continue
        p = chart.get("payload")
        try:
            payload = p if isinstance(p, dict) else json.loads(p or "{}")
        except Exception:
            payload = {}
        result.append({
            "member": {
                "id": str(row[0]),
                "group_id": str(row[1]),
                "chart_id": str(row[2]),
                "role": str(row[3]),
                "display_name": row[4],
                "birth_order": int(row[5] or 0),
            },
            "payload": payload,
        })
    return result


@router.get("/groups/{group_id}/predictions")
def get_family_predictions(
    group_id: str,
    year: int = None,
    user: dict = Depends(get_current_user),
):
    """Return cached family prediction or trigger a new LLM run."""
    if year is None:
        year = date.today().year
    user_id = user["id"]

    with get_conn() as conn:
        group = _assert_group_owner(conn, group_id, user_id)
        members_with_charts = _load_members_with_charts(conn, group_id)

        if not members_with_charts:
            raise HTTPException(status_code=400, detail="No valid member charts found")

        result = run_family_prediction(
            group={"id": group_id, "name": group["name"]},
            members_with_charts=members_with_charts,
            year=year,
            db=conn,
        )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.get("/groups/{group_id}/predictions/pdf")
def get_family_predictions_pdf(
    group_id: str,
    year: int = None,
    user: dict = Depends(get_current_user),
):
    """Render family prediction as PDF. Triggers LLM run if not cached."""
    if year is None:
        year = date.today().year
    user_id = user["id"]

    with get_conn() as conn:
        group = _assert_group_owner(conn, group_id, user_id)
        members_with_charts = _load_members_with_charts(conn, group_id)

        if not members_with_charts:
            raise HTTPException(status_code=400, detail="No valid member charts found")

        prediction = run_family_prediction(
            group={"id": group_id, "name": group["name"]},
            members_with_charts=members_with_charts,
            year=year,
            db=conn,
        )

    if "error" in prediction:
        raise HTTPException(status_code=500, detail=prediction["error"])

    member_names = [
        item["member"].get("display_name")
        or item["payload"].get("birth_details", {}).get("name", item["member"]["role"])
        for item in members_with_charts
    ]

    try:
        pdf_bytes = render_family_pdf(
            group_name=group["name"],
            member_names=member_names,
            year=year,
            prediction=prediction,
        )
    except Exception as e:
        logger.error(f"Family PDF render failed: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="family_prediction_{year}.pdf"'
        },
    )


@router.delete("/groups/{group_id}/predictions", status_code=204)
def clear_family_predictions_cache(
    group_id: str,
    year: int = None,
    user: dict = Depends(get_current_user),
):
    """Clear cached family prediction to force a fresh LLM run."""
    if year is None:
        year = date.today().year
    user_id = user["id"]

    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)
        conn.execute(
            "DELETE FROM family_predictions WHERE group_id = ? AND year = ?",
            [group_id, year],
        )


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_chart_payload(conn, chart_id: str) -> dict:
    """Fetch and parse chart payload from base_charts."""
    chart = get_base_chart_by_id(conn, chart_id)
    if not chart:
        return {}
    p = chart.get("payload") if isinstance(chart, dict) else None
    if p is None:
        return {}
    try:
        return p if isinstance(p, dict) else json.loads(p or "{}")
    except Exception:
        return {}


# ── Children Timing ───────────────────────────────────────────────────────────

@router.get("/groups/{group_id}/children-timing")
def get_children_timing(
    group_id: str,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    if year_from is None:
        year_from = date.today().year
    if year_to is None:
        year_to = date.today().year + 3
    user_id = user["id"]
    with get_conn() as conn:
        group = _assert_group_owner(conn, group_id, user_id)
        # Find husband and wife payloads
        member_rows = conn.execute("""
            SELECT id, chart_id, role, display_name FROM family_members
            WHERE group_id = ? AND role IN ('husband', 'wife')
        """, [group_id]).fetchall()
        husband_payload = {}
        wife_payload = {}
        for row in member_rows:
            if row[2] == "husband":
                husband_payload = _get_chart_payload(conn, str(row[1]))
            elif row[2] == "wife":
                wife_payload = _get_chart_payload(conn, str(row[1]))
        if not husband_payload or not wife_payload:
            raise HTTPException(status_code=400, detail="Children timing requires both husband and wife charts")
        result = run_children_timing(
            group_id=group_id,
            husband_payload=husband_payload,
            wife_payload=wife_payload,
            year_from=year_from,
            year_to=year_to,
            db=conn,
        )
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.delete("/groups/{group_id}/children-timing", status_code=204)
def clear_children_timing_cache(
    group_id: str,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    if year_from is None:
        year_from = date.today().year
    if year_to is None:
        year_to = date.today().year + 3
    user_id = user["id"]
    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)
        conn.execute(
            "DELETE FROM family_children_timing WHERE group_id = ? AND year_from = ? AND year_to = ?",
            [group_id, year_from, year_to],
        )


# ── Timeline ──────────────────────────────────────────────────────────────────

@router.get("/groups/{group_id}/timeline")
def get_family_timeline(
    group_id: str,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    if from_year is None:
        from_year = date.today().year
    if to_year is None:
        to_year = date.today().year + 5
    user_id = user["id"]
    with get_conn() as conn:
        group = _assert_group_owner(conn, group_id, user_id)
        members_with_charts = _load_members_with_charts(conn, group_id)
        if not members_with_charts:
            raise HTTPException(status_code=400, detail="No valid member charts found")
        result = build_timeline(
            group={"id": group_id, "name": group["name"]},
            members_with_charts=members_with_charts,
            from_year=from_year,
            to_year=to_year,
            db=conn,
        )
    return result


@router.delete("/groups/{group_id}/timeline", status_code=204)
def clear_timeline_cache(
    group_id: str,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    if from_year is None:
        from_year = date.today().year
    if to_year is None:
        to_year = date.today().year + 5
    user_id = user["id"]
    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)
        conn.execute(
            "DELETE FROM family_timeline_cache WHERE group_id = ? AND from_year = ? AND to_year = ?",
            [group_id, from_year, to_year],
        )


# ── Child Predictions ─────────────────────────────────────────────────────────

@router.get("/groups/{group_id}/members/{member_id}/predictions")
def get_child_predictions(
    group_id: str,
    member_id: str,
    year: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    if year is None:
        year = date.today().year
    user_id = user["id"]
    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)
        member_row = conn.execute("""
            SELECT id, chart_id, role, display_name FROM family_members
            WHERE id = ? AND group_id = ?
        """, [member_id, group_id]).fetchone()
        if not member_row:
            raise HTTPException(status_code=404, detail="Member not found")
        if str(member_row[2]) != "child":
            raise HTTPException(status_code=400, detail="Child predictions only available for child members")
        payload = _get_chart_payload(conn, str(member_row[1]))
        result = run_child_prediction(
            member_id=member_id,
            chart_payload=payload,
            year=year,
            db=conn,
        )
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.get("/groups/{group_id}/children-timing/pdf")
def get_children_timing_pdf(
    group_id: str,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    """Render children timing analysis as PDF."""
    if year_from is None:
        year_from = date.today().year
    if year_to is None:
        year_to = date.today().year + 3
    data = get_children_timing(group_id, year_from, year_to, user)

    from app.pdf.family_report.family_pdf_renderer import render_children_timing_pdf
    with get_conn() as conn:
        group = _assert_group_owner(conn, group_id, user["id"])
    try:
        pdf_bytes = render_children_timing_pdf(
            group_name=group["name"],
            year_from=year_from,
            year_to=year_to,
            data=data,
        )
    except Exception as e:
        logger.error(f"Children timing PDF render failed: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="children_timing_{year_from}_{year_to}.pdf"'
        },
    )


@router.get("/groups/{group_id}/members/{member_id}/predictions/pdf")
def get_child_predictions_pdf(
    group_id: str,
    member_id: str,
    year: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    """Render child prediction as PDF."""
    if year is None:
        year = date.today().year
    data = get_child_predictions(group_id, member_id, year, user)

    with get_conn() as conn:
        member_row = conn.execute(
            "SELECT display_name FROM family_members WHERE id = ? AND group_id = ?",
            [member_id, group_id],
        ).fetchone()
    child_name = (member_row[0] if member_row and member_row[0] else None) or "Child"

    from app.pdf.family_report.family_pdf_renderer import render_child_prediction_pdf
    try:
        pdf_bytes = render_child_prediction_pdf(
            child_name=child_name,
            year=year,
            data=data,
        )
    except Exception as e:
        logger.error(f"Child prediction PDF render failed: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="child_prediction_{child_name}_{year}.pdf"'
        },
    )


@router.delete("/groups/{group_id}/members/{member_id}/predictions", status_code=204)
def clear_child_predictions_cache(
    group_id: str,
    member_id: str,
    year: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    if year is None:
        year = date.today().year
    user_id = user["id"]
    with get_conn() as conn:
        _assert_group_owner(conn, group_id, user_id)
        conn.execute(
            "DELETE FROM family_child_predictions WHERE member_id = ? AND year = ?",
            [member_id, year],
        )
