# app/api/prospects.py
"""
Chart-to-chart Porutham prospects (Phase G1) — compatibility links between
any two charts owned by the same account, independent of family groups.
A prospect link simply exists (no status field) until deleted, and can be
converted into a real family group without recomputing its Porutham.

Routes:
  POST   /api/prospects                               Create a prospect link
  GET    /api/charts/{chart_id}/prospects              List links involving a chart (either direction)
  GET    /api/prospects/{prospect_id}/porutham          Compute/return the Porutham result
  DELETE /api/prospects/{prospect_id}                   Delete the link outright
  POST   /api/prospects/{prospect_id}/convert-to-family  Create a new family group from the pair
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
from app.llm.payload_builder import _extract_nak_rasi
from app.api.family import _chart_owned_by_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Prospects"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class CreateProspectRequest(BaseModel):
    source_chart_id: str
    candidate_chart_id: str
    source_role: str  # "boy" | "girl" -- the other chart gets the opposite role


# ── Helpers ───────────────────────────────────────────────────────────────────

def _can_access_chart(conn, chart_id: str, user: dict) -> bool:
    """Admins retain existing cross-account access to all charts."""
    if user.get("role") == "admin":
        return True
    return _chart_owned_by_user(conn, chart_id, user["id"])


def _resolve_boy_girl_ids(source_chart_id: str, candidate_chart_id: str, source_role: str) -> tuple[str, str]:
    if source_role == "boy":
        return source_chart_id, candidate_chart_id
    return candidate_chart_id, source_chart_id


def _payload_of(chart: dict) -> dict:
    p = chart.get("payload")
    try:
        return p if isinstance(p, dict) else json.loads(p or "{}")
    except Exception:
        return {}


def _get_or_compute_prospect_porutham(conn, prospect_row: tuple) -> Optional[dict]:
    """
    Cache-first Porutham lookup for a prospect link, mirroring
    app.llm.payload_builder._get_or_compute_porutham()'s pattern but keyed
    by prospect_id instead of (group_id, member_id_1, member_id_2) -- a
    prospect link already IS the pairing entity, so the result is cached
    directly on porutham_prospects.result_json rather than a second table.

    prospect_row: (id, source_chart_id, candidate_chart_id, source_role, result_json)
    Returns {"boy": {chart_id, name, nakshatra, rasi}, "girl": {...}, "porutham": {...}},
    or None if either chart or its nakshatra/rasi can't be resolved.
    """
    prospect_id, source_chart_id, candidate_chart_id, source_role, result_raw = prospect_row
    if result_raw:
        return result_raw if isinstance(result_raw, dict) else json.loads(result_raw)

    boy_id, girl_id = _resolve_boy_girl_ids(str(source_chart_id), str(candidate_chart_id), source_role)
    boy_chart = get_base_chart_by_id(conn, boy_id)
    girl_chart = get_base_chart_by_id(conn, girl_id)
    if not boy_chart or not girl_chart:
        return None

    boy_payload = _payload_of(boy_chart)
    girl_payload = _payload_of(girl_chart)
    boy_nak, boy_rasi = _extract_nak_rasi(boy_payload)
    girl_nak, girl_rasi = _extract_nak_rasi(girl_payload)
    if not boy_nak or not boy_rasi or not girl_nak or not girl_rasi:
        return None

    boy_name = boy_payload.get("birth_details", {}).get("name", "")
    girl_name = girl_payload.get("birth_details", {}).get("name", "")

    porutham_result = compute_porutham(
        boy_nakshatra=boy_nak, boy_rasi=boy_rasi,
        girl_nakshatra=girl_nak, girl_rasi=girl_rasi,
    )
    full_result = {
        "boy": {"chart_id": boy_id, "name": boy_name, "nakshatra": boy_nak, "rasi": boy_rasi},
        "girl": {"chart_id": girl_id, "name": girl_name, "nakshatra": girl_nak, "rasi": girl_rasi},
        "porutham": porutham_result,
    }
    try:
        conn.execute(
            "UPDATE porutham_prospects SET result_json = ? WHERE id = ?",
            [json.dumps(full_result), prospect_id],
        )
    except Exception as e:
        logger.warning(f"Prospect porutham cache write failed: {e}")
    return full_result


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/prospects", status_code=201)
def create_prospect(req: CreateProspectRequest, user: dict = Depends(get_current_user)):
    """Create a chart-to-chart prospect link. Both charts must belong to
    the requesting user's account (or the requester is admin)."""
    if req.source_role not in ("boy", "girl"):
        raise HTTPException(status_code=400, detail="source_role must be 'boy' or 'girl'")
    if req.source_chart_id == req.candidate_chart_id:
        raise HTTPException(status_code=400, detail="A chart cannot be checked against itself")

    user_id = user["id"]
    with get_conn() as conn:
        if not _can_access_chart(conn, req.source_chart_id, user):
            raise HTTPException(status_code=403, detail="Source chart not owned by you")
        if not _can_access_chart(conn, req.candidate_chart_id, user):
            raise HTTPException(status_code=403, detail="Candidate chart not owned by you")

        existing = conn.execute("""
            SELECT id FROM porutham_prospects
            WHERE user_id = ?
              AND ((source_chart_id = ? AND candidate_chart_id = ?)
                OR (source_chart_id = ? AND candidate_chart_id = ?))
        """, [user_id, req.source_chart_id, req.candidate_chart_id,
              req.candidate_chart_id, req.source_chart_id]).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="A prospect link already exists between these two charts")

        prospect_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO porutham_prospects
                (id, user_id, source_chart_id, candidate_chart_id, source_role)
            VALUES (?, ?, ?, ?, ?)
        """, [prospect_id, user_id, req.source_chart_id, req.candidate_chart_id, req.source_role])

    return {
        "id": prospect_id,
        "source_chart_id": req.source_chart_id,
        "candidate_chart_id": req.candidate_chart_id,
        "source_role": req.source_role,
    }


@router.get("/charts/{chart_id}/prospects")
def list_prospects_for_chart(chart_id: str, user: dict = Depends(get_current_user)):
    """
    List prospect links involving this chart, shown from BOTH directions --
    a chart can be the 'source' in one link and the 'candidate' in another,
    and from the chart owner's point of view "who initiated the check"
    isn't relevant to seeing their own compatibility-checks list.
    """
    user_id = user["id"]
    with get_conn() as conn:
        if not _can_access_chart(conn, chart_id, user):
            raise HTTPException(status_code=403, detail="Chart not owned by you")

        if user.get("role") == "admin":
            rows = conn.execute("""
                SELECT id, source_chart_id, candidate_chart_id, source_role, result_json, created_at
                FROM porutham_prospects
                WHERE source_chart_id = ? OR candidate_chart_id = ?
                ORDER BY created_at DESC
            """, [chart_id, chart_id]).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, source_chart_id, candidate_chart_id, source_role, result_json, created_at
                FROM porutham_prospects
                WHERE user_id = ? AND (source_chart_id = ? OR candidate_chart_id = ?)
                ORDER BY created_at DESC
            """, [user_id, chart_id, chart_id]).fetchall()

        prospects = []
        for row in rows:
            pid, src_id, cand_id, source_role, result_raw, created_at = row
            other_chart_id = str(cand_id) if str(src_id) == chart_id else str(src_id)

            result = _get_or_compute_prospect_porutham(
                conn, (pid, src_id, cand_id, source_role, result_raw)
            )
            porutham = result.get("porutham") if result else None
            other_name = ""
            if result:
                other_side = result["boy"] if result["boy"]["chart_id"] == other_chart_id else result["girl"]
                other_name = other_side.get("name", "")

            prospects.append({
                "id": str(pid),
                "chart_id": chart_id,
                "other_chart_id": other_chart_id,
                "other_name": other_name,
                "score": porutham.get("total_score") if porutham else None,
                "max_score": porutham.get("max_score") if porutham else None,
                "grade": porutham.get("grade") if porutham else None,
                "created_at": str(created_at),
            })

    return {"prospects": prospects}


@router.get("/prospects/{prospect_id}/porutham")
def get_prospect_porutham(prospect_id: str, user: dict = Depends(get_current_user)):
    """Compute (cache-first) and return the full Porutham breakdown for a prospect link."""
    user_id = user["id"]
    with get_conn() as conn:
        row = conn.execute("""
            SELECT id, user_id, source_chart_id, candidate_chart_id, source_role, result_json
            FROM porutham_prospects WHERE id = ?
        """, [prospect_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prospect not found")
        if user.get("role") != "admin" and str(row[1]) != user_id:
            raise HTTPException(status_code=403, detail="Not your prospect link")

        result = _get_or_compute_prospect_porutham(
            conn, (row[0], row[2], row[3], row[4], row[5])
        )

    if result is None:
        raise HTTPException(
            status_code=422,
            detail="Could not compute Porutham -- missing nakshatra/rasi data on one or both charts",
        )
    return result


@router.delete("/prospects/{prospect_id}", status_code=204)
def delete_prospect(prospect_id: str, user: dict = Depends(get_current_user)):
    """Delete a prospect link outright. No soft-delete/limbo state."""
    user_id = user["id"]
    with get_conn() as conn:
        row = conn.execute(
            "SELECT user_id FROM porutham_prospects WHERE id = ?", [prospect_id]
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prospect not found")
        if user.get("role") != "admin" and str(row[0]) != user_id:
            raise HTTPException(status_code=403, detail="Not your prospect link")
        conn.execute("DELETE FROM porutham_prospects WHERE id = ?", [prospect_id])


@router.post("/prospects/{prospect_id}/convert-to-family", status_code=201)
def convert_prospect_to_family(prospect_id: str, user: dict = Depends(get_current_user)):
    """
    Create a brand-new family group from this prospect's two charts --
    boy -> husband, girl -> wife (source_role's labeling maps directly onto
    family_members' husband/wife roles). Additive, not a merge: doesn't
    check or care whether either chart already belongs to another family
    group elsewhere.

    Single-sided: only the prospect link's owner (or admin) needs to
    trigger this -- the ownership check below intentionally checks only
    the prospect row's owner, not the candidate chart separately, to honor
    that requirement literally (today the two are equivalent anyway, since
    creating a prospect link already requires same-account ownership of
    both charts).

    Carries over the already-computed Porutham result verbatim into the
    new group's family_porutham_cache entry, in the exact shape
    GET /family/groups/{id}/porutham expects (husband/wife dicts with
    name+nakshatra+rasi -- the same shape Phase F1 found and fixed a
    missing-name regression in) -- no recompute, so the score can't drift
    between the prospect view and the new family group's view.

    Leaves the prospect link itself untouched: no delete, no status change.
    """
    user_id = user["id"]
    with get_conn() as conn:
        row = conn.execute("""
            SELECT id, user_id, source_chart_id, candidate_chart_id, source_role, result_json
            FROM porutham_prospects WHERE id = ?
        """, [prospect_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prospect not found")
        prospect_owner_id = str(row[1])
        if user.get("role") != "admin" and prospect_owner_id != user_id:
            raise HTTPException(status_code=403, detail="Not your prospect link")

        result = _get_or_compute_prospect_porutham(
            conn, (row[0], row[2], row[3], row[4], row[5])
        )
        if result is None:
            raise HTTPException(
                status_code=422,
                detail="Could not compute Porutham -- missing nakshatra/rasi data on one or both charts",
            )

        boy = result["boy"]
        girl = result["girl"]
        boy_name = boy["name"] or "Chart"
        girl_name = girl["name"] or "Chart"

        group_id = str(uuid.uuid4())
        group_name = f"{boy_name} & {girl_name}"
        # The new group belongs to the prospect's owning account, not
        # necessarily the requester (an admin could be triggering this on
        # another account's behalf).
        conn.execute("""
            INSERT INTO family_groups (id, user_id, name)
            VALUES (?, ?, ?)
        """, [group_id, prospect_owner_id, group_name])

        husband_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO family_members (id, group_id, chart_id, role, display_name, birth_order)
            VALUES (?, ?, ?, 'husband', ?, 0)
        """, [husband_id, group_id, boy["chart_id"], boy_name])

        wife_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO family_members (id, group_id, chart_id, role, display_name, birth_order)
            VALUES (?, ?, ?, 'wife', ?, 0)
        """, [wife_id, group_id, girl["chart_id"], girl_name])

        family_cache_result = {
            "husband": {"name": boy["name"], "nakshatra": boy["nakshatra"], "rasi": boy["rasi"]},
            "wife": {"name": girl["name"], "nakshatra": girl["nakshatra"], "rasi": girl["rasi"]},
            "porutham": result["porutham"],
        }
        conn.execute("""
            INSERT INTO family_porutham_cache (group_id, member_id_1, member_id_2, result_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (group_id, member_id_1, member_id_2) DO UPDATE
            SET result_json = EXCLUDED.result_json, computed_at = NOW()
        """, [group_id, husband_id, wife_id, json.dumps(family_cache_result)])

    return {"group_id": group_id, "name": group_name, "member_count": 2}
