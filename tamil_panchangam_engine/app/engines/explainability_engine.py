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
    navamsa: dict | None = None,
) -> ExplainabilityBlock:
    """
    EPIC-8 + EPIC-3 (Explainability layer)

    Deterministic explainability builder.
    - No astrology interpretation
    - No life areas
    - Evidence-only drivers
    """

    drivers: List[ExplainabilityDriver] = []

    # -------------------------------------------------
    # Dasha overlap metrics
    # -------------------------------------------------
    overlap = dasha_context.get("overlap", {})
    coverage_ratio = overlap.get("coverage_ratio", 0.0)
    dominant_segment = overlap.get("dominant_segment")

    active = dasha_context.get("active") or {}

    # Build dominant dasha string with null safety
    maha = active.get("maha") or {}
    antar = active.get("antar") or {}
    pratyantar = active.get("pratyantar") or {}
    
    dominant_dasha = "–".join(
        filter(None, [
            maha.get("lord", ""),
            antar.get("lord", ""),
            pratyantar.get("lord", ""),
        ])
    )

    # -------------------------------------------------
    # DRIVER: Dasha overlap dominance
    # -------------------------------------------------
    if coverage_ratio >= 0.7 and dominant_segment:
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

    # -------------------------------------------------
    # DRIVER: Dasha stability (no transitions)
    # -------------------------------------------------
    transitions = dasha_context.get("transitions", {})
    if transitions and not any(transitions.values()):
        drivers.append(
            ExplainabilityDriver(
                type="DASHA_STABILITY",
                label="No major dasha transitions during this period",
                evidence=transitions,
            )
        )

    # -------------------------------------------------
    # DRIVER: Period granularity
    # -------------------------------------------------
    drivers.append(
        ExplainabilityDriver(
            type="PERIOD_GRANULARITY",
            label=f"Prediction computed at {period_type} granularity",
            evidence={"period_type": period_type},
        )
    )

    # -------------------------------------------------
    # EPIC-3 ADDITIVE DRIVER: Navamsa (D9) dignity
    # -------------------------------------------------
    if navamsa:
        dignity = navamsa.get("dignity", {})
        active_maha = maha.get("lord")

        if active_maha and active_maha in dignity:
            dignity_value = dignity[active_maha]

            confidence_effect = (
                "reinforced" if dignity_value == "exalted"
                else "reduced" if dignity_value == "debilitated"
                else "neutral"
            )

            drivers.append(
                ExplainabilityDriver(
                    type="NAVAMSA_DIGNITY",
                    label=f"Navamsa dignity of active dasha lord: {dignity_value}",
                    evidence={
                        "planet": active_maha,
                        "dignity": dignity_value,
                        "confidence_effect": confidence_effect,
                    },
                )
            )

    # -------------------------------------------------
    # SUMMARY (period-aware, deterministic)
    # -------------------------------------------------
    score = confidence.get("overall", confidence.get("score", 0.0))

    if period_type == "yearly":
        if score >= 0.65:
            summary = (
                "Higher confidence period driven by stable long-term dasha influences. "
                "Yearly predictions reflect broad themes rather than short-term events."
            )
        else:
            summary = (
                "Moderate confidence year with evolving dasha influences. "
                "Use this prediction to guide long-term direction rather than timing."
            )

    elif period_type == "weekly":
        summary = (
            "Lower confidence due to short-term planetary and dasha fluctuations. "
            "Weekly predictions emphasize timing and momentum rather than outcomes."
        )

    else:  # monthly (default)
        if score >= 0.75:
            summary = (
                "High confidence month driven by stable and dominant dasha overlap."
            )
        elif score >= 0.55:
            summary = (
                "Moderate confidence month with mixed dasha influences shaping outcomes."
            )
        else:
            summary = (
                "Lower confidence month due to competing or shifting dasha influences."
            )

    return ExplainabilityBlock(
        summary=summary,
        dominant_dasha=dominant_dasha,
        drivers=drivers,
        transit_highlights=[],  # EPIC-8 keeps this empty
    )
