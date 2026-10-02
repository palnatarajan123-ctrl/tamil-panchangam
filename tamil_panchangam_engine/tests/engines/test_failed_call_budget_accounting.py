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
    """_persist_interpretation logs every attempt through log_llm_call(),
    which writes the token ledger too (success or failure)."""
    conn = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = conn
    with patch.object(orch, "get_conn", return_value=cm), patch.object(orch, "log_llm_call") as log:
        orch._persist_interpretation("c", "yearly", "2026", "prediction", "v7", "anthropic", "m",
                                     12900, 4000, 16900, {"det": 1}, "json_parse_error", "full")
    kw = log.call_args.kwargs
    assert kw["input_tokens"] == 12900 and kw["output_tokens"] == 4000
    assert kw["status"] == "error" and kw["prompt_version"] == "v7"


def test_auto_pause_rechecked_after_a_failed_call_that_cost_money():
    db = MagicMock()
    with patch.object(bg, "_check_budget") as check:
        bg.log_llm_call(db, "c", "prediction", "yearly/2026", 12900, 4000, status="error", fallback_reason="json_parse_error")
    check.assert_called_once()


def test_log_llm_call_writes_both_ledgers_and_is_the_only_token_writer():
    """2026-10-02: the token budget reflects ALL real spend. log_llm_call()
    (which every LLM call site already uses) now also writes llm_token_usage
    via record_token_usage(), so chat, family chat, dasha summary, daily
    guidance, porutham commentary and the family/children/child engines all
    count -- and no site can log one ledger and forget the other."""
    import inspect
    import app.api.natal_interpretation as nat
    db = MagicMock()
    with patch.object(bg, "_check_budget"):
        bg.log_llm_call(db, "c", "chat", "chat", 3000, 400, prompt_version=None)
    sqls = [c[0][0] for c in db.execute.call_args_list]
    assert any("INSERT INTO llm_calls" in q for q in sqls) and any("INSERT INTO llm_token_usage" in q for q in sqls)
    token_row = next(c[0][1] for c in db.execute.call_args_list if "llm_token_usage" in c[0][0])
    assert token_row[1:] == ["chat", "n/a", 3400]
    db.reset_mock()
    bg.record_token_usage(db, "kp_natal", "kp-v1.0", 0)
    db.execute.assert_not_called()
    for fn in (nat._save_cache, nat._save_kp_cache, orch._persist_interpretation):
        src = inspect.getsource(fn)
        assert "record_token_usage(" not in src and "INSERT INTO llm_token_usage" not in src, fn.__name__
        assert "prompt_version=" in src, fn.__name__


def test_interrupted_stream_logs_partial_cost_not_zero():
    from types import SimpleNamespace
    stream = SimpleNamespace(current_message_snapshot=SimpleNamespace(usage=SimpleNamespace(input_tokens=2500, output_tokens=0)))
    assert bg.partial_stream_usage(stream, "x" * 400) == (2500, 100)
    broken = SimpleNamespace()
    assert bg.partial_stream_usage(broken, "") == (0, 0)
