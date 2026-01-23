Got it. Below is a **clean, retraceable, copy-paste–ready** document you can drop straight into your repo as:

📄 **`BIRTH_CHART_ID_FLOW.md`**

It is written to help:

* you (3 months from now),
* a new engineer,
* or a future auditor
  understand **exactly how `base_chart_id` flows end-to-end** without reading the entire codebase.

---

```md
# BIRTH_CHART_ID_FLOW.md

## Purpose

This document explains **how `base_chart_id` flows through the system**, from UI request → backend retrieval → synthesis → scoring.

Goals:
- Make debugging retraceable
- Avoid accidental contract breaks
- Establish a single mental model for ID ownership
- Clarify what is *derived* vs *persisted*

This is a **reference document**, not executable logic.

---

## Core Principle (Non-Negotiable)

> **`base_chart_id` is the SINGLE SOURCE OF TRUTH for all astrology facts.**

Everything else is:
- Derived
- Computed
- Enriched
- Scored
- Or narrated

But **never re-identified**.

---

## High-Level Flow

```

UI
└── GET /ui/birth-chart?base_chart_id=UUID
└── Backend fetches base_chart (immutable)
└── build_birth_chart_view_model()
└── UI rendering

UI
└── POST /prediction/monthly
├── base_chart_id
├── year
└── month
└── Backend fetches SAME base_chart
└── build_monthly_prediction_envelope()
└── synthesize_from_envelope()
└── LifeAreaScorer

```

At no point is a second chart created.

---

## Step-by-Step: Birth Chart UI

### 1. UI Request

**Endpoint**
```

GET /ui/birth-chart?base_chart_id=<uuid>

```

**Responsibility**
- UI supplies `base_chart_id`
- UI does NOT compute astrology
- UI does NOT infer houses, dashas, or dignity

---

### 2. API Layer

**File**
```

app/api/birth_chart.py

````

**Responsibility**
- Validate `base_chart_id`
- Fetch persisted base chart from storage
- No astrology logic here

Pseudo-flow:
```python
base_chart = get_base_chart_by_id(base_chart_id)
return build_birth_chart_view_model(base_chart)
````

---

### 3. Birth Chart View Builder (UI-only)

**File**

```
app/services/birth_chart_builder.py
```

**Function**

```python
build_birth_chart_view_model(base_chart)
```

**What happens here**

* Houses are DERIVED from lagna + rasi
* Planet → house mapping is computed
* D1, D9, rasi_view, nakshatra_view built
* Dasha overlays applied for UI highlighting

**What does NOT happen**

* ❌ No scoring
* ❌ No prediction
* ❌ No month/year logic

**Output**

* Immutable, UI-ready structure
* Still traceable back to `base_chart_id`

---

## Step-by-Step: Monthly Prediction

### 4. UI Prediction Request

**Endpoint**

```
POST /prediction/monthly
```

**Payload**

```json
{
  "base_chart_id": "uuid",
  "year": 2026,
  "month": 1
}
```

Important:

* UI sends the SAME `base_chart_id`
* No chart recomputation

---

### 5. Prediction API

**File**

```
app/api/prediction.py
```

**Responsibility**

* Fetch base chart using `base_chart_id`
* Pass base chart forward unchanged

```python
base_chart = get_base_chart_by_id(base_chart_id)
envelope = build_monthly_prediction_envelope(
    base_chart=base_chart,
    year=year,
    month=month,
)
```

---

### 6. Prediction Envelope (FACTUAL ONLY)

**File**

```
app/engines/prediction_envelope.py
```

**Function**

```python
build_monthly_prediction_envelope(...)
```

**Critical rule**

> This function builds FACTS, not opinions.

**Key actions**

* Derives houses ONCE using `build_birth_chart_view_model`
* Resolves:

  * active maha / antar dasha
  * transits
  * pakshi rhythm
  * navamsa dignity (raw)
* Assembles envelope

**Important**

```python
birth_chart_view = build_birth_chart_view_model(base_chart)
houses = birth_chart_view["houses"]  # SINGLE SOURCE
```

This guarantees:

* UI and prediction use identical house logic
* No drift between screens

---

## Envelope Contract (What Synthesis Can Rely On)

```python
{
  "reference": {...},
  "houses": [...],          # REQUIRED
  "ephemeris": {...},
  "environment": {...},
  "time_ruler": {...},
  "dasha_context": {...},   # REQUIRED
  "biological_rhythm": {...},
  "navamsa": {...},
}
```

If `houses` or `dasha_context` are missing → scoring WILL degrade.

---

## Step-by-Step: Synthesis & Scoring

### 7. Synthesis Engine

**File**

```
app/engines/synthesis_engine.py
```

**Responsibility**

* Convert envelope → normalized signals
* No astrology math
* No UI formatting

**Key logic**

* Build `house_lords` from `envelope["houses"]`
* Emit signals like:

  * `DASHA_Saturn_H1`
  * `DASHA_Venus_H9`
  * `NAVAMSA_DIGNITY`

No IDs change here.

---

### 8. Life Area Scoring

**File**

```
app/engines/life_area_scorer.py
```

**Responsibility**

* Apply deterministic math to signals
* Use weights from `life_area_config.py`

Scorer does NOT know:

* who the person is
* what year it is
* what chart this is

It only knows signals.

---

## Debugging Checklist (When Something Looks Wrong)

1. Log `base_chart_id` at API entry
2. Confirm base chart exists in storage
3. Verify `build_birth_chart_view_model()` returns 12 houses
4. Verify envelope includes `houses`
5. Verify synthesis emits house-aware dasha signals
6. Tune weights ONLY in `life_area_config.py`

---

## Anti-Patterns (DO NOT DO)

❌ Recompute houses differently in prediction
❌ Pass partial chart fragments between layers
❌ Store derived data back into base chart
❌ Tune Saturn (or any planet) in the scorer
❌ Let UI infer astrology logic

---

## Design Guarantees

✔ One chart per person
✔ One ID per chart
✔ Deterministic outputs
✔ Fully traceable decisions
✔ Safe to refactor UI or scoring independently

---

## Summary (Mental Model)

> **`base_chart_id` → immutable facts → derived envelope → signals → scores**

If you preserve that chain, the system remains:

* explainable
* debuggable
* astrologically sane

---

**Last updated:** 2026-01
**Owner:** Astrology Engine Core

```

---

If you want, next we can:
- add a **one-page diagram (ASCII or Mermaid)**,
- embed **debug log examples per step**, or
- add a **“golden chart” test case** tied to a known `base_chart_id`.

You’re building this the *right* way.
```
