# tests/engines/test_transit_hits_chat.py
"""
select_chat_transit_hits() (transit_hits_engine.py, 2026-10-02): chat-facing
filter over compute_transit_hits(). Only Vedic-meaningful relations are
surfaced (conjunction, opposition = 7th aspect, and trine/square ONLY where
they coincide with Jupiter 5th/9th, Mars 4th, Saturn 10th special drishti);
house/life_area_hint are never surfaced (Equal House); hits on the scan's
edge day are flagged as not-yet/no-longer exact.
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


def test_trine_kept_only_as_jupiter_special_drishti():
    jup_9th = _hit("Jupiter", "Moon", 120.8, 0.8, "trine")       # Moon 240 deg ahead -> 9th
    mars_trine = _hit("Mars", "Moon", 121.0, 0.8, "trine")       # no Mars 5th/9th drishti
    saturn_trine = _hit("Saturn", "Mars", 344.3, 222.4, "trine")  # no Saturn 5th/9th drishti
    sel = select_chat_transit_hits([jup_9th, mars_trine, saturn_trine], REF)
    assert len(sel) == 1
    assert "special 9th-house aspect" in sel[0]["relation"]


def test_square_kept_only_for_mars_4th_and_saturn_10th():
    mars_4th = _hit("Mars", "Venus", 100.0, 190.0, "square")       # 90 ahead -> 4th
    mars_10th = _hit("Mars", "Moon", 90.7, 0.8, "square")          # 270 ahead -> no Mars drishti
    saturn_10th = _hit("Saturn", "Sun", 100.0, 10.0, "square")     # 270 ahead -> 10th
    jupiter_sq = _hit("Jupiter", "Saturn", 112.5, 22.5, "square")  # Jupiter has no square drishti
    sel = select_chat_transit_hits([mars_4th, mars_10th, saturn_10th, jupiter_sq], REF)
    rel = [s["relation"] for s in sel]
    assert rel == [
        "casting its special 4th-house aspect exactly onto your natal Venus",
        "casting its special 10th-house aspect exactly onto your natal Sun",
    ]


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
    assert sel["Rahu2026-11-16"].startswith("tightening; becomes exact after 2026-11-16")
    assert sel["Mars2026-08-18"].startswith("was exact before 2026-08-18")
    assert sel["Jupiter2026-08-26"] == "exact on 2026-08-26 (past, now separating)"


def test_compact_limits_to_nearest():
    hits = [_hit("Mars", "Sun", 108.5, 288.4, "opposition", hit_date=d)
            for d in ("2026-09-01", "2026-10-03", "2026-10-10", "2026-11-10")]
    text = format_chat_transit_hits_compact(select_chat_transit_hits(hits, REF), REF, limit=2)
    assert "2026-10-03" in text and "2026-10-10" in text and "2026-11-10" not in text
