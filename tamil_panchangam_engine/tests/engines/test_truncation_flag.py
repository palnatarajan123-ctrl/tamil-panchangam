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
