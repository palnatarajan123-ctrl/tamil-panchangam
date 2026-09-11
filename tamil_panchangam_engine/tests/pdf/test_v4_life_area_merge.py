# tests/pdf/test_v4_life_area_merge.py
"""
Phase 2 of the PDF redesign: the v4+ individual report used to render
the same 5 life areas twice -- once as front narrative
(_build_v4_life_areas: paragraph, DO/AVOID, WHAT THIS MAY LOOK LIKE,
"Astrological basis," "Chart insight") and again as a back breakdown
(_build_predictions: score, raw "Signals" list with numeric deltas).
_build_v4_life_areas now also carries the score (as a colored badge) and
a single merged "Why" note folding astrological_basis + divisional_insight
+ the strongest signals together; _build_predictions grew an
include_area_detail flag so the legacy v1-3 branch (which never had a
front narrative to merge with) keeps its original, un-merged shape.

Tests inspect ReportLab flowables directly (Paragraph.text / Table
cell text), same technique as test_canonical_report_prospects.py --
raw PDF-byte search doesn't work (ReportLab compresses content
streams). Real end-to-end visual verification (rendered PDF actually
looks right, page count drops, legacy branch byte-for-byte unchanged
from its Phase 1 baseline) was done separately against a real chart.
"""

import unittest
from unittest.mock import MagicMock

from reportlab.platypus import Table, KeepTogether

from app.pdf.canonical_report.pdf_renderer import (
    _build_v4_life_areas,
    _build_predictions,
    _build_v4_area_why_note,
    _find_prediction_area,
    _create_styles,
)
from app.pdf.canonical_report.models import (
    CanonicalReportData, V4LifeArea, PredictionArea, SignalAttribution,
    SignalDetail, MethodologyInfo, TransitContext,
)


def _flatten_text(elements) -> str:
    """Collect all Paragraph text and Table cell text into one string,
    for substring assertions. Recurses into KeepTogether."""
    parts = []
    for el in elements:
        if isinstance(el, KeepTogether):
            parts.append(_flatten_text(el._content))
            continue
        if isinstance(el, Table):
            for row in el._cellvalues:
                for cell in row:
                    if hasattr(cell, "text"):
                        parts.append(cell.text)
                    elif isinstance(cell, str):
                        parts.append(cell)
            continue
        if hasattr(el, "text"):
            parts.append(el.text)
    return "\n".join(parts)


def _v4_area(**overrides) -> V4LifeArea:
    defaults = dict(
        plain_english="Career holds solid momentum this month.",
        do=["Consolidate existing projects"],
        avoid=["Avoid confrontational conversations"],
        real_life_patterns="You may notice collaborations move forward smoothly.",
        astrological_basis="Mars aspects on communication sectors introduce friction.",
        divisional_insight="The career destiny chart favors steady output.",
        karmic_note=None,
    )
    defaults.update(overrides)
    return V4LifeArea(**defaults)


def _signal(engine, direction, weight, hint) -> SignalDetail:
    return SignalDetail(engine=engine, direction=direction, weight=weight, interpretive_hint=hint)


def _pred_area(area="Career", score=79, **overrides) -> PredictionArea:
    defaults = dict(
        area=area,
        score=score,
        outlook="favorable",
        interpretation="Career holds solid momentum this month.",
        attribution=SignalAttribution(
            dasha="Jupiter/Venus", planets=["Mars"],
            engines=["Gochara (Transits)", "Drishti (Aspects)"],
            signals_count=2,
            signals=[
                _signal("GOCHARA_JUPITER", "pos", 0.47, "Rahu-Ketu axis 5-11 (favorable)"),
                _signal("DRISHTI_MARS", "neg", 0.13, "Mars aspects house 3 (challenging)"),
            ],
        ),
    )
    defaults.update(overrides)
    return PredictionArea(**defaults)


class TestBuildV4AreaWhyNote(unittest.TestCase):
    def test_merges_basis_insight_and_signals_into_one_note(self):
        area = _v4_area()
        pred = _pred_area()
        note = _build_v4_area_why_note(area, pred)
        self.assertIn("Mars aspects on communication sectors introduce friction", note)
        self.assertIn("career destiny chart favors steady output", note)
        # Strongest signal of each polarity woven in by name...
        self.assertIn("Rahu-Ketu axis 5-11", note)
        self.assertIn("Mars aspects house 3", note)
        # ...but never as a raw numeric delta.
        self.assertNotIn("0.47", note)
        self.assertNotIn("+0.47", note)
        self.assertNotIn("0.13", note)
        self.assertNotIn("-0.13", note)
        # Parenthetical qualifiers stripped, not duplicated with the prose.
        self.assertNotIn("(favorable)", note)
        self.assertNotIn("(challenging)", note)

    def test_no_pred_area_still_uses_basis_and_insight(self):
        note = _build_v4_area_why_note(_v4_area(), None)
        self.assertIn("Mars aspects on communication sectors", note)
        self.assertIn("career destiny chart", note)

    def test_no_signals_no_hints_falls_back_to_basis_and_insight_only(self):
        pred = _pred_area()
        pred.attribution.signals = []
        note = _build_v4_area_why_note(_v4_area(), pred)
        self.assertIn("Mars aspects on communication sectors", note)
        self.assertNotIn("further shaped", note)

    def test_nothing_available_returns_empty_string(self):
        area = _v4_area(astrological_basis=None, divisional_insight=None)
        pred = _pred_area()
        pred.attribution = None
        self.assertEqual(_build_v4_area_why_note(area, pred), "")


class TestFindPredictionArea(unittest.TestCase):
    def test_matches_snake_case_key_to_title_case_area(self):
        data = MagicMock(spec=CanonicalReportData, prediction_areas=[
            _pred_area(area="Personal Growth", score=74),
        ])
        found = _find_prediction_area(data, "personal_growth")
        self.assertIsNotNone(found)
        self.assertEqual(found.score, 74)

    def test_no_match_returns_none(self):
        data = MagicMock(spec=CanonicalReportData, prediction_areas=[])
        self.assertIsNone(_find_prediction_area(data, "career"))


class TestBuildV4LifeAreasMerged(unittest.TestCase):
    def setUp(self):
        self.styles = _create_styles()

    def _data(self, areas=("career",)):
        v4_areas = {key: _v4_area() for key in areas}
        pred_areas = [_pred_area(area=key.replace("_", " ").title()) for key in areas]
        return MagicMock(spec=CanonicalReportData, v4_life_areas=v4_areas, prediction_areas=pred_areas)

    def test_score_do_avoid_and_why_each_appear_exactly_once(self):
        data = self._data()
        elements = _build_v4_life_areas(data, self.styles)
        text = _flatten_text(elements)

        self.assertEqual(text.count("79/100"), 1)
        self.assertEqual(text.count("Consolidate existing projects"), 1)
        self.assertEqual(text.count("Avoid confrontational conversations"), 1)
        self.assertEqual(text.count("collaborations move forward smoothly"), 1)
        self.assertEqual(text.count("Mars aspects on communication sectors"), 1)
        # Old two-block labels are gone -- merged under one "WHY" label.
        self.assertNotIn("Astrological basis:", text)
        self.assertNotIn("Chart insight:", text)
        self.assertIn("WHY", text)

    def test_no_raw_signal_deltas_leak_into_merged_section(self):
        data = self._data()
        elements = _build_v4_life_areas(data, self.styles)
        text = _flatten_text(elements)
        self.assertNotIn("+0.47", text)
        self.assertNotIn("-0.13", text)

    def test_narrative_content_unchanged_from_pre_merge_shape(self):
        """DO/AVOID/WHAT THIS MAY LOOK LIKE text must survive the merge
        verbatim -- Phase 2 changes structure, not this content."""
        data = self._data()
        elements = _build_v4_life_areas(data, self.styles)
        text = _flatten_text(elements)
        self.assertIn("Career holds solid momentum this month.", text)
        self.assertIn("Consolidate existing projects", text)
        self.assertIn("Avoid confrontational conversations", text)
        self.assertIn("collaborations move forward smoothly", text)

    def test_missing_prediction_area_degrades_gracefully_no_badge(self):
        v4_areas = {"career": _v4_area()}
        data = MagicMock(spec=CanonicalReportData, v4_life_areas=v4_areas, prediction_areas=[])
        elements = _build_v4_life_areas(data, self.styles)
        text = _flatten_text(elements)
        # Narrative still renders even with no matching score.
        self.assertIn("Career holds solid momentum this month.", text)

    def test_no_v4_life_areas_returns_empty_list(self):
        data = MagicMock(spec=CanonicalReportData, v4_life_areas=None, prediction_areas=[])
        self.assertEqual(_build_v4_life_areas(data, self.styles), [])


class TestBuildPredictionsIncludeAreaDetailFlag(unittest.TestCase):
    """include_area_detail=True (default) is the legacy v1-3 branch's
    unchanged shape; =False is the new v4+ usage where the per-area
    breakdown has been merged elsewhere (Phase 2)."""

    def setUp(self):
        self.styles = _create_styles()

    def _data(self):
        return MagicMock(
            spec=CanonicalReportData,
            is_v3=False, is_v2=False,
            yearly_mantra=None, dasha_transit_synthesis=None,
            monthly_theme=None, overview_v2=None,
            prediction_overview="This period marks a challenging dynamics.",
            methodology=MethodologyInfo(calculation_confidence="medium"),
            prediction_areas=[_pred_area()],
            transit_context=TransitContext(
                jupiter_transit="", saturn_transit="", rahu_ketu_axis="",
            ),
        )

    def test_default_true_keeps_full_legacy_breakdown(self):
        elements = _build_predictions(self._data(), self.styles)
        text = _flatten_text(elements)
        self.assertIn("Detailed Insights", text)
        self.assertIn("Career - 79/100", text)
        self.assertIn("Signals", text)
        # Legacy branch is allowed to show raw deltas -- unchanged behavior.
        self.assertIn("+0.47", text)

    def test_false_drops_area_detail_keeps_section_level_content(self):
        elements = _build_predictions(self._data(), self.styles, include_area_detail=False)
        text = _flatten_text(elements)
        self.assertNotIn("Detailed Insights", text)
        self.assertNotIn("Career - 79/100", text)
        self.assertNotIn("Signals", text)
        self.assertNotIn("+0.47", text)
        # Section-level content is NOT part of the per-area duplication --
        # it still renders once, in its original position.
        self.assertIn("Overview", text)
        self.assertIn("challenging dynamics", text)
        self.assertIn("Prediction Confidence", text)
        self.assertIn("ASTROLOGICAL INFLUENCES", text)


if __name__ == "__main__":
    unittest.main()
