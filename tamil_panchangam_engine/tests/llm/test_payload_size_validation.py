# tests/llm/test_payload_size_validation.py
"""
Issue 2 (2026-09-11 regression investigation): Monthly predictions on a
brand-new chart's first generation silently showed the deterministic
"ai-interpretation-v1.0" fallback instead of the real LLM ("v7.0")
result -- looked like a cache/version-selection bug but wasn't. Root
cause: MAX_PROMPT_TOKENS["monthly"] (2000) had gone stale relative to the
payload-building logic's actual typical output size after v7's context
additions (yogas/KP sublords/upagraha/shadbala/divisional signals) --
MAX_TOTAL_TOKENS(8000) - MAX_COMPLETION_TOKENS(5000) already budgets
3000 real prompt tokens, but this explicit sub-cap was never raised to
match. A real chart's built monthly payload measured 2001 estimated
tokens (estimate_tokens() is a crude len//4 heuristic, not an exact
tokenizer -- 2000 left zero margin for that imprecision), tripped
validate_payload_size()'s "prompt_too_large" branch in
llm_interpretation_orchestrator.generate_llm_interpretation(), and fell
back to the deterministic interpretation silently -- no error, no
exception, is_llm_enabled() still reported LLM as on, "existing charts"
generated fine because their cached prediction rows already had a real
v7 result from before this exact edge was hit.

fixtures_monthly_payload_inputs.json is extract_payload_inputs()'s ACTUAL
output for the real chart that reproduced this bug (base_chart_id
11656fc5-..., a genuinely fresh chart created during the investigation,
computed via the real envelope/synthesis pipeline) -- not a hand-
approximated dict. An earlier version of this test used a fabricated
fixture and it measured barely a third the real payload's size (818 vs
2001 estimated tokens) -- nowhere near the threshold it exists to guard,
so it would have passed regardless of whether the fix was in place. This
is the actual data shape that broke; using anything smaller risks
writing a test with no teeth again.

Nothing here existed before (no test file for payload_builder.py's size
validation at all) -- that's the coverage gap that let this through, not
just "a new chart wasn't in the fixture." A fixture built from mocked/
aged chart data would never reproduce this either, because the bug isn't
about chart age -- it's about payload size proximity to a threshold that
had gone stale. These tests guard the threshold itself, not a specific
chart.
"""

import json
import unittest
from pathlib import Path

from app.llm.payload_builder import (
    MAX_PROMPT_TOKENS,
    MAX_COMPLETION_TOKENS,
    MAX_TOTAL_TOKENS,
    build_llm_payload,
    validate_payload_size,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures_monthly_payload_inputs.json"


def _real_monthly_payload_inputs() -> dict:
    with open(FIXTURE_PATH) as f:
        return json.load(f)


class TestMonthlyPayloadSizeThreshold(unittest.TestCase):
    def test_real_new_chart_payload_fits_within_monthly_cap(self):
        payload_inputs = _real_monthly_payload_inputs()
        payload = build_llm_payload(explainability_mode="full", **payload_inputs)
        is_valid, reason, estimated_tokens = validate_payload_size(payload, "monthly")

        # Confirms this fixture actually exercises the boundary the bug
        # lived at, not some comfortably-small payload that would pass
        # regardless of the threshold -- a test with no teeth is worse
        # than no test, since it looks like coverage.
        self.assertGreater(
            estimated_tokens, 1900,
            "Fixture no longer represents a realistically-sized monthly "
            "payload -- this test needs data close to the threshold to "
            "mean anything.",
        )

        self.assertTrue(
            is_valid,
            f"A real new-chart monthly payload ({estimated_tokens} estimated "
            f"tokens) failed validate_payload_size with reason={reason!r} -- this "
            f"is exactly the silent-fallback-to-v1.0 bug (Issue 2). If this starts "
            f"failing again, MAX_PROMPT_TOKENS['monthly'] has gone stale relative "
            f"to payload_builder's actual output size -- raise it, don't just "
            f"accept the fallback.",
        )
        self.assertEqual(reason, "ok")

    def test_monthly_prompt_cap_has_real_margin_under_total_budget(self):
        """Structural guard, not just a point-in-time number check: the
        explicit MAX_PROMPT_TOKENS sub-cap must stay meaningfully under
        what MAX_TOTAL_TOKENS - MAX_COMPLETION_TOKENS already allows.
        Zero or negative margin here is exactly how Issue 2 happened --
        the sub-cap fell behind the real budget instead of tracking it."""
        for period in ("weekly", "monthly", "yearly"):
            implied_ceiling = MAX_TOTAL_TOKENS[period] - MAX_COMPLETION_TOKENS[period]
            margin = implied_ceiling - MAX_PROMPT_TOKENS[period]
            self.assertGreater(
                margin, 0,
                f"{period}: MAX_PROMPT_TOKENS ({MAX_PROMPT_TOKENS[period]}) leaves no "
                f"margin under the total-budget-implied ceiling ({implied_ceiling}) -- "
                f"any estimate_tokens() imprecision (it's a len//4 heuristic, not an "
                f"exact tokenizer) can silently trip the fallback path.",
            )


if __name__ == "__main__":
    unittest.main()
