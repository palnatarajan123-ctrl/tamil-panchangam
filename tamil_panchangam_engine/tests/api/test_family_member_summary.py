# tests/api/test_family_member_summary.py
"""
Phase A2: extends family.py's _build_member_summary() (used by
family_group_chat_stream, the endpoint serving children-timing-screen.tsx,
family-timeline-screen.tsx, family-prediction-screen.tsx, and
child-prediction-screen.tsx) with the same yogas + upagraha enrichment
chat.py's _build_family_member_context() got in today's earlier Phase 3.

Both call sites now share app.llm.payload_builder._build_family_yoga_upagraha_suffix()
rather than duplicating the extraction logic -- the two functions' BASE
fields (lagna/moon vs nakshatra/rasi, sade-sati-always-shown vs
conditional) had already diverged before this change, so only the new
suffix logic was unified, not the pre-existing formats.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.api.family import _build_member_summary, _build_porutham_chat_block
from app.llm.payload_builder import _build_family_yoga_upagraha_suffix


def _member_payload(name="Test", rasi="Mesham", nak="Ashwini", lagna="Mesham",
                     maha_lord="Saturn", antar_lord="Venus"):
    now = datetime.now(timezone.utc)
    return {
        "birth_details": {"name": name},
        "ephemeris": {
            "lagna": {"rasi": lagna},
            "moon": {"rasi": rasi, "nakshatra": {"name": nak}},
        },
        "dashas": {"vimshottari": {
            "timeline": [{
                "mahadasha": maha_lord,
                "start": now.replace(year=now.year - 5).isoformat(),
                "end": now.replace(year=now.year + 5).isoformat(),
                "antar_dashas": [{
                    "antar_lord": antar_lord,
                    "start": now.replace(year=now.year - 1).isoformat(),
                    "end": now.replace(year=now.year + 1).isoformat(),
                }],
            }],
        }},
    }


def _old_build_member_summary(row: tuple) -> str:
    """
    Verbatim copy of _build_member_summary() as it existed BEFORE this
    change (no yoga_upagraha_suffix), kept independent so the regression
    check below is a real before/after diff, not the new function compared
    against itself.
    """
    import json
    from app.engines.dasha_resolver import resolve_antar_dasha
    from app.engines.sade_sati_engine import compute_sade_sati

    _, role, display_name, _chart_id, payload_raw = row
    payload = payload_raw if isinstance(payload_raw, dict) else json.loads(payload_raw or "{}")
    birth = payload.get("birth_details", {})
    eph = payload.get("ephemeris", {})
    moon = eph.get("moon", {})

    name = display_name or birth.get("name", role)
    lagna = eph.get("lagna", {}).get("rasi", "?")
    moon_rasi = moon.get("rasi", "?")
    nak = moon.get("nakshatra", {})
    nak_name = nak.get("name", "?") if isinstance(nak, dict) else str(nak or "?")

    vimshottari = payload.get("dashas", {}).get("vimshottari", {}) \
        if isinstance(payload.get("dashas"), dict) else {}
    dasha = resolve_antar_dasha(vimshottari=vimshottari, reference_date=datetime.now(timezone.utc))
    maha = dasha.get("maha", {}).get("lord", "—") if dasha else "—"
    antar = dasha.get("antar", {}).get("lord", "—") if dasha else "—"

    ss = compute_sade_sati(payload)
    ss_data = ss.get("sade_sati", {}) if ss else {}
    ss_suffix = f", Sade Sati active – {ss_data.get('phase_name', '')}" \
        if ss_data.get("active") else ""

    return (
        f"{role.upper()} {name}: "
        f"Lagna {lagna}, Moon {moon_rasi} ({nak_name}), "
        f"Dasha {maha}›{antar}"
        f"{ss_suffix}"
    )


class TestFamilyYogaUpagrahaSuffixSharedHelper(unittest.TestCase):
    """Pure-function tests for the shared helper itself."""

    def test_yogas_present_line(self):
        payload = {"yogas": {"error": None, "summary": {"yoga_names": ["Raja Yoga", "Dhana Yoga"]}}}
        self.assertEqual(_build_family_yoga_upagraha_suffix(payload), ", Yogas: Raja Yoga, Dhana Yoga")

    def test_yogas_capped_at_five(self):
        names = [f"Yoga{i}" for i in range(8)]
        payload = {"yogas": {"error": None, "summary": {"yoga_names": names}}}
        suffix = _build_family_yoga_upagraha_suffix(payload)
        self.assertIn(", ".join(names[:5]), suffix)
        self.assertNotIn("Yoga7", suffix)

    def test_upagraha_present_line(self):
        payload = {"upagrahas": {"gulika": {"rasi": "Cancer", "rasi_lord": "Moon"}}}
        self.assertEqual(_build_family_yoga_upagraha_suffix(payload), ", Shadow point: Cancer (Moon)")

    def test_neither_present_empty_string(self):
        self.assertEqual(_build_family_yoga_upagraha_suffix({}), "")

    def test_kp_sublords_and_predictive_signals_never_read(self):
        """Explicit skip: presence of these keys must not affect the suffix at all."""
        payload = {
            "kp_sublords": {"cuspal_significators": {"2": ["Venus"]}},
            "predictive_signals": {"active_yogas": [{"name": "X", "currently_active": True}]},
        }
        self.assertEqual(_build_family_yoga_upagraha_suffix(payload), "")


class TestBuildMemberSummaryExtension(unittest.TestCase):
    def test_base_fields_unaffected_when_no_new_data(self):
        """Regression: rows without yogas/upagrahas produce byte-identical
        output to the pre-change function."""
        payload = _member_payload(name="Ravi", rasi="Mesham", nak="Ashwini", lagna="Mesham")
        row = ("member-1", "husband", "Ravi", "chart-1", payload)
        old = _old_build_member_summary(row)
        new = _build_member_summary(row)
        self.assertEqual(old, new)

    def test_yogas_and_shadow_point_appended(self):
        payload = _member_payload(name="Ravi")
        payload["yogas"] = {"error": None, "summary": {"yoga_names": ["Raja Yoga"]}}
        payload["upagrahas"] = {"gulika": {"rasi": "Taurus", "rasi_lord": "Venus"}}
        row = ("member-1", "husband", "Ravi", "chart-1", payload)

        summary = _build_member_summary(row)
        self.assertIn("HUSBAND Ravi: Lagna Mesham, Moon Mesham (Ashwini), Dasha Saturn›Venus", summary)
        self.assertIn("Yogas: Raja Yoga", summary)
        self.assertIn("Shadow point: Taurus (Venus)", summary)

    def test_appended_after_sade_sati_suffix_when_both_present(self):
        """Sade Sati suffix (conditional) and the new yoga/upagraha suffix
        must compose correctly when both are present -- not clobber each
        other."""
        payload = _member_payload(name="Ravi")
        payload["yogas"] = {"error": None, "summary": {"yoga_names": ["Raja Yoga"]}}
        row = ("member-1", "husband", "Ravi", "chart-1", payload)
        summary = _build_member_summary(row)
        # Order: base fields, then (conditionally) sade sati, then yoga/upagraha.
        self.assertIn("Dasha Saturn›Venus", summary)
        self.assertIn("Yogas: Raja Yoga", summary)
        self.assertTrue(summary.index("Dasha") < summary.index("Yogas"))


def _row(member_id, role, display_name, payload):
    """Matches the (fm.id, fm.role, fm.display_name, fm.chart_id, bc.payload)
    shape family_group_chat_stream() actually fetches."""
    return (member_id, role, display_name, "chart-x", payload)


class TestBuildPoruthamChatBlock(unittest.TestCase):
    """
    Phase F2: family.py's family_group_chat_stream() (the endpoint serving
    children-timing-screen.tsx, family-timeline-screen.tsx,
    family-prediction-screen.tsx, child-prediction-screen.tsx) now includes
    a couple-level Porutham block, extracted into _build_porutham_chat_block()
    so it's testable without mocking the full async streaming flow.
    """

    def test_no_wife_returns_empty_string_no_db_call(self):
        rows = [_row("h-id", "husband", "Ravi", _member_payload(name="Ravi"))]
        with patch("app.api.family.get_conn") as mock_get_conn:
            result = _build_porutham_chat_block(rows, "group-1")
        self.assertEqual(result, "")
        mock_get_conn.assert_not_called()

    def test_husband_and_wife_renders_block(self):
        rows = [
            _row("h-id", "husband", "Ravi", _member_payload(name="Ravi", rasi="Mesham", nak="Ashwini")),
            _row("w-id", "wife", "Priya", _member_payload(name="Priya", rasi="Kanni", nak="Hasta")),
        ]
        mock_conn = MagicMock()
        cached_row = ({
            "husband": {"name": "Ravi", "nakshatra": "Ashwini", "rasi": "Mesham"},
            "wife": {"name": "Priya", "nakshatra": "Hasta", "rasi": "Kanni"},
            "porutham": {
                "total_score": 16, "max_score": 33, "percent": 48.5, "grade": "Average",
                "mandatory_fail": False,
                "points": [{"name": "Nadi", "score": 8, "max": 8, "pass": True, "mandatory": True}],
            },
        },)
        mock_conn.execute.return_value.fetchone.return_value = cached_row
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_conn
        mock_cm.__exit__.return_value = False

        with patch("app.api.family.get_conn", return_value=mock_cm):
            result = _build_porutham_chat_block(rows, "group-1")

        self.assertIn("PORUTHAM (Husband x Wife compatibility, 10-point Tamil Kuta system):", result)
        self.assertIn("Score: 16/33 (48.5%) — Average", result)
        self.assertIn("Nadi 8/8", result)

    def test_no_cached_result_and_missing_data_returns_empty(self):
        """Missing nak/rasi -> _get_or_compute_porutham returns None ->
        block must be empty, not a crash or placeholder text."""
        rows = [
            _row("h-id", "husband", "Ravi", {"birth_details": {"name": "Ravi"}, "ephemeris": {}}),
            _row("w-id", "wife", "Priya", {"birth_details": {"name": "Priya"}, "ephemeris": {}}),
        ]
        result = _build_porutham_chat_block(rows, "group-1")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
