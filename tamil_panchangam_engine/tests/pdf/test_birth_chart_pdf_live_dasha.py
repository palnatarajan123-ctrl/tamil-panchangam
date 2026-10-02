# tests/pdf/test_birth_chart_pdf_live_dasha.py
"""
Birth-chart PDF "Active Dasha Period" (data_loader._extract_dasha_context_from_payload)
must resolve live from the Vimshottari timeline, not the creation-time
vimshottari["current"] field -- that field was stale for 6/41 real charts on
2026-10-01 (e.g. 130d0025's PDF said Rahu>Jupiter while chat said Rahu>Saturn).
"""
from datetime import date

from app.pdf.canonical_report.data_loader import _extract_dasha_context_from_payload


def _payload(current=None):
    return {"dashas": {"vimshottari": {
        "current": current if current is not None else
            {"lord": "Rahu", "end": "2038-08-28T00:00:00+00:00", "antar": {"lord": "Jupiter"}},  # deliberately stale
        "timeline": [{
            "mahadasha": "Rahu", "start": "2020-08-28T00:00:00+00:00", "end": "2038-08-28T00:00:00+00:00",
            "antar_dashas": [
                {"antar_lord": "Jupiter", "start": "2023-05-10T00:00:00+00:00", "end": "2025-10-03T00:00:00+00:00"},
                {"antar_lord": "Saturn", "start": "2025-10-03T00:00:00+00:00", "end": "2028-08-08T00:00:00+00:00"},
            ],
        }],
    }}}


def test_pdf_dasha_ignores_stale_current_field():
    ctx = _extract_dasha_context_from_payload(_payload(), date(2026, 10, 1))
    assert ctx.mahadasha == "Rahu"
    assert ctx.antardasha == "Saturn"  # not the stored "Jupiter"
    assert ctx.dasha_balance.endswith("years remaining")


def test_pdf_dasha_falls_back_to_stored_field_outside_timeline():
    ctx = _extract_dasha_context_from_payload(_payload(), date(2045, 1, 1))
    assert (ctx.mahadasha, ctx.antardasha) == ("Rahu", "Jupiter")
