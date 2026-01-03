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

The main application runs on port 5000 via `npm run dev`.

For the Python FastAPI engine (optional):
```bash
cd tamil_panchangam_engine
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Recent Changes
- Initial project setup with complete structure
- Frontend with all pages and components
- Backend API endpoints (stubs)
- Python FastAPI structure with engine stubs
