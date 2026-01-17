"""
EPIC-4.3 — Yearly Prediction Envelope

Adapter layer.

Principles:
- Reuse monthly envelope logic
- Explicit yearly reference metadata
- No astrology computation here
"""

from app.engines.prediction_envelope import build_monthly_prediction_envelope


def build_yearly_prediction_envelope(
    *,
    base_chart: dict,
    year: int
) -> dict:
    """
    Build a yearly prediction envelope.

    CURRENT BEHAVIOR (INTENTIONAL):
    - Uses January as reference month
    - Year-level interpretation handled downstream
    """

    envelope = build_monthly_prediction_envelope(
        base_chart=base_chart,
        year=year,
        month=1,
    )

    envelope["reference"]["period_type"] = "yearly"
    envelope["reference"]["year"] = year
    envelope["reference"]["year_reference_month"] = 1

    return envelope
