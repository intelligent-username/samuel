import asyncio
import logging
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import get_db
from app.routers import auth, generate, github, history, resume

logger = logging.getLogger(__name__)


async def _cleanup_old_debug_dirs():
    """Delete debug directories older than settings.debug_retention_hours."""
    debug_root = Path(settings.debug_dir)
    if not debug_root.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.debug_retention_hours)
    for entry in debug_root.iterdir():
        if not entry.is_dir():
            continue
        mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            shutil.rmtree(entry, ignore_errors=True)
            logger.debug("Cleaned up debug dir: %s", entry)


async def _periodic_cleanup():
    while True:
        await asyncio.sleep(3600)
        try:
            await _cleanup_old_debug_dirs()
        except Exception:
            logger.exception("Error during debug cleanup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_periodic_cleanup())
    yield
    task.cancel()


app = FastAPI(title="Samuel API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:1111"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(github.router)
app.include_router(resume.router)
app.include_router(generate.router)
app.include_router(history.router)


@app.get("/health")
async def health():
    try:
        async for db in get_db():
            await db.execute(__import__("sqlalchemy").text("SELECT 1"))
            return {"status": "ok", "db": "connected"}
    except Exception:
        return {"status": "ok", "db": "unavailable"}