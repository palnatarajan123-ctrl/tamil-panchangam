"""
Regression tests for the hardcoded true-node transit bug.

swisseph_utils.py used to hardcode swe.TRUE_NODE for Rahu regardless of
the chart's own chart_metadata.node_type, while the natal engine
(ephemeris.py) defaults to mean node -- the traditional Tamil astrology
convention. This moved Rahu's real-world Dec 2026 Capricorn ingress
~10 days early (Nov 26 true-node vs the correct Dec 6 mean-node date
external sources report). See CLAUDE.md's 2026-09-12 Rahu-Ketu peyarchi
investigation.
"""
from datetime import datetime

from app.utils.swisseph_utils import compute_planet_longitude, compute_planet_longitude_with_speed
from app.engines.gochara_engine import compute_gochara


def test_mean_node_default_matches_ephemeris_convention():
    # Rahu moves retrograde (Aquarius -> Capricorn -> Sagittarius as time
    # advances). On Nov 30, 2026: true node has already crossed into
    # Capricorn (ingressed Nov 26), mean node hasn't yet (ingresses Dec 6)
    # and is still in Aquarius.
    dt = datetime(2026, 11, 30)
    mean_lon = compute_planet_longitude("Rahu", dt)  # default node_type="mean"
    true_lon = compute_planet_longitude("Rahu", dt, node_type="true")

    assert int(mean_lon // 30) == 10  # Aquarius
    assert int(true_lon // 30) == 9   # Capricorn


def test_rahu_ingress_date_matches_external_sources_under_mean_node():
    from datetime import timedelta

    def find_ingress(node_type):
        d = datetime(2026, 11, 20)
        prev_idx = None
        while d < datetime(2026, 12, 15):
            lon = compute_planet_longitude("Rahu", d, node_type=node_type)
            idx = int(lon // 30) % 12
            if prev_idx is not None and idx != prev_idx:
                return d
            prev_idx = idx
            d += timedelta(days=1)
        return None

    assert find_ingress("mean") == datetime(2026, 12, 6)
    assert find_ingress("true") == datetime(2026, 11, 26)


def test_ketu_speed_still_opposite_of_rahu_for_both_node_types():
    dt = datetime(2026, 12, 10)
    for node_type in ("mean", "true"):
        rahu_long, rahu_speed = compute_planet_longitude_with_speed("Rahu", dt, node_type=node_type)
        ketu_long, ketu_speed = compute_planet_longitude_with_speed("Ketu", dt, node_type=node_type)
        assert abs((ketu_long - rahu_long) % 360 - 180) < 1e-6
        assert ketu_speed == -rahu_speed


def test_gochara_node_type_param_defaults_to_mean_and_can_be_overridden():
    kwargs = dict(
        reference_date_utc=datetime(2026, 11, 30),
        latitude=13.08,
        longitude=80.27,
        natal_moon_rasi="Aries",
        natal_lagna_rasi="Aries",
    )
    default_result = compute_gochara(**kwargs)
    mean_result = compute_gochara(node_type="mean", **kwargs)
    true_result = compute_gochara(node_type="true", **kwargs)

    assert default_result["rahu_ketu"]["rahu_rasi"] == mean_result["rahu_ketu"]["rahu_rasi"] == "Aquarius"
    assert true_result["rahu_ketu"]["rahu_rasi"] == "Capricorn"
