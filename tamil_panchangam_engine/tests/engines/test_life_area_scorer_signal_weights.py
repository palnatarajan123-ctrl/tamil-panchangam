"""
Regression test for life_area_scorer.py's signal-weighting gap
(2026-09-15 fix).

score_one() computed `raw = (house_w + planet_w) * strength * src_bias *
val_mult`. Any signal carrying neither a house nor a planet (yogas,
Tara Bala, Ashtakavarga validation, Chandra Gati rhythm, Navamsa
dignity, aspect-balance summaries, event-window confluence, some
divisional-chart refinements) got house_w=planet_w=0.0 regardless of
its own "strength" field -- raw was always exactly 0, so `if abs(raw) >
0` silently excluded these signals from both top_signals and the
resulting score/delta for EVERY life area, no matter how strong.

Fixed by adding two declarative weight tables to life_area_config.py
(per area): signal_key_weights (exact-key overrides for signals whose
classical relevance genuinely differs by area, e.g. a wealth yoga
matters more to "finance" than "health") and signal_source_weights (a
per-source fallback for dynamically-suffixed keys like
"TARA_BALA_SAMPAT"/"ASHTAKAVARGA_STRONG_SUPPORT", applied only when a
signal has no house/planet AND no exact-key override). A signal that
DOES carry a house/planet but legitimately scores 0 for a specific area
(e.g. a Sun-related signal in an area that doesn't weight Sun) is
untouched -- that's a real "not relevant here", not the structural gap.
"""
from app.engines.life_area_scorer import LifeAreaScorer
from app.engines.life_area_config import LIFE_AREAS
from app.db.postgres import get_conn
from app.engines.prediction_envelope import build_monthly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope

CHART_7C6E34BE = "7c6e34be-fa46-4821-8bb0-c0186b28d6e4"


def _bindus(overrides=None):
    return overrides or {}


class TestStructurallyHouselessSignalsGetRealWeight:
    """Unit-level: every previously-silent signal type, isolated."""

    def _signal(self, key, source, strength=0.6, valence="pos"):
        return {
            "key": key, "source": source, "valence": valence,
            "strength": strength, "confidence": 0.7, "rationale": "test",
        }

    def test_yoga_signal_contributes_nonzero_across_all_areas(self):
        scorer = LifeAreaScorer()
        signal = self._signal("YOGA_RAJA", "yoga", strength=0.65)
        for area in LIFE_AREAS:
            result = scorer.score_one(
                area=area, base_score_0_100=50.0, base_confidence_0_1=0.6,
                signals=[signal],
            )
            assert len(result["top_signals"]) == 1, f"{area}: YOGA_RAJA excluded"
            assert result["top_signals"][0]["contrib"] != 0.0, f"{area}: zero contribution"

    def test_tara_bala_dynamic_key_gets_source_fallback_weight(self):
        """TARA_BALA_SAMPAT (dynamically suffixed) isn't in
        signal_key_weights by exact key -- must fall back to the
        "nakshatra" source weight, not silently stay at 0."""
        scorer = LifeAreaScorer()
        signal = self._signal("TARA_BALA_SAMPAT", "nakshatra", strength=0.65)
        result = scorer.score_one(
            area="career", base_score_0_100=50.0, base_confidence_0_1=0.6,
            signals=[signal],
        )
        assert len(result["top_signals"]) == 1
        assert result["top_signals"][0]["contrib"] != 0.0

    def test_ashtakavarga_dynamic_key_gets_source_fallback_weight(self):
        scorer = LifeAreaScorer()
        signal = self._signal("ASHTAKAVARGA_STRONG_SUPPORT", "ashtakavarga", strength=0.6)
        result = scorer.score_one(
            area="finance", base_score_0_100=50.0, base_confidence_0_1=0.6,
            signals=[signal],
        )
        assert len(result["top_signals"]) == 1
        assert result["top_signals"][0]["contrib"] != 0.0

    def test_chandra_gati_rhythm_gets_real_weight(self):
        scorer = LifeAreaScorer()
        signal = self._signal("CHANDRA_GATI_RHYTHM", "chandra_gati", strength=0.5)
        result = scorer.score_one(
            area="relationships", base_score_0_100=50.0, base_confidence_0_1=0.6,
            signals=[signal],
        )
        assert len(result["top_signals"]) == 1
        assert result["top_signals"][0]["contrib"] != 0.0

    def test_navamsa_dignity_gets_real_weight(self):
        scorer = LifeAreaScorer()
        signal = self._signal("NAVAMSA_DIGNITY", "derived", strength=0.5)
        result = scorer.score_one(
            area="relationships", base_score_0_100=50.0, base_confidence_0_1=0.6,
            signals=[signal],
        )
        assert len(result["top_signals"]) == 1
        assert result["top_signals"][0]["contrib"] != 0.0

    def test_drishti_balance_summary_gets_real_weight(self):
        scorer = LifeAreaScorer()
        signal = self._signal("DRISHTI_BALANCE_BENEFIC", "drishti", strength=0.45)
        result = scorer.score_one(
            area="health", base_score_0_100=50.0, base_confidence_0_1=0.6,
            signals=[signal],
        )
        assert len(result["top_signals"]) == 1
        assert result["top_signals"][0]["contrib"] != 0.0

    def test_event_windows_favorable_gets_real_weight(self):
        scorer = LifeAreaScorer()
        signal = self._signal("EVENT_WINDOWS_FAVORABLE", "event_windows", strength=0.55)
        result = scorer.score_one(
            area="career", base_score_0_100=50.0, base_confidence_0_1=0.6,
            signals=[signal],
        )
        assert len(result["top_signals"]) == 1
        assert result["top_signals"][0]["contrib"] != 0.0

    def test_house_planet_signal_legitimately_zero_for_area_is_unaffected(self):
        """A signal that DOES carry a house/planet but isn't weighted at
        all by this specific area's config must stay excluded -- the fix
        must not paper over a real "not relevant here"."""
        scorer = LifeAreaScorer()
        # Sun has no entry in personal_growth's benefics/malefics, and
        # house 2 has no entry in personal_growth's houses.
        signal = {
            "key": "SOME_SUN_H2_SIGNAL", "source": "transit", "house": 2,
            "planet": "Sun", "valence": "pos", "strength": 0.6,
            "confidence": 0.7, "rationale": "test",
        }
        result = scorer.score_one(
            area="personal_growth", base_score_0_100=50.0, base_confidence_0_1=0.6,
            signals=[signal],
        )
        assert len(result["top_signals"]) == 0, "legitimate zero must remain excluded"


class TestRealChartRajaYogaContributesToScore:
    """
    Real-chart-data regression test that would have caught the original
    exclusion bug: chart 7c6e34be has a confirmed active Raja Yoga
    (yogas.summary.has_raja_yoga = True), which produces a YOGA_RAJA
    signal in synthesize_from_envelope()'s real signal list. Before the
    fix, this signal was silently excluded from top_signals/scoring for
    every life area -- a real chart with a strong yoga scored no
    differently than one without it.
    """

    def test_yoga_raja_signal_present_and_contributes(self):
        with get_conn() as conn:
            row = conn.execute(
                "SELECT payload FROM base_charts WHERE id = %s", (CHART_7C6E34BE,)
            ).fetchone()
        assert row, "expected chart fixture missing from DB"
        payload = row[0] if isinstance(row[0], dict) else __import__("json").loads(row[0])

        assert payload.get("yogas", {}).get("summary", {}).get("has_raja_yoga") is True, (
            "test fixture chart no longer has an active Raja Yoga -- pick a different chart"
        )

        envelope = build_monthly_prediction_envelope(base_chart=payload, year=2026, month=9)
        synthesis = synthesize_from_envelope(envelope)

        life_areas = synthesis.get("life_areas", {})
        if "scores" in life_areas:
            life_areas = life_areas["scores"]

        found_nonzero_yoga_raja = False
        for area, area_result in life_areas.items():
            for sig in area_result.get("top_signals", []):
                if sig["key"] == "YOGA_RAJA":
                    assert sig["contrib"] != 0.0, f"YOGA_RAJA contributes 0 in {area}"
                    found_nonzero_yoga_raja = True

        assert found_nonzero_yoga_raja, (
            "YOGA_RAJA never appeared in any life area's top_signals for a chart "
            "with a confirmed active Raja Yoga -- the exclusion bug has regressed"
        )
