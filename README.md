# Tamil Panchangam Astrology Engine

A full-stack Tamil Panchangam application providing birth-chart calculations, daily Panchangam (Tithi, Vara, Nakshatra, Yoga, Karana), Dasha timelines, AI-powered interpretations, and PDF report generation.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Tailwind CSS + shadcn/ui |
| Build | Vite 7 |
| Express layer | Node.js 20 + Express + Drizzle ORM (PostgreSQL) |
| Astrology engine | Python 3.11 + FastAPI + DuckDB |
| Ephemeris | pyswisseph (Swiss Ephemeris) |
| PDF generation | ReportLab + svgwrite |
| AI interpretation | OpenAI API |

---

## Prerequisites

- **Node.js 20+** and **npm**
- **Python 3.11+**
- **PostgreSQL 16+** (for the Express/Drizzle layer)
- System libraries for PDF rendering (see below)

### System libraries (macOS)

```bash
brew install cairo pkg-config freetype harfbuzz glib pango gdk-pixbuf ghostscript
```

### System libraries (Ubuntu/Debian)

```bash
sudo apt-get install -y libcairo2-dev pkg-config libfreetype6-dev \
  libharfbuzz-dev libglib2.0-dev libpango1.0-dev libgdk-pixbuf2.0-dev ghostscript
```

---

## Setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd tamil-panchangam
cp .env.example .env
# Edit .env and fill in OPENAI_API_KEY and DATABASE_URL
```

### 2. Install Node dependencies

```bash
npm install
```

### 3. Install Python dependencies

```bash
cd tamil_panchangam_engine
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
cd ..
```

### 4. Set up PostgreSQL database (Express layer)

```bash
# Ensure DATABASE_URL is set in .env, then:
npm run db:push
```

### 5. Run in development

```bash
# Terminal 1 — Python FastAPI backend (port 8000)
cd tamil_panchangam_engine
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Vite frontend dev server (port 5000, proxies /api → 8000)
npm run dev
```

Or use the convenience script (runs both):

```bash
bash scripts/start-dev.sh
```

### 6. Build for production

```bash
npm run build
# Outputs to dist/public/  — FastAPI serves this automatically
```

---

## Environment Variables

See [.env.example](.env.example) for the full list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | For AI features | OpenAI API key |
| `DATABASE_URL` | For Express layer | PostgreSQL connection string |
| `STATIC_DIR` | No | Override path to built React app (default: `dist/public`) |
| `PORT` | No | Express server port (default: 5001) |

---

## Project Structure

```
tamil-panchangam/
├── client/                     # React frontend (Vite)
│   └── src/
│       ├── components/         # UI components (shadcn/ui)
│       ├── pages/              # Route pages
│       └── lib/                # API client, query helpers
├── server/                     # Express.js layer (Node)
│   ├── index.ts                # Entry point
│   └── routes.ts               # API routes
├── shared/                     # Shared Zod/Drizzle schemas
├── tamil_panchangam_engine/    # Python FastAPI engine
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── api/                # Route handlers
│   │   ├── engines/            # Core astrology calculation engines
│   │   ├── llm/                # OpenAI integration
│   │   ├── db/                 # DuckDB connection + bootstrap
│   │   ├── pdf/                # PDF report generation
│   │   ├── repositories/       # Data access layer
│   │   ├── services/           # Business logic
│   │   └── schemas/            # Pydantic models
│   └── data/
│       └── panchangam.duckdb   # Main database (NOT in git — see below)
├── scripts/
│   └── start-dev.sh            # Dev startup convenience script
├── .env.example                # Environment variable template
├── pyproject.toml              # Python dependencies
├── package.json                # Node dependencies
└── vite.config.ts              # Vite build config
```

---

## Database

The app uses **DuckDB** (`tamil_panchangam_engine/data/panchangam.duckdb`) as its primary store. This file is excluded from git due to its size (300+ MB). Options for sharing it:

- **Git LFS:** `git lfs track "*.duckdb"`
- **Cloud storage:** Upload to S3/GCS and download during CI/CD setup
- **Seed script:** Regenerate from source data (if a seed script is available)

The legacy SQLite file (`panchangam.db`) is deprecated and can be ignored.

---

## Deployment (Vercel — frontend only)

The React frontend can be deployed to Vercel as a static site. The Python engine must be hosted separately (e.g., Railway, Render, Fly.io).

```bash
# Build the frontend
npm run build

# Deploy with Vercel CLI
vercel --prod
```

Set `VITE_API_URL` (or configure the Vite proxy target) to point at your deployed FastAPI backend.

---

## Domain Glossary

| Term | Meaning |
|------|---------|
| **Tithi** | Lunar day (30 per lunar month) |
| **Vara** | Day of the week (with planetary ruler) |
| **Nakshatra** | Lunar mansion (27 total) |
| **Yoga** | Combined Sun+Moon longitude value |
| **Karana** | Half of a Tithi |
| **Rahu Kalam** | Inauspicious time period of the day |
| **Yamagandam** | Another inauspicious daily time window |
| **Dasha** | Planetary period system (Vimshottari) |
| **Gochara** | Current planetary transits over natal chart |
| **Ashtakavarga** | Eight-source point system for transit strength |
