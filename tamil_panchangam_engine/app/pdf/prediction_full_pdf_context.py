"""
Prediction Full PDF Context

Canonical, time-bound context for the Comprehensive Prediction PDF.

This context represents *assembled truth* only.
It must never contain raw envelopes, synthesis internals,
or astrology computation logic.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class PredictionFullPdfContext:
    """
    Immutable context for the Full Prediction Report PDF.
    """

    # -----------------------------
    # Metadata (REQUIRED)
    # -----------------------------
    metadata: Dict[str, str]
    # chart_id, year, generated_at

    # -----------------------------
    # Birth Foundation
    # -----------------------------
    birth_summary: Dict[str, str]
    charts: Dict[str, str]  # d1_svg, d9_svg
    birth_highlights: List[Dict[str, str]]

    # -----------------------------
    # Dasha Context
    # -----------------------------
    dasha_summary: Dict[str, str]
    antar_influence: List[Dict[str, str]]

    # -----------------------------
    # Monthly Predictions (12)
    # -----------------------------
    monthly_predictions: List[Dict]
    # Each item:
    # {
    #   "month": "March 2026",
    #   "theme": "...",
    #   "life_areas": [
    #       {"area": "...", "interpretation": "...", "confidence": "..."}
    #   ],
    #   "timing": {
    #       "supportive_windows": [...],
    #       "caution_windows": [...]
    #   }
    # }

    # -----------------------------
    # Explainability
    # -----------------------------
    explainability: List[Dict[str, str]]

    # -----------------------------
    # Remedies & Recommendations
    # -----------------------------
    remedies: List[Dict[str, str]]

    # -----------------------------
    # AI Layer (Optional – EPIC-16)
    # -----------------------------
    ai_explanation: Optional[str] = None

    # -----------------------------
    # Versioning (DEFAULT — MUST BE LAST)
    # -----------------------------
    pdf_context_version: str = "prediction-full-v1"
