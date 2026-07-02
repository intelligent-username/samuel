import uuid
from asyncio import sleep
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        user = await self._get_user()
        generation = await self._get_generation()
        sections = extract_sections(generation.resume.extracted_text)
        repos = await self._get_repos(user)

        generation.status = "running"
        await self.db.commit()

        yield {"event": "step-start", "data": {"step": "jd_parser", "message": "Parsing job description..."}}
        jd_req = await JDParserSkill().run(generation.job_description_text, self.llm, debug_dir=self.debug_dir)
        yield {"event": "step-done", "data": {"step": "jd_parser", "summary": f"Extracted {len(jd_req.keywords)} keywords, {len(jd_req.hard_requirements)} requirements"}}

        yield {"event": "step-start", "data": {"step": "project_matcher", "message": "Matching projects to job..."}}
        jd_dict = jd_req.model_dump()
        repo_dicts = [
            {
                "name": r.name,
                "description": r.description,
                "stars": r.stars,
                "languages": r.languages,
                "readme_text": r.readme_text,
                "topics": r.topics,
            }
            for r in repos
        ]
        ranked = await ProjectMatcherSkill().run(jd_dict, repo_dicts, self.llm, debug_dir=self.debug_dir)
        yield {"event": "step-done", "data": {"step": "project_matcher", "summary": f"Ranked {len(ranked)} projects by relevance"}}

        yield {"event": "step-start", "data": {"step": "resume_writer", "message": "Rewriting resume skills and projects..."}}
        rewritten = await ResumeWriterSkill().run(sections["skills"], sections["projects"], jd_dict, ranked, self.llm, debug_dir=self.debug_dir)
        rewritten_text = f"## Skills\n\n{rewritten['skills']}\n\n## Projects\n\n{rewritten['projects']}"
        yield {"event": "step-done", "data": {"step": "resume_writer", "summary": "Skills and projects sections rewritten"}}

        yield {"event": "step-start", "data": {"step": "ats_checker", "message": "Checking ATS compatibility..."}}
        ats_report = await ATSCheckerSkill().run(rewritten_text, jd_req.keywords, self.llm, debug_dir=self.debug_dir)
        yield {"event": "step-done", "data": {"step": "ats_checker", "summary": f"ATS score: {ats_report.get('score', 'N/A')}/100"}}

        generation.rewritten_resume_text = rewritten_text
        generation.ats_report = ats_report
        generation.status = "completed"
        generation.completed_at = datetime.now(timezone.utc)
        generation.skill_chain_debug_path = str(self.debug_dir)
        await self.db.commit()

        yield {"event": "output", "data": rewritten_text}
        yield {"event": "done", "data": {"generation_id": str(self.generation_id), "ats_score": ats_report.get("score", 0)}}

    async def _get_user(self) -> User:
        result = await self.db.execute(
            select(User).join(Generation).where(Generation.id == self.generation_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        return user

    async def _get_generation(self) -> Generation:
        result = await self.db.execute(
            select(Generation).where(Generation.id == self.generation_id)
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