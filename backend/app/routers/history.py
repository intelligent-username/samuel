import uuid

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.generation import Generation
from app.schemas import GenerationResponse, UpdateGenerationRequest
from app.services.auth import get_session_user_id

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/")
async def list_generations(request: Request, db: AsyncSession = Depends(get_db)) -> list:
    """List the most recent generations for the authenticated user."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Generation)
        .where(Generation.user_id == user_id)
        .order_by(Generation.created_at.desc())
        .limit(20)
    )
    gens = result.scalars().all()
    return [GenerationResponse.model_validate(g) for g in gens]


@router.get("/{generation_id}")
async def get_generation(
    generation_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> GenerationResponse:
    """Get full details for a specific generation."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Generation).where(Generation.id == generation_id, Generation.user_id == user_id)
    )
    gen = result.scalar_one_or_none()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")

    return GenerationResponse.model_validate(gen)


@router.patch("/{generation_id}")
async def update_generation(
    generation_id: uuid.UUID,
    body: UpdateGenerationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GenerationResponse:
    """Update a generation's custom title."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Generation).where(Generation.id == generation_id, Generation.user_id == user_id)
    )
    gen = result.scalar_one_or_none()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")

    new_title = body.title.strip()
    gen.title = new_title if new_title else None
    await db.commit()
    await db.refresh(gen)

    return GenerationResponse.model_validate(gen)


@router.delete("/{generation_id}")
async def delete_generation(
    generation_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete a single generation (tailored resume)."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Generation).where(Generation.id == generation_id, Generation.user_id == user_id)
    )
    gen = result.scalar_one_or_none()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")

    await db.delete(gen)
    await db.commit()

    try:
        debug_path = Path(settings.debug_dir) / str(generation_id)
        if debug_path.exists():
            if debug_path.is_dir():
                shutil.rmtree(debug_path)
            else:
                debug_path.unlink()
    except Exception:
        pass

    return {"message": "Generation deleted"}
