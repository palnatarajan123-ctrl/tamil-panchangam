# EPIC-4 UI Freeze Ledger

## Why this exists
UI boot was unstable due to EPIC-4 dependent components rendering
before prediction/synthesis data was guaranteed.

This file tracks EXACTLY what was disconnected so it can be restored.

---

## Backend (UNCHANGED)
- MonthlySynthesis
- life_areas scoring
- prediction gates
- interpretation aggregation
- vimshottari confidence logic

✅ Backend EPIC-4 is intact.

---

## UI Components Frozen (NOT deleted)

### 1. ExplainabilityDrawer
Files involved:
- client/src/components/ExplainabilityDrawer.tsx
- client/src/components/prediction/ExplainabilityDrawer.tsx

Issue:
- Accessed synthesis.life_areas during render
- No hard guards → runtime crash → blank UI

Action:
- Temporarily removed from all pages

Restore plan:
- Single ExplainabilityDrawer
- Props must be optional
- Hard guards before any access

---

### 2. life_areas rendering
Location:
- Any UI accessing `synthesis.life_areas[area]`

Issue:
- synthesis undefined during initial render

Action:
- All life area visualizations disabled

Restore plan:
- Adapter guarantees empty object fallback

---

### 3. Prediction gates UI
Location:
- Chart detail / Predictions pages

Issue:
- prediction_gates assumed present

Action:
- UI wiring removed (backend still returns it)

Restore plan:
- Gates rendered only when prediction exists

---

## Adapter TODO
- birthChartAdapter.ts to normalize:
  - rasi_view
  - nakshatra_view
  - houses
  - NO synthesis here

EPIC-4 adapters will be added later.

---

## Re-enable Order (MANDATORY)
1. UI boots
2. Birth chart renders
3. Predictions render
4. EPIC-4 explainability added last
