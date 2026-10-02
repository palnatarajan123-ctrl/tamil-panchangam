# tests/engines/test_transit_hits_chat.py
"""
select_chat_transit_hits() (transit_hits_engine.py, 2026-10-02): chat-facing
filter over compute_transit_hits(). Only Vedic-meaningful relations are
surfaced (conjunction, opposition = 7th aspect, and the special drishti
computed by compute_transit_hits(vedic_drishti=True): Jupiter 5th/9th, Mars
4th/8th, Saturn 3rd/10th, by FORWARD angle); house/life_area_hint are never
surfaced (Equal House); hits on the scan's edge day are flagged as not-yet/no-longer exact.
"""
from datetime import date

from app.engines.transit_hits_engine import (
    format_chat_transit_hits,
    format_chat_transit_hits_compact,
    select_chat_transit_hits,
)

REF = date(2026, 10, 2)


def _hit(tp, np_, t_deg, n_deg, aspect, hit_date="2026-10-20"):
    return {"transit_planet": tp, "natal_planet": np_, "transit_degree": t_deg, "natal_degree": n_deg,
            "aspect_type": aspect, "hit_date": hit_date, "orb": 0.1, "house": 10, "life_area_hint": "career"}


def test_conjunction_and_opposition_kept_in_vedic_terms():
    sel = select_chat_transit_hits([
        _hit("Rahu", "Rahu", 301.0, 301.0, "conjunction"),
        _hit("Mars", "Sun", 108.5, 288.4, "opposition"),
    ], REF)
    assert [s["relation"] for s in sel] == [
        "transiting over your natal Rahu",
        "exactly opposite your natal Sun (its 7th-house aspect)",
    ]


def test_drishti_hits_named_and_western_trine_square_dropped():
    sel = select_chat_transit_hits([
        _hit("Saturn", "Venus", 0.0, 60.0, "drishti_3rd"),
        _hit("Mars", "Moon", 0.0, 210.0, "drishti_8th"),
        _hit("Jupiter", "Moon", 120.8, 0.8, "trine"),   # Western band: never relabelled now
        _hit("Saturn", "Sun", 100.0, 10.0, "square"),
    ], REF)
    assert [s["relation"] for s in sel] == [
        "casting its special 3rd-house aspect exactly onto your natal Venus",
        "casting its special 8th-house aspect exactly onto your natal Moon",
    ]


def _fixed_sky(monkeypatch, lons):
    from app.engines import transit_hits_engine
    monkeypatch.setattr(transit_hits_engine, "compute_planet_longitude",
                        lambda planet, dt, ayanamsa, node_type="mean": lons[planet])


def _natal(**lons):
    return {"lagna": {"longitude_deg": 0.0},
            "planets": {n: {"longitude_deg": v} for n, v in lons.items()}}


def test_vedic_drishti_covers_every_special_aspect_by_forward_angle(monkeypatch):
    """Until 2026-10-02 the chats relabelled the Western trine/square bands,
    which are one-sided (transit - natal against one angle) and so only ever
    caught forward 240/270: Jupiter 5th, Mars 4th/8th and Saturn 3rd were
    never computed."""
    from app.engines.transit_hits_engine import compute_transit_hits
    # Rahu/Ketu parked where they touch nothing.
    _fixed_sky(monkeypatch, {"Jupiter": 20.0, "Saturn": 100.0, "Mars": 200.0, "Rahu": 345.0, "Ketu": 165.0})
    eph = _natal(J5=140.0, J9=260.0, S3=160.0, S10=10.0, M4=290.0, M8=50.0)
    hits = compute_transit_hits(eph, reference_date=REF, window_days=0, vedic_drishti=True)
    got = {(h["transit_planet"], h["natal_planet"], h["aspect_type"]) for h in hits}
    assert got == {
        ("Jupiter", "J5", "drishti_5th"), ("Jupiter", "J9", "drishti_9th"),
        ("Saturn", "S3", "drishti_3rd"), ("Saturn", "S10", "drishti_10th"),
        ("Mars", "M4", "drishti_4th"), ("Mars", "M8", "drishti_8th"),
    }
    # Direction matters: natal 90 deg BEHIND Mars is forward 270, not its 4th.
    _fixed_sky(monkeypatch, {"Jupiter": 300.0, "Saturn": 300.0, "Mars": 100.0, "Rahu": 300.0, "Ketu": 120.0})
    hits = compute_transit_hits(_natal(X=10.0), reference_date=REF, window_days=0, vedic_drishti=True)
    assert hits == []


def test_default_path_unchanged_for_monthly_reports(monkeypatch):
    """predictive_signals_engine (monthly reports) keeps the Western set."""
    from app.engines.transit_hits_engine import compute_transit_hits
    _fixed_sky(monkeypatch, {"Jupiter": 130.0, "Saturn": 300.0, "Mars": 300.0, "Rahu": 300.0, "Ketu": 120.0})
    hits = compute_transit_hits(_natal(X=10.0), reference_date=REF, window_days=0)
    assert {(h["transit_planet"], h["aspect_type"]) for h in hits} == {("Jupiter", "trine")}


def test_house_and_life_area_never_surfaced():
    sel = select_chat_transit_hits([_hit("Mars", "Sun", 108.5, 288.4, "opposition")], REF)
    assert "house" not in sel[0] and "life_area_hint" not in sel[0]
    text = format_chat_transit_hits(sel) + format_chat_transit_hits_compact(sel, REF)
    assert "career" not in text


def test_window_edge_hits_are_not_presented_as_exact():
    end_edge = _hit("Rahu", "Rahu", 301.1, 300.95, "conjunction", hit_date="2026-11-16")
    start_edge = _hit("Mars", "Sun", 108.5, 288.4, "opposition", hit_date="2026-08-18")
    past = _hit("Jupiter", "Sun", 108.4, 288.4, "opposition", hit_date="2026-08-26")
    sel = {s["transit_planet"] + s["hit_date"]: s["when"] for s in select_chat_transit_hits([end_edge, start_edge, past], REF)}
    assert sel["Rahu2026-11-16"].startswith("tightening; becomes exact after 16 Nov 2026")
    assert sel["Mars2026-08-18"].startswith("was exact before 18 Aug 2026")
    assert sel["Jupiter2026-08-26"] == "exact on 26 Aug 2026 (past, now separating)"


def test_compact_limits_to_nearest():
    hits = [_hit("Mars", "Sun", 108.5, 288.4, "opposition", hit_date=d)
            for d in ("2026-09-01", "2026-10-03", "2026-10-10", "2026-11-10")]
    text = format_chat_transit_hits_compact(select_chat_transit_hits(hits, REF), REF, limit=2)
    assert "3 Oct 2026" in text and "10 Oct 2026" in text and "10 Nov 2026" not in text
