"""
Regression tests for the 2026-09-13 malefic-planet-list consolidation.

Four files each independently declared a malefic-planet list;
synthesis_engine.py's excluded Sun while the other three included it --
a real, confirmed drift. Decided doctrine: Sun is a natural malefic for
any binary classification (standard mainstream practice, matches 3 of
4 existing lists). All four now import app.utils.planet_lists.NATURAL_MALEFICS.
See CLAUDE.md's 2026-09-13 entry.
"""
from app.utils.planet_lists import NATURAL_MALEFICS
from app.engines.synthesis_engine import MALEFIC_LORDS
from app.engines.house_strength_engine import NATURAL_MALEFICS as house_strength_malefics
from app.engines.functional_role_engine import NATURAL_MALEFICS as functional_role_malefics
from app.engines.event_window_engine import _MALEFIC_PLANETS as event_window_malefics


def test_canonical_list_includes_sun():
    assert NATURAL_MALEFICS == {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}


def test_all_four_consuming_files_share_the_same_canonical_list():
    assert MALEFIC_LORDS is NATURAL_MALEFICS
    assert house_strength_malefics is NATURAL_MALEFICS
    assert functional_role_malefics is NATURAL_MALEFICS
    assert event_window_malefics is NATURAL_MALEFICS


def test_synthesis_engine_no_longer_excludes_sun():
    """Regression guard against reintroducing the exact drift: this used
    to be a local {"Saturn", "Mars", "Rahu", "Ketu"} missing Sun."""
    assert "Sun" in MALEFIC_LORDS
