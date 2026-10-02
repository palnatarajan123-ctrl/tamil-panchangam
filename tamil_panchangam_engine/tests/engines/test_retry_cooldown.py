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


# ── Family prediction / children timing / child prediction (2026-10-02) ──────
# These don't store failed attempts as report rows, but already log every
# failed call (with real tokens) to llm_calls -- the cooldown counts there.

ENGINES = (
    ("app.engines.family_prediction_engine", "run_family_prediction"),
    ("app.engines.children_timing_engine", "run_children_timing"),
    ("app.engines.child_prediction_engine", "run_child_prediction"),
)


def test_llm_call_cooldown_counts_real_failures_since_last_success():
    import app.engines.budget_guard as bg
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (3, None)
    assert bg.llm_call_cooldown(db, "g", "family_prediction", "family_yearly/2028")["failures"] == 3
    sql = db.execute.call_args[0][0]
    assert "status <> 'success' AND COALESCE(total_tokens, 0) > 0" in sql and "status = 'success'" in sql
    db.execute.return_value.fetchone.return_value = (2, None)
    assert bg.llm_call_cooldown(db, "g", "family_prediction", "family_yearly/2028") is None


def test_engines_check_cooldown_before_calling_and_log_success_only_after_parse():
    """Logging "success" before parsing gave every parse failure a success
    row AND an error row -- double-counted in the $ ledger, and the fake
    success reset the cooldown so it never engaged (found in the live smoke)."""
    import importlib
    for mod_name, fn_name in ENGINES:
        src = inspect.getsource(getattr(importlib.import_module(mod_name), fn_name))
        assert src.index("llm_call_cooldown(") < src.index("messages.create("), fn_name
        assert src.index('status="success"') > src.index("json.loads(clean)"), fn_name
