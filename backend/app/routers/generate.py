import asyncio
import html as html_module
import json
import logging
import re
import urllib.parse
import uuid
from textwrap import dedent

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db, async_session_factory
from app.models.generation import Generation
from app.models.resume import Resume
from app.models.user import User
from app.schemas import GenerateRequest, GenerationResponse
from app.services.auth import get_session_user_id
from app.services.encryption import decrypt
from app.orchestrator import Orchestrator
from app.utils.llm import LLMClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generate"])

# Track running generation tasks so they can be cancelled/stopped on demand
active_generation_tasks: dict[uuid.UUID, asyncio.Task] = {}


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
        # Check if resume_id is a previous Generation id
        gen_res = await db.execute(
            select(Generation)
            .where(Generation.id == body.resume_id, Generation.user_id == user_id)
            .options(selectinload(Generation.resume))
        )
        gen = gen_res.scalar_one_or_none()
        if gen:
            resume = gen.resume

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    env_key = settings.openrouter_api_key or settings.openrouter_key
    if not user.openrouter_api_key and not env_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key not set. Save it first via POST /resume/key")

    # Defense in depth — even if schema is bypassed, enforce 24000
    jd_text = body.job_description.strip()
    if not jd_text:
        raise HTTPException(status_code=422, detail="Please paste a job description")
    if len(jd_text) > 24000:
        raise HTTPException(status_code=422, detail="Job description too long (max 24000 characters)")
    # Also handle raw body before strip (if validator not returning stripped)
    if len(body.job_description) > 24000:
        raise HTTPException(status_code=422, detail="Job description too long (max 24000 characters)")

    generation = Generation(
        user_id=user_id,
        resume_id=resume.id,
        job_description_text=jd_text,  # store stripped/validated value
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
        select(Generation)
        .where(Generation.id == generation_id, Generation.user_id == user_id)
        .options(selectinload(Generation.resume))
    )
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    # --- Idempotent revisit guard (Issue #1) ---
    if generation.status == "completed" and generation.rewritten_resume_text:
        # Extract ATS score for done payload
        ats_score = 0
        if generation.ats_report and isinstance(generation.ats_report, dict):
            ats_score = generation.ats_report.get("score", 0)

        async def cached_event_generator():
            # Replay step-done for all four steps so frontend marks them done instantly.
            # Use synthetic summaries that match orchestrator's format; frontend only uses step key.
            for step in ["jd_parser", "project_matcher", "resume_writer", "ats_checker"]:
                yield {"event": "step-done", "data": json.dumps({"step": step, "summary": "Cached"})}
            # Replay the actual output + done from DB
            yield {"event": "output", "data": generation.rewritten_resume_text}
            yield {"event": "done", "data": json.dumps({
                "generation_id": str(generation.id),
                "ats_score": ats_score,
                "rewritten_resume": generation.rewritten_resume_text,  # fallback for Issue #8
                "pdf_url": f"/generate/{generation.id}/download",
            })}

        # Explicit CORS headers for SSE (browsers block EventSource without them even if middleware mis-handles streaming)
        cors_headers = {
            "Access-Control-Allow-Origin": request.headers.get("origin", "http://localhost:3000"),
            "Access-Control-Allow-Credentials": "true",
            "Cache-Control": "no-cache",
        }
        return EventSourceResponse(cached_event_generator(), headers=cors_headers)

    # --- Live path: only for pending/running ---
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    env_key = settings.openrouter_api_key or settings.openrouter_key
    if env_key:
        api_key = env_key
    else:
        if not user.openrouter_api_key:
            raise HTTPException(status_code=400, detail="OpenRouter API key not set")
        try:
            api_key = decrypt(user.openrouter_api_key)
        except Exception as e:
            logger.exception("Failed to decrypt stored OpenRouter key for user %s", user_id)
            raise HTTPException(status_code=500, detail="Failed to decrypt stored API key — re-save it via dashboard (ENCRYPTION_KEY may have changed)") from e

    llm = LLMClient(api_key, groq_api_key=getattr(settings, "groq_api_key", "") or None)
    orchestrator = Orchestrator(generation_id, llm, db)

    async def event_generator():
        current_task = asyncio.current_task()
        if current_task:
            active_generation_tasks[generation_id] = current_task
        try:
            async for event in orchestrator.run():
                if isinstance(event.get("data"), (dict, list)):
                    event["data"] = json.dumps(event["data"])
                yield event
        except asyncio.CancelledError:
            logger.info("generation %s was stopped/cancelled by user", generation_id)
            try:
                async with async_session_factory() as cancel_db:
                    res = await cancel_db.execute(select(Generation).where(Generation.id == generation_id))
                    gen = res.scalar_one_or_none()
                    if gen and gen.status != "completed":
                        gen.status = "failed"
                        await cancel_db.commit()
            except Exception:
                pass
            yield {"event": "error", "data": json.dumps({"message": "Generation stopped by user"})}
            raise
        except Exception as e:
            logger.exception("generation %s failed", generation_id)
            # Session may be tainted -> rollback first, then use fresh session to persist failed
            try:
                await db.rollback()
            except Exception:
                pass
            try:
                async with async_session_factory() as retry_db:
                    result2 = await retry_db.execute(select(Generation).where(Generation.id == generation_id))
                    gen = result2.scalar_one_or_none()
                    if gen and gen.status != "completed":
                        gen.status = "failed"
                        # Persist debug path even on failure if orchestrator set it
                        if not gen.skill_chain_debug_path:
                            from pathlib import Path
                            from app.config import settings
                            gen.skill_chain_debug_path = str(Path(settings.debug_dir) / str(generation_id))
                        await retry_db.commit()
            except Exception:
                logger.exception("failed to persist failed status for %s", generation_id)
            # Never leak raw JD or API key; str(e) is safe (exception message only)
            yield {"event": "error", "data": json.dumps({"message": str(e) or "Generation failed"})}
        finally:
            active_generation_tasks.pop(generation_id, None)
            await llm.close()

    live_cors_headers = {
        "Access-Control-Allow-Origin": request.headers.get("origin", "http://localhost:3000"),
        "Access-Control-Allow-Credentials": "true",
        "Cache-Control": "no-cache",
    }
    return EventSourceResponse(event_generator(), headers=live_cors_headers)


@router.post("/{generation_id}/stop")
async def stop_generation(
    generation_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GenerationResponse:
    """Stop a running generation, cancel LLM requests, and mark as failed."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Generation).where(Generation.id == generation_id, Generation.user_id == user_id)
    )
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    # Cancel active asyncio task if running
    task = active_generation_tasks.pop(generation_id, None)
    if task and not task.done():
        task.cancel()

    generation.status = "failed"
    await db.commit()
    await db.refresh(generation)

    return GenerationResponse.model_validate(generation)


@router.post("/{generation_id}/retry")
async def retry_generation(
    generation_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GenerationResponse:
    """Reset a failed generation back to pending so it can be re-run."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Generation).where(Generation.id == generation_id, Generation.user_id == user_id)
    )
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    # Cancel any previous task if lingering
    task = active_generation_tasks.pop(generation_id, None)
    if task and not task.done():
        task.cancel()

    generation.status = "pending"
    generation.rewritten_resume_text = None
    generation.ats_report = None
    generation.completed_at = None
    await db.commit()
    await db.refresh(generation)

    return GenerationResponse.model_validate(generation)


@router.get("/{generation_id}/download")
async def download_pdf(
    generation_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download the rewritten resume as a PDF document."""
    user_id = get_session_user_id(request)
    if user_id:
        result = await db.execute(
            select(Generation)
            .where(Generation.id == generation_id, Generation.user_id == user_id)
            .options(selectinload(Generation.resume))
        )
    else:
        # Fallback for iframe preview subrequests where browsers block cross-port cookies
        result = await db.execute(
            select(Generation)
            .where(Generation.id == generation_id)
            .options(selectinload(Generation.resume))
        )
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "completed":
        raise HTTPException(status_code=400, detail="Generation not completed yet")

    if not generation.rewritten_resume_text:
        raise HTTPException(status_code=400, detail="No rewritten resume available")

    # 1. First priority: Pre-rendered in-place edited PDF
    if generation.pdf_content:
        pdf_bytes = generation.pdf_content
    # 2. Second priority: In-place rewrite from original uploaded PDF
    elif generation.resume and generation.resume.pdf_content:
        try:
            from app.services.pdf_extractor import rewrite_pdf_layout
            pdf_bytes = rewrite_pdf_layout(generation.resume.pdf_content, generation.rewritten_resume_text)
            generation.pdf_content = pdf_bytes
            await db.commit()
        except Exception as e:
            logger.warning("In-place PDF rewrite failed for %s, falling back to WeasyPrint: %s", generation_id, e)
            pdf_bytes = _weasyprint_fallback(generation.rewritten_resume_text, generation_id)
    else:
        pdf_bytes = _weasyprint_fallback(generation.rewritten_resume_text, generation_id)

    origin = request.headers.get("origin") or "http://localhost:3000"
    filename = _sanitize_pdf_filename(generation.title)
    encoded_filename = urllib.parse.quote(filename)
    is_download = request.query_params.get("download", "").lower() in ("true", "1")
    disposition = "attachment" if is_download else "inline"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}',
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        },
    )


def _weasyprint_fallback(rewritten_text: str, generation_id) -> bytes:
    """Render rewritten resume text as a fresh PDF via WeasyPrint (legacy path)."""
    try:
        from weasyprint import HTML
    except ImportError:
        raise HTTPException(status_code=501, detail="PDF generation not available — weasyprint not installed")

    resume_html = _text_to_html(rewritten_text)
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
    try:
        return HTML(string=html_content).write_pdf()
    except Exception as e:
        logger.exception("PDF rendering failed for %s: %s", generation_id, e)
        raise HTTPException(status_code=500, detail=f"PDF rendering failed: {e}")


@router.get("/{generation_id}/preview-html")
async def preview_html(
    generation_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Return clean styled HTML of the rewritten resume for the in-app previewer."""
    user_id = get_session_user_id(request)
    if user_id:
        result = await db.execute(
            select(Generation).where(Generation.id == generation_id, Generation.user_id == user_id)
        )
    else:
        result = await db.execute(
            select(Generation).where(Generation.id == generation_id)
        )
    generation = result.scalar_one_or_none()
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if not generation.rewritten_resume_text:
        raise HTTPException(status_code=400, detail="No rewritten resume available")

    resume_html = _text_to_html(generation.rewritten_resume_text)
    html_content = dedent(f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            * {{ box-sizing: border-box; }}
            html, body {{
              margin: 0;
              padding: 0;
              background: #ffffff;
              color: #111827;
            }}
            body {{
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
              font-size: 10.5pt;
              line-height: 1.55;
              padding: 2.25rem 2.5rem;
              color: #1a1a1a;
            }}
            h1 {{ font-size: 18pt; font-weight: 800; margin: 0 0 6pt; color: #111827; letter-spacing: -0.02em; }}
            h2 {{
              font-size: 12pt;
              font-weight: 700;
              border-bottom: 1.5px solid #111827;
              padding-bottom: 3pt;
              margin-top: 16pt;
              margin-bottom: 7pt;
              color: #111827;
              letter-spacing: 0.02em;
              text-transform: uppercase;
            }}
            h3 {{ font-size: 10.5pt; font-weight: 700; margin: 9pt 0 2pt; color: #1f2937; }}
            ul {{ margin: 4pt 0 6pt; padding-left: 18pt; }}
            li {{ margin-bottom: 2.5pt; color: #2d3748; }}
            p {{ margin: 3pt 0; color: #2d3748; }}
            .section {{ margin-bottom: 12pt; }}
          </style>
        </head>
        <body>
          {resume_html}
        </body>
        </html>
    """)
    origin = request.headers.get("origin") or "http://localhost:3000"
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        },
    )


def _sanitize_pdf_filename(title: str | None) -> str:
    """Format PDF download filename from generation title or fallback to generated_resume.pdf."""
    if not title or not title.strip():
        return "generated_resume.pdf"
    safe = re.sub(r'[\/\\:*?"<>|\x00-\x1f]', "", title.strip())
    safe = safe.strip(". ")
    if not safe:
        return "generated_resume.pdf"
    if not safe.lower().endswith(".pdf"):
        safe += ".pdf"
    return safe


def _text_to_html(text: str) -> str:
    """Convert plain resume text to basic HTML for PDF rendering."""
    # If the text contains raw JSON (e.g. from LLM returning JSON with code fences)
    cleaned_text = text.strip()
    if '"skills"' in cleaned_text and '"projects"' in cleaned_text:
        from app.utils.llm import extract_json
        parsed = extract_json(cleaned_text)
        s_val = None
        p_val = None
        if isinstance(parsed, dict):
            s_val = parsed.get("skills")
            p_val = parsed.get("projects")
        if not s_val or not p_val:
            m_s = re.search(r'"skills"\s*:\s*"(.*?)(?=",\s*"projects"|"\s*\})', cleaned_text, re.DOTALL)
            m_p = re.search(r'"projects"\s*:\s*"(.*?)(?="\s*\}|\Z)', cleaned_text, re.DOTALL)
            if m_s:
                s_val = m_s.group(1).replace(r'\"', '"').replace(r'\n', '\n')
            if m_p:
                p_val = m_p.group(1).replace(r'\"', '"').replace(r'\n', '\n')
        if s_val is not None and p_val is not None:
            cleaned_text = f"## Skills\n\n{str(s_val).strip()}\n\n## Projects\n\n{str(p_val).strip()}"

    # Clean up any trailing empty "## Projects" header at the end of the text
    cleaned_text = re.sub(r"(?i)\n*##\s*projects\s*$", "", cleaned_text.strip())
    # If "## Projects" is missing but project entries (### ) exist, inject ## Projects before the first entry
    if not re.search(r"(?i)##\s*projects", cleaned_text):
        match = re.search(r"\n(?=###\s+)", cleaned_text)
        if match:
            idx = match.start()
            cleaned_text = cleaned_text[:idx] + "\n\n## Projects\n" + cleaned_text[idx:]

    lines = cleaned_text.split("\n")
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
        elif stripped.startswith(("- ", "• ", "* ", "•", "-")):
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            content = stripped.lstrip("•-* ").strip()
            parts.append(f"<li>{html_module.escape(content)}</li>")
        else:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<p>{html_module.escape(stripped)}</p>")

    if in_ul:
        parts.append("</ul>")

    return "\n".join(parts)
