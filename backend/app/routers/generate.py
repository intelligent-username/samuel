import uuid
import logging
from textwrap import dedent

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.generation import Generation
from app.models.resume import Resume
from app.models.user import User
from app.schemas import GenerateRequest, GenerationResponse
from app.services.auth import get_session_user_id
from app.services.encryption import decrypt
from app.skills.orchestrator import Orchestrator
from app.utils.llm import LLMClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("/")
async def start_generation(
    body: GenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GenerationResponse:
    """Create a new generation record (pending) and return its ID for SSE streaming."""
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

    env_key = settings.openrouter_api_key or settings.openrouter_key
    if not user.openrouter_api_key and not env_key:
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
    """SSE stream that runs the skill chain and yields progress events in real time."""
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

    env_key = settings.openrouter_api_key or settings.openrouter_key
    api_key = env_key if env_key else decrypt(user.openrouter_api_key)
    llm = LLMClient(api_key)
    orchestrator = Orchestrator(generation_id, llm, db)

    async def event_generator():
        try:
            async for event in orchestrator.run():
                yield event
        except Exception as e:
            result = await db.execute(select(Generation).where(Generation.id == generation_id))
            gen = result.scalar_one_or_none()
            if gen:
                gen.status = "failed"
                await db.commit()
            yield {"event": "error", "data": {"message": str(e)}}
        finally:
            await llm.close()

    return EventSourceResponse(event_generator())


@router.get("/{generation_id}/download")
async def download_pdf(
    generation_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download the rewritten resume as a PDF document."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Generation).where(Generation.id == generation_id, Generation.user_id == user_id)
    )
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "completed":
        raise HTTPException(status_code=400, detail="Generation not completed yet")

    if not generation.rewritten_resume_text:
        raise HTTPException(status_code=400, detail="No rewritten resume available")

    try:
        from weasyprint import HTML
    except ImportError:
        raise HTTPException(status_code=501, detail="PDF generation not available — weasyprint not installed")

    resume_html = _text_to_html(generation.rewritten_resume_text)
    html_content = dedent(f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: 'Helvetica', 'Arial', sans-serif; font-size: 11pt; line-height: 1.5; margin: 0.75in; color: #1a1a1a; }}
            h1 {{ font-size: 18pt; margin-bottom: 4pt; }}
            h2 {{ font-size: 13pt; border-bottom: 1px solid #333; padding-bottom: 3pt; margin-top: 16pt; margin-bottom: 6pt; }}
            h3 {{ font-size: 11pt; font-weight: bold; margin-top: 8pt; }}
            ul {{ margin: 4pt 0; padding-left: 18pt; }}
            li {{ margin-bottom: 2pt; }}
            p {{ margin: 4pt 0; }}
            .section {{ margin-bottom: 12pt; }}
          </style>
        </head>
        <body>
          {resume_html}
        </body>
        </html>
    """)
    pdf_bytes = HTML(string=html_content).write_pdf()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resume.pdf"},
    )


def _text_to_html(text: str) -> str:
    """Convert plain resume text to basic HTML for PDF rendering."""
    import html as html_module

    lines = text.split("\n")
    parts = []
    in_ul = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append("<br>")
            continue

        if stripped.startswith("# "):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<h1>{html_module.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<h2>{html_module.escape(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<h3>{html_module.escape(stripped[4:])}</h3>")
        elif stripped.startswith(("- ", "• ", "* ")):
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{html_module.escape(stripped[2:])}</li>")
        else:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<p>{html_module.escape(stripped)}</p>")

    if in_ul:
        parts.append("</ul>")

    return "\n".join(parts)
