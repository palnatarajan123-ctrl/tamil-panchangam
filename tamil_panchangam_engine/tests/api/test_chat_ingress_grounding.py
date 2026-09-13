# tests/api/test_chat_ingress_grounding.py
"""
Regression test for chat's UPCOMING SIGN CHANGES (peyarchi) wiring.

The 2026-09-12 chat-grounding fix gave the model CURRENT transit
positions but nothing about FUTURE sign changes, so a "when does Rahu
enter Capricorn" question correctly refused rather than fabricate --
but the refusal was masking a real, closeable gap: the app can compute
exact future ingress dates via ingress_engine.py (a global fact, not
per-user, so it's cheap: computed once, cached in
planet_ingress_events, and looked up -- never a live ephemeris call in
the chat request path). See CLAUDE.md's 2026-09-13 entry.
"""
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.api import chat as chat_module


def _payload_with_tamil_rasi_names() -> dict:
    return {
        "birth_details": {
            "name": "Test Person",
            "date_of_birth": "1990-01-01",
            "time_of_birth": "10:00",
            "place_of_birth": "Chennai",
            "latitude": 13.0827,
            "longitude": 80.2707,
        },
        "ephemeris": {
            "lagna": {"rasi": "Simmam"},
            "moon": {"rasi": "Simmam", "longitude_deg": 130.0, "nakshatra": {"name": "Magha"}},
            "planets": {},
            "ayanamsa": "lahiri",
        },
        "dashas": {},
        "chart_metadata": {"node_type": "mean"},
    }


def _mock_conn_for_payload(payload: dict) -> MagicMock:
    conn = MagicMock()
    conn.execute.return_value.fetchone.side_effect = [(payload,), None, None]
    conn_cm = MagicMock()
    conn_cm.__enter__.return_value = conn
    conn_cm.__exit__.return_value = False
    return conn_cm


class _FakeIngressConn:
    """Same in-memory stand-in used by test_ingress_engine.py, reused
    here since _build_chat_context() opens its own get_conn() for the
    ingress lookup, separate from the chart/monthly/yearly one."""

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


class TestChatIngressGrounding(unittest.TestCase):
    def test_ingress_context_populated_for_all_four_planets(self):
        payload = _payload_with_tamil_rasi_names()
        fake_ingress_conn = _FakeIngressConn()

        def fake_get_conn():
            # First call (inside _build_chat_context's opening `with`) is
            # for chart/monthly/yearly; subsequent calls are for ingress.
            if not fake_get_conn.first_call_done:
                fake_get_conn.first_call_done = True
                return _mock_conn_for_payload(payload)
            return fake_ingress_conn
        fake_get_conn.first_call_done = False

        with patch.object(chat_module, "get_conn", side_effect=fake_get_conn):
            context = chat_module._build_chat_context("fake-chart-id")

        self.assertIn("ingress_context", context)
        ic = context["ingress_context"]
        for planet in ("Rahu", "Ketu", "Jupiter", "Saturn"):
            self.assertIn(planet, ic)
            self.assertIn("to_sign", ic[planet])
            self.assertIn("ingress_date_utc", ic[planet])
            self.assertIn("house_from_moon", ic[planet])
            self.assertIn("house_from_lagna", ic[planet])

    def test_upcoming_sign_changes_block_renders_with_real_date(self):
        payload = _payload_with_tamil_rasi_names()
        fake_ingress_conn = _FakeIngressConn()

        def fake_get_conn():
            if not fake_get_conn.first_call_done:
                fake_get_conn.first_call_done = True
                return _mock_conn_for_payload(payload)
            return fake_ingress_conn
        fake_get_conn.first_call_done = False

        with patch.object(chat_module, "get_conn", side_effect=fake_get_conn):
            context = chat_module._build_chat_context("fake-chart-id")

        system_prompt = chat_module._build_system_prompt(context)

        self.assertIn("## UPCOMING SIGN CHANGES (Peyarchi)", system_prompt)
        self.assertIn("Rahu: next enters", system_prompt)
        rahu_entry = context["ingress_context"]["Rahu"]
        expected_date = rahu_entry["ingress_date_utc"].strftime("%Y-%m-%d")
        self.assertIn(expected_date, system_prompt)
        self.assertIn("use them directly when asked", system_prompt)

    def test_ingress_lookup_failure_degrades_gracefully(self):
        """No moon rasi -> ingress lookup must not raise; rest of chat
        context building must still complete."""
        payload = _payload_with_tamil_rasi_names()
        payload["ephemeris"]["moon"]["rasi"] = ""

        with patch.object(chat_module, "get_conn", return_value=_mock_conn_for_payload(payload)):
            context = chat_module._build_chat_context("fake-chart-id")

        self.assertIn("ingress_context", context)
        self.assertFalse(context["ingress_context"])
        system_prompt = chat_module._build_system_prompt(context)
        self.assertNotIn("## UPCOMING SIGN CHANGES", system_prompt)


if __name__ == "__main__":
    unittest.main()
