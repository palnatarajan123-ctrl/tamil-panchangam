# tests/api/test_family_children_timing_chat.py
"""
Regression test for family.py's children-timing chat wiring (2026-09-18).

children_timing_engine.py does a real, classical dasha-timing analysis
(5th house/lord + Jupiter Putra Karaka dasha windows) for exactly the
question "when might we have children?" -- already reachable via its
own dedicated endpoint/PDF (get_children_timing/get_children_timing_pdf)
-- but family_group_chat_stream() never referenced it, so asking this
same question through family chat had nothing to ground on even when
the answer was already cached in family_children_timing.

_build_children_timing_chat_block() is a plain, read-only cache lookup
(same default year_from=this year/year_to=+3 window
get_children_timing() uses) -- it must NOT trigger a fresh
run_children_timing() computation (that has its own LLM call and should
stay out of the chat context-building path).
"""
from datetime import date
from unittest.mock import MagicMock, patch

from app.api import family as family_module


class _FakeConn:
    def __init__(self, row):
        self._row = row

    def execute(self, sql, params=None):
        return self

    def fetchone(self):
        return self._row

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestChildrenTimingChatBlock:
    def test_cached_analysis_surfaces_in_chat_block(self):
        year_from = date.today().year
        year_to = year_from + 3
        row = ("Favorable window for children around 2027-2028, driven by Jupiter dasha.", '["2027: Jupiter Antardasha", "2028: 5th lord Mercury Antardasha"]', False)
        with patch.object(family_module, "get_conn", return_value=_FakeConn(row)):
            block = family_module._build_children_timing_chat_block("fake-group-id")

        assert "CHILDREN TIMING" in block
        assert str(year_from) in block and str(year_to) in block
        assert "Favorable window for children around 2027-2028" in block
        assert "Jupiter Antardasha" in block

    def test_no_cached_row_returns_empty_string(self):
        with patch.object(family_module, "get_conn", return_value=_FakeConn(None)):
            block = family_module._build_children_timing_chat_block("fake-group-id")
        assert block == ""

    def test_does_not_call_run_children_timing(self):
        """Must be a plain cache read -- never trigger a fresh
        (expensive, LLM-calling) computation from the chat path."""
        with patch.object(family_module, "get_conn", return_value=_FakeConn(None)):
            with patch.object(family_module, "run_children_timing") as mock_run:
                family_module._build_children_timing_chat_block("fake-group-id")
                mock_run.assert_not_called()

    def test_has_children_already_flag_surfaces(self):
        row = ("Some outlook", "[]", True)
        with patch.object(family_module, "get_conn", return_value=_FakeConn(row)):
            block = family_module._build_children_timing_chat_block("fake-group-id")
        assert "already has child member" in block

    def test_lookup_failure_degrades_gracefully(self):
        class _RaisingConn:
            def __enter__(self):
                raise RuntimeError("db down")

            def __exit__(self, *a):
                return False

        with patch.object(family_module, "get_conn", return_value=_RaisingConn()):
            block = family_module._build_children_timing_chat_block("fake-group-id")
        assert block == ""
