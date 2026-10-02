# tests/engines/test_truncation_flag.py
"""
A reply that hit max_tokens and was JSON-repaired must not be
indistinguishable from a clean success (2026-10-02). The provider now
reports usage_info["truncated"] / ["json_repaired"]; natal/KP store such a
reply as fallback_reason="truncated" (retried, cooldown-bounded) instead of
caching it as success -- reproduced on the old code: the repaired partial
reply was cached and served forever.
"""
import inspect
from types import SimpleNamespace
from unittest.mock import patch

import anthropic

from app.llm.providers import anthropic_provider


def _fake(text, stop_reason):
    return SimpleNamespace(content=[SimpleNamespace(text=text)], stop_reason=stop_reason,
                           usage=SimpleNamespace(input_tokens=100, output_tokens=50))


def _call(text, stop_reason):
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "x"}), \
         patch.object(anthropic.resources.messages.Messages, "create", return_value=_fake(text, stop_reason)):
        return anthropic_provider.call_llm("sys", "user", 50)


def test_truncated_and_repaired_reply_is_flagged():
    parsed, usage, err = _call('{"a": {"b": 1}, "c": "done"', "max_tokens")
    assert err is None and parsed == {"a": {"b": 1}, "c": "done"}
    assert usage["truncated"] is True and usage["json_repaired"] is True and usage["stop_reason"] == "max_tokens"


def test_clean_reply_is_not_flagged():
    parsed, usage, err = _call('{"a": 1}', "end_turn")
    assert parsed == {"a": 1} and usage["truncated"] is False and usage["json_repaired"] is False


def test_natal_and_kp_never_cache_a_truncated_reply_as_success():
    from app.api import natal_interpretation as nat
    for fn, saver in ((nat.get_natal_interpretation, "_save_cache("), (nat.get_kp_interpretation, "_save_kp_cache(")):
        src = inspect.getsource(fn)
        i = src.index('.get("truncated")')
        assert '"truncated"' in src[i:i + 600] and saver in src[i:i + 600]


def test_orchestrator_stores_truncated_reply_as_truncated_not_success():
    """Monthly/yearly/weekly (2026-10-02): a truncated reply that still passes
    validation was stored as a clean success (the f5da25da yearly case).
    Reproduced on the old code; now fallback_reason="truncated", content
    kept, and it counts toward the retry cooldown like any failed call."""
    import app.engines.llm_interpretation_orchestrator as orch
    usage = {"prompt_tokens": 13000, "completion_tokens": 5000, "total_tokens": 18000, "model": "m", "truncated": True}
    with patch.object(orch, "is_llm_enabled", return_value=True), \
         patch.object(orch, "_check_cache", return_value=None), \
         patch.object(orch, "retry_cooldown_status", return_value=None), \
         patch.object(orch, "get_monthly_token_usage", return_value={"remaining": 10**6, "used": 0, "budget": 10**6, "percent_used": 0}), \
         patch.object(orch.openai_provider, "is_available", return_value=True), \
         patch.object(orch, "extract_payload_inputs", return_value={}), \
         patch.object(orch, "build_generation_payload", return_value={"x": 1}), \
         patch.object(orch, "validate_payload_size", return_value=(True, "ok", 10)), \
         patch.object(orch, "_validate_llm_output", return_value=True), \
         patch.object(orch.openai_provider, "call_openai", return_value=({"executive_summary": {}}, usage, None)), \
         patch.object(orch, "_persist_interpretation") as persist:
        out = orch.generate_llm_interpretation("c", {}, {}, {"det": 1}, 2026, "yearly", "2026")
    assert out["llm_metadata"]["fallback_reason"] == "truncated"
    assert out["llm_interpretation"]["_truncated"] is True and "executive_summary" in out["llm_interpretation"]
    args = persist.call_args[0]
    assert args[11] == "truncated" and args[9] == 18000   # fallback_reason, total_tokens (counts for cooldown)
