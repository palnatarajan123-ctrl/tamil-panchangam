
No logic from this model may move upstream or downstream.

---

## 3. Core Design Principles

### 3.1 Determinism
- Given the same signals, the model MUST produce identical results.
- No randomness.
- No adaptive learning.
- No user feedback loops.

### 3.2 Explainability
Every score must be decomposable into:
- contributing signals
- their weights
- their signed impact

### 3.3 Stability Over Optimality
- Stability is preferred over “feels right”.
- Minor inaccuracies are acceptable.
- Continuous tuning is explicitly disallowed.

---

## 4. Life Areas (Canonical)

The system defines exactly five life areas:

- Career
- Finance
- Relationships
- Health
- Personal Growth

These are **semantic containers**, not astrological constructs.

---

## 5. Signal Contract (Input)

The scoring model accepts only **pre-computed signals**.

It does NOT:
- detect signals
- evaluate astrology
- interpret meaning

Each signal conforms to:

```json
{
  "key": "string",
  "source": "dasha | transit | birth | derived | panchangam | pakshi",
  "kind": "planet | house | score | event",
  "house": 1-12 (optional),
  "planet": "Sun..Ketu" (optional),
  "valence": "pos | neg | mix",
  "strength": 0.0 - 1.0,
  "confidence": 0.0 - 1.0,
  "rationale": "string (optional)"
}
