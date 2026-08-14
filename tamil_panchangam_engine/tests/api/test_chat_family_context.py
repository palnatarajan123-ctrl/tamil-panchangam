# tests/api/test_chat_family_context.py
"""
Phase 2: extraction-only test for _build_family_member_context().

This tests ONLY that pulling chat.py:562-615's inline family-member loop
into a named function was behavior-identical -- same 4 fields (nakshatra,
rasi, dasha, sade sati), byte-for-byte equivalent output -- before Phase 3
adds any new depth. Mirrors the _build_system_prompt extraction pattern
from earlier this session (TestSystemPromptExtractionIsNoOp in
test_chat_context.py): diff against an independently-kept copy of the
pre-refactor logic, not the new function compared against itself.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.api import chat as chat_module
from app.engines.dasha_resolver import resolve_antar_dasha
from app.engines.sade_sati_engine import compute_sade_sati


def _pre_refactor_build_family_member_context(members: list) -> str:
    """
    Verbatim copy of the loop as it existed inline in chat_stream() BEFORE
    extraction -- operates on raw (role, display_name, chart_id, payload_raw)
    tuples exactly as fetched from the DB, same as the original code. Kept
    independent of app/api/chat.py so this is a real before/after diff.
    """
    import json as _json

    member_lines = []
    for m in members:
        role, display_name, chart_id, payload_raw = m
        payload = payload_raw if isinstance(payload_raw, dict) \
                  else _json.loads(payload_raw or "{}")
        birth = payload.get("birth_details", {})
        moon = payload.get("ephemeris", {}).get("moon", {})
        vimshottari = payload.get("dashas", {}).get("vimshottari", {})
        dasha = resolve_antar_dasha(
            vimshottari=vimshottari,
            reference_date=datetime.now(timezone.utc)
        )
        ss = compute_sade_sati(payload)
        ss_data = ss.get("sade_sati", {}) if ss else {}

        name = display_name or birth.get("name", role)
        nak = moon.get("nakshatra", {})
        nak_name = nak.get("name", "") if isinstance(nak, dict) else nak
        rasi = moon.get("rasi", "")
        maha = dasha.get("maha", {}).get("lord", "—") if dasha else "—"
        antar = dasha.get("antar", {}).get("lord", "—") if dasha else "—"
        ss_active = ss_data.get("active", False)
        ss_phase = ss_data.get("phase_name", "")

        member_lines.append(
            f"{role.upper()} — {name}: "
            f"Nakshatra {nak_name}, Rasi {rasi}, "
            f"Dasha {maha}›{antar}, "
            f"Sade Sati: {'Active – ' + ss_phase if ss_active else 'None'}"
        )

    if not member_lines:
        return ""

    return (
        "\n\n## FAMILY CONTEXT\n"
        "You are advising this couple/family. "
        "Use ALL members' charts when answering family questions:\n"
        + "\n".join(member_lines)
    )


def _member_payload(role="husband", name="Test", rasi="Mesham", nak="Ashwini",
                     maha_lord="Saturn", antar_lord="Venus"):
    """
    dashas.vimshottari schema verified against dasha_resolver.resolve_antar_dasha's
    documented "EXPECTED vimshottari schema (LOCKED)" -- timeline of
    {mahadasha, start, end, antar_dashas: [{antar_lord, start, end}]}, not
    guessed. Window spans well before/after "now" so resolve_antar_dasha
    actually finds a match regardless of when the test runs.
    """
    now = datetime.now(timezone.utc)
    md_start = now.replace(year=now.year - 5).isoformat()
    md_end = now.replace(year=now.year + 5).isoformat()
    ad_start = now.replace(year=now.year - 1).isoformat()
    ad_end = now.replace(year=now.year + 1).isoformat()
    return {
        "birth_details": {"name": name},
        "ephemeris": {"moon": {"rasi": rasi, "nakshatra": {"name": nak}}},
        "dashas": {"vimshottari": {
            "timeline": [{
                "mahadasha": maha_lord,
                "start": md_start,
                "end": md_end,
                "antar_dashas": [{
                    "antar_lord": antar_lord,
                    "start": ad_start,
                    "end": ad_end,
                }],
            }],
        }},
    }


class TestFamilyMemberContextExtractionIsNoOp(unittest.TestCase):
    """Diffs the new extracted function against an independently-kept copy
    of the pre-refactor inline logic -- both fed equivalent inputs."""

    def _run_both(self, role_name_rasi_nak_maha_list):
        """Each item: (role, display_name, chart_id, payload)."""
        old_style_rows = [
            (role, display_name, chart_id, payload)
            for role, display_name, chart_id, payload in role_name_rasi_nak_maha_list
        ]
        new_style_payloads = [
            {"role": role, "display_name": display_name, "payload": payload}
            for role, display_name, chart_id, payload in role_name_rasi_nak_maha_list
        ]
        old_output = _pre_refactor_build_family_member_context(old_style_rows)
        new_output = chat_module._build_family_member_context(new_style_payloads)
        return old_output, new_output

    def test_empty_members_list_byte_identical(self):
        old, new = self._run_both([])
        self.assertEqual(old, new)
        self.assertEqual(new, "")

    def test_single_member_byte_identical(self):
        payload = _member_payload(role="husband", name="Ravi", rasi="Mesham", nak="Ashwini")
        old, new = self._run_both([("husband", "Ravi", "chart-1", payload)])
        self.assertEqual(old, new)
        self.assertIn("HUSBAND — Ravi", new)

    def test_multiple_members_byte_identical(self):
        members = [
            ("husband", "Ravi", "chart-1", _member_payload(role="husband", name="Ravi", rasi="Mesham")),
            ("wife", "Priya", "chart-2", _member_payload(role="wife", name="Priya", rasi="Kanni")),
            ("child", None, "chart-3", _member_payload(role="child", name="Kid", rasi="Simmam")),
        ]
        old, new = self._run_both(members)
        self.assertEqual(old, new)

    def test_display_name_none_falls_back_to_birth_name_byte_identical(self):
        payload = _member_payload(role="child", name="Chart Name")
        old, new = self._run_both([("child", None, "chart-1", payload)])
        self.assertEqual(old, new)
        self.assertIn("CHILD — Chart Name", new)

    def test_json_string_payload_parses_same_as_dict_payload(self):
        """
        Old inline code accepted payload_raw as either a dict or a raw JSON
        string and parsed it itself. The extraction moved that parsing step
        into chat_stream() (now happens once, before building
        member_payloads) -- _build_family_member_context() itself now only
        ever receives already-parsed dicts. This isn't a regression: confirm
        old(JSON string) == new(pre-parsed dict of the same data), i.e. the
        parsing step that moved didn't change what ends up in the prompt.
        """
        import json
        payload_dict = _member_payload(role="husband", name="Ravi")
        payload_str = json.dumps(payload_dict)

        old = _pre_refactor_build_family_member_context(
            [("husband", "Ravi", "chart-1", payload_str)]
        )
        new = chat_module._build_family_member_context(
            [{"role": "husband", "display_name": "Ravi", "payload": payload_dict}]
        )
        self.assertEqual(old, new)


if __name__ == "__main__":
    unittest.main()
