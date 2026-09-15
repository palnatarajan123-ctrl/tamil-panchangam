"""
Regression test for ai_interpretation_engine.py's signal-source
inference (2026-09-15 fix).

top_signals entries (from life_area_scorer.py) carry no "source" field
of their own, so ai_interpretation_engine.py infers it from the key
prefix -- but that inference used to be duplicated independently in
_normalize_signals() and _generate_life_area_interpretation()'s
engines_used loop, and only covered the signal types that could ever
reach a non-empty top_signals BEFORE the 2026-09-15 life_area_scorer.py
structural-exclusion fix. MARAKA_ACTIVE_*, YOGAKARAKA_ACTIVE_*,
CHANDRA_GATI_RHYTHM, NAVAMSA_DIGNITY, D10_*/D2_*/D7_*, and
EVENT_WINDOWS_* fell through every branch, leaving source=None -- which
downstream became a literal "key": None in the LLM payload's
signals_used attribution and failed schema validation
("None is not of type 'string'"). Confirmed live: this crashed one row
(chart f1eb7ec4, monthly 2026-07, health area) during the post-fix
backfill via a real MARAKA_ACTIVE_Mars signal.

Fixed by extracting a single shared _infer_source_from_key() covering
every real signal key prefix, used by both call sites.
"""
from app.engines.ai_interpretation_engine import (
    _infer_source_from_key,
    _normalize_signals,
    generate_interpretation,
)
from app.db.postgres import get_conn
from app.engines.prediction_envelope import build_monthly_prediction_envelope
from app.engines.synthesis_engine import synthesize_from_envelope
import json

CHART_F1EB7EC4_PREFIX = "f1eb7ec4"


class TestInferSourceFromKeyCoversEveryRealSignalType:
    """One assertion per real key prefix found in synthesis_engine.py --
    the exact set life_area_scorer.py's top_signals can now legitimately
    contain since the structural-exclusion fix."""

    def test_maraka_active_maps_to_functional_roles(self):
        assert _infer_source_from_key("MARAKA_ACTIVE_Mars") == "functional_roles"

    def test_yogakaraka_active_maps_to_functional_roles_not_yoga(self):
        # "YOGAKARAKA" also starts with "YOGA" -- must not be misclassified.
        assert _infer_source_from_key("YOGAKARAKA_ACTIVE_Jupiter") == "functional_roles"

    def test_yoga_signals_map_to_yoga(self):
        assert _infer_source_from_key("YOGA_RAJA") == "yoga"
        assert _infer_source_from_key("YOGA_DHANA") == "yoga"
        assert _infer_source_from_key("YOGA_GAJA_KESARI") == "yoga"

    def test_chandra_gati_maps_to_chandra_gati(self):
        assert _infer_source_from_key("CHANDRA_GATI_RHYTHM") == "chandra_gati"

    def test_navamsa_dignity_maps_to_derived(self):
        assert _infer_source_from_key("NAVAMSA_DIGNITY") == "derived"

    def test_divisional_chart_signals_map_correctly(self):
        assert _infer_source_from_key("D10_Sun") == "divisional_d10"
        assert _infer_source_from_key("D2_WEALTH_PATTERN") == "divisional_d2"
        assert _infer_source_from_key("D7_CREATIVE_POTENTIAL") == "divisional_d7"

    def test_event_windows_maps_to_event_windows(self):
        assert _infer_source_from_key("EVENT_WINDOWS_FAVORABLE") == "event_windows"
        assert _infer_source_from_key("EVENT_WINDOWS_CHALLENGING") == "event_windows"

    def test_previously_covered_prefixes_unaffected(self):
        assert _infer_source_from_key("GOCHARA_RAHU_KETU") == "gochara"
        assert _infer_source_from_key("DRISHTI_BALANCE_MALEFIC") == "drishti"
        assert _infer_source_from_key("HOUSE_WEAKNESS_H1") == "house_strength"
        assert _infer_source_from_key("DASHA_Jupiter_H1") == "dasha"
        assert _infer_source_from_key("TARA_BALA_SAMPAT") == "nakshatra"
        assert _infer_source_from_key("ASHTAKAVARGA_STRONG_SUPPORT") == "ashtakavarga"

    def test_unknown_prefix_returns_none(self):
        assert _infer_source_from_key("SOMETHING_UNRECOGNIZED") is None


class TestNormalizeSignalsNeverLeaksNoneKey:
    def test_maraka_signal_gets_a_real_source_not_none(self):
        raw = [{"key": "MARAKA_ACTIVE_Mars", "strength": 0.6, "valence": "neg"}]
        normalized = _normalize_signals(raw)
        assert normalized[0]["source"] == "functional_roles"
        assert normalized[0]["source"] is not None


class TestRealChartRegressionForOriginalCrash:
    """The exact real chart/period/area that crashed during the
    2026-09-15 post-fix backfill -- a real MARAKA_ACTIVE_Mars signal in
    chart f1eb7ec4's health area for monthly 2026-07."""

    def test_generate_interpretation_does_not_raise_on_maraka_signal(self):
        with get_conn() as conn:
            row = conn.execute(
                "SELECT payload FROM base_charts WHERE id::text LIKE %s",
                (CHART_F1EB7EC4_PREFIX + "%",),
            ).fetchone()
        assert row, "expected chart fixture missing from DB"
        payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])

        envelope = build_monthly_prediction_envelope(base_chart=payload, year=2026, month=7)
        synthesis = synthesize_from_envelope(envelope)

        # Must not raise -- this is the exact call that previously hit
        # "Schema validation failed at 'life_areas -> health ->
        # attribution -> signals_used -> 2 -> key': None is not of type
        # 'string'".
        result = generate_interpretation(envelope=envelope, synthesis=synthesis, year=2026, month=7)

        health = result["life_areas"]["health"]
        for entry in health["attribution"]["signals_used"]:
            assert entry["key"] is not None
            assert isinstance(entry["key"], str)
