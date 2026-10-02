"""
Regression tests for the Tamil/English rasi-name mismatch bug.

Chart payloads store ephemeris.moon.rasi / ephemeris.lagna.rasi in Tamil
(e.g. "Simmam"), but gochara_engine.py and moon_transit_engine.py key
their house-counting lookups in English ("Leo"). Passing the Tamil name
straight through used to silently fall back to index 0 ("as if Moon is
in Aries") for every non-Aries chart -- see CLAUDE.md's 2026-09-12
Rahu-Ketu peyarchi investigation for the real production incident this
traces back to.
"""
from datetime import datetime

from app.utils.rasi_utils import to_english_rasi, ENGLISH_TO_TAMIL_RASI
from app.engines.gochara_engine import compute_gochara
from app.engines.moon_transit_engine import compute_chandra_gati


def test_to_english_rasi_converts_tamil():
    assert to_english_rasi("Simmam") == "Leo"
    assert to_english_rasi("Mesham") == "Aries"


def test_to_english_rasi_passes_through_english_and_none():
    assert to_english_rasi("Leo") == "Leo"
    assert to_english_rasi(None) is None
    assert to_english_rasi("") == ""


def test_all_twelve_tamil_names_round_trip():
    for english, tamil in ENGLISH_TO_TAMIL_RASI.items():
        assert to_english_rasi(tamil) == english


def test_gochara_house_from_moon_matches_for_tamil_and_english_input():
    kwargs = dict(
        reference_date_utc=datetime(2026, 12, 10),
        latitude=13.08,
        longitude=80.27,
    )
    tamil_result = compute_gochara(natal_moon_rasi="Simmam", natal_lagna_rasi="Simmam", **kwargs)
    english_result = compute_gochara(natal_moon_rasi="Leo", natal_lagna_rasi="Leo", **kwargs)

    assert tamil_result["rahu_ketu"]["rahu_from_moon_house"] == english_result["rahu_ketu"]["rahu_from_moon_house"]
    assert tamil_result["saturn"]["from_moon_house"] == english_result["saturn"]["from_moon_house"]
    assert tamil_result["jupiter"]["from_moon_house"] == english_result["jupiter"]["from_moon_house"]


def test_gochara_rahu_house_for_capricorn_transit_from_leo_moon():
    # Capricorn is the 6th sign counted from Leo -- independent of the
    # Tamil/English bug, this pins the actual expected value so a future
    # regression can't silently reintroduce the Aries-fallback behavior.
    result = compute_gochara(
        reference_date_utc=datetime(2026, 12, 10),
        latitude=13.08,
        longitude=80.27,
        natal_moon_rasi="Simmam",
        natal_lagna_rasi="Simmam",
    )
    assert result["rahu_ketu"]["rahu_rasi"] == "Capricorn"
    assert result["rahu_ketu"]["rahu_from_moon_house"] == 6


def test_chandra_gati_house_from_natal_matches_for_tamil_and_english_input():
    tamil_result = compute_chandra_gati(2026, 12, "Simmam")
    english_result = compute_chandra_gati(2026, 12, "Leo")

    tamil_houses = [p["house_from_natal"] for p in tamil_result["moon_positions"]]
    english_houses = [p["house_from_natal"] for p in english_result["moon_positions"]]
    assert tamil_houses == english_houses


# ── 2026-10-02: Ashtakavarga sign-name consolidation ─────────────────────────

def test_variant_spellings_normalize():
    from app.utils.rasi_utils import to_english_rasi, to_payload_rasi
    assert to_english_rasi("Kadagam") == "Cancer" and to_english_rasi("Kadakam") == "Cancer"
    assert to_english_rasi("Midhunam") == "Gemini" and to_english_rasi("Simham") == "Leo"
    assert to_payload_rasi("Kadagam") == "Kadakam" and to_payload_rasi("Leo") == "Simmam"
    assert to_payload_rasi("nonsense") == "nonsense" and to_payload_rasi(None) is None


def test_refined_av_keys_match_payload_rasi_spelling():
    """refined_av_engine used "Midhunam/Kadagam/Simham" while every chart
    payload (ephemeris.get_rasi) says "Mithunam/Kadakam/Simmam": a lookup by
    a transiting planet's payload rasi silently returned None for those
    three signs (real chart 7c6e34be, Oct 2026: Jupiter in Kadakam, Ketu in
    Simmam both missed)."""
    from app.engines.ephemeris import RASI_NAMES as PAYLOAD_RASI_NAMES, get_rasi
    from app.engines.refined_av_engine import compute_refined_av, refined_score_for_rasi
    bav = {p: {"bindus_per_sign": [5] * 12} for p in
           ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn")}
    sav = compute_refined_av(bav)["sarvashtakavarga_refined"]
    assert list(sav) == PAYLOAD_RASI_NAMES
    for lon in (75.0, 100.0, 130.0):  # Gemini, Cancer, Leo
        assert sav.get(get_rasi(lon)) is not None
    assert refined_score_for_rasi(sav, "Kadagam") == sav["Kadakam"] == refined_score_for_rasi(sav, "Cancer")


def test_event_window_signal5_uses_same_sign_list_as_refined_av():
    import inspect
    from app.engines import event_window_engine, refined_av_engine
    assert refined_av_engine.RASI_NAMES is event_window_engine.TAMIL_RASI_ORDER
    assert "Kadagam" not in inspect.getsource(event_window_engine)


def test_bav_rasi_fallback_accepts_payload_tamil_spelling():
    """A planet with only a (Tamil) rasi and no longitude used to be dropped:
    the fallback checked the Tamil string against an English SIGN_INDEX."""
    from app.engines.bhinnashtakavarga_engine import compute_bhinnashtakavarga
    eph = {"lagna": {"longitude_deg": 15.0}, "planets": {
        p: {"longitude_deg": 15.0} for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus")}}
    eph["planets"]["Saturn"] = {"rasi": "Kadakam"}
    by_rasi = compute_bhinnashtakavarga(eph)
    eph["planets"]["Saturn"] = {"longitude_deg": 100.0}  # Cancer
    assert by_rasi == compute_bhinnashtakavarga(eph)
    assert by_rasi["saturn"]["total"] == 39
