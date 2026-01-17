from typing import List
from app.schemas.explainability import (
    ExplainabilityBlock,
    ExplainabilityDriver,
)


def build_explainability(
    *,
    dasha_context: dict,
    confidence: dict,
    period_type: str,
) -> ExplainabilityBlock:
    """
    EPIC-8 explainability builder.

    Deterministic.
    No astrology interpretation.
    No life areas.
    """

    drivers: List[ExplainabilityDriver] = []

    overlap = dasha_context.get("overlap", {})
    coverage_ratio = overlap.get("coverage_ratio", 0.0)
    dominant_segment = overlap.get("dominant_segment")

    active = dasha_context.get("active", {})

    dominant_dasha = "–".join(
        [
            active.get("maha", {}).get("lord", ""),
            active.get("antara", {}).get("lord", ""),
            active.get("pratyantara", {}).get("lord", ""),
        ]
    ).strip("–")

    # ---------------------------------------------
    # DRIVER: Dasha overlap dominance
    # ---------------------------------------------
    if coverage_ratio >= 0.7:
        drivers.append(
            ExplainabilityDriver(
                type="DASHA_OVERLAP",
                label=f"{dominant_segment.capitalize()} dasha dominates most of the period",
                evidence={
                    "coverage_ratio": round(coverage_ratio, 2),
                    "dominant_segment": dominant_segment,
                },
            )
        )

    # ---------------------------------------------
    # DRIVER: Stability (no transitions)
    # ---------------------------------------------
    transitions = dasha_context.get("transitions", {})
    if not any(transitions.values()):
        drivers.append(
            ExplainabilityDriver(
                type="DASHA_STABILITY",
                label="No major dasha transitions during this period",
                evidence=transitions,
            )
        )

    # ---------------------------------------------
    # DRIVER: Period granularity
    # ---------------------------------------------
    drivers.append(
        ExplainabilityDriver(
            type="PERIOD_GRANULARITY",
            label=f"Prediction computed at {period_type} granularity",
            evidence={"period_type": period_type},
        )
    )

    # ---------------------------------------------
    # SUMMARY (deterministic template)
    # ---------------------------------------------
    score = confidence.get("score", 0.0)

    if score >= 0.75:
        summary = "High confidence period driven by stable and dominant dasha overlap."
    elif score >= 0.55:
        summary = "Moderate confidence period with mixed dasha influence."
    else:
        summary = "Lower confidence period due to competing or shifting dasha influences."

    return ExplainabilityBlock(
        summary=summary,
        dominant_dasha=dominant_dasha,
        drivers=drivers,
        transit_highlights=[],  # EPIC-8 keeps this empty
    )
