"""
Kage Scan — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import settings
from app.database import init_db
from app.routers import export, pipeline, projects


# ── Lifespan (startup / shutdown) ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown of the application."""
    # ── Startup ────────────────────────────────────────────────────
    logger.info("🚀 Kage Scan starting up...")

    # Ensure data directory exists
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Create database tables
    await init_db()
    logger.info("✅ Database initialized")

    yield

    # ── Shutdown ───────────────────────────────────────────────────
    logger.info("👋 Kage Scan shutting down...")


# ── App Instance ──────────────────────────────────────────────────────
app = FastAPI(
    title="Kage Scan API",
    description="Automated manga/manhwa/webtoon translation & editing tool",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS (allow all for local app) ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(projects.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(export.router, prefix="/api")

# ── Static Files (serve uploaded images) ──────────────────────────────
# Mount the data directory so frontend can load images via:
#   http://localhost:8000/data/projects/{project_id}/image.png
data_path = Path(settings.DATA_DIR)
data_path.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=str(data_path)), name="data")


# ── Health Check ──────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "kage-scan"}


# ── Dev Server ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
