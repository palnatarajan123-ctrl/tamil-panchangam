from fastapi import APIRouter, HTTPException, Depends

from app.api.prediction import generate_monthly_prediction
from app.core.auth import get_current_user
from app.engines.interpretation_builder import build_interpretation
from app.engines.paraphraser import paraphrase_interpretation

router = APIRouter()


@router.post("/monthly")
def generate_monthly_interpretation(payload: dict, user: dict = Depends(get_current_user)):
    """
    Generate human-readable monthly interpretation.
    This is a PURE consumer of the prediction engine.

    Auth (security fix, 2026-09-08): this route calls
    generate_monthly_prediction() as a direct Python function call below,
    which does NOT go through FastAPI's route dispatch -- so adding auth
    to prediction.py's own /monthly route does not protect this call path.
    This route needs (and now has) its own independent auth dependency.

    Separately: this call site is currently broken regardless of auth --
    generate_monthly_prediction() is wrapped by a slowapi rate-limit
    decorator that requires its first positional arg to be a real
    starlette Request, but this line passes a plain dict. It throws an
    unhandled exception on every call today. Not fixing that crash here
    (out of scope for the security task), but flagging it since it means
    this endpoint is not currently a *live* bypass either way -- it's
    just also broken. Left as-is per "don't skip ahead" scope discipline;
    the auth fix is what was asked for.
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
