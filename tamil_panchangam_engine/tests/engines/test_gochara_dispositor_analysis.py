"""
Regression test for gochara_engine.py's dispositor analysis (2026-09-17
fix).

Confirmed gap: Gochara prediction was house-position-only -- the same
static JUPITER_EFFECTS/SATURN_PHASES table applied identically to every
chart with the same house-from-Moon transit, regardless of who ruled
that house or that lord's natal condition. This meant "Saturn transiting
your 10th house" meant the exact same thing for two people with
different 10th-house lords -- the scenario classical dispositor analysis
exists to differentiate.

Fixed by adding _dispositor_analysis() to gochara_engine.py: looks up
the transited house's own lord (from Lagna, reusing
house_strength_engine.get_lord_for_house()), that lord's natal placement
(reusing shadbala_engine.compute_sthana_bala(), which already combines
dignity + kendra/trikona bonus), and this specific chart's
yogakaraka/maraka status for that lord (reusing
functional_role_engine.compute_functional_roles()). The result modulates
signal strength the same way the existing drishti_aspect_bonus already
does -- it does not replace the base house-position classification.
"""
import json

from app.db.postgres import get_conn
from app.engines.prediction_envelope import build_monthly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope
from app.engines.gochara_engine import compute_gochara
from app.engines.functional_role_engine import compute_functional_roles
from datetime import datetime, timezone

# Two real charts, confirmed live: on 2026-09, Saturn transits the exact
# SAME house from Moon (7) in the exact SAME phase (kantaka_sani,
# "challenging") for both -- an identical base Gochara reading -- and
# the transited house's own dispositor (from Lagna) is the SAME lord
# (Jupiter) in the SAME natal placement (own_sign) for both. The only
# difference is each chart's own Lagna-specific functional role for
# that lord: yogakaraka for one chart, maraka for the other.
CHART_YOGAKARAKA_DISPOSITOR = "cc8325b8"  # Jupiter: own_sign, yogakaraka
CHART_MARAKA_DISPOSITOR = "fca1abca"      # Jupiter: own_sign, maraka


def _load_chart(prefix: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT payload FROM base_charts WHERE id::text LIKE %s", (prefix + "%",)
        ).fetchone()
    assert row, f"expected chart fixture {prefix} missing from DB"
    return row[0] if isinstance(row[0], dict) else json.loads(row[0])


class TestDispositorAnalysisPresent:
    def test_gochara_entry_carries_dispositor_when_inputs_available(self):
        payload = _load_chart(CHART_YOGAKARAKA_DISPOSITOR)
        eph = payload["ephemeris"]
        fr = compute_functional_roles(ephemeris=eph, houses={})
        result = compute_gochara(
            reference_date_utc=datetime(2026, 9, 17, tzinfo=timezone.utc),
            latitude=payload["birth_details"]["latitude"],
            longitude=payload["birth_details"]["longitude"],
            natal_moon_rasi=eph["moon"]["rasi"],
            natal_moon_longitude=eph["moon"]["longitude_deg"],
            natal_lagna_rasi=eph["lagna"]["rasi"],
            natal_lagna_longitude=eph["lagna"]["longitude_deg"],
            natal_planets=eph.get("planets", {}),
            functional_roles=fr,
            ayanamsa=eph.get("ayanamsa", "lahiri"),
        )
        assert "dispositor" in result["saturn"]
        disp = result["saturn"]["dispositor"]
        assert disp["lord"]
        assert disp["lord_placement"]
        assert isinstance(disp["strength_bonus"], float)

    def test_dispositor_absent_when_inputs_missing_graceful_degradation(self):
        payload = _load_chart(CHART_YOGAKARAKA_DISPOSITOR)
        eph = payload["ephemeris"]
        result = compute_gochara(
            reference_date_utc=datetime(2026, 9, 17, tzinfo=timezone.utc),
            latitude=payload["birth_details"]["latitude"],
            longitude=payload["birth_details"]["longitude"],
            natal_moon_rasi=eph["moon"]["rasi"],
            natal_lagna_rasi=eph["lagna"]["rasi"],
            # natal_lagna_longitude / natal_planets / functional_roles omitted
            ayanamsa=eph.get("ayanamsa", "lahiri"),
        )
        assert "dispositor" not in result["saturn"]


class TestTwoRealChartsDifferentiateOnDispositor:
    """
    THE core proof: two real charts, identical base Gochara reading
    (same transiting planet, same phase, same house, same dispositor
    lord in the same natal placement) -- must now produce genuinely
    different scoring output because of each chart's own functional-role
    relationship to that lord. Before this fix, this test would have
    been impossible to write: both charts' GOCHARA_SATURN_* signal
    strength and rationale were identical, driven by house-position
    alone.
    """

    def _build(self, prefix):
        payload = _load_chart(prefix)
        envelope = build_monthly_prediction_envelope(base_chart=payload, year=2026, month=9)
        synthesis = synthesize_from_envelope(envelope)
        return envelope, synthesis

    def test_base_gochara_reading_is_identical_for_both_charts(self):
        """Sanity check the premise: same transiting planet, phase, and
        moon-house for both charts -- so any difference downstream must
        come from the dispositor layer, not a different base transit."""
        env_a, _ = self._build(CHART_YOGAKARAKA_DISPOSITOR)
        env_b, _ = self._build(CHART_MARAKA_DISPOSITOR)
        sat_a, sat_b = env_a["gochara"]["saturn"], env_b["gochara"]["saturn"]
        assert sat_a["phase"] == sat_b["phase"] == "kantaka_sani"
        assert sat_a["effect"] == sat_b["effect"] == "challenging"
        assert sat_a["from_moon_house"] == sat_b["from_moon_house"] == 7

    def test_dispositor_lord_and_placement_are_identical_but_functional_role_differs(self):
        env_a, _ = self._build(CHART_YOGAKARAKA_DISPOSITOR)
        env_b, _ = self._build(CHART_MARAKA_DISPOSITOR)
        disp_a = env_a["gochara"]["saturn"]["dispositor"]
        disp_b = env_b["gochara"]["saturn"]["dispositor"]
        assert disp_a["lord"] == disp_b["lord"] == "Jupiter"
        assert disp_a["lord_placement"] == disp_b["lord_placement"] == "own_sign"
        assert disp_a["lord_functional_role"] == "yogakaraka"
        assert disp_b["lord_functional_role"] == "maraka"
        assert disp_a["strength_bonus"] > disp_b["strength_bonus"]

    def test_final_signal_strength_and_score_genuinely_differ(self):
        """The actual proof: identical base transit, different final
        contribution to the score, because of chart-specific dispositor
        functional role -- not something the old house-position-only
        engine could ever produce."""
        _, synth_a = self._build(CHART_YOGAKARAKA_DISPOSITOR)
        _, synth_b = self._build(CHART_MARAKA_DISPOSITOR)

        def _saturn_signal(synth):
            life_areas = synth.get("life_areas", {})
            if "scores" in life_areas:
                life_areas = life_areas["scores"]
            for area, data in life_areas.items():
                for sig in data.get("top_signals", []):
                    if sig["key"].startswith("GOCHARA_SATURN"):
                        return sig
            return None

        sig_a = _saturn_signal(synth_a)
        sig_b = _saturn_signal(synth_b)
        assert sig_a is not None and sig_b is not None
        assert sig_a["contrib"] != sig_b["contrib"]
        assert "yogakaraka" in sig_a["rationale"]
        assert "maraka" in sig_b["rationale"]
