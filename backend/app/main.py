from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
import shutil
import time
import asyncio
import logging

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    
    yield

    # Cancel background task on shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
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
