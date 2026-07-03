import logging

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas import ResumeResponse
from app.services.auth import get_session_user_id
from app.services.encryption import encrypt
from app.services.pdf_extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/upload")
async def upload_resume(request: Request, file: UploadFile, db: AsyncSession = Depends(get_db)) -> ResumeResponse:
    """Upload a PDF resume and extract its text."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    try:
        text = extract_text_from_pdf(content)
    except Exception as e:
        logger.warning("PDF extraction failed: %s", e)
        raise HTTPException(status_code=400, detail="Failed to extract PDF text")

    resume = Resume(
        user_id=user_id,
        original_filename=file.filename,
        extracted_text=text,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    return ResumeResponse.model_validate(resume)


@router.post("/key")
async def save_openrouter_key(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Save the user's OpenRouter API key (encrypted at rest)."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    body = await request.json()
    api_key = body.get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.openrouter_api_key = encrypt(api_key)
    await db.commit()
    return {"message": "API key saved"}


@router.get("/key-status")
async def key_status(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Check whether an OpenRouter API key is available (from user or env)."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    env_configured = bool(settings.openrouter_api_key) or bool(settings.openrouter_key)
    has_key = bool(user.openrouter_api_key) or env_configured
    return {"has_key": has_key, "env_configured": env_configured}


@router.get("/resumes")
async def list_resumes(request: Request, db: AsyncSession = Depends(get_db)) -> list:
    """List all uploaded resumes for the authenticated user."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()
    return [ResumeResponse.model_validate(r) for r in resumes]
