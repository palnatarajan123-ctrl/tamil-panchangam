import app.db.sqlite_patch  # 🔴 MUST be first

import os
from dotenv import load_dotenv
load_dotenv()  # loads .env from project root (or nearest parent)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.base_chart import router as base_chart_router, load_charts_from_db
from app.api.prediction import router as prediction_router
from app.api.interpretation import router as interpretation_router
from app.api.ui_reports import router as ui_reports_router
from app.api.ui_birth_chart import router as ui_birth_chart_router
from app.api.prediction_weekly import router as prediction_weekly_router
from app.api.prediction_yearly import router as prediction_yearly_router
from app.api.realtime_context import router as realtime_context_router
from app.api.admin_llm import router as admin_llm_router
from app.api.canonical_report import router as canonical_report_router
from app.db.bootstrap import bootstrap



# =====================================================
# FRONTEND STATIC PATH
# Set STATIC_DIR env var to override (e.g. in production).
# Default: <project-root>/dist/public (two levels up from this file's package root)
# =====================================================
_default_static = Path(__file__).resolve().parents[2] / "dist" / "public"
STATIC_DIR = Path(os.environ.get("STATIC_DIR", str(_default_static)))
ASSETS_DIR = STATIC_DIR / "assets"

print("📦 STATIC_DIR:", STATIC_DIR)
print("📦 ASSETS_DIR:", ASSETS_DIR)
print("📂 STATIC_DIR exists:", STATIC_DIR.exists())
print("📂 ASSETS_DIR exists:", ASSETS_DIR.exists())

# =====================================================
# FASTAPI APP
# =====================================================
app = FastAPI(
    title="Tamil Panchangam Astrology Engine",
    description="Drik Ganita based Tamil astrology with Lahiri ayanamsa",
    version="0.1.0",
)

# -----------------------------
# Middleware
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tamil-panchangam-alpha.vercel.app", "http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# API ROUTES  (all under /api so frontend calls work in both dev and prod)
# -----------------------------
app.include_router(base_chart_router,       prefix="/api")
app.include_router(prediction_router,       prefix="/api")

@app.on_event("startup")
def startup_event():
    """Bootstrap database and load charts on startup."""
    bootstrap()
    load_charts_from_db()

app.include_router(interpretation_router,   prefix="/api")
app.include_router(ui_reports_router,       prefix="/api")
app.include_router(ui_birth_chart_router,   prefix="/api")
app.include_router(prediction_weekly_router, prefix="/api")
app.include_router(prediction_yearly_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(realtime_context_router, prefix="/api")
app.include_router(admin_llm_router,        prefix="/api")
app.include_router(canonical_report_router, prefix="/api")

# =====================================================
# FRONTEND SERVING (conditional — skipped in dev when dist/ not built yet)
# =====================================================
if not STATIC_DIR.exists():
    print(f"⚠️  STATIC_DIR not found ({STATIC_DIR}). "
          "Frontend static serving disabled. Run `npm run build` for production.")
else:
    # Serve assets EXACTLY
    app.mount(
        "/assets",
        StaticFiles(directory=ASSETS_DIR),
        name="assets",
    )

    # Root entry
    @app.get("/")
    def serve_root():
        index_file = STATIC_DIR / "index.html"
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="index.html not found")
        return FileResponse(index_file)

    # SPA fallback (non-asset, non-API routes)
    @app.get("/{path:path}")
    def spa_fallback(path: str):
        if path.startswith("api/") or "." in path:
            raise HTTPException(status_code=404)
        return FileResponse(STATIC_DIR / "index.html")
