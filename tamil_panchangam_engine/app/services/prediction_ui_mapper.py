from datetime import datetime
from app.models.report_schema import PredictionReportSnapshot
from app.models.ui_prediction_schema import (
    MonthlyPredictionUIModel,
    UIMeta,
    UIIdentity,
    UILifeArea,
    UITiming,
    UIChartMeta,
)


LIFE_AREA_LABELS = {
    "career": "Career",
    "finance": "Finance",
    "relationships": "Relationships",
    "health": "Health",
    "personal_growth": "Personal Growth",
}


def score_to_sentiment(score: int) -> str:
    if score >= 70:
        return "Strong"
    if score >= 55:
        return "Supportive"
    if score >= 40:
        return "Mixed"
    return "Challenging"


def build_monthly_prediction_ui_model(
    snapshot: PredictionReportSnapshot,
) -> MonthlyPredictionUIModel:
    """
    EPIC-7.2.1
    Convert PredictionReportSnapshot → UI Read Model.
    No astrology logic. No recomputation.
    """

    # -----------------------------
    # META
    # -----------------------------
    meta = UIMeta(
        generated_at=snapshot.metadata.generated_at,
        engine_version=snapshot.metadata.engine_versions["prediction"],
        period_label=f"{snapshot.monthly_prediction['month']:02d}/{snapshot.monthly_prediction['year']}",
    )

    # -----------------------------
    # IDENTITY
    # -----------------------------
    birth = snapshot.base_chart["birth_details"]

    identity = UIIdentity(
        name=birth["name"],
        place_of_birth=birth["place_of_birth"],
        birth_date=birth["date_of_birth"],
        moon_sign=snapshot.base_chart["ephemeris"]["moon"]["rasi"],
        lagna=snapshot.base_chart["ephemeris"]["lagna"]["rasi"],
    )

    # -----------------------------
    # OVERVIEW
    # -----------------------------
    scores = [
        v["score"]
        for v in snapshot.monthly_prediction["synthesis"]["life_areas"].values()
    ]

    avg_score = int(sum(scores) / len(scores))

    overview = {
        "headline": "A balanced month with steady progress.",
        "confidence": 0.9,
        "overall_score": avg_score,
        "tone": score_to_sentiment(avg_score),
    }

    # -----------------------------
    # LIFE AREAS
    # -----------------------------
    life_areas = []

    synthesis_areas = snapshot.monthly_prediction["synthesis"]["life_areas"]
    interpretation_areas = snapshot.monthly_prediction["interpretation"]["by_life_area"]

    for key, synth in synthesis_areas.items():
        interp = interpretation_areas[key]

        life_areas.append(
            UILifeArea(
                key=key,
                label=LIFE_AREA_LABELS[key],
                score=synth["score"],
                confidence=synth["confidence"],
                sentiment=score_to_sentiment(synth["score"]),
                summary=interp["text"].split(".")[0] + ".",
                detail=interp["text"],
            )
        )

    # -----------------------------
    # TIMING
    # -----------------------------
    pakshi = snapshot.monthly_prediction["envelope"]["biological_rhythm"]["pancha_pakshi_daily"]

    timing = UITiming(
        dominant_pakshi=pakshi["dominant_pakshi"],
        recommended=pakshi["recommended_activities"],
        avoid=pakshi["avoid_activities"],
    )

    # -----------------------------
    # CHARTS
    # -----------------------------
    charts = [
        UIChartMeta(type=k, label=v, available=True)
        for k, v in {
            "D1": "Rasi Chart",
            "panchangam": "Birth Panchangam",
        }.items()
    ]

    # -----------------------------
    # FINAL MODEL
    # -----------------------------
    return MonthlyPredictionUIModel(
        meta=meta,
        identity=identity,
        overview=overview,
        life_areas=life_areas,
        timing=timing,
        charts=charts,
        disclaimers=[
            "Astrological guidance is interpretive, not deterministic.",
            "Use this report as supportive insight, not absolute prediction.",
        ],
    )


# --------------------------------------------------
# 🔑 BACKWARD-COMPATIBLE ALIAS (EPIC-7.3 expects this)
# --------------------------------------------------
def map_snapshot_to_ui_read_model(
    snapshot: PredictionReportSnapshot,
) -> MonthlyPredictionUIModel:
    return build_monthly_prediction_ui_model(snapshot)
