"""
EPIC-9 — Weekly Prediction Envelope

Adapter layer.

Principles:
- Reuse monthly envelope plumbing (no duplication of astrology logic)
- Make the *weekly reference* explicit (ISO week Monday)
- Annotate metadata for downstream interpretation/explainability
"""

from datetime import datetime, timezone, date

from app.engines.prediction_envelope import build_monthly_prediction_envelope


def _week_start_utc(year: int, week: int) -> datetime:
    """
    ISO week Monday at 00:00 UTC (stdlib only).
    """
    d = date.fromisocalendar(year, week, 1)  # Monday
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)


def build_weekly_prediction_envelope(
    *,
    base_chart: dict,
    year: int,
    week: int
) -> dict:
    """
    Build a weekly prediction envelope.

    CURRENT BEHAVIOR (INTENTIONAL, EPIC-9):
    - Delegates to monthly envelope for core facts computation
    - Adds weekly reference metadata

    NOTE:
    Monthly envelope currently anchors to a month reference date.
    This weekly adapter chooses the *month containing ISO-week Monday*.
    If you want true week-window transits later, we’ll add a shared
    envelope builder that accepts reference_date_utc without changing contracts.
    """

    week_ref_utc = _week_start_utc(year, week)

    # Delegate to monthly envelope (reuse)
    month = week_ref_utc.month

    envelope = build_monthly_prediction_envelope(
        base_chart=base_chart,
        year=year,
        month=month,
    )

    # Weekly annotations (facts/metadata only)
    envelope["reference"]["week"] = week
    envelope["reference"]["period_type"] = "weekly"
    envelope["reference"]["week_reference_date_utc"] = week_ref_utc.isoformat()

    return envelope
