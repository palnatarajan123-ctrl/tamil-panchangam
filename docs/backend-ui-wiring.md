✅ COMMIT 1
docs/backend-ui-wiring.md

Purpose: Lock architecture + prevent future regressions like the one we just fixed.

# Backend → UI Wiring & Prediction Architecture
Tamil Panchangam Engine

This document locks the architectural contract between backend engines and UI.
Any future prediction type (weekly, monthly, yearly) must conform to this flow.

---

## 1. Core Design Principles

### 1.1 Separation of Concerns

| Layer | Responsibility | Rules |
|-----|---------------|------|
| Base Chart | Immutable birth facts | Never recomputed |
| Envelope | Astrological facts for a period | No prose, no scores |
| Synthesis | Numerical scoring | Deterministic |
| Interpretation | Human-readable meaning | Derived only |
| Explainability | Why the engine thinks so | Derived, never persisted |
| UI | Visualization | No astrology logic |

---

### 1.2 Schema Evolution Rule (Critical)

Persisted data may lag current schema.  
**Runtime must normalize envelopes before usage.**

This is intentional and mandatory.

---

## 2. End-to-End Prediction Flow



Base Chart (immutable)
↓
Prediction Envelope (facts only)
↓
Synthesis (scores + confidence)
↓
Interpretation (text)
↓
Explainability (derived)
↓
UI


---

## 3. API Entry (Monthly Example)

**Endpoint**


POST /api/prediction/monthly


**Input**
```json
{
  "base_chart_id": "...",
  "year": 2026,
  "month": 1
}

4. Base Chart (Immutable Input)

Loaded via:

get_base_chart_by_id(db, base_chart_id)


Invariants

base_chart.payload is immutable JSON

base_chart.locked == True

Contains:

birth_details

ephemeris

dashas.vimshottari

pancha_pakshi_birth

5. Prediction Envelope (FACTS ONLY)

Location:

app/engines/*_prediction_envelope.py

Mandatory keys
{
  "reference": {},
  "environment": {},
  "time_ruler": {},
  "dasha_context": {},
  "biological_rhythm": {}
}

Hard rules

No interpretation

No scores

No prose

dasha_context MUST exist

6. Dasha Context (Prediction-Facing Abstraction)

Purpose: isolate prediction logic from raw dasha math.

{
  "maha_lord": "Jupiter",
  "antar_lord": null,
  "is_maha_active": true,
  "confidence": "high",
  "active_lords": ["Jupiter"]
}


Future expansion (EPIC-6):

antar

pratyantar

7. Synthesis Layer

Location:

app/engines/synthesis_engine.py


Input:

envelope

Output:

{
  "life_areas": {...},
  "confidence": {...},
  "engine_version": "synthesis-v1"
}

8. Interpretation Layer

Location:

app/engines/interpretation_engine.py


Input:

envelope

synthesis

Output:

prose grouped by life area

9. Explainability (Derived Only)

Location:

app/engines/explainability_engine.py


Rules:

Never persisted

Derived at response time

Explains WHY, not WHAT

10. Persistence Rules

Persisted:

envelope

synthesis

interpretation

Not persisted:

explainability

UI models

11. Schema Normalization Pattern (Locked)
if "dasha_context" not in envelope:
    envelope["dasha_context"] = derive_from_time_ruler(envelope)


This is required for backward compatibility.

12. Prediction Types
Type	Period	Envelope Variant
Weekly	7 days	weekly envelope
Monthly	1 month	monthly envelope
Yearly	1 year	yearly envelope

All reuse:

synthesis

interpretation

explainability

Only envelope builders differ.

END OF DOCUMENT


✅ **Commit message**


docs: lock backend-to-UI wiring and prediction architecture