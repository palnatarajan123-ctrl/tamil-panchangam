# tests/engines/test_retry_cooldown.py
"""
Retry cooldown (2026-10-02): after RETRY_COOLDOWN_FAILURES real failed calls
in RETRY_COOLDOWN_HOURS, a never-succeeded report stops calling the LLM on
every view. Smoke-tested live: 3 real failures, then the 4th view made 0
calls and spent 0 tokens; after the window it retried and succeeded.
"""
import inspect
from unittest.mock import MagicMock, patch

import app.engines.llm_interpretation_orchestrator as orch


def _gen(**patches):
    with patch.object(orch, "is_llm_enabled", return_value=True), \
         patch.object(orch, "_check_cache", return_value=None), \
         patch.object(orch.openai_provider, "is_available", return_value=True), \
         patch.object(orch.openai_provider, "call_openai") as call, \
         patch.object(orch, "retry_cooldown_status", return_value=patches.get("cooldown")), \
         patch.object(orch, "get_monthly_token_usage", return_value={"remaining": 0, "used": 1, "budget": 1, "percent_used": 100}), \
         patch.object(orch, "_persist_interpretation") as persist:
        out = orch.generate_llm_interpretation("c", {}, {}, {"det": 1}, 2027, "monthly", "2027-03")
    return out, call, persist


def test_in_cooldown_no_call_no_row():
    out, call, persist = _gen(cooldown={"failures": 3, "retry_after": None})
    assert out["llm_metadata"]["fallback_reason"] == "retry_cooldown"
    assert out["llm_interpretation"] == {"det": 1}
    call.assert_not_called()
    persist.assert_not_called()


def test_not_in_cooldown_proceeds_past_the_check():
    out, call, persist = _gen(cooldown=None)
    # proceeds to the budget gate (patched to "exhausted" so no call is made)
    assert out["llm_metadata"]["fallback_reason"] == "budget_exceeded"


def test_cooldown_counts_only_real_failed_calls_since_last_success():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (2, None)
    cm = MagicMock(); cm.__enter__.return_value = conn
    with patch.object(orch, "get_conn", return_value=cm):
        assert orch.retry_cooldown_status("c", "monthly", "2027-03") is None
    sql = conn.execute.call_args[0][0]
    assert "fallback_reason IS NOT NULL AND COALESCE(total_tokens, 0) > 0" in sql
    assert "fallback_reason IS NULL" in sql  # resets after a success
    assert orch.RETRY_COOLDOWN_FAILURES == 3 and orch.RETRY_COOLDOWN_HOURS == 24


def test_monthly_route_does_not_schedule_a_retry_in_cooldown():
    from app.api import prediction
    src = inspect.getsource(prediction.generate_monthly_prediction)
    assert "retry_cooldown_status(" in src and "and not _in_cooldown" in src
