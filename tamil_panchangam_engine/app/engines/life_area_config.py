# app/engines/life_area_config.py
from __future__ import annotations

"""
============================================================
ASTROLOGY TUNING ZONE — HANDLE WITH CARE ⚠️
============================================================

This file defines LIFE-AREA SCORING POLICY.
It is:
- Declarative
- Deterministic
- Versioned
- The ONLY place where astrology “opinions” live

❌ Do NOT add logic here
❌ Do NOT reference runtime data
❌ Do NOT mutate weights dynamically

If scores feel “off”, tune HERE — not in the scorer.

------------------------------------------------------------
SATURN PHILOSOPHY (IMPORTANT)
------------------------------------------------------------
Saturn is NOT treated as “bad”.

We model Saturn as:
- Delay
- Effort
- Responsibility
- Karmic pressure
- Long-term restructuring

Rules we follow:
1. Saturn is strongest when tied to IDENTITY (1), WORK (6), or STRUCTURE (10)
2. Saturn softens in:
   - 12th house (internalization, withdrawal, spiritual work)
   - 9th house (maturity through philosophy, mentors)
3. Saturn should REDUCE scores, not CRUSH them
4. Saturn’s value comes from DURATION, not SHOCK

Therefore:
- Saturn weights are moderate
- House weights do most of the work
- Valence multiplier stays at -1.0 (no dramatization)
"""

# -------------------------------------------------
# LIFE AREAS (LOCKED CONTRACT)
# -------------------------------------------------

LIFE_AREAS = (
    "career",
    "finance",
    "relationships",
    "health",
    "personal_growth",
)

# -------------------------------------------------
# V1.1 — STABLE, EXPLAINABLE, TUNABLE
# -------------------------------------------------
# Changes from v1:
# - Explicit Saturn softening via house weights (12, 9)
# - No change to scorer logic
# - Comments added for traceability

LIFE_AREA_WEIGHTS = {
    # ============================================================
    # CAREER
    # ============================================================
    # Saturn here = slow grind, delayed recognition, responsibility
    # NOT failure.
    "career": {
        "houses": {
            10: 1.00,  # authority, role, profession
            6: 0.55,   # service, effort, workload
            2: 0.35,   # earnings from work
            11: 0.35,  # gains, recognition
            1: 0.20,   # identity pressure (Saturn hits here)
            12: 0.10,  # ⬅ Saturn softens here (internal work, not collapse)
        },
        "benefics": {
            "Sun": 0.40,
            "Jupiter": 0.45,
            "Mercury": 0.30,
            "Venus": 0.15,
        },
        "malefics": {
            "Saturn": 0.45,  # strong but not punitive
            "Rahu": 0.35,
            "Ketu": 0.15,
            "Mars": 0.25,
        },
        "source_bias": {
            "dasha": 1.10,
            "transit": 1.00,
            "birth": 0.90,
            "derived": 0.95,
            "panchangam": 0.75,
            "pakshi": 0.70,
        },
        "valence_multiplier": {
            "pos": 1.00,
            "neg": -1.00,
            "mix": 0.25,
        },
        "max_abs_contrib_per_signal": 1.50,
    },

    # ============================================================
    # FINANCE
    # ============================================================
    # Saturn here = delayed liquidity, conservative growth
    "finance": {
        "houses": {
            2: 1.00,   # income
            11: 0.80,  # gains
            8: 0.35,   # other people's money, risk
            12: 0.25,  # ⬅ loss but also expense discipline
        },
        "benefics": {
            "Jupiter": 0.50,
            "Venus": 0.40,
            "Mercury": 0.25,
        },
        "malefics": {
            "Saturn": 0.30,  # softened vs career
            "Rahu": 0.40,
            "Ketu": 0.20,
            "Mars": 0.25,
        },
        "source_bias": {
            "dasha": 1.05,
            "transit": 1.00,
            "birth": 0.90,
            "derived": 0.95,
            "panchangam": 0.70,
            "pakshi": 0.65,
        },
        "valence_multiplier": {
            "pos": 1.00,
            "neg": -1.00,
            "mix": 0.20,
        },
        "max_abs_contrib_per_signal": 1.40,
    },

    # ============================================================
    # RELATIONSHIPS
    # ============================================================
    # Saturn here = boundaries, commitment tests, maturity
    "relationships": {
        "houses": {
            7: 1.00,   # marriage, partnership
            5: 0.45,   # romance
            2: 0.35,   # family
            8: 0.30,   # intimacy
            12: 0.25,  # emotional withdrawal
        },
        "benefics": {
            "Venus": 0.55,
            "Moon": 0.40,
            "Jupiter": 0.25,
        },
        "malefics": {
            "Saturn": 0.20,  # intentionally light
            "Mars": 0.45,
            "Rahu": 0.25,
            "Ketu": 0.30,
        },
        "source_bias": {
            "dasha": 1.05,
            "transit": 1.00,
            "birth": 0.95,
            "derived": 0.95,
            "panchangam": 0.70,
            "pakshi": 0.70,
        },
        "valence_multiplier": {
            "pos": 1.00,
            "neg": -1.00,
            "mix": 0.20,
        },
        "max_abs_contrib_per_signal": 1.40,
    },

    # ============================================================
    # HEALTH
    # ============================================================
    # Saturn here = chronic conditions, stamina, recovery time
    "health": {
        "houses": {
            6: 1.00,   # disease
            1: 0.75,   # body
            8: 0.55,   # longevity
            12: 0.30,  # ⬅ hospitalization/rest, not death
        },
        "benefics": {
            "Moon": 0.40,
            "Jupiter": 0.30,
            "Mercury": 0.20,
        },
        "malefics": {
            "Saturn": 0.45,
            "Mars": 0.50,
            "Rahu": 0.25,
            "Ketu": 0.20,
        },
        "source_bias": {
            "dasha": 1.05,
            "transit": 1.00,
            "birth": 0.95,
            "derived": 0.95,
            "panchangam": 0.75,
            "pakshi": 0.80,
        },
        "valence_multiplier": {
            "pos": 1.00,
            "neg": -1.00,
            "mix": 0.25,
        },
        "max_abs_contrib_per_signal": 1.50,
    },

    # ============================================================
    # PERSONAL GROWTH
    # ============================================================
    # Saturn here = spiritual discipline, solitude, inner work
    "personal_growth": {
        "houses": {
            9: 1.00,   # philosophy, mentors
            5: 0.65,   # learning
            12: 0.60,  # ⬅ Saturn strongest *positive* here
            8: 0.40,   # transformation
        },
        "benefics": {
            "Jupiter": 0.55,
            "Ketu": 0.35,
            "Moon": 0.15,
        },
        "malefics": {
            "Saturn": 0.20,  # intentionally gentle
            "Rahu": 0.40,
            "Mars": 0.15,
        },
        "source_bias": {
            "dasha": 1.05,
            "transit": 1.00,
            "birth": 0.95,
            "derived": 0.95,
            "panchangam": 0.75,
            "pakshi": 0.75,
        },
        "valence_multiplier": {
            "pos": 1.00,
            "neg": -1.00,
            "mix": 0.25,
        },
        "max_abs_contrib_per_signal": 1.40,
    },
}
