import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.generation import Generation
from app.models.resume import Resume
from app.models.user import User
from app.schemas import GenerateRequest, GenerationResponse
from app.services.auth import get_session_user_id
from app.services.encryption import decrypt
from app.skills.orchestrator import Orchestrator
from app.utils.llm import LLMClient

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("/")
async def start_generation(
    body: GenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Resume).where(Resume.id == body.resume_id, Resume.user_id == user_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not user.openrouter_api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key not set. Save it first via POST /resume/key")

    generation = Generation(
        user_id=user_id,
        resume_id=body.resume_id,
        job_description_text=body.job_description,
        status="pending",
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    return GenerationResponse.model_validate(generation)


@router.get("/{generation_id}/stream")
async def stream_generation(
    generation_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Generation).where(Generation.id == generation_id, Generation.user_id == user_id)
    )
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    api_key = decrypt(user.openrouter_api_key)
    llm = LLMClient(api_key)

    orchestrator = Orchestrator(generation_id, llm, db)

    async def event_generator():
        try:
            result = await orchestrator.run()
            for event in orchestrator.pop_events():
                yield event

            yield {
                "event": "output",
                "data": result["rewritten_resume"],
            }
        except Exception as e:
            generation.status = "failed"
            await db.commit()
            yield {"event": "error", "data": {"message": str(e)}}
        finally:
            await llm.close()

    return EventSourceResponse(event_generator())