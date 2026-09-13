"""
Shared planet classification constants.

Single source of truth for planet groupings that used to be
independently redeclared per-file -- see CLAUDE.md's 2026-09-13 entry
for the audit that found synthesis_engine.py's copy silently excluded
Sun while three other files (house_strength_engine.py,
functional_role_engine.py, event_window_engine.py) included it, with
no test coverage to catch the drift.
"""

# Sun is treated as a natural malefic here for any binary malefic/
# benefic classification -- standard mainstream Vedic astrology
# practice, and matches 3 of the 4 independent lists this constant
# replaces (synthesis_engine.py's MALEFIC_LORDS was the one outlier,
# excluding Sun -- confirmed to be a drift, not a deliberate choice,
# since nothing in that file's history documents excluding Sun as
# intentional).
NATURAL_MALEFICS = frozenset({"Saturn", "Mars", "Rahu", "Ketu", "Sun"})
