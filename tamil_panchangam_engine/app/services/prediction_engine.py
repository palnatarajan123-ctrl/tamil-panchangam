"""
UI-facing prediction orchestration service.

IMPORTANT:
- This is NOT a computation engine
- It delegates to existing prediction pipelines
- Exists to satisfy UI + API contracts
"""

from typing import Literal, Dict, Any
from datetime import datetime

from app.engines.prediction_envelope import build_monthly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope
from app.engines.interpretation_engine import build_interpretation_from_synthesis
from app.engines.paraphrasing_engine import paraphrase_interpretation
from app.engines.explainability_engine import build_explainability
from app.engines.ai_interpretation_engine import generate_interpretation as generate_ai_interpretation


# -------------------------------------------------
# Functional pipeline (source of truth)
# -------------------------------------------------

def run_prediction_pipeline(
    *,
    base_chart: Dict[str, Any],
    period_type: Literal["monthly"],
    year: int,
    month: int,
) -> Dict[str, Any]:
    if period_type != "monthly":
        raise NotImplementedError("Only monthly supported")

    envelope = build_monthly_prediction_envelope(
        base_chart=base_chart,
        year=year,
        month=month,
    )

    synthesis = synthesize_from_envelope(envelope)

    interpretation = build_interpretation_from_synthesis(
        envelope=envelope,
        synthesis=synthesis,
    )

    ai_interpretation = generate_ai_interpretation(
        envelope=envelope,
        synthesis=synthesis,
        year=year,
        month=month,
    )

    interpretation = paraphrase_interpretation(interpretation)
    interpretation["ai_interpretation"] = ai_interpretation

    explainability = build_explainability(
        dasha_context=envelope["dasha_context"],
        confidence=synthesis["confidence"],
        period_type="monthly",
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "envelope": envelope,
        "synthesis": synthesis,
        "interpretation": interpretation,
        "ai_interpretation": ai_interpretation,
        "explainability": explainability.model_dump(),
    }


# -------------------------------------------------
# Class wrapper (API / UI compatibility)
# -------------------------------------------------

class PredictionEngine:
    """
    Compatibility wrapper expected by predictions_ui.py.
    DO NOT put logic here.
    """

    @staticmethod
    def run_monthly(
        *,
        base_chart: Dict[str, Any],
        year: int,
        month: int,
    ) -> Dict[str, Any]:
        return run_prediction_pipeline(
            base_chart=base_chart,
            period_type="monthly",
            year=year,
            month=month,
        )
# -------------------------------------------------
# EPIC-6 UI Context (Compatibility Object)
# -------------------------------------------------

class Epic6PredictionContext:
    """
    UI-facing aggregation context used by predictions_ui.

    This is NOT a computation object.
    It exists only to bundle prediction outputs
    in a stable, typed structure.
    """

    def __init__(
        self,
        *,
        period_type: str,
        envelope: dict,
        synthesis: dict,
        interpretation: dict,
        explainability: dict,
    ):
        self.period_type = period_type
        self.envelope = envelope
        self.synthesis = synthesis
        self.interpretation = interpretation
        self.explainability = explainability

    def to_dict(self) -> dict:
        return {
            "period_type": self.period_type,
            "envelope": self.envelope,
            "synthesis": self.synthesis,
            "interpretation": self.interpretation,
            "explainability": self.explainability,
        }
