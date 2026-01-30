import app.db.sqlite_patch  # 🔴 MUST be first

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
# 🔒 FRONTEND PATH — HARD LOCK (NO AUTO DISCOVERY)
# =====================================================
WORKSPACE_ROOT = Path("/home/runner/workspace")
STATIC_DIR = WORKSPACE_ROOT / "dist" / "public"
ASSETS_DIR = STATIC_DIR / "assets"

print("🚀 WORKSPACE_ROOT:", WORKSPACE_ROOT)
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# API ROUTES
# -----------------------------
app.include_router(base_chart_router)
app.include_router(prediction_router)

@app.on_event("startup")
def startup_event():
    """Bootstrap database and load charts on startup."""
    bootstrap()
    load_charts_from_db()

app.include_router(interpretation_router)
app.include_router(ui_reports_router)
app.include_router(ui_birth_chart_router)
app.include_router(prediction_weekly_router)
app.include_router(prediction_yearly_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(realtime_context_router)
app.include_router(admin_llm_router)
app.include_router(canonical_report_router)

# =====================================================
# FRONTEND SERVING (SAFE, MINIMAL)
# =====================================================
if not STATIC_DIR.exists():
    raise RuntimeError(f"STATIC_DIR missing: {STATIC_DIR}")

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
        raise RuntimeError(f"index.html missing at {index_file}")
    return FileResponse(index_file)

# SPA fallback (non-asset, non-API)
@app.get("/{path:path}")
def spa_fallback(path: str):
    if "." in path:
        raise HTTPException(status_code=404)
    return FileResponse(STATIC_DIR / "index.html")
