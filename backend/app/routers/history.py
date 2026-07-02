from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.generation import Generation
from app.schemas import GenerationResponse
from app.services.auth import get_session_user_id

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/")
async def list_generations(request: Request, db: AsyncSession = Depends(get_db)):
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
