from fastapi import APIRouter, HTTPException

from app.api.prediction import generate_monthly_prediction
from app.engines.interpretation_builder import build_interpretation
from app.engines.paraphraser import paraphrase_interpretation

router = APIRouter()


@router.post("/monthly")
def generate_monthly_interpretation(payload: dict):
    """
    Generate human-readable monthly interpretation.
    This is a PURE consumer of the prediction engine.
    """

    # --------------------------------------------------
    # Step 1️⃣: Call prediction engine internally
    # --------------------------------------------------
    prediction_response = generate_monthly_prediction(payload)

    if not prediction_response:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate prediction"
        )

    # --------------------------------------------------
    # Step 2️⃣: Build interpretation from synthesis
    # --------------------------------------------------
    interpretation = build_interpretation(
        synthesis=prediction_response.synthesis.model_dump(),
        narrative_style="short"
    )

    # --------------------------------------------------
    # Step 3️⃣: Optional paraphrasing (safe)
    # --------------------------------------------------
    interpretation = paraphrase_interpretation(
        interpretation
        # llm_fn injected later (OpenAI, Claude, etc.)
    )

    # --------------------------------------------------
    # Step 4️⃣: Final response (clean & decoupled)
    # --------------------------------------------------
    return {
        "base_chart_id": prediction_response.base_chart_id,
        "target_month": payload.get("target_month"),
        "interpretation": interpretation
    }
