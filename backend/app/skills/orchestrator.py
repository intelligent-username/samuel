import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.generation import Generation
from app.models.repository import Repository
from app.models.user import User
from app.skills.ats_checker import ATSCheckerSkill
from app.skills.jd_parser import JDParserSkill
from app.skills.project_matcher import ProjectMatcherSkill
from app.skills.resume_writer import ResumeWriterSkill
from app.utils.llm import LLMClient
from app.services.pdf_extractor import extract_sections


class Orchestrator:
    """Master agent that calls skills in sequence and yields SSE events in real time."""

    def __init__(self, generation_id: uuid.UUID, llm: LLMClient, db: AsyncSession):
        self.generation_id = generation_id
        self.llm = llm
        self.db = db
        self.debug_dir = Path(settings.debug_dir) / str(generation_id)

    async def run(self) -> AsyncGenerator[dict, None]:
        """Yield SSE events for the 4-skill chain.

        Note: Idempotency is enforced by the router's cached-replay guard.
        This method assumes status is pending/running; calling it for a
        completed generation would re-run LLM calls and overwrite DB.
        """
        generation = await self._get_generation()
        # Get user via explicit FK — avoids join ambiguity that caused "User not found"
        result = await self.db.execute(select(User).where(User.id == generation.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        sections = extract_sections(generation.resume.extracted_text)
        repos = await self._get_repos(user)
        
        # Check for fallback sections and emit warning before resume_writer
        is_fallback = bool(sections.get("_fallback")) or (not sections.get("skills") and not sections.get("projects"))
        if is_fallback:
            # Emit warning before resume_writer so frontend can show it; do not abort generation
            yield {"event": "warning", "data": {"message": "Could not detect Skills/Projects sections — using full resume text"}}

        generation.status = "running"
        await self.db.commit()

        # Helper to persist debug path even on failure
        def _debug_path():
            return str(self.debug_dir)

        # Step 1: JD Parser
        yield {"event": "step-start", "data": {"step": "jd_parser", "message": "Parsing job description..."}}
        try:
            jd_req = await JDParserSkill().run(generation.job_description_text, self.llm, debug_dir=self.debug_dir)
        except Exception as e:
            generation.skill_chain_debug_path = _debug_path()
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
            yield {"event": "step-error", "data": {"step": "jd_parser", "message": str(e)}}
            raise
        yield {"event": "step-done", "data": {"step": "jd_parser", "summary": f"Extracted {len(jd_req.keywords)} keywords, {len(jd_req.hard_requirements)} requirements"}}

        # Step 2: Project Matcher
        yield {"event": "step-start", "data": {"step": "project_matcher", "message": "Matching projects to job..."}}
        try:
            jd_dict = jd_req.model_dump()
            repo_dicts = [
                {"name": r.name, "description": r.description, "stars": r.stars, "languages": r.languages, "readme_text": r.readme_text, "topics": r.topics}
                for r in repos
            ]
            ranked = await ProjectMatcherSkill().run(jd_dict, repo_dicts, self.llm, debug_dir=self.debug_dir)
        except Exception as e:
            generation.skill_chain_debug_path = _debug_path()
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
            yield {"event": "step-error", "data": {"step": "project_matcher", "message": str(e)}}
            raise
        yield {"event": "step-done", "data": {"step": "project_matcher", "summary": f"Ranked {len(ranked)} projects by relevance"}}

        # Step 3: Resume Writer
        yield {"event": "step-start", "data": {"step": "resume_writer", "message": "Rewriting resume skills and projects..."}}
        try:
            rewritten = await ResumeWriterSkill().run(
                skills_section=str(sections.get("skills", "")),
                projects_section=str(sections.get("projects", "")),
                jd_requirements=jd_dict,
                ranked_projects=ranked,
                llm=self.llm,
                debug_dir=self.debug_dir,
            )
            rewritten_text = f"## Skills\n\n{rewritten['skills']}\n\n## Projects\n\n{rewritten['projects']}"
        except Exception as e:
            generation.skill_chain_debug_path = _debug_path()
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
            yield {"event": "step-error", "data": {"step": "resume_writer", "message": str(e)}}
            raise
        yield {"event": "step-done", "data": {"step": "resume_writer", "summary": "Skills and projects sections rewritten"}}

        # Step 4: ATS Checker
        yield {"event": "step-start", "data": {"step": "ats_checker", "message": "Checking ATS compatibility..."}}
        try:
            ats_report = await ATSCheckerSkill().run(rewritten_text, jd_req.keywords, self.llm, debug_dir=self.debug_dir)
        except Exception as e:
            generation.skill_chain_debug_path = _debug_path()
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
            yield {"event": "step-error", "data": {"step": "ats_checker", "message": str(e)}}
            raise
        yield {"event": "step-done", "data": {"step": "ats_checker", "summary": f"ATS score: {ats_report.get('score', 'N/A')}/100"}}

        generation.rewritten_resume_text = rewritten_text
        generation.ats_report = ats_report
        generation.status = "completed"
        generation.completed_at = datetime.now(timezone.utc)
        generation.skill_chain_debug_path = str(self.debug_dir)
        await self.db.commit()

        yield {"event": "output", "data": rewritten_text}
        yield {"event": "done", "data": {"generation_id": str(self.generation_id), "ats_score": ats_report.get("score", 0), "rewritten_resume": rewritten_text, "pdf_url": f"/generate/{self.generation_id}/download"}}

    async def _get_user(self) -> User:
        # Fetch generation first to get user_id explicitly — avoids ambiguous join
        gen = await self._get_generation()
        result = await self.db.execute(select(User).where(User.id == gen.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        return user

    async def _get_generation(self) -> Generation:
        result = await self.db.execute(
            select(Generation)
            .where(Generation.id == self.generation_id)
            .options(selectinload(Generation.resume))
        )
        gen = result.scalar_one_or_none()
        if not gen:
            raise ValueError("Generation not found")
        return gen

    async def _get_repos(self, user: User) -> list[Repository]:
        result = await self.db.execute(
            select(Repository).where(Repository.user_id == user.id).order_by(Repository.stars.desc())
        )
        return list(result.scalars().all())