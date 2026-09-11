# tests/engines/test_window_summary_momentum.py
"""
2026-09-11 front/back Overview-contradiction investigation: the v4-v7
front narrative (payload_builder.py's extract_payload_inputs) reads
each life area's actual weighted score directly, but the deterministic
"Overview" text (ai_interpretation_engine.py's _generate_window_summary)
derived its momentum from an independently recomputed pos/neg count over
top_signals -- which structurally excludes yoga/dasha-activation signals
(life_area_scorer.py gives them zero weight since they carry no
house/planet field, so they never enter top_signals). Traced against 4
real charts spanning avg scores 57-77: all four produced "pressure"
regardless of how positive the actual score was.

Fixed by having momentum (_momentum_from_score) read the same average
per-area score the front narrative and life-area labels already use,
instead of recomputing an independent, incomplete signal count.

fixtures_base_chart_{high,low}_score.json are real base_chart payloads
pulled from the dev DB (birth_details.name anonymized; all astrological
data real) -- the highest- and lowest-scoring charts found across a
scan of every chart x 4 months in that DB (avg 77.0 and 53.2
respectively; no real chart there ever averaged below 45, so the
"pressure" band's real-pipeline behavior is exercised only up to the
"consolidation" boundary here -- the band below that is covered by the
direct _momentum_from_score() unit tests instead, which is fine since
it's a pure function over a single float, not a data-shape fixture that
could be unrepresentative the way a hand-approximated JSON payload
would be. Same reasoning as fixtures_monthly_payload_inputs.json in
tests/llm/test_payload_size_validation.py -- real chart data run
through the real pipeline, not a fabricated fixture, so this test would
have actually caught tonight's bug.
"""

import json
import unittest
from pathlib import Path

from app.services.prediction_engine import run_prediction_pipeline
from app.engines.ai_interpretation_engine import _momentum_from_score, _determine_outcome_mode

FIXTURES_DIR = Path(__file__).parent

PRESSURE_WORDS = ["obstacle", "delay", "challenging", "pressure", "testing phase", "karmic pressure"]
GROWTH_WORDS = ["ease", "smoothness", "expansion", "advancement", "rising trajectory", "progressive momentum"]


def _load_chart(name: str) -> dict:
    with open(FIXTURES_DIR / f"fixtures_base_chart_{name}.json") as f:
        return json.load(f)


class TestMomentumFromScoreThresholds(unittest.TestCase):
    """Pure-function threshold tests -- avg_score is a plain float, so
    there's no data-shape fixture to get wrong here (unlike the real-
    chart tests below, which exist to catch a wiring bug between the
    real scoring pipeline and this function)."""

    def test_high_score_is_growth(self):
        self.assertEqual(_momentum_from_score(77.0), "growth")
        self.assertEqual(_momentum_from_score(65.0), "growth")

    def test_mid_score_is_consolidation(self):
        self.assertEqual(_momentum_from_score(57.0), "consolidation")
        self.assertEqual(_momentum_from_score(45.0), "consolidation")

    def test_low_score_is_pressure(self):
        self.assertEqual(_momentum_from_score(44.9), "pressure")
        self.assertEqual(_momentum_from_score(20.0), "pressure")

    def test_outcome_mode_follows_momentum(self):
        self.assertEqual(_determine_outcome_mode("growth"), "ease")
        self.assertEqual(_determine_outcome_mode("pressure"), "delay")
        self.assertEqual(_determine_outcome_mode("consolidation"), "effort")


class TestOverviewMatchesRealScoreEndToEnd(unittest.TestCase):
    """Runs the real envelope -> synthesis -> ai_interpretation pipeline
    against real chart data -- this is the test that would have caught
    the original bug, since it exercises the actual wiring between the
    real per-area scores and the Overview text, not a mocked score."""

    def test_high_scoring_real_chart_overview_is_not_pressure_framed(self):
        payload = _load_chart("high_score")
        result = run_prediction_pipeline(base_chart=payload, period_type="monthly", year=2026, month=10)

        life_areas = result["synthesis"]["life_areas"]
        avg_score = sum(la["score"] for la in life_areas.values()) / len(life_areas)
        self.assertGreater(avg_score, 75, "fixture drifted -- expected a clearly high-scoring chart")

        window_summary = result["interpretation"]["ai_interpretation"]["window_summary"]
        self.assertEqual(window_summary["momentum"], "growth")
        self.assertEqual(window_summary["outcome_mode"], "ease")
        overview_lower = window_summary["overview"].lower()
        for word in PRESSURE_WORDS:
            self.assertNotIn(word, overview_lower, f"high-scoring chart's Overview used pressure framing: {word!r}")

    def test_lower_scoring_real_chart_overview_is_not_growth_framed(self):
        payload = _load_chart("low_score")
        result = run_prediction_pipeline(base_chart=payload, period_type="monthly", year=2026, month=10)

        life_areas = result["synthesis"]["life_areas"]
        avg_score = sum(la["score"] for la in life_areas.values()) / len(life_areas)
        self.assertLess(avg_score, 60, "fixture drifted -- expected a clearly lower-scoring chart")

        window_summary = result["interpretation"]["ai_interpretation"]["window_summary"]
        self.assertEqual(window_summary["momentum"], "consolidation")
        self.assertEqual(window_summary["outcome_mode"], "effort")
        overview_lower = window_summary["overview"].lower()
        for word in GROWTH_WORDS:
            self.assertNotIn(word, overview_lower, f"lower-scoring chart's Overview used growth framing: {word!r}")

    def test_high_and_low_chart_overviews_use_correct_article(self):
        """Regression for the 'a expansion'/'a integration period' bug
        this fix exposed -- unreachable before since only the always-
        selected "pressure" phrases happened to start with a consonant."""
        for name in ("high_score", "low_score"):
            payload = _load_chart(name)
            result = run_prediction_pipeline(base_chart=payload, period_type="monthly", year=2026, month=10)
            overview = result["interpretation"]["ai_interpretation"]["window_summary"]["overview"]
            self.assertNotIn(" a expansion", overview)
            self.assertNotIn(" a integration period", overview)
            self.assertNotIn(" a advancement", overview)


if __name__ == "__main__":
    unittest.main()
