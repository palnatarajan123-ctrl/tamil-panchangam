# Tamil Panchangam Astrology Engine

## Overview
A traditional Tamil Panchangam-based astrology system using Drik Ganita calculations with Lahiri Ayanamsa. The application provides birth chart generation and monthly predictions with South Indian square-style chart visualization.

## Architecture

### Two-Service Model
1. **Base Chart Service** - Computes immutable birth chart data (computed once per birth)
2. **Prediction Service** - Generates temporal predictions consuming stored base chart data

### Technology Stack
- **Frontend**: React + TypeScript + Vite + TailwindCSS + shadcn/ui
- **Backend**: Express.js (Node.js) with in-memory storage
- **Python Engine**: FastAPI with Swiss Ephemeris (stubs for astrology calculations)

## Project Structure

```
├── client/                    # React frontend
│   └── src/
│       ├── components/        # Reusable UI components
│       │   ├── chart-form.tsx
│       │   ├── chart-list.tsx
│       │   ├── hero-section.tsx
│       │   ├── navigation.tsx
│       │   ├── south-indian-chart.tsx
│       │   ├── status-badge.tsx
│       │   └── theme-toggle.tsx
│       └── pages/             # Route pages
│           ├── home.tsx
│           ├── predictions.tsx
│           ├── health.tsx
│           ├── reports.tsx
│           ├── docs.tsx
│           └── chart-detail.tsx
├── server/                    # Express backend
│   └── routes.ts              # API endpoints
├── shared/                    # Shared types
│   └── schema.ts
├── tamil_panchangam_engine/   # Python FastAPI (stubs)
│   └── app/
│       ├── api/               # FastAPI routes
│       ├── engines/           # Astrology calculation stubs
│       ├── charts/            # SVG chart generation
│       ├── pdf/               # Report generation
│       ├── models/            # Pydantic schemas
│       └── utils/             # Time utilities
```

## API Endpoints

### Health
- `GET /api/health` - Service status

### Base Chart Service
- `POST /api/base-chart/create` - Create birth chart
- `GET /api/base-chart/list` - List all charts
- `GET /api/base-chart/:chartId` - Get specific chart

### Prediction Service
- `POST /api/prediction/monthly` - Generate monthly prediction
- `GET /api/prediction/transits/:chartId` - Get current transits

## Key Features

### Calculation Method
- **Drik Ganita**: Modern astronomical calculations
- **Lahiri Ayanamsa**: Official Indian Ephemeris standard
- **South Indian Charts**: Traditional square-style visualization

### Frontend Features
- Birth chart input form with validation
- South Indian chart SVG visualization
- Chart list with saved charts
- Monthly prediction generator
- Health status monitoring
- API documentation page
- Dark/light theme support

## Design System

### Typography
- Headers: Playfair Display (serif)
- Body/UI: Inter (sans-serif)
- Data/Charts: JetBrains Mono (monospace)

### Colors
- Primary: Warm amber (28° hue)
- Semantic status colors for system health
- Full dark mode support

## Running the Application

Press the **green Run button** to start both services automatically.

**Architecture:**
- **Frontend (Vite)**: Port 5000 (exposed as external port 80)
- **Backend (Uvicorn)**: Port 8000

**Startup Script:** `scripts/start-dev.sh` runs both servers in parallel.

**Full Configuration Details:** See `docs/STARTUP_CONFIGURATION.md`

### Critical Configuration Notes

1. **vite.config.ts** must have `allowedHosts: true` for Replit proxy
2. **API Proxy**: Frontend `/api/*` requests are proxied to backend port 8000
3. **Production**: Uvicorn serves both API and static frontend on port 5000

## AI Interpretation Engine Governance

### Contract (v1.0)
- **Schema**: `docs/contracts/ai_interpretation_v1.schema.json`
- **Documentation**: `docs/INTERPRETATION_CONTRACT.md`
- Strict JSON Schema validation with fail-fast enforcement
- 3-level structure: Window Summary, Life Areas, Attribution

### Explainability Modes
- **minimal**: Summary only (visibility flags hide details)
- **standard**: Summary + explanation (hide signal attribution)
- **full**: Complete output with all attribution

### Key Files
- `app/engines/ai_interpretation_engine.py` - Main interpretation engine
- `app/engines/explainability_filter.py` - Post-processing visibility filter
- `app/engines/synthesis_engine.py` - Signal synthesis

### Frontend Adapter
- `client/src/adapters/aiInterpretationAdapter.ts` - Maps AI Interpretation v1.0 → UI View Model
- Strict field omission (no defaults/fallbacks)
- Visibility gating respects `_visibility` metadata or explicit level parameter

## Recent Changes
- 2026-01-24: Fixed AI Interpretation explainability toggle - standard shows deeper explanation but not attribution, full shows all
- 2026-01-24: Added attribution UI (planets, dasha, engines) and signals display in AI Interpretation section
- 2026-01-24: Fixed cached predictions to apply explainability filter
- 2026-01-24: Fixed Functional Role Planets display to show yogakarakas, benefics, or lagna info
- 2026-01-24: Added startup loading of charts from DuckDB to in-memory store
- 2026-01-24: Fixed yogakaraka logic order (yogakaraka check before benefic check)
- 2026-01-24: Fixed JSON payload parsing for charts loaded from DuckDB
- 2026-01-23: Refactored Birth Chart UI with BirthAstroContextTable (5 grouped sections)
- 2026-01-23: Removed Rasi/Nakshatra/Houses tab switcher from chart detail page
- 2026-01-23: Added AI Interpretation section with explainability toggle on chart detail page
- 2026-01-23: Created prediction_signal_inventory.md documentation
- 2026-01-23: Added explainability toggle UI to prediction screen (minimal/standard/full)
- 2026-01-23: Extended AI Interpretation to weekly and yearly prediction endpoints
- 2026-01-23: Removed redundant NarrativeCard and AntarRemediesCard (content now in AI Interpretation)
- 2026-01-23: Refactored Prediction UI to use AI Interpretation v1.0 as single source of truth
- 2026-01-23: Created aiInterpretationAdapter.ts with strict field omission (no fallbacks)
- 2026-01-23: Deprecated legacy predictionAdapter.ts
- 2026-01-23: Added AI Interpretation Engine governance with JSON Schema contract
- 2026-01-23: Created explainability filter (minimal/standard/full modes)
- 2026-01-23: Added schema validation with fail-fast enforcement
- 2026-01-22: Fixed startup configuration - dual server setup with Vite + Uvicorn
- 2026-01-22: Added `allowedHosts: true` to fix Replit proxy blocking
- 2026-01-22: Created `scripts/start-dev.sh` for parallel server startup
- Initial project setup with complete structure
- Frontend with all pages and components
- Backend API endpoints (stubs)
- Python FastAPI structure with engine stubs
