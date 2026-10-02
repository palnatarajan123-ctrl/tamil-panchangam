# tests/engines/test_envelope_live_mahadasha.py
"""
The prediction envelope (monthly/yearly LLM input) and the birth-chart view
must resolve the Mahadasha LIVE for the reference date -- not read
vimshottari["current"], which is frozen at chart creation (2026-10-02).

Real failure before the fix: chart fc588066's Jupiter MD ends 2027-04-14,
so its May 2027 envelope said "MD Jupiter (weight 0.7), AD Saturn" while
chat/PDF said Saturn MD. Fixture below: Jupiter MD to 2032-09-06, then Saturn.
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.engines.prediction_envelope import build_monthly_prediction_envelope
from app.engines.pratyantar_dasha_engine import compute_dasha_snapshot
from app.services.birth_chart_builder import extract_active_dasha_lords

_FIXTURE = Path(__file__).parent / "fixtures_base_chart_high_score.json"


def _chart():
    p = json.loads(_FIXTURE.read_text())
    return p.get("payload", p)


def test_envelope_md_after_stored_current_md_has_ended():
    chart = _chart()
    assert chart["dashas"]["vimshottari"]["current"]["lord"] == "Jupiter"  # stored, ends 2032-09-06
    env = build_monthly_prediction_envelope(base_chart=chart, year=2033, month=3)
    dc = env["dasha_context"]
    snap = compute_dasha_snapshot(chart["dashas"]["vimshottari"], date(2033, 3, 15))
    assert dc["maha_lord"] == "Saturn" == snap["mahadasha"]["lord"]
    assert dc["antar_lord"] == snap["antardasha"]["lord"]
    assert dc["active"]["maha"]["start"].startswith("2032-09-06")
    assert env["time_ruler"]["vimshottari_dasha"]["lord"] == "Saturn"
    assert "Jupiter" not in dc["active_lords"]


def test_envelope_md_unchanged_inside_stored_period():
    chart = _chart()
    env = build_monthly_prediction_envelope(base_chart=chart, year=2026, month=10)
    assert env["dasha_context"]["maha_lord"] == "Jupiter"


def test_birth_chart_view_dasha_lord_is_live():
    dashas = _chart()["dashas"]
    assert extract_active_dasha_lords(dashas, datetime(2026, 10, 1, tzinfo=timezone.utc))["maha"] == "Jupiter"
    assert extract_active_dasha_lords(dashas, datetime(2040, 1, 1, tzinfo=timezone.utc))["maha"] == "Saturn"


def test_birth_chart_view_falls_back_to_stored_field_without_timeline():
    assert extract_active_dasha_lords({"vimshottari": {"current": {"lord": "Venus"}}})["maha"] == "Venus"
