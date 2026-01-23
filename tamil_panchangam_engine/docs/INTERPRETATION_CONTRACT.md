# AI Interpretation Engine Contract

## Overview

The AI Interpretation Engine generates human-readable interpretations from computed astrological signals. This document defines the versioned contract that guarantees stable output structure for UI, PDF, and downstream consumers.

## Version: v1.0

**Engine Identifier:** `ai-interpretation-v1.0`

**Schema Location:** `docs/contracts/ai_interpretation_v1.schema.json`

### Purpose

1. **Stability** - UI and PDF layers can trust the interpretation shape permanently
2. **Validation** - Every output is validated against JSON Schema before return
3. **Traceability** - Every interpretation includes attribution back to signals/engines
4. **Determinism** - Same inputs produce structurally consistent outputs

### Three-Level Structure

#### Level 1: Window Summary
Prediction-level overview describing the overall momentum and timing.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `momentum` | enum | Yes | `growth`, `consolidation`, `pressure`, `transition` |
| `overview` | string | Yes | High-level summary (20-500 chars) |
| `dominant_forces` | array | Yes | Top 2-3 astrological forces |
| `outcome_mode` | enum | Yes | `ease`, `effort`, `delay` |
| `timing_guidance` | string | No | Timing recommendations |

#### Level 2: Life Area Blocks
Per-area interpretations for 5 life domains.

| Life Area | Description |
|-----------|-------------|
| `career` | Professional advancement, recognition, work |
| `finance` | Wealth, investments, material gains |
| `relationships` | Family, partnerships, social connections |
| `health` | Physical vitality, wellness, energy |
| `personal_growth` | Spiritual development, learning, wisdom |

Each block contains:
- `score` (0-100): From synthesis engine
- `outlook`: `positive`, `neutral`, or `challenging`
- `summary`: Brief interpretation (10-300 chars)
- `deeper_explanation`: Signal interaction narrative (10-800 chars)
- `attribution`: Astrological grounding

#### Level 3: Astrological Attribution
Every life area includes attribution linking interpretation to astrology:

| Field | Description |
|-------|-------------|
| `planets` | Planets influencing this area |
| `dasha` | Current dasha period (e.g., "Jupiter/Saturn") |
| `engines` | Contributing engines (Gochara, Drishti, etc.) |
| `signals_used` | Specific signals with valence and strength |

---

## Explainability Modes (v1.1)

The explainability filter allows controlling interpretation verbosity without regenerating content.

### Available Modes

| Mode | Content Included |
|------|------------------|
| `minimal` | Summary only - brief overview without technical details |
| `standard` | Summary + explanation - readable interpretation without signal attribution |
| `full` | Complete output - full interpretation with astrological attribution |

### Usage

```python
from app.engines.explainability_filter import apply_explainability

# Get full interpretation
interpretation = generate_interpretation(envelope, synthesis, year, month)

# Apply filter for UI consumption
minimal_view = apply_explainability(interpretation, "minimal")
standard_view = apply_explainability(interpretation, "standard")
```

### Guarantees

- Output remains schema-valid after filtering
- Same interpretation instance → different visibility only
- No content is regenerated or invented by the filter

---

## Upgrade Path

### v1.0 → v1.1+

Future versions follow these rules:

1. **Additive Only** - New fields can be added, existing fields cannot be removed
2. **Backward Compatible** - v1.0 consumers continue to work with v1.1+ output
3. **Version Identifier** - `engine_version` field indicates current version
4. **Schema Versioning** - New schema files (v1.1.schema.json) for new versions

### Breaking Changes (v2.0)

If breaking changes are required:

1. New major version (`ai-interpretation-v2.0`)
2. Separate schema file
3. Migration guide provided
4. Parallel support period for v1.x

---

## Validation

Every interpretation is validated before return:

```python
# Validation is automatic in generate_interpretation()
# Manual validation:
from app.engines.ai_interpretation_engine import _validate_interpretation

try:
    _validate_interpretation(interpretation)
except ValueError as e:
    print(f"Validation failed: {e}")
```

### Error Handling

If validation fails:
- Clear error message with path to invalid field
- ValueError raised with details
- Interpretation is NOT returned to caller

---

## Non-Negotiable Constraints

- ❌ No changes to synthesis engine scores
- ❌ No astrology recalculation
- ❌ No random text generation beyond vocabulary selection
- ❌ No UI assumptions in interpretation content
- ✅ Deterministic output structure
- ✅ Strict schema enforcement
- ✅ Clear logging and error messages
- ✅ Version-safe design
