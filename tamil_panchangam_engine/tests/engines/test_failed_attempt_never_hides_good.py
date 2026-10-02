# tests/engines/test_failed_attempt_never_hides_good.py
"""
A failed LLM attempt must never replace a previously good stored result
(2026-10-02). prediction_llm_interpretation is append-only; every reader used
to take the newest row, so a failed retry (json_parse_error, llm_disabled...)
buried a good report -- 966f5254's yearly 2026 PDF served deterministic
fallback text for 23 minutes. Reproduced on real data before the fix.
"""
from unittest.mock import MagicMock, patch

import app.engines.llm_interpretation_orchestrator as orch

GOOD = {"content": {"engine_version": "ai-interpretation-v7.0"}, "fallback_reason": None, "reflection_text": None}
FAILED = {"content": {"engine_version": "ai-interpretation-v1.0"}, "fallback_reason": "json_parse_error", "reflection_text": None}


def _conn_returning(row):
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = row
    cm = MagicMock()
    cm.__enter__.return_value = conn
    return cm, conn


def test_reader_prefers_newest_success_over_newer_failure():
    cm, conn = _conn_returning(('{"engine_version": "v7"}', None, None))
    with patch.object(orch, "get_conn", return_value=cm):
        row = orch.load_stored_interpretation("c", "yearly", "2026")
    sql = conn.execute.call_args[0][0]
    assert "ORDER BY (fallback_reason IS NULL) DESC, created_at DESC" in sql
    assert row["content"] == {"engine_version": "v7"} and row["fallback_reason"] is None


def test_check_cache_serves_success_and_never_a_fallback():
    with patch.object(orch, "load_stored_interpretation", return_value=GOOD):
        assert orch._check_cache("c", "yearly", "2026", "prediction", "v7", "full") == GOOD["content"]
    for reason in ("json_parse_error", "llm_disabled", "budget_exceeded"):
        with patch.object(orch, "load_stored_interpretation", return_value={**FAILED, "fallback_reason": reason}):
            assert orch._check_cache("c", "yearly", "2026", "prediction", "v7", "full") is None


def test_llm_disabled_serves_existing_good_result_without_writing_a_fallback():
    with patch.object(orch, "is_llm_enabled", return_value=False), \
         patch.object(orch, "load_stored_interpretation", return_value=GOOD), \
         patch.object(orch, "_persist_interpretation") as persist:
        out = orch.generate_llm_interpretation("c", {}, {}, {"det": 1}, 2026, "yearly", "2026", explainability_mode="full")
    assert out["llm_interpretation"] == GOOD["content"]
    persist.assert_not_called()


def test_readers_use_the_shared_reader():
    import inspect
    from app.api import chat, prediction
    from app.pdf.canonical_report import data_loader
    assert "load_stored_interpretation" in inspect.getsource(data_loader.load_cached_llm_interpretation)
    assert "load_stored_interpretation" in inspect.getsource(prediction.generate_monthly_prediction)
    assert "load_stored_interpretation" in inspect.getsource(chat._build_chat_context) or \
        "load_stored_interpretation" in inspect.getsource(chat)


def test_monthly_background_writer_keeps_good_interpretation_on_failed_retry():
    from app.api import prediction as pred
    existing = {"interpretation": {"llm_interpretation": {"engine_version": "v7"}, "llm_metadata": {"fallback_reason": None}},
                "envelope": {}, "synthesis": {}}
    failed = {"llm_interpretation": {"engine_version": "v1"}, "llm_metadata": {"fallback_reason": "json_parse_error"}}
    with patch.object(pred, "generate_llm_interpretation", return_value=failed), \
         patch.object(pred, "get_monthly_prediction", return_value=existing), \
         patch.object(pred, "save_monthly_prediction") as save:
        pred._run_llm_background("c", {}, {}, {}, 2026, 10, {})
    save.assert_not_called()
