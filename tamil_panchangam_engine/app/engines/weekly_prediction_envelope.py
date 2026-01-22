"""
EPIC-9 — Weekly Prediction Envelope

Adapter layer.

Principles:
- Reuse monthly envelope plumbing (no duplication of astrology logic)
- Make the *weekly reference* explicit (ISO week Monday)
- Annotate metadata for downstream interpretation/explainability
"""

from datetime import datetime, timezone, date
from typing import Dict, Any

from app.engines.prediction_envelope import build_monthly_prediction_envelope


def _week_start_utc(year: int, week: int) -> datetime:
    """
    ISO week Monday at 00:00 UTC (stdlib only).
    """
    d = date.fromisocalendar(year, week, 1)  # Monday
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)


def build_weekly_prediction_envelope(
    *,
    base_chart: Dict[str, Any],
    year: int,
    week: int,
) -> Dict[str, Any]:
    """
    Build a weekly prediction envelope.

    CURRENT BEHAVIOR (INTENTIONAL, EPIC-9):
    - Delegates to monthly envelope for core facts computation
    - Adds weekly reference metadata

    NOTE:
    Monthly envelope currently anchors to a month reference date.
    This weekly adapter chooses the *month containing ISO-week Monday*.
    """

    # ----------------------------
    # Guardrails (API boundary)
    # ----------------------------
    if not isinstance(base_chart, dict):
        raise TypeError(
            f"base_chart must be a dict payload, got {type(base_chart)}"
        )

    if "birth_details" not in base_chart:
        raise KeyError(
            "base_chart payload missing required key: 'birth_details'"
        )

    # ----------------------------
    # Weekly reference
    # ----------------------------
    week_ref_utc = _week_start_utc(year, week)

    # Delegate to monthly envelope (reuse core logic)
    month = week_ref_utc.month

    envelope = build_monthly_prediction_envelope(
        base_chart=base_chart,  # MUST be full payload
        year=year,
        month=month,
    )

    # ----------------------------
    # Weekly annotations (facts only)
    # ----------------------------
    envelope["reference"]["week"] = week
    envelope["reference"]["period_type"] = "weekly"
    envelope["reference"]["week_reference_date_utc"] = (
        week_ref_utc.isoformat()
    )

    return envelope
