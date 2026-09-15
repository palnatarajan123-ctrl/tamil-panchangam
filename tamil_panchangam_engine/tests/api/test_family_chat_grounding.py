# tests/api/test_family_chat_grounding.py
"""
Regression test for family_group_chat_stream()'s grounding fix (2026-09-14).

family.py's family_group_chat_stream() is a fully independent
implementation from chat.py's chat_stream() (see CLAUDE.md's architecture
notes: "a fix to one does NOT reach the other"). Confirmed via live
reproduction that this independence meant chat.py's 2026-09-12/13
grounding fixes (GROUNDING system-prompt rule, real ingress/peyarchi
dates) never reached family.py -- a live call using the exact original
repro question ("Ragu, Kethu peyarchi for Mesha rasi in 2026 transition?")
against the exact chart that originally exposed chat.py's bug produced a
confident, unhedged, WRONG answer (wrong sign, wrong house). This test
pins the ported fix: _FAMILY_CHAT_SYSTEM_PROMPT now carries the same
GROUNDING/HOUSE-COUNTING rules as chat.py's SYSTEM_PROMPT_TEMPLATE, and
_build_family_ingress_block() gives the model real per-member ingress
data the same way chat.py's _build_chat_context() does.
"""
import unittest
from unittest.mock import MagicMock, patch

from app.api import family as family_module


def _member_row(role: str, display_name: str, chart_id: str, moon_rasi: str, lagna_rasi: str) -> tuple:
    payload = {
        "birth_details": {"name": display_name},
        "ephemeris": {
            "lagna": {"rasi": lagna_rasi},
            "moon": {"rasi": moon_rasi, "longitude_deg": 10.0, "nakshatra": {"name": "Ashwini"}},
            "planets": {},
        },
        "dashas": {},
        "chart_metadata": {"node_type": "mean"},
    }
    return (f"member-{role}", role, display_name, chart_id, payload)


class _FakeIngressConn:
    """Same in-memory stand-in as test_chat_ingress_grounding.py's --
    _build_family_ingress_block() opens its own get_conn(), independent
    of any chart/member query, same as chat.py's ingress lookup."""

    def __init__(self):
        self.rows = []

    def execute(self, sql, params=None):
        sql_stripped = sql.strip()
        if sql_stripped.startswith("SELECT"):
            planet, node_type, now_utc, count = params
            matched = [
                r for r in self.rows
                if r["planet"] == planet and r["node_type"] == node_type and r["ingress_date_utc"] > now_utc
            ]
            matched.sort(key=lambda r: r["ingress_date_utc"])
            self._last_result = [
                (r["to_sign"], r["ingress_date_utc"], r["retrograde_return_date_utc"]) for r in matched[:count]
            ]
        elif sql_stripped.startswith("INSERT"):
            planet, node_type, from_sign, to_sign, ingress_date_utc, retro = params
            exists = any(
                r["planet"] == planet and r["node_type"] == node_type
                and r["to_sign"] == to_sign and r["ingress_date_utc"] == ingress_date_utc
                for r in self.rows
            )
            if not exists:
                self.rows.append({
                    "planet": planet, "node_type": node_type, "from_sign": from_sign,
                    "to_sign": to_sign, "ingress_date_utc": ingress_date_utc,
                    "retrograde_return_date_utc": retro,
                })
        return self

    def fetchall(self):
        return self._last_result

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestFamilyChatSystemPromptGrounding(unittest.TestCase):
    def test_system_prompt_carries_grounding_and_house_convention_rules(self):
        rendered = family_module._FAMILY_CHAT_SYSTEM_PROMPT.format(
            group_name="Test Family", member_lines="- HUSBAND Test: Lagna Mesham"
        )
        self.assertIn("GROUNDING", rendered)
        self.assertIn("I don't have that specific data available", rendered)
        self.assertIn("HOUSE-COUNTING CONVENTION", rendered)


class TestFamilyIngressBlock(unittest.TestCase):
    def test_ingress_block_populated_per_member_for_all_four_planets(self):
        rows = [
            _member_row("husband", "Husband", "chart-h", "Simmam", "Simmam"),
            _member_row("wife", "Wife", "chart-w", "Kanni", "Kumbham"),
        ]
        fake_conn = _FakeIngressConn()

        with patch.object(family_module, "get_conn", return_value=fake_conn):
            block = family_module._build_family_ingress_block(rows)

        self.assertIn("## UPCOMING SIGN CHANGES (Peyarchi)", block)
        for name in ("Husband", "Wife"):
            for planet in ("Rahu", "Ketu", "Jupiter", "Saturn"):
                self.assertIn(f"{name}: {planet} next enters", block)
        # Different members with different Moon/Lagna signs must get
        # independently-computed house numbers, not a shared/copy-pasted one.
        self.assertIn("from Husband's Moon sign", block)
        self.assertIn("from Wife's Moon sign", block)

    def test_ingress_lookup_missing_moon_rasi_skips_member_without_raising(self):
        rows = [
            _member_row("husband", "Husband", "chart-h", "", "Simmam"),
        ]
        fake_conn = _FakeIngressConn()

        with patch.object(family_module, "get_conn", return_value=fake_conn):
            block = family_module._build_family_ingress_block(rows)

        self.assertEqual(block, "")

    def test_ingress_cache_reuses_lookup_across_members_sharing_node_type(self):
        """Two members with the same node_type must not each trigger a
        separate DB round-trip per planet -- same cost-consciousness
        already applied elsewhere in this file for per-member context."""
        rows = [
            _member_row("husband", "Husband", "chart-h", "Simmam", "Simmam"),
            _member_row("wife", "Wife", "chart-w", "Kanni", "Kumbham"),
        ]
        fake_conn = _FakeIngressConn()
        call_count = {"n": 0}
        real_execute = fake_conn.execute

        def counting_execute(sql, params=None):
            if sql.strip().startswith("SELECT"):
                call_count["n"] += 1
            return real_execute(sql, params)
        fake_conn.execute = counting_execute

        with patch.object(family_module, "get_conn", return_value=fake_conn):
            family_module._build_family_ingress_block(rows)

        # get_upcoming_ingresses() issues 2 SELECTs per cache-miss (initial
        # query, then a re-query after lazy-backfill INSERT) -- see its own
        # docstring. 4 planets x 1 shared node_type ("mean") across both
        # members -> 4 distinct lookups x 2 SELECTs = 8, not 16 (which is
        # what 2 members each triggering their own lookup would cost).
        self.assertEqual(call_count["n"], 8)


if __name__ == "__main__":
    unittest.main()
