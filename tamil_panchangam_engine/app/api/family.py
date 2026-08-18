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
import os
import uuid
from datetime import date, datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.db.postgres import get_conn
from app.repositories.base_chart_repo import get_base_chart_by_id
from app.engines.porutham_engine import compute_porutham
from app.llm.payload_builder import _extract_nak_rasi, _get_or_compute_porutham, _format_porutham_lines
from app.engines.sade_sati_engine import compute_sade_sati
from app.engines.dasha_resolver import resolve_antar_dasha
from app.engines.budget_guard import log_llm_call
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


# _extract_nak_rasi moved to app.llm.payload_builder (2026-08-17) so
# app.engines.family_prediction_engine can share it without a circular
# import (this module imports run_family_prediction from that engine).


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
    husband_id = None
    wife_id = None
    for row in rows:
        member_id = str(row[0])
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
            husband_id = member_id
        elif role == "wife" and wife is None:
            wife = member_info
            wife_id = member_id

    if not husband:
        raise HTTPException(status_code=422, detail="Group has no husband member")
    if not wife:
        raise HTTPException(status_code=422, detail="Group has no wife member")
    if not husband["nakshatra"] or not husband["rasi"]:
        raise HTTPException(status_code=422, detail="Husband chart missing nakshatra/rasi data")
    if not wife["nakshatra"] or not wife["rasi"]:
        raise HTTPException(status_code=422, detail="Wife chart missing nakshatra/rasi data")

    id1, id2 = husband_id, wife_id

    # Check cache
    with get_conn() as conn:
        cached_row = conn.execute("""
            SELECT result_json FROM family_porutham_cache
            WHERE group_id = %s
              AND ((member_id_1 = %s AND member_id_2 = %s)
                OR (member_id_1 = %s AND member_id_2 = %s))
            LIMIT 1
        """, (group_id, id1, id2, id2, id1)).fetchone()

    if cached_row:
        result_json = cached_row[0] if isinstance(cached_row[0], dict) else json.loads(cached_row[0])
        return result_json

    result = compute_porutham(
        boy_nakshatra=husband["nakshatra"], boy_rasi=husband["rasi"],
        girl_nakshatra=wife["nakshatra"], girl_rasi=wife["rasi"],
    )

    full_result = {
        "husband": husband,
        "wife": wife,
        "porutham": result,
    }

    # Cache result
    try:
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO family_porutham_cache
                    (group_id, member_id_1, member_id_2, result_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (group_id, member_id_1, member_id_2) DO UPDATE
                SET result_json = EXCLUDED.result_json,
                    computed_at = NOW()
            """, (group_id, id1, id2, json.dumps(full_result)))
            conn.commit()
    except Exception as e:
        logger.warning(f"Porutham cache write failed: {e}")

    return full_result


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


def _resolve_porutham_for_pdf(members_with_charts: list, group_id: str):
    """
    Resolve (porutham, husband_name, wife_name) for the family PDF, or
    (None, None, None) if there's no husband+wife pairing / no resolvable
    result. Extracted from what was inline in get_family_predictions_pdf()
    so it's directly testable, mirroring the _build_porutham_chat_block()
    extraction pattern from Phase F2.

    Uses _get_or_compute_porutham() (payload_builder.py) -- the same
    cache-first lookup Phase F1/F2 already use, not a fourth copy.

    members_with_charts: list of {"member": {...with "id"/"role"/
      "display_name"...}, "payload": {...}} dicts, the shape
      _load_members_with_charts() returns (used by this endpoint,
      different from family_group_chat_stream()'s raw row tuples --
      that's why this isn't shared with _build_porutham_chat_block()
      despite doing conceptually the same thing).
    """
    husband_item = next((i for i in members_with_charts if i["member"]["role"] == "husband"), None)
    wife_item = next((i for i in members_with_charts if i["member"]["role"] == "wife"), None)
    if not husband_item or not wife_item:
        return None, None, None

    try:
        h_payload = husband_item["payload"] if isinstance(husband_item["payload"], dict) else {}
        w_payload = wife_item["payload"] if isinstance(wife_item["payload"], dict) else {}
        h_nak, h_rasi = _extract_nak_rasi(h_payload)
        w_nak, w_rasi = _extract_nak_rasi(w_payload)
        husband_name = husband_item["member"].get("display_name") or h_payload.get("birth_details", {}).get("name", "Husband")
        wife_name = wife_item["member"].get("display_name") or w_payload.get("birth_details", {}).get("name", "Wife")
        with get_conn() as conn:
            porutham = _get_or_compute_porutham(
                conn, group_id,
                str(husband_item["member"].get("id")), husband_name, h_nak, h_rasi,
                str(wife_item["member"].get("id")), wife_name, w_nak, w_rasi,
            )
        return porutham, husband_name, wife_name
    except Exception as e:
        logger.warning(f"Porutham lookup failed for family PDF: {e}")
        return None, None, None


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

    porutham, husband_name, wife_name = _resolve_porutham_for_pdf(members_with_charts, group_id)

    try:
        pdf_bytes = render_family_pdf(
            group_name=group["name"],
            member_names=member_names,
            year=year,
            prediction=prediction,
            porutham=porutham,
            husband_name=husband_name,
            wife_name=wife_name,
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

def generate_timeline_summary(
    group: dict,
    members_with_charts: list,
    from_year: int,
    to_year: int,
    db,
) -> Optional[str]:
    """Generate an LLM summary of the family's collective dasha landscape."""
    group_id = group["id"]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        budget_row = db.execute(
            "SELECT llm_enabled, paused_reason FROM llm_budget WHERE id = 1"
        ).fetchone()
        if budget_row and not budget_row[0]:
            return None
    except Exception as e:
        logger.warning(f"Budget check failed: {e}")

    # Cache check
    try:
        row = db.execute(
            "SELECT summary FROM family_timeline_cache WHERE group_id = %s "
            "AND from_year = %s AND to_year = %s AND summary IS NOT NULL",
            [group_id, from_year, to_year]
        ).fetchone()
        if row:
            return row[0]
    except Exception as e:
        logger.warning(f"Timeline summary cache read failed: {e}")

    # Build member context using resolve_antar_dasha
    now = datetime.now(timezone.utc)
    member_lines = []
    for item in members_with_charts:
        name = item["member"].get("display_name") or item["member"].get("role", "Member")
        payload = item["payload"]
        vimshottari = payload.get("dashas", {}).get("vimshottari", {})
        sade_sati = payload.get("sade_sati", {}).get("phase_name", "Not active")

        dasha = resolve_antar_dasha(vimshottari=vimshottari, reference_date=now)
        if dasha:
            mahadasha = dasha["maha"]["lord"]
            antardasha = dasha["antar"]["lord"]
        else:
            mahadasha = "Unknown"
            antardasha = "Unknown"

        member_lines.append(
            f"- {name}: Mahadasha: {mahadasha} | Antardasha: {antardasha} "
            f"| Sade Sati: {sade_sati}"
        )

    # Prompt
    system_prompt = (
        "You are a Vedic astrology advisor. Write in warm, clear language. "
        "No bullet points. No markdown. No headers."
    )
    user_message = (
        f"Given this family's planetary periods from {from_year} to {to_year}:\n\n"
        + "\n".join(member_lines)
        + f"\n\nWrite a 2-3 sentence summary of their collective dasha landscape "
        f"for this period. Be specific to their actual dashas — name the planets. "
        f"End with exactly this format on a new line: Collective Theme: [one phrase]"
    )

    # LLM call
    input_tokens = 0
    output_tokens = 0
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        summary = response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Timeline summary LLM call failed: {e}")
        try:
            log_llm_call(
                db=db,
                chart_id=group_id,
                call_type="timeline_summary",
                period=f"{from_year}_{to_year}",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                status="error",
                fallback_reason=str(e)[:100],
            )
        except Exception:
            pass
        return None

    # Log success
    try:
        log_llm_call(
            db=db,
            chart_id=group_id,
            call_type="timeline_summary",
            period=f"{from_year}_{to_year}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            status="success",
        )
    except Exception as e:
        logger.warning(f"log_llm_call failed: {e}")

    # Cache write
    try:
        db.execute(
            "UPDATE family_timeline_cache SET summary = %s "
            "WHERE group_id = %s AND from_year = %s AND to_year = %s",
            [summary, group_id, from_year, to_year]
        )
    except Exception as e:
        logger.warning(f"Timeline summary cache write failed: {e}")

    return summary


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
        try:
            summary = generate_timeline_summary(
                group={"id": group_id, "name": group["name"]},
                members_with_charts=members_with_charts,
                from_year=from_year,
                to_year=to_year,
                db=conn,
            )
            result["summary"] = summary
        except Exception as e:
            logger.error(f"Timeline summary generation failed: {e}")
            result["summary"] = None
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


# ── Family Chat ───────────────────────────────────────────────────────────────

class _FamilyChatMessage(BaseModel):
    role: str
    content: str


class _FamilyChatRequest(BaseModel):
    base_chart_id: str
    question: str
    history: list[_FamilyChatMessage] = []
    # TODO: add reading_as_name: str | None = None when member-focused context needed


def _build_family_yearly_block(group_id: str) -> str:
    """
    Fetch the current year's cached family prediction and return a compact
    system-prompt block (≤200 tokens). Returns "" if not available.
    """
    year = datetime.now(timezone.utc).year
    try:
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT executive_summary, caution_windows, financial_peaks
                FROM family_predictions
                WHERE group_id = %s AND year = %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (group_id, year),
            ).fetchone()
        if not row:
            return ""
        exec_summary, caution_windows, financial_peaks = row

        lines = ["## THIS YEAR'S FAMILY FORECAST (already computed)"]

        if exec_summary:
            lines.append(f"Executive Summary: {exec_summary[:300]}")

        if isinstance(caution_windows, list) and caution_windows:
            lines.append(
                "Caution Windows: "
                + ", ".join(str(w)[:80] for w in caution_windows[:3])
            )

        if isinstance(financial_peaks, list) and financial_peaks:
            lines.append(
                "Financial Peaks: "
                + ", ".join(str(f)[:80] for f in financial_peaks[:3])
            )

        return "\n".join(lines) if len(lines) > 1 else ""
    except Exception as e:
        logger.warning(f"Failed to fetch family yearly block for {group_id}: {e}")
        return ""


_FAMILY_CHAT_SYSTEM_PROMPT = """You are Jyotishi, a warm family astrologer advising {group_name}.

FAMILY MEMBERS:
{member_lines}

RESPONSE FORMAT — strictly follow every time:
1. One direct answer in plain English — yes/likely/unlikely/no + one reason why.
2. One practical suggestion the family can act on.
3. One closing line — a memorable takeaway or gentle caution.

RULES:
- For questions about one person, focus on their chart. For family dynamics, consider all.
- Reference members by name, not role.
- If two members have conflicting planetary influences, say so: "Mixed signals between X and Y —"
- 3–5 sentences for direct questions; up to 5 short paragraphs for complex ones.
- No preamble. No restating the question. No generic advice."""


def _build_member_summary(row: tuple) -> str:
    """One compact line per family member for the system prompt."""
    _, role, display_name, _chart_id, payload_raw = row
    payload = payload_raw if isinstance(payload_raw, dict) else json.loads(payload_raw or "{}")
    birth = payload.get("birth_details", {})
    eph = payload.get("ephemeris", {})
    moon = eph.get("moon", {})

    name = display_name or birth.get("name", role)
    lagna = eph.get("lagna", {}).get("rasi", "?")
    moon_rasi = moon.get("rasi", "?")
    nak = moon.get("nakshatra", {})
    nak_name = nak.get("name", "?") if isinstance(nak, dict) else str(nak or "?")

    vimshottari = payload.get("dashas", {}).get("vimshottari", {}) \
        if isinstance(payload.get("dashas"), dict) else {}
    dasha = resolve_antar_dasha(
        vimshottari=vimshottari,
        reference_date=datetime.now(timezone.utc),
    )
    maha = dasha.get("maha", {}).get("lord", "—") if dasha else "—"
    antar = dasha.get("antar", {}).get("lord", "—") if dasha else "—"

    ss = compute_sade_sati(payload)
    ss_data = ss.get("sade_sati", {}) if ss else {}
    ss_suffix = f", Sade Sati active – {ss_data.get('phase_name', '')}" \
        if ss_data.get("active") else ""

    # Yogas + Upagraha (Gulika/Mandi) -- shared with chat.py's
    # _build_family_member_context() (same feature, same cost reasoning,
    # added to both endpoints in the same change). predictive_signals and
    # kp_sublords deliberately NOT included here -- see
    # _build_family_yoga_upagraha_suffix()'s docstring for the full cost
    # reasoning (same as chat.py's Phase 3 fix: per-member expansion of
    # either would multiply DB/cost per message by family size).
    from app.llm.payload_builder import _build_family_yoga_upagraha_suffix
    yoga_upagraha_suffix = _build_family_yoga_upagraha_suffix(payload)

    return (
        f"{role.upper()} {name}: "
        f"Lagna {lagna}, Moon {moon_rasi} ({nak_name}), "
        f"Dasha {maha}›{antar}"
        f"{ss_suffix}"
        f"{yoga_upagraha_suffix}"
    )


def _build_porutham_chat_block(rows: list, group_id: str) -> str:
    """
    Build the couple-level PORUTHAM block for family_group_chat_stream()'s
    system prompt, or "" if there's no husband+wife pair (or no resolvable
    result). Extracted from what was inline in the endpoint so it's
    directly testable without mocking the full async streaming flow --
    mirrors chat.py's _build_family_member_context() extraction pattern.

    rows: the raw (fm.id, fm.role, fm.display_name, fm.chart_id, bc.payload)
      tuples already fetched by the endpoint -- no new query.
    """
    husband_row = next((r for r in rows if r[1] == "husband"), None)
    wife_row = next((r for r in rows if r[1] == "wife"), None)
    if not husband_row or not wife_row:
        return ""

    try:
        h_id, _, h_display, _, h_payload_raw = husband_row
        w_id, _, w_display, _, w_payload_raw = wife_row
        h_payload = h_payload_raw if isinstance(h_payload_raw, dict) else json.loads(h_payload_raw or "{}")
        w_payload = w_payload_raw if isinstance(w_payload_raw, dict) else json.loads(w_payload_raw or "{}")
        h_nak, h_rasi = _extract_nak_rasi(h_payload)
        w_nak, w_rasi = _extract_nak_rasi(w_payload)
        h_name = h_display or h_payload.get("birth_details", {}).get("name", "husband")
        w_name = w_display or w_payload.get("birth_details", {}).get("name", "wife")
        with get_conn() as conn:
            porutham = _get_or_compute_porutham(
                conn, group_id, str(h_id), h_name, h_nak, h_rasi,
                str(w_id), w_name, w_nak, w_rasi,
            )
        porutham_lines = _format_porutham_lines(porutham)
        if not porutham_lines:
            return ""
        return (
            "\n\nPORUTHAM (Husband x Wife compatibility, 10-point Tamil Kuta system):\n"
            + "\n".join(porutham_lines)
        )
    except Exception as e:
        logger.warning(f"Porutham lookup failed for family chat: {e}")
        return ""


@router.post("/groups/{group_id}/chat/stream")
async def family_group_chat_stream(
    group_id: str,
    req: _FamilyChatRequest,
    user: dict = Depends(get_current_user),
):
    """Streaming family chat — all member charts included in LLM context."""
    user_id = user["id"]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM not configured")

    with get_conn() as conn:
        group = _assert_group_owner(conn, group_id, user_id)

        rows = conn.execute("""
            SELECT fm.id, fm.role, fm.display_name, fm.chart_id, bc.payload
            FROM family_members fm
            JOIN base_charts bc ON bc.id = fm.chart_id
            WHERE fm.group_id = %s
            ORDER BY fm.role, fm.birth_order
        """, (group_id,)).fetchall()

        budget_row = conn.execute(
            "SELECT llm_enabled, paused_reason FROM llm_budget WHERE id = 1"
        ).fetchone()

    if not rows:
        raise HTTPException(status_code=400, detail="No members in this family group")

    member_lines = "\n".join(f"- {_build_member_summary(r)}" for r in rows)

    system_prompt = _FAMILY_CHAT_SYSTEM_PROMPT.format(
        group_name=group.get("name", "Family"),
        member_lines=member_lines,
    )

    # Inject cached family yearly interpretation for richer context
    family_block = _build_family_yearly_block(group_id)
    if family_block:
        system_prompt = system_prompt + "\n\n" + family_block

    # Porutham -- couple-level, not per-member, so resolved once here
    # rather than inside _build_member_summary()'s per-row loop. Same
    # cache-first helper as chat.py's family chat and Phase F1's family
    # predictions -- family_porutham_cache is shared across all three, so
    # this never diverges from what the dedicated /porutham endpoint would
    # return for the same pair.
    porutham_block = _build_porutham_chat_block(rows, group_id)
    if porutham_block:
        system_prompt += porutham_block

    history_trimmed = req.history[-12:]
    messages = [{"role": m.role, "content": m.content} for m in history_trimmed]
    messages.append({"role": "user", "content": req.question})

    async def generate():
        if budget_row and not budget_row[0]:
            yield f"data: {json.dumps({'error': 'llm_paused', 'reason': budget_row[1]})}\n\n"
            return

        import anthropic
        full_response: list[str] = []
        input_tokens = 0
        output_tokens = 0
        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    full_response.append(text)
                    yield f"data: {json.dumps({'text': text})}\n\n"
                final_msg = stream.get_final_message()
                input_tokens = final_msg.usage.input_tokens
                output_tokens = final_msg.usage.output_tokens

            with get_conn() as db:
                log_llm_call(
                    db=db,
                    chart_id=req.base_chart_id,
                    call_type="family_chat",
                    period="chat",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    status="success",
                )

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            logger.error(f"Family group chat stream error: {e}")
            try:
                with get_conn() as db:
                    log_llm_call(
                        db=db,
                        chart_id=req.base_chart_id,
                        call_type="family_chat",
                        period="chat",
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        status="error",
                        fallback_reason=str(e)[:100],
                    )
            except Exception:
                pass
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
