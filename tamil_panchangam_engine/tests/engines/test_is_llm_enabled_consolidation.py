# tests/engines/test_is_llm_enabled_consolidation.py
"""
Part A (2026-09-11 follow-up to the stale-fallback-cache fix): is_llm_enabled()
is THE single source of truth for "may any LLM call be made right now,
anywhere in the app" -- see its own docstring for the full history.
Before this consolidation, it only checked llm_config.llm_enabled (the
admin's manual toggle); a SEPARATE, independent flag,
llm_budget.llm_enabled (the automatic $-spend auto-pause set by
budget_guard._check_budget()), was checked directly via raw SQL in three
places (chat.py once, family.py twice) instead -- meaning those three
call sites never respected the manual toggle except via a best-effort,
swallowed-exception sync in admin_llm.py's /toggle route, and every OTHER
call site (natal_interpretation.py, daily.py, prediction.py, the
orchestrator itself) never respected the budget auto-pause at all.

These tests exercise is_llm_enabled() directly, covering all four
combinations of the two underlying flags, plus get_llm_pause_reason()'s
contract (never a gating decision, only human-facing detail).
"""

import unittest
from unittest.mock import MagicMock, patch

from app.engines.llm_interpretation_orchestrator import is_llm_enabled, get_llm_pause_reason


def _conn_with(*, config_value, budget_row):
    """A mock connection whose first .execute() (llm_config lookup)
    returns config_value via fetchone(), and whose second .execute()
    (llm_budget lookup) returns budget_row."""
    conn = MagicMock()
    config_result = MagicMock()
    config_result.fetchone.return_value = (config_value,) if config_value is not None else None
    budget_result = MagicMock()
    budget_result.fetchone.return_value = budget_row
    conn.execute.side_effect = [config_result, budget_result]
    return conn


def _cm(conn):
    cm = MagicMock()
    cm.__enter__.return_value = conn
    cm.__exit__.return_value = False
    return cm


class TestIsLlmEnabledConsolidation(unittest.TestCase):
    def test_both_enabled_returns_true(self):
        conn = _conn_with(config_value="true", budget_row=(True,))
        with patch("app.engines.llm_interpretation_orchestrator.get_conn", return_value=_cm(conn)):
            self.assertTrue(is_llm_enabled())

    def test_manual_toggle_off_returns_false_even_if_budget_says_on(self):
        conn = _conn_with(config_value="false", budget_row=(True,))
        with patch("app.engines.llm_interpretation_orchestrator.get_conn", return_value=_cm(conn)):
            self.assertFalse(is_llm_enabled())

    def test_budget_auto_pause_returns_false_even_if_manual_toggle_says_on(self):
        """The exact gap this consolidation closes: previously
        is_llm_enabled() didn't check this table at all, so natal-
        interpretation/daily/monthly/yearly would keep calling the LLM
        after a budget auto-pause fired."""
        conn = _conn_with(config_value="true", budget_row=(False,))
        with patch("app.engines.llm_interpretation_orchestrator.get_conn", return_value=_cm(conn)):
            self.assertFalse(is_llm_enabled())

    def test_both_disabled_returns_false(self):
        conn = _conn_with(config_value="false", budget_row=(False,))
        with patch("app.engines.llm_interpretation_orchestrator.get_conn", return_value=_cm(conn)):
            self.assertFalse(is_llm_enabled())

    def test_missing_rows_default_to_enabled_fail_open(self):
        conn = _conn_with(config_value=None, budget_row=None)
        with patch("app.engines.llm_interpretation_orchestrator.get_conn", return_value=_cm(conn)):
            self.assertTrue(is_llm_enabled())

    def test_db_error_fails_open_not_closed(self):
        conn = MagicMock()
        conn.execute.side_effect = Exception("db unavailable")
        with patch("app.engines.llm_interpretation_orchestrator.get_conn", return_value=_cm(conn)):
            self.assertTrue(is_llm_enabled())


class TestGetLlmPauseReason(unittest.TestCase):
    def test_returns_none_when_enabled(self):
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=True):
            self.assertIsNone(get_llm_pause_reason())

    def test_returns_paused_reason_from_llm_budget_when_disabled(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = ("budget_exceeded",)
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=False), \
             patch("app.engines.llm_interpretation_orchestrator.get_conn", return_value=_cm(conn)):
            self.assertEqual(get_llm_pause_reason(), "budget_exceeded")

    def test_defaults_to_manual_when_reason_missing(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        with patch("app.engines.llm_interpretation_orchestrator.is_llm_enabled", return_value=False), \
             patch("app.engines.llm_interpretation_orchestrator.get_conn", return_value=_cm(conn)):
            self.assertEqual(get_llm_pause_reason(), "manual")


if __name__ == "__main__":
    unittest.main()
