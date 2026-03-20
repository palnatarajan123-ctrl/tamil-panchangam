from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from typing import Any, Dict
import json

from app.db.session import get_db
from app.repositories.base_chart_repo import get_base_chart_by_id
from app.repositories.prediction_repo import get_monthly_prediction

from app.engines.prediction_envelope import build_monthly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope
from app.engines.interpretation_engine import build_interpretation_from_synthesis
from app.engines.paraphrasing_engine import paraphrase_interpretation
from app.engines.explainability_engine import build_explainability
from app.engines.ai_interpretation_engine import generate_interpretation as generate_ai_interpretation
from app.engines.explainability_filter import apply_explainability


router = APIRouter(prefix="/prediction", tags=["Prediction"])


def _normalize_confidence(synthesis: Dict[str, Any]) -> Dict[str, Any]:
    """
    EPIC-7 guardrail: ensure confidence exists even if engines omit it.
    API layer only — do not move into engines.
    """
    if "confidence" not in synthesis or synthesis["confidence"] is None:
        synthesis["confidence"] = {
            "overall": 0.6,
            "variance": 0.0,
            "active_lords": [],
        }
    elif isinstance(synthesis["confidence"], (int, float)):
        synthesis["confidence"] = {
            "overall": float(synthesis["confidence"]),
            "variance": 0.0,
            "active_lords": [],
        }
    return synthesis


@router.post("/weekly")
def generate_weekly_prediction(payload: dict, db=Depends(get_db)):
    """
    Weekly prediction — derives from the corresponding monthly prediction.

    Rules:
    - No separate LLM call; reuses or builds the monthly envelope
    - If the monthly prediction is cached in DB, return it directly
    - If not cached, build envelope + deterministic AI interpretation only
    - Monthly remains the system of record (weekly is not persisted)
    """

    base_chart_id = payload.get("base_chart_id")
    year = payload.get("year")
    week = payload.get("week")

    if not base_chart_id or year is None or week is None:
        raise HTTPException(
            status_code=400,
            detail="Missing base_chart_id, year, or week"
        )

    # Map ISO week → approximate month (used for monthly cache lookup)
    approx_month = min(12, max(1, (int(week) - 1) // 4 + 1))

    # --------------------------------------------------
    # Try to return existing monthly prediction for this period
    # --------------------------------------------------
    existing = get_monthly_prediction(
        base_chart_id=base_chart_id,
        year=int(year),
        month=approx_month,
    )

    if existing:
        envelope = json.loads(existing["envelope"])
        synthesis = json.loads(existing["synthesis"])
        interpretation = (
            json.loads(existing["interpretation"])
            if existing.get("interpretation")
            else {}
        )
        # Ensure full explainability on cached AI interpretation
        if interpretation and "ai_interpretation" in interpretation:
            interpretation["ai_interpretation"] = apply_explainability(
                interpretation["ai_interpretation"], "full"
            )

        explainability = build_explainability(
            dasha_context=envelope.get("dasha_context", {}),
            confidence=synthesis.get("confidence"),
            period_type="weekly",
        )

        prediction_id = f"weekly:{base_chart_id}:{int(year)}:{int(week)}"
        return {
            "id": prediction_id,
            "base_chart_id": base_chart_id,
            "year": int(year),
            "week": int(week),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
            "summary": None,
            "cache_hit": True,
            "details": {
                "envelope": envelope,
                "synthesis": synthesis,
                "interpretation": interpretation,
            },
            "explainability": (
                explainability.model_dump()
                if hasattr(explainability, "model_dump")
                else explainability
            ),
        }

    # --------------------------------------------------
    # No monthly cache — fetch base chart and build
    # envelope + deterministic AI only (no LLM call)
    # --------------------------------------------------
    base_chart_record = get_base_chart_by_id(db, base_chart_id)

    if not base_chart_record:
        raise HTTPException(status_code=404, detail="Birth chart not found")

    raw_payload = (
        base_chart_record["payload"]
        if isinstance(base_chart_record, dict)
        else base_chart_record.payload
    )
    base_chart_payload = (
        json.loads(raw_payload)
        if isinstance(raw_payload, str)
        else raw_payload
    )

    envelope = build_monthly_prediction_envelope(
        base_chart=base_chart_payload,
        year=int(year),
        month=approx_month,
    )

    synthesis = synthesize_from_envelope(envelope)
    synthesis = _normalize_confidence(synthesis)

    # Normalise life_areas shape (mirrors monthly endpoint fix)
    life_areas = synthesis.get("life_areas")
    if isinstance(life_areas, dict) and "scores" in life_areas:
        synthesis = {**synthesis, "life_areas": life_areas["scores"]}

    interpretation = build_interpretation_from_synthesis(
        envelope=envelope,
        synthesis=synthesis,
    )
    interpretation = paraphrase_interpretation(interpretation)

    # Deterministic AI interpretation only — no LLM call
    ai_interpretation = generate_ai_interpretation(
        envelope=envelope,
        synthesis=synthesis,
        year=int(year),
        month=approx_month,
    )
    ai_interpretation = apply_explainability(ai_interpretation, "full")
    interpretation["ai_interpretation"] = ai_interpretation

    explainability = build_explainability(
        dasha_context=envelope["dasha_context"],
        confidence=synthesis.get("confidence"),
        period_type="weekly",
    )

    prediction_id = f"weekly:{base_chart_id}:{int(year)}:{int(week)}"

    summary = None
    if isinstance(interpretation, dict):
        summary = interpretation.get("summary") or interpretation.get("headline")

    return {
        "id": prediction_id,
        "base_chart_id": base_chart_id,
        "year": int(year),
        "week": int(week),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "summary": summary,
        "cache_hit": False,
        "details": {
            "envelope": envelope,
            "synthesis": synthesis,
            "interpretation": interpretation,
        },
        "explainability": (
            explainability.model_dump()
            if hasattr(explainability, "model_dump")
            else explainability
        ),
    }
