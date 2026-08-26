from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
import shutil
import time
import asyncio
import logging

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine, get_db
from app.models import Base
from app.routers import auth, generate, github, history, resume

logger = logging.getLogger(__name__)


async def cleanup_debug_files() -> None:
    """Background task to delete debug files/directories older than 24 hours."""
    while True:
        try:
            debug_dir = Path(settings.debug_dir)
            if debug_dir.exists():
                now = time.time()
                for item in debug_dir.iterdir():
                    try:
                        if item.is_dir():
                            mtime = item.stat().st_mtime
                            # 24 hours = 86400 seconds
                            if now - mtime > 86400:
                                shutil.rmtree(item)
                                logger.info("Cleaned up old debug directory: %s", item)
                        elif item.is_file() and item.suffix == ".json":
                            mtime = item.stat().st_mtime
                            if now - mtime > 86400:
                                item.unlink()
                                logger.info("Cleaned up old debug file: %s", item)
                    except Exception as sub_err:
                        logger.error("Failed to clean item %s: %s", item, sub_err)
        except Exception as e:
            logger.error("Error in debug cleanup task: %s", e)
        await asyncio.sleep(3600)  # run every hour


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Start background cleanup task
    cleanup_task = asyncio.create_task(cleanup_debug_files())
    
    # First-run cleanup of any existing JSON debug files at root
    try:
        debug_dir = Path(settings.debug_dir)
        if debug_dir.exists():
            for f in debug_dir.iterdir():
                if f.is_file() and f.suffix == ".json":
                    f.unlink()
    except Exception as cleanup_err:
        logger.error("Initial debug cleanup failed: %s", cleanup_err)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Startup banner — clear host addresses (0.0.0.0 is inside container, show localhost for user)
    banner = (
        "\n"
        "  Samuel ready\n"
        "  ──────────────────────────────────────\n"
        "  Frontend → http://localhost:3000\n"
        "  Backend  → http://localhost:8000  (health: /health)\n"
        "  Database → postgresql://samuel:***@localhost:5432/samuel (container: db:5432)\n"
        "  ──────────────────────────────────────\n"
    )
    logger.info(banner)
    print(banner, flush=True)
    
    yield

    # Cancel background task on shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)

# Ensure CORS headers are present even on 500/error responses (EventSource is strict)
@app.middleware("http")
async def _force_cors_headers(request, call_next):
    from fastapi import HTTPException as FastHTTPException
    from fastapi.responses import JSONResponse

    try:
        response = await call_next(request)
    except FastHTTPException as e:
        # Preserve HTTPException status/detail but ensure CORS headers are still added
        logger.warning("HTTPException on %s %s: %s %s", request.method, request.url.path, e.status_code, e.detail)
        response = JSONResponse(status_code=e.status_code, content={"detail": e.detail}, headers=getattr(e, "headers", None))
    except Exception as e:
        # Ensure even unhandled 500s get CORS headers so browser can read the error
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        response = JSONResponse(status_code=500, content={"detail": str(e) or "Internal Server Error"})
    # Always attach CORS for localhost:3000 (EventSource requires it even on errors)
    origin = request.headers.get("origin")
    if origin in ("http://localhost:3000", "http://127.0.0.1:3000") or (origin and origin.startswith("http://localhost:")):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
    # Also handle preflight
    if request.method == "OPTIONS":
        response.headers["Access-Control-Allow-Origin"] = origin or "http://localhost:3000"
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

app.include_router(auth.router)
app.include_router(github.router)
app.include_router(resume.router)
app.include_router(generate.router)
app.include_router(history.router)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connectivity failed: {e}")
