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


class TestFamilyMemberContextPhase3Enrichment(unittest.TestCase):
    """
    Phase 3: yogas and upagraha added per non-anchor family member, read
    directly from already-fetched payload (no new query, no per-member
    LLM/cache call). predictive_signals and kp_sublords are deliberately
    NOT extended here -- both would require expensive per-member work
    (cached KP lookup, time-window narrative build) that scales unbounded
    with family size for the lowest-value case.
    """

    def _payload_with(self, yogas=None, upagrahas=None, kp_sublords=None,
                       predictive_signals=None, **kwargs):
        payload = _member_payload(**kwargs)
        if yogas is not None:
            payload["yogas"] = yogas
        if upagrahas is not None:
            payload["upagrahas"] = upagrahas
        if kp_sublords is not None:
            payload["kp_sublords"] = kp_sublords
        if predictive_signals is not None:
            payload["predictive_signals"] = predictive_signals
        return payload

    def test_yogas_line_appears_for_non_anchor_member(self):
        payload = self._payload_with(
            role="child", name="Kid",
            yogas={"error": None, "summary": {"yoga_names": ["Raja Yoga", "Dhana Yoga"]}},
        )
        ctx = chat_module._build_family_member_context(
            [{"role": "child", "display_name": "Kid", "payload": payload}]
        )
        self.assertIn("Yogas: Raja Yoga, Dhana Yoga", ctx)

    def test_yogas_capped_at_five(self):
        names = [f"Yoga{i}" for i in range(8)]
        payload = self._payload_with(
            role="wife", name="W",
            yogas={"error": None, "summary": {"yoga_names": names}},
        )
        ctx = chat_module._build_family_member_context(
            [{"role": "wife", "display_name": "W", "payload": payload}]
        )
        self.assertIn(", ".join(names[:5]), ctx)
        self.assertNotIn("Yoga7", ctx)

    def test_empty_yogas_dict_no_line_no_crash(self):
        payload = self._payload_with(role="wife", name="W", yogas={})
        ctx = chat_module._build_family_member_context(
            [{"role": "wife", "display_name": "W", "payload": payload}]
        )
        self.assertNotIn("Yogas:", ctx)

    def test_shadow_point_line_appears(self):
        payload = self._payload_with(
            role="husband", name="H",
            upagrahas={"gulika": {"rasi": "Taurus", "rasi_lord": "Venus"}},
        )
        ctx = chat_module._build_family_member_context(
            [{"role": "husband", "display_name": "H", "payload": payload}]
        )
        self.assertIn("Shadow point: Taurus (Venus)", ctx)

    def test_no_upagrahas_no_shadow_point_line(self):
        payload = self._payload_with(role="husband", name="H")
        ctx = chat_module._build_family_member_context(
            [{"role": "husband", "display_name": "H", "payload": payload}]
        )
        self.assertNotIn("Shadow point", ctx)

    def test_kp_sublords_present_but_excluded_from_output(self):
        """Explicit skip decision: even when kp_sublords IS present on the
        payload, it must not appear in non-anchor family context."""
        payload = self._payload_with(
            role="husband", name="H",
            kp_sublords={
                "planets": {}, "house_cusps": {},
                "cuspal_significators": {"2": ["Venus", "Saturn"]},
            },
        )
        ctx = chat_module._build_family_member_context(
            [{"role": "husband", "display_name": "H", "payload": payload}]
        )
        self.assertNotIn("cuspal", ctx.lower())
        self.assertNotIn("significator", ctx.lower())

    def test_predictive_signals_present_but_excluded_from_output(self):
        """Explicit skip decision: even when predictive_signals IS present,
        event windows / active-yoga narrative must not appear for
        non-anchor members."""
        payload = self._payload_with(
            role="wife", name="W",
            predictive_signals={
                "computed_for": "2026-08",
                "active_yogas": [{"name": "Sarala Yoga", "currently_active": True}],
                "event_windows": [{
                    "window_start": "2026-05-17", "window_end": "2026-05-30",
                    "life_area": "self", "direction": "opportunity", "confidence": "very high",
                }],
            },
        )
        ctx = chat_module._build_family_member_context(
            [{"role": "wife", "display_name": "W", "payload": payload}]
        )
        self.assertNotIn("2026-05-17", ctx)
        self.assertNotIn("window", ctx.lower())
        self.assertNotIn("Sarala Yoga", ctx)  # only from present-yogas summary, not active_yogas

    def test_full_enrichment_line_format_for_one_member(self):
        payload = self._payload_with(
            role="husband", name="Ravi",
            yogas={"error": None, "summary": {"yoga_names": ["Raja Yoga"]}},
            upagrahas={"gulika": {"rasi": "Taurus", "rasi_lord": "Venus"}},
        )
        ctx = chat_module._build_family_member_context(
            [{"role": "husband", "display_name": "Ravi", "payload": payload}]
        )
        self.assertIn(
            "HUSBAND — Ravi: Nakshatra Ashwini, Rasi Mesham, Dasha Saturn›Venus, "
            "Sade Sati:",
            ctx,
        )
        self.assertIn("Yogas: Raja Yoga", ctx)
        self.assertIn("Shadow point: Taurus (Venus)", ctx)


class TestPoruthamInFamilyChatContext(unittest.TestCase):
    """
    Phase F2: _build_family_member_context() now accepts an optional
    couple-level `porutham` dict (not per-member, hence a separate
    parameter rather than folded into member_payloads like yogas/upagraha).
    Stays a pure function -- chat_stream() fetches (cache-first, via
    _get_or_compute_porutham()) and passes the resolved dict in.
    """

    def _members(self):
        return [
            {"id": "h-id", "role": "husband", "display_name": "Ravi", "payload": _member_payload(role="husband", name="Ravi")},
            {"id": "w-id", "role": "wife", "display_name": "Priya", "payload": _member_payload(role="wife", name="Priya")},
        ]

    def test_no_porutham_arg_no_section_backward_compatible(self):
        """Default (no porutham passed) must be identical to Phase A2/3
        behavior -- confirms this addition didn't change anything for
        callers that don't pass it."""
        ctx = chat_module._build_family_member_context(self._members())
        self.assertNotIn("PORUTHAM", ctx)

    def test_porutham_none_no_section(self):
        ctx = chat_module._build_family_member_context(self._members(), porutham=None)
        self.assertNotIn("PORUTHAM", ctx)

    def test_porutham_present_renders_within_family_context_block(self):
        porutham = {
            "total_score": 16, "max_score": 33, "percent": 48.5, "grade": "Average",
            "mandatory_fail": False,
            "points": [
                {"name": "Nadi", "score": 8, "max": 8, "pass": True, "mandatory": True},
                {"name": "Dinam", "score": 0, "max": 3, "pass": False},
            ],
        }
        ctx = chat_module._build_family_member_context(self._members(), porutham=porutham)
        self.assertIn("PORUTHAM (Husband x Wife compatibility, 10-point Tamil Kuta system):", ctx)
        self.assertIn("Score: 16/33 (48.5%) — Average", ctx)
        self.assertIn("Nadi 8/8", ctx)
        self.assertIn("Dinam 0/3", ctx)
        # Couple-level data appears once, after the per-member lines, within
        # the same "## FAMILY CONTEXT" block -- not a separate top-level section.
        self.assertIn("## FAMILY CONTEXT", ctx)
        family_idx = ctx.index("## FAMILY CONTEXT")
        porutham_idx = ctx.index("PORUTHAM")
        self.assertGreater(porutham_idx, family_idx)

    def test_empty_porutham_dict_no_section(self):
        ctx = chat_module._build_family_member_context(self._members(), porutham={})
        self.assertNotIn("PORUTHAM", ctx)


class TestBuildProspectContext(unittest.TestCase):
    """
    Phase G2: _build_prospect_context() renders Phase G1's chart-to-chart
    prospect links into a compact chat system-prompt block -- summary line
    per prospect (candidate name + score + grade), not the full 10-category
    breakdown, mirroring Phase F2's cost-conscious non-anchor-member pattern.
    Pure function -- chat_stream() resolves the prospect rows/porutham via
    DB + _get_or_compute_prospect_porutham() and passes plain dicts in.
    """

    def test_empty_list_no_section(self):
        ctx = chat_module._build_prospect_context([])
        self.assertEqual(ctx, "")

    def test_single_prospect_renders_summary_line(self):
        ctx = chat_module._build_prospect_context(
            [{"other_name": "Priya", "score": 16, "max_score": 33, "grade": "Average"}]
        )
        self.assertIn("## COMPATIBILITY CHECKS", ctx)
        self.assertIn("- Priya: 16/33 Porutham points (Average)", ctx)

    def test_multiple_prospects_each_get_a_line(self):
        ctx = chat_module._build_prospect_context([
            {"other_name": "Priya", "score": 16, "max_score": 33, "grade": "Average"},
            {"other_name": "Divya", "score": 28, "max_score": 33, "grade": "Excellent"},
        ])
        self.assertIn("- Priya: 16/33 Porutham points (Average)", ctx)
        self.assertIn("- Divya: 28/33 Porutham points (Excellent)", ctx)

    def test_prospect_with_no_score_skipped_not_crashed(self):
        """A prospect whose Porutham couldn't be resolved (score=None,
        e.g. missing nak/rasi on one chart) must be silently omitted, not
        rendered as 'None/None' or crash the format string."""
        ctx = chat_module._build_prospect_context([
            {"other_name": "Priya", "score": None, "max_score": None, "grade": None},
        ])
        self.assertEqual(ctx, "")

    def test_mixed_resolved_and_unresolved_only_resolved_rendered(self):
        ctx = chat_module._build_prospect_context([
            {"other_name": "Priya", "score": 16, "max_score": 33, "grade": "Average"},
            {"other_name": "Unresolved", "score": None, "max_score": None, "grade": None},
        ])
        self.assertIn("Priya", ctx)
        self.assertNotIn("Unresolved", ctx)

    def test_full_breakdown_not_inlined(self):
        """Cost-conscious guard: the block must stay summary-level -- no
        per-category names should ever appear here (that's exclusively the
        dedicated prospect view's job)."""
        ctx = chat_module._build_prospect_context(
            [{"other_name": "Priya", "score": 16, "max_score": 33, "grade": "Average"}]
        )
        for category in ["Dinam", "Ganam", "Yoni", "Rasi", "Rasiyathipaty",
                          "Rajju", "Vedha", "Mahendra", "Stree Deergha", "Nadi"]:
            self.assertNotIn(category, ctx)


if __name__ == "__main__":
    unittest.main()
