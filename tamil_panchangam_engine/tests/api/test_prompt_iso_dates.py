# tests/api/test_prompt_iso_dates.py
"""
No raw ISO date may reach a chat system prompt (2026-10-02).

The chat model restated "2029-05-22" as "29 May 2029" in 2/3 live runs (the
year's "29" bleeding into the day). Dates are rendered "22 May 2029" at
source (app/utils/prompt_dates.py), and each chat's assembled system prompt
goes through humanize_iso_dates() as a safety net. These tests guard the
PATTERN, not one date:
  1. the helpers themselves;
  2. every date-bearing formatter that feeds chat.py / family.py;
  3. both prompt assemblers end to end, with every section builder forced
     to emit ISO dates -- so a section added later is covered too;
  4. both streaming endpoints send exactly the assembled prompt.
"""
import inspect
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from app.utils.prompt_dates import (
    contains_iso_date, fmt_dasha_windows, fmt_date, fmt_month, humanize_iso_dates,
)

ISO_SOUP = (
    "Born 1990-01-01. Saturn return 2029-05-22. Ingress 2026-12-05T00:00:00+00:00. "
    "Next return around 2027-07. Window 2028-2031 stays a year range."
)


# ── 1. helpers ────────────────────────────────────────────────────────────────

def test_fmt_date_is_unambiguous():
    assert fmt_date("2029-05-22") == "22 May 2029"
    assert fmt_date(date(2029, 5, 22)) == "22 May 2029"
    assert fmt_date(datetime(2026, 12, 5, tzinfo=timezone.utc)) == "5 Dec 2026"
    assert fmt_date("2026-12-05T00:00:00+00:00") == "5 Dec 2026"
    assert fmt_date(None) == "" and fmt_date("unknown") == "unknown"
    assert fmt_month("2027-07") == "Jul 2027"


def test_humanize_rewrites_every_iso_form_but_not_year_ranges():
    out = humanize_iso_dates(ISO_SOUP)
    assert not contains_iso_date(out)
    assert "22 May 2029" in out and "1 Jan 1990" in out and "5 Dec 2026" in out and "Jul 2027" in out
    assert "2028-2031" in out
    assert humanize_iso_dates("2026-12-05T03:12:00+00:00") == "5 Dec 2026 03:12 UTC"


def test_fmt_dasha_windows():
    w = [{"from": "2032-02-24", "to": "2033-04-03", "level": "antardasha", "lord": "Mars"}]
    assert fmt_dasha_windows(w) == "Mars antardasha 24 Feb 2032 to 3 Apr 2033"
    assert fmt_dasha_windows([]) == "none in range"


# ── 2. every date-bearing formatter used by the chats ─────────────────────────

_WIN = [{"from": "2029-05-22", "to": "2031-01-09", "level": "antardasha", "lord": "Venus"}]


def test_dasha_snapshot_formatter():
    from app.engines.pratyantar_dasha_engine import format_dasha_snapshot_context
    p = {"lord": "Saturn", "start": "2026-07-28", "end": "2029-06-02", "duration_days": 1040}
    text = format_dasha_snapshot_context({"mahadasha": p, "antardasha": p, "pratyantar": p})
    assert "28 Jul 2026 to 2 Jun 2029" in text and not contains_iso_date(text)


def test_varshaphal_formatters():
    from app.engines.varshaphal_engine import format_varshaphal_compact, format_varshaphal_context
    vp = {"solar_return_date": "2025-12-05", "next_return_approx": "2026-12", "lagna": "Meenam",
          "lagna_english": "Pisces", "annual_lagna_lord": "Jupiter", "muntha": "Simham",
          "muntha_english": "Leo", "muntha_house": 6, "muntha_house_from_natal_lagna": 9,
          "benefics_in_kendra": 0}
    for text in (format_varshaphal_context(vp), format_varshaphal_compact(vp)):
        assert "5 Dec 2025" in text and not contains_iso_date(text)


def test_transit_hit_formatters():
    from app.engines.transit_hits_engine import (
        format_chat_transit_hits, format_chat_transit_hits_compact, select_chat_transit_hits,
    )
    ref = date(2026, 10, 2)
    hits = [{"transit_planet": "Jupiter", "natal_planet": "Moon", "aspect_type": "conjunction",
             "hit_date": "2026-10-20", "orb": 0.1, "house": 1, "transit_degree": 100.0}]
    sel = select_chat_transit_hits(hits, ref)
    text = format_chat_transit_hits(sel) + format_chat_transit_hits_compact(sel, ref)
    assert sel and "20 Oct 2026" in text and not contains_iso_date(text)


def test_marriage_health_wealth_formatters():
    from app.engines.health_events_engine import format_health_events_context
    from app.engines.marriage_timing_engine import format_marriage_timing_context
    from app.engines.wealth_events_engine import format_wealth_events_context
    marriage = {"seventh_lord": "Venus", "seventh_lord_dashas": _WIN, "darakaraka": "Sun",
                "darakaraka_dashas": _WIN, "gender_known": True, "kalatra_karaka": "Venus",
                "kalatra_karaka_dashas": _WIN}
    health = {f"{k}_{f}": v for k in ("sixth", "eighth") for f, v in
              (("lord", "Mars"), ("lord_dashas", _WIN), ("house_afflicted", False),
               ("house_afflicting_planets", []))}
    wealth = {"second_lord": "Sun", "eleventh_lord": "Venus", "second_lord_dashas": _WIN,
              "eleventh_lord_dashas": _WIN, "dhana_yogas": [], "kp_available": False}
    for text in (format_marriage_timing_context(marriage), format_health_events_context(health),
                 format_wealth_events_context(wealth)):
        assert "Venus antardasha 22 May 2029 to 9 Jan 2031" in text
        assert not contains_iso_date(text)


# ── 3. both assemblers end to end, every section forced to emit ISO dates ─────

def _empty_conn():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []
    conn.execute.return_value.fetchone.return_value = None
    cm = MagicMock()
    cm.__enter__.return_value = conn
    cm.__exit__.return_value = False
    return cm


def test_chat_assembler_output_has_no_iso_dates():
    from types import SimpleNamespace
    from app.api import chat
    req = SimpleNamespace(base_chart_id="c1", group_id=None, reading_as_name=None, context_type=None)
    with patch.object(chat, "_build_chat_context", return_value={}), \
         patch.object(chat, "_build_system_prompt", return_value=ISO_SOUP), \
         patch.object(chat, "_build_prospect_context", return_value="\nProspect checked 2026-09-30."), \
         patch.object(chat, "_build_monthly_context_block", return_value="Monthly 2026-10 report, peak 2026-10-14"), \
         patch.object(chat, "get_conn", side_effect=lambda: _empty_conn()):
        prompt = chat._assemble_chat_system_prompt(req, "u1")
    assert "22 May 2029" in prompt and "14 Oct 2026" in prompt
    assert not contains_iso_date(prompt), prompt


def test_family_assembler_output_has_no_iso_dates():
    from app.api import family
    row = ("m1", "husband", "PN", "c1", {})
    with patch.object(family, "_build_member_summary", return_value=ISO_SOUP), \
         patch.object(family, "_build_family_ingress_block", return_value="\n- PN: Rahu enters 2026-12-05"), \
         patch.object(family, "_build_family_yearly_block", return_value="Yearly 2026-03-01"), \
         patch.object(family, "_build_porutham_chat_block", return_value="\nPorutham 2026-01-02"), \
         patch.object(family, "_build_children_timing_chat_block", return_value="\nChild 2030-04-05"), \
         patch.object(family, "_build_prospect_chat_block", return_value="\nProspect 2026-09-30"):
        prompt = family._assemble_family_chat_system_prompt({"name": "Fam"}, [row], "g1", "u1", "c1")
    assert "5 Apr 2030" in prompt
    assert not contains_iso_date(prompt), prompt


# ── 4. the streaming endpoints send exactly the assembled prompt ──────────────

def _assert_stream_uses_only(fn, assembler_call: str):
    src = inspect.getsource(fn)
    assignments = [l.strip() for l in src.splitlines()
                   if l.strip().startswith("system_prompt") and "=" in l]
    assert assignments == [f"system_prompt = {assembler_call}"], assignments
    assert "system=system_prompt" in src


def test_chat_stream_sends_only_the_assembled_prompt():
    from app.api import chat
    _assert_stream_uses_only(chat.chat_stream, "_assemble_chat_system_prompt(req, user_id)")


def test_family_stream_sends_only_the_assembled_prompt():
    from app.api import family
    _assert_stream_uses_only(
        family.family_group_chat_stream,
        "_assemble_family_chat_system_prompt(group, rows, group_id, user_id, req.base_chart_id)",
    )
