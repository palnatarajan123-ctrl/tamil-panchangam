# tests/engines/test_av_transit_strength.py
"""
One shared Ashtakavarga transit-strength path (2026-10-02):
bhinnashtakavarga_engine.bav_transit_strength() + format_bav_transit_line(),
used by chat.py, family.py, both canonical PDFs and monthly/yearly
generation. These tests pin the format/threshold and that the consumers
render the SAME numbers from the same chart + transits.
"""
import inspect

from app.engines import bhinnashtakavarga_engine as be
from app.engines.bhinnashtakavarga_engine import (
    AV_TRANSIT_THRESHOLD, bav_transit_strength, compute_bhinnashtakavarga, format_bav_transit_line,
    gochara_transit_longitudes,
)

_EPH = {"lagna": {"longitude_deg": 285.0}, "planets": {
    "Sun": {"longitude_deg": 160.0}, "Moon": {"longitude_deg": 310.0}, "Mars": {"longitude_deg": 220.0},
    "Mercury": {"longitude_deg": 185.0}, "Jupiter": {"longitude_deg": 75.0},
    "Venus": {"longitude_deg": 165.0}, "Saturn": {"longitude_deg": 130.0}}}
_GOCHARA = {"saturn": {"longitude": 345.0, "transit_rasi": "Pisces"}, "jupiter": {"longitude": 112.0, "transit_rasi": "Cancer"},
            "rahu_ketu": {"rahu_rasi": "Aquarius", "ketu_rasi": "Leo"}}


def _bav():
    return compute_bhinnashtakavarga(_EPH)


def test_threshold_is_four_inclusive():
    assert AV_TRANSIT_THRESHOLD == 4
    bav = _bav()
    for planet in ("saturn", "jupiter"):
        for idx, n in enumerate(bav[planet]["bindus_per_sign"]):
            e = bav_transit_strength(bav, {planet: idx * 30.0 + 1})[planet]
            assert e["bindus"] == n
            assert e["label"] == ("above threshold" if n >= 4 else "below threshold")


def test_saturn_and_jupiter_only_and_format():
    s = bav_transit_strength(_bav(), {"saturn": 345.0, "jupiter": 112.0, "rahu": 304.0})
    assert set(s) == {"saturn", "jupiter"}
    line = format_bav_transit_line(s["jupiter"])
    assert line.startswith("Jupiter in Cancer: ") and line.endswith(("/8, above threshold", "/8, below threshold"))


def test_consumers_render_the_same_numbers():
    from app.llm.payload_builder import _build_bav_context
    from app.pdf.canonical_report.data_loader import _extract_transit_context
    bav = _bav()
    expected = bav_transit_strength(bav, gochara_transit_longitudes(_GOCHARA))
    ctx = _build_bav_context(bav, _GOCHARA)
    pdf = _extract_transit_context({"gochara": _GOCHARA}, {"bhinnashtakavarga": bav})
    for planet, e in expected.items():
        assert ctx[planet]["line"] == format_bav_transit_line(e)
        assert getattr(pdf, f"{planet}_bindus") == e["bindus"]
        assert f"{e['bindus']}/8, {e['label']}" in getattr(pdf, f"{planet}_transit")


def test_no_consumer_uses_the_old_engine_for_transit_strength():
    from app.api import chat, family
    from app.llm import payload_builder
    from app.pdf.canonical_report import data_loader
    for mod in (chat, family, payload_builder, data_loader):
        assert "bav_transit_strength" in inspect.getsource(mod), mod.__name__
    src = inspect.getsource(data_loader._extract_transit_context)
    assert 'envelope.get("ashtakavarga"' not in src


def test_with_av_transit_strength_returns_a_copy_with_corrected_values():
    """Serve-time attach for the web view (2026-10-02): the monthly badge
    used to read envelope["ashtakavarga"] (old 57-total heuristic) from the
    cached envelope; it now reads av_transit_strength, never persisted."""
    from app.engines.bhinnashtakavarga_engine import with_av_transit_strength
    env = {"gochara": _GOCHARA, "ashtakavarga": {"jupiter": {"bindus": 9}}}
    out = with_av_transit_strength(env, {"ephemeris": _EPH})
    assert "av_transit_strength" not in env  # input untouched
    assert out["av_transit_strength"] == bav_transit_strength(_bav(), gochara_transit_longitudes(_GOCHARA))
    assert out["ashtakavarga"] is env["ashtakavarga"]


def test_web_view_reads_corrected_strength_not_old_engine():
    from pathlib import Path
    tsx = (Path(__file__).parents[3] / "client/src/components/prediction/MonthlyPredictionView.tsx").read_text()
    assert "envelope.av_transit_strength" in tsx
    assert "envelope.ashtakavarga" not in tsx.replace("not envelope.ashtakavarga", "")
