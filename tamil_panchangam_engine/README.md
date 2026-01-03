# Tamil Panchangam Astrology Engine

A Python FastAPI application for traditional Tamil Panchangam-based astrology calculations.

## Features

- **Drik Ganita** - Accurate astronomical calculations
- **Lahiri Ayanamsa** - Standard sidereal zodiac
- **South Indian Charts** - Traditional square-style chart visualization
- **Base Chart Service** - Immutable birth chart computation
- **Prediction Service** - Temporal predictions for future months

## Architecture

This application separates astronomical truth from interpretive predictions:

1. **Base Chart Service** - Computed once per birth, never recomputed
2. **Prediction Service** - Consumes stored base chart data for temporal analysis

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Base Chart Service
- `POST /base-chart/create` - Create a new birth chart
- `GET /base-chart/list` - List all stored charts
- `GET /base-chart/{chart_id}` - Get specific chart

### Prediction Service
- `POST /prediction/monthly` - Generate monthly predictions
- `GET /prediction/transits/{chart_id}` - Get current transits

## Calculation Engines

- `ephemeris.py` - Swiss Ephemeris planetary calculations
- `panchangam.py` - Tithi, Nakshatra, Yoga, Karana, Vara
- `divisional.py` - Varga chart calculations (D1, D9, etc.)
- `dasha_vimshottari.py` - Vimshottari Dasha periods
- `transits.py` - Gochara and transit analysis
- `pancha_pakshi.py` - Five Birds timing system

## Running the Application

```bash
cd tamil_panchangam_engine
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Dependencies

- FastAPI - Web framework
- PySwissEph - Swiss Ephemeris Python bindings
- PyTZ - Timezone handling
- TimezoneFinder - Coordinate to timezone conversion
- SVGWrite - SVG chart generation
- ReportLab - PDF report generation
- Pydantic - Data validation
