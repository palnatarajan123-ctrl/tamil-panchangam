# app/engines/timeline_aggregator.py
"""
Timeline Aggregator Engine.
Aggregates multi-member Dasha + Sade Sati + milestone data into a
time-series structure for the frontend SVG timeline.
No LLM calls. Pure computation.
Cache: family_timeline_cache table.
"""

import json
import logging
import uuid
from datetime import date

from app.engines.dasha_resolver import resolve_antar_dasha
from app.engines.sade_sati_engine import compute_sade_sati

logger = logging.getLogger(__name__)

MEMBER_COLORS = {
    "husband": "#3B82F6",
    "wife":    "#EC4899",
    "child":   "#8B5CF6",
    "other":   "#6B7280",
}

PLANET_COLORS = {
    "Sun": "#F59E0B", "Moon": "#93C5FD", "Mars": "#EF4444",
    "Mercury": "#34D399", "Jupiter": "#F97316", "Venus": "#F9A8D4",
    "Saturn": "#8B5CF6", "Rahu": "#374151", "Ketu": "#6B7280",
}


def _date_to_str(d) -> str:
    if isinstance(d, str):
        return d[:10]
    if hasattr(d, 'isoformat'):
        return d.isoformat()[:10]
    return str(d)


def _build_dasha_track(vimshottari, from_year: int, to_year: int) -> list:
    """
    Build Dasha period bars from vimshottari dict.
    vimshottari is a dict with "timeline" key. Each entry has:
      mahadasha, start, end, antar_dashas: [{antar_lord, start, end}]
    """
    if not vimshottari or not isinstance(vimshottari, dict):
        return []
    range_start = date(from_year, 1, 1)
    range_end = date(to_year, 12, 31)
    bars = []
    timeline = vimshottari.get("timeline", [])
    for maha in timeline:
        if not isinstance(maha, dict):
            continue
        maha_lord = maha.get("mahadasha", "")
        maha_start_raw = maha.get("start", "")
        maha_end_raw = maha.get("end", "")
        try:
            maha_start = date.fromisoformat(str(maha_start_raw)[:10])
            maha_end = date.fromisoformat(str(maha_end_raw)[:10])
        except Exception:
            continue
        if maha_start > range_end or maha_end < range_start:
            continue

        antar_dashas = maha.get("antar_dashas", [])
        if isinstance(antar_dashas, list) and antar_dashas:
            for antar in antar_dashas:
                if not isinstance(antar, dict):
                    continue
                antar_lord = antar.get("antar_lord", "")
                antar_start_raw = antar.get("start", "")
                antar_end_raw = antar.get("end", "")
                try:
                    antar_start = date.fromisoformat(str(antar_start_raw)[:10])
                    antar_end = date.fromisoformat(str(antar_end_raw)[:10])
                except Exception:
                    continue
                if antar_start > range_end or antar_end < range_start:
                    continue
                eff_start = max(antar_start, range_start)
                eff_end = min(antar_end, range_end)
                bars.append({
                    "from": _date_to_str(eff_start),
                    "to": _date_to_str(eff_end),
                    "mahadasha": maha_lord,
                    "antardasha": antar_lord,
                    "color": PLANET_COLORS.get(maha_lord, "#6B7280"),
                    "label": f"{maha_lord} \u203a {antar_lord}",
                })
        else:
            eff_start = max(maha_start, range_start)
            eff_end = min(maha_end, range_end)
            bars.append({
                "from": _date_to_str(eff_start),
                "to": _date_to_str(eff_end),
                "mahadasha": maha_lord,
                "antardasha": "",
                "color": PLANET_COLORS.get(maha_lord, "#6B7280"),
                "label": maha_lord,
            })
    return bars


def _build_sade_sati_track(payload: dict, from_year: int, to_year: int) -> list:
    try:
        ss_result = compute_sade_sati(payload)
    except Exception:
        return []
    if not ss_result or not isinstance(ss_result, dict):
        return []
    ss = ss_result.get("sade_sati", {})
    if not isinstance(ss, dict) or not ss.get("active"):
        return []
    start_raw = ss.get("start_date") or ss.get("start") or f"{from_year}-01-01"
    end_raw = ss.get("end_date") or ss.get("end") or ss.get("current_phase_ends") or f"{to_year}-12-31"
    return [{
        "from": _date_to_str(start_raw),
        "to": _date_to_str(end_raw),
        "phase": ss.get("phase", "active"),
        "active": True,
    }]


def _build_milestone_track(vimshottari, from_year: int, to_year: int, cached_milestones: list = None) -> list:
    milestones = []
    range_start = date(from_year, 1, 1)
    range_end = date(to_year, 12, 31)
    if vimshottari and isinstance(vimshottari, dict):
        timeline = vimshottari.get("timeline", [])
        for maha in timeline:
            if not isinstance(maha, dict):
                continue
            start_raw = maha.get("start", "")
            try:
                t = date.fromisoformat(str(start_raw)[:10])
                if range_start <= t <= range_end:
                    milestones.append({
                        "date": _date_to_str(t),
                        "type": "dasha_transition",
                        "label": f"{maha.get('mahadasha', '')} Mahadasha begins",
                        "significance": "high",
                        "plain_english": f"Start of {maha.get('mahadasha', '')} Mahadasha period.",
                    })
            except Exception:
                pass
    if cached_milestones:
        for m in cached_milestones:
            milestones.append({
                "date": m.get("date") or m.get("period", ""),
                "type": m.get("type", "milestone"),
                "label": m.get("label", ""),
                "significance": m.get("significance", "medium"),
                "plain_english": m.get("plain_english", ""),
            })
    return milestones


def _find_shared_events(members_data: list, from_year: int, to_year: int, cached_caution_windows: list = None) -> list:
    shared = []
    if cached_caution_windows:
        for w in cached_caution_windows:
            members = w.get("members_affected", [])
            if len(members) >= 2:
                shared.append({
                    "period": w.get("period", ""),
                    "type": "shared_caution",
                    "members_involved": members,
                    "label": w.get("theme", "Caution period").title(),
                    "significance": w.get("intensity", "moderate"),
                    "plain_english": w.get("plain_english", ""),
                    "remedy_hint": w.get("remedy_hint", ""),
                })
    return shared


def build_timeline(
    group: dict,
    members_with_charts: list,
    from_year: int,
    to_year: int,
    db,
) -> dict:
    group_id = group["id"]

    # Cache check (positional tuple access)
    try:
        existing = db.execute("""
            SELECT timeline_data FROM family_timeline_cache
            WHERE group_id = ? AND from_year = ? AND to_year = ?
        """, [group_id, from_year, to_year]).fetchone()
    except Exception as e:
        logger.warning(f"Timeline cache check failed: {e}")
        existing = None

    if existing:
        try:
            data = json.loads(existing[0])
            data["cached"] = True
            return data
        except Exception:
            pass

    # Fetch cached caution windows from last family prediction
    cached_caution_windows = []
    try:
        pred_row = db.execute("""
            SELECT caution_windows FROM family_predictions
            WHERE group_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, [group_id]).fetchone()
        if pred_row and pred_row[0]:
            cached_caution_windows = json.loads(pred_row[0]) if isinstance(pred_row[0], str) else (pred_row[0] or [])
    except Exception:
        pass

    members_output = []
    for item in members_with_charts:
        member = item["member"]
        payload = item["payload"]
        role = member.get("role", "other")
        name = (member.get("display_name") or
                (payload.get("birth_details", {}).get("name", role) if isinstance(payload, dict) else role))
        vimshottari = (
            payload.get("dashas", {}).get("vimshottari", {})
            if isinstance(payload, dict) else {}
        )
        dasha_track = _build_dasha_track(vimshottari, from_year, to_year)
        sade_sati_track = _build_sade_sati_track(payload, from_year, to_year)
        milestone_track = _build_milestone_track(vimshottari, from_year, to_year)
        members_output.append({
            "member_id": member["id"],
            "role": role,
            "display_name": name,
            "color": MEMBER_COLORS.get(role, MEMBER_COLORS["other"]),
            "tracks": {
                "dasha": dasha_track,
                "sade_sati": sade_sati_track,
                "milestones": milestone_track,
            },
        })

    shared_events = _find_shared_events(members_output, from_year, to_year, cached_caution_windows)

    timeline_data = {
        "group_id": group_id,
        "group_name": group["name"],
        "from_year": from_year,
        "to_year": to_year,
        "generated_at": date.today().isoformat(),
        "members": members_output,
        "shared_events": shared_events,
        "cached": False,
    }

    try:
        db.execute("""
            INSERT INTO family_timeline_cache
                (id, group_id, from_year, to_year, timeline_data, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (group_id, from_year, to_year) DO UPDATE SET
                timeline_data = EXCLUDED.timeline_data,
                created_at = CURRENT_TIMESTAMP
        """, [str(uuid.uuid4()), group_id, from_year, to_year, json.dumps(timeline_data)])
    except Exception as e:
        logger.error(f"Failed to persist timeline: {e}")

    return timeline_data
