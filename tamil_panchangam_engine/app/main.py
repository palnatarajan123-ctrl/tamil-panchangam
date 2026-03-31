import app.db.sqlite_patch  # 🔴 MUST be first

import os
from dotenv import load_dotenv
load_dotenv()  # loads .env from project root (or nearest parent)
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter

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
from app.api.natal_interpretation import router as natal_interpretation_router
from app.api.auth import router as auth_router
from app.api.user_charts import router as user_charts_router
from app.api.chat import router as chat_router
from app.api.family import router as family_router
from app.api.admin import router as admin_router
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

# ─── Rate limiting ────────────────────────────────────────────────────────────
app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please wait before trying again.",
            "retry_after": "60 seconds",
        },
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)


# ─── Request size middleware (1 MB max) ───────────────────────────────────────
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_000_000:
        return JSONResponse(
            status_code=413,
            content={"detail": "Request body too large. Maximum size is 1 MB."},
        )
    return await call_next(request)

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
    # Auto-create admin from env vars on first startup
    try:
        import os, uuid
        from app.core.auth import hash_password
        from app.db.postgres import get_conn
        admin_email = os.environ.get('ADMIN_EMAIL')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        admin_name = os.environ.get('ADMIN_NAME', 'Admin')
        if admin_email and admin_password:
            with get_conn() as conn:
                existing = conn.execute('SELECT id FROM users WHERE email = ?', [admin_email]).fetchone()
                if not existing:
                    conn.execute('INSERT INTO users (id, email, password_hash, name, role) VALUES (?, ?, ?, ?, ?)',
                        [str(uuid.uuid4()), admin_email.lower(), hash_password(admin_password), admin_name, 'admin'])
                    conn.commit()
                    print(f'✅ Admin auto-seeded: {admin_email}')
    except Exception as e:
        print(f'⚠️  Admin seed skipped: {e}')
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
app.include_router(natal_interpretation_router, prefix="/api")
app.include_router(auth_router,             prefix="/api")
app.include_router(user_charts_router,      prefix="/api")
app.include_router(chat_router,             prefix="/api")
app.include_router(family_router,           prefix="/api")
app.include_router(admin_router,            prefix="/api")

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
