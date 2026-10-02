# tests/engines/test_failed_call_budget_accounting.py
"""
Failed LLM calls must count against the budget (2026-10-02). The orchestrator
logged 0/0/0 tokens on a provider error (json_parse_error after a truncated
~16k-token call) and excluded every fallback from llm_token_usage, so
LLM_MONTHLY_TOKEN_BUDGET under-counted (~50k tokens in one session).
"""
from unittest.mock import MagicMock, patch

import app.engines.budget_guard as bg
import app.engines.llm_interpretation_orchestrator as orch

USAGE = {"prompt_tokens": 12900, "completion_tokens": 4000, "total_tokens": 16900, "model": "claude-sonnet-4-6"}


def test_provider_error_persists_real_usage():
    with patch.object(orch, "is_llm_enabled", return_value=True), \
         patch.object(orch, "_check_cache", return_value=None), \
         patch.object(orch, "get_monthly_token_usage", return_value={"remaining": 10**6, "used": 0, "budget": 10**6, "percent_used": 0}), \
         patch.object(orch.openai_provider, "is_available", return_value=True), \
         patch.object(orch, "extract_payload_inputs", return_value={}), \
         patch.object(orch, "build_generation_payload", return_value={"x": 1}), \
         patch.object(orch, "validate_payload_size", return_value=(True, "ok", 10)), \
         patch.object(orch.openai_provider, "call_openai", return_value=(None, USAGE, "json_parse_error")), \
         patch.object(orch, "_persist_interpretation") as persist:
        out = orch.generate_llm_interpretation("c", {}, {}, {"det": 1}, 2026, "yearly", "2026")
    assert out["llm_metadata"]["fallback_reason"] == "json_parse_error"
    args = persist.call_args[0]
    assert args[5:10] == ("anthropic", "claude-sonnet-4-6", 12900, 4000, 16900)


def test_failed_attempt_still_counts_in_token_budget_table():
    conn = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = conn
    with patch.object(orch, "get_conn", return_value=cm), patch.object(orch, "log_llm_call") as log:
        orch._persist_interpretation("c", "yearly", "2026", "prediction", "v7", "anthropic", "m",
                                     12900, 4000, 16900, {"det": 1}, "json_parse_error", "full")
    sqls = [call[0][0] for call in conn.execute.call_args_list]
    assert any("INSERT INTO llm_token_usage" in s for s in sqls)
    assert log.call_args.kwargs["input_tokens"] == 12900 and log.call_args.kwargs["status"] == "error"


def test_auto_pause_rechecked_after_a_failed_call_that_cost_money():
    db = MagicMock()
    with patch.object(bg, "_check_budget") as check:
        bg.log_llm_call(db, "c", "prediction", "yearly/2026", 12900, 4000, status="error", fallback_reason="json_parse_error")
    check.assert_called_once()
