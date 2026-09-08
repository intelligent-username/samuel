import json
import logging
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
from app.ats import ATS
from app.schemas.ats import ATSResult
from app.services.ats_base import ATEvaluationError, ATSProvider
from app.services.ats_stagnation import should_early_break
from app.skills.jd_parser import JDParserSkill
from app.skills.project_matcher import ProjectMatcherSkill
from app.skills.resume_writer import ResumeWriterSkill
from app.utils.llm import LLMClient
from app.services.pdf_extractor import extract_sections, replace_sections_in_text, rewrite_pdf_layout

logger = logging.getLogger(__name__)


class Orchestrator:
    """Master agent that calls skills in sequence and yields SSE events in real time."""

    def __init__(self, generation_id: uuid.UUID, llm: LLMClient, db: AsyncSession, ats_provider: ATSProvider | None = None):
        self.generation_id = generation_id
        self.llm = llm
        self.db = db
        self.debug_dir = Path(settings.debug_dir) / str(generation_id)
        if ats_provider is not None:
            self.ats_provider = ats_provider
        else:
            try:
                from app.services.ats_registry import registry

                self.ats_provider = registry.get_default()
            except Exception:
                self.ats_provider = None  # type: ignore[assignment]

    async def _evaluate_ats(self, pdf_bytes: bytes | None, resume_text: str, jd_text: str) -> ATSResult:
        try:
            if self.ats_provider is None:
                from app.services.ats_registry import registry

                self.ats_provider = registry.get_default()
            return await self.ats_provider.evaluate(pdf_bytes or b"", jd_text, resume_text)
        except ATEvaluationError:
            logger.warning("ATS eval failed: %s", "ATEvaluationError")
            return ATSResult(score=0, details={"error": "evaluation failed"}, raw_report=None)
        except Exception as e:
            logger.warning("ATS eval unexpected: %s", type(e).__name__)
            return ATSResult(score=0, details={"error": "evaluation failed"}, raw_report=None)

    async def run(self) -> AsyncGenerator[dict, None]:
        """Yield SSE events for the 4-skill chain.

        Note: Idempotency is enforced by the router's cached-replay guard.
        This method assumes status is pending/running; calling it for a
        completed generation would re-run LLM calls and overwrite DB.
        """
        generation = await self._get_generation()
        result = await self.db.execute(select(User).where(User.id == generation.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        original_text = generation.resume.extracted_text if generation.resume else ""
        sections = extract_sections(original_text)
        repos = await self._get_repos(user)
        
        # Check for fallback sections and emit warning before resume_writer
        is_fallback = bool(sections.get("_fallback")) or (not sections.get("skills") and not sections.get("projects"))
        if is_fallback:
            yield {"event": "warning", "data": json.dumps({"message": "Could not detect Skills/Projects sections — using full resume text"})}

        generation.status = "running"
        await self.db.commit()

        # Step 1: JD Parser (sends ONLY the raw JD text)
        yield {"event": "step-start", "data": json.dumps({"step": "jd_parser", "message": "Analyzing job description requirements..."})}
        jd_parser = JDParserSkill()
        jd_requirements = await jd_parser.run(generation.job_description_text, self.llm, self.debug_dir)
        num_keywords = len(getattr(jd_requirements, "keywords", []) or [])
        yield {"event": "step-done", "data": json.dumps({"step": "jd_parser", "summary": f"Identified {num_keywords} key skills/requirements"})}

        # Step 2: Project Matcher (sends ONLY parsed JD requirements and compact repo summaries)
        yield {"event": "step-start", "data": json.dumps({"step": "project_matcher", "message": "Matching repositories against requirements..."})}
        matcher = ProjectMatcherSkill()
        repo_dicts = [
            {
                "name": r.name,
                "description": r.description,
                "stars": r.stars,
                "languages": r.languages,
                "topics": r.topics,
                "readme_text": r.readme_text,
            }
            for r in repos
        ]
        jd_req_dict = jd_requirements.model_dump() if hasattr(jd_requirements, "model_dump") else jd_requirements
        ranked_projects = await matcher.run(jd_req_dict, repo_dicts, self.llm, self.debug_dir)
        yield {"event": "step-done", "data": json.dumps({"step": "project_matcher", "summary": f"Ranked {len(ranked_projects)} matching projects"})}

        # Step 3: Resume Writer (sends ONLY the extracted Skills & Projects text)
        yield {"event": "step-start", "data": json.dumps({"step": "resume_writer", "message": "Rewriting Skills and Projects sections..."})}
        writer = ResumeWriterSkill()
        skills_raw = str(sections.get("skills") or "")
        projects_raw = str(sections.get("projects") or "")
        rewritten_sections = await writer.run(
            skills_section=skills_raw,
            projects_section=projects_raw,
            jd_requirements=jd_req_dict,
            ranked_projects=ranked_projects,
            llm=self.llm,
            debug_dir=self.debug_dir,
        )
        new_skills = rewritten_sections.get("skills", "").strip()
        new_projects = rewritten_sections.get("projects", "").strip()
        full_rewritten_text = replace_sections_in_text(original_text, new_skills, new_projects)
        yield {"event": "step-done", "data": json.dumps({"step": "resume_writer", "summary": "Skills and Projects rewritten to match job profile"})}

        # Step 4: Deterministic Algorithmic ATS Evaluation
        yield {"event": "step-start", "data": json.dumps({"step": "ats_checker", "message": "Running deterministic ATS compatibility audit..."})}
        ats_engine = ATS()
        ats_report = ats_engine.evaluate(
            resume_text=full_rewritten_text,
            context={
                "keywords": getattr(jd_requirements, "keywords", []) or [],
                "hard_requirements": getattr(jd_requirements, "hard_requirements", []) or [],
                "preferred_skills": getattr(jd_requirements, "preferred_skills", []) or [],
                "job_description_text": generation.job_description_text,
            },
        )
        ats_score = ats_report.get("score", 100)
        yield {"event": "step-done", "data": json.dumps({"step": "ats_checker", "summary": f"ATS Score: {ats_score}/100"})}

        # In-place PDF rewrite preserving original fonts, icons, layout, and ruling lines
        original_pdf = None
        if generation.resume and generation.resume.pdf_content:
            original_pdf = generation.resume.pdf_content
        else:
            fallback_asset = Path(__file__).parent / "assets" / "resume.pdf"
            if fallback_asset.exists():
                original_pdf = fallback_asset.read_bytes()
                if generation.resume and not generation.resume.pdf_content:
                    generation.resume.pdf_content = original_pdf

        if original_pdf:
            try:
                rewritten_md = f"## Skills\n{new_skills}\n\n## Projects\n{new_projects}"
                pdf_bytes = rewrite_pdf_layout(original_pdf, rewritten_md)
            except Exception as e:
                logging.getLogger(__name__).warning("In-place PDF rewrite failed, keeping original: %s", e)
                pdf_bytes = original_pdf
        else:
            pdf_bytes = None

        generation.rewritten_resume_text = full_rewritten_text
        generation.pdf_content = pdf_bytes
        generation.ats_report = ats_report
        generation.ats_scores = [ats_score]
        generation.iterations = [{"iteration": 1, "score": ats_score}]
        generation.ats_exit_reason = "single_pass"
        generation.status = "completed"
        generation.completed_at = datetime.now(timezone.utc)
        await self.db.commit()

        yield {"event": "output", "data": full_rewritten_text}
        yield {"event": "done", "data": json.dumps({
            "generation_id": str(self.generation_id),
            "ats_score": ats_score,
            "ats_scores": [ats_score],
            "exit_reason": "single_pass",
            "iterations": [{"iteration": 1, "score": ats_score}],
            "rewritten_resume": full_rewritten_text,
            "pdf_url": f"/generate/{self.generation_id}/download",
        })}

    async def run_with_ats_loop(
        self,
        ats_threshold: int | None = None,
        ats_max_iterations: int | None = None,
    ) -> AsyncGenerator[dict, None]:
        if ats_threshold is None or ats_threshold == 0:
            generation = await self._get_generation()
            result = await self.db.execute(select(User).where(User.id == generation.user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise ValueError("User not found")
            original_text = generation.resume.extracted_text if generation.resume else ""
            sections = extract_sections(original_text)
            repos = await self._get_repos(user)
            is_fallback = bool(sections.get("_fallback")) or (not sections.get("skills") and not sections.get("projects"))
            if is_fallback:
                yield {"event": "warning", "data": json.dumps({"message": "Could not detect Skills/Projects sections — using full resume text"})}
            generation.status = "running"
            generation.ats_threshold = ats_threshold
            generation.ats_max_iterations = ats_max_iterations or settings.ats_max_iterations
            generation.ats_exit_reason = "single_pass"
            await self.db.commit()

            yield {"event": "step-start", "data": json.dumps({"step": "jd_parser", "message": "Analyzing job description requirements..."})}
            jd_parser = JDParserSkill()
            jd_requirements = await jd_parser.run(generation.job_description_text, self.llm, self.debug_dir)
            num_keywords = len(getattr(jd_requirements, "keywords", []) or [])
            yield {"event": "step-done", "data": json.dumps({"step": "jd_parser", "summary": f"Identified {num_keywords} key skills/requirements"})}

            yield {"event": "step-start", "data": json.dumps({"step": "project_matcher", "message": "Matching repositories against requirements..."})}
            matcher = ProjectMatcherSkill()
            repo_dicts = [{"name": r.name, "description": r.description, "stars": r.stars, "languages": r.languages, "topics": r.topics, "readme_text": r.readme_text} for r in repos]
            jd_req_dict = jd_requirements.model_dump() if hasattr(jd_requirements, "model_dump") else jd_requirements
            ranked_projects = await matcher.run(jd_req_dict, repo_dicts, self.llm, self.debug_dir)
            yield {"event": "step-done", "data": json.dumps({"step": "project_matcher", "summary": f"Ranked {len(ranked_projects)} matching projects"})}

            yield {"event": "step-start", "data": json.dumps({"step": "resume_writer", "message": "Rewriting Skills and Projects sections..."})}
            writer = ResumeWriterSkill()
            skills_raw = str(sections.get("skills") or "")
            projects_raw = str(sections.get("projects") or "")
            rewritten_sections = await writer.run(skills_section=skills_raw, projects_section=projects_raw, jd_requirements=jd_req_dict, ranked_projects=ranked_projects, llm=self.llm, debug_dir=self.debug_dir)
            new_skills = rewritten_sections.get("skills", "").strip()
            new_projects = rewritten_sections.get("projects", "").strip()
            full_rewritten_text = replace_sections_in_text(original_text, new_skills, new_projects)
            yield {"event": "step-done", "data": json.dumps({"step": "resume_writer", "summary": "Skills and Projects rewritten to match job profile"})}

            yield {"event": "step-start", "data": json.dumps({"step": "ats_checker", "message": "Running deterministic ATS compatibility audit..."})}
            original_pdf = None
            if generation.resume and generation.resume.pdf_content:
                original_pdf = generation.resume.pdf_content
            else:
                fallback_asset = Path(__file__).parent / "assets" / "resume.pdf"
                if fallback_asset.exists():
                    original_pdf = fallback_asset.read_bytes()
                    if generation.resume and not generation.resume.pdf_content:
                        generation.resume.pdf_content = original_pdf
            pdf_bytes: bytes | None = None
            if original_pdf:
                try:
                    rewritten_md = f"## Skills\n{new_skills}\n\n## Projects\n{new_projects}"
                    pdf_bytes = rewrite_pdf_layout(original_pdf, rewritten_md)
                except Exception as e:
                    logger.warning("In-place PDF rewrite failed, keeping original: %s", type(e).__name__)
                    pdf_bytes = original_pdf
            else:
                try:
                    from app.services.pdf_renderer import render_resume_to_pdf

                    pdf_bytes = render_resume_to_pdf(full_rewritten_text)
                except Exception as e:
                    logger.warning("PDF render failed: %s", type(e).__name__)
                    pdf_bytes = None

            ats_result = await self._evaluate_ats(pdf_bytes, full_rewritten_text, generation.job_description_text)
            ats_score = ats_result.score
            ats_report = {"score": ats_score, "details": ats_result.details, "raw_report": ats_result.raw_report}
            yield {"event": "step-done", "data": json.dumps({"step": "ats_checker", "summary": f"ATS Score: {ats_score}/100"})}
            yield {"event": "ats_evaluation", "data": json.dumps({"score": ats_score, "threshold": ats_threshold, "will_retry": False, "iteration": 1})}

            generation.rewritten_resume_text = full_rewritten_text
            generation.pdf_content = pdf_bytes
            generation.ats_report = ats_report
            generation.ats_scores = [ats_score]
            generation.iterations = [{"iteration": 1, "score": ats_score}]
            generation.status = "completed"
            generation.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            yield {"event": "output", "data": full_rewritten_text}
            yield {"event": "done", "data": json.dumps({"generation_id": str(self.generation_id), "ats_score": ats_score, "ats_scores": [ats_score], "exit_reason": "single_pass", "iterations": generation.iterations, "rewritten_resume": full_rewritten_text, "pdf_url": f"/generate/{self.generation_id}/download"})}
            return

        generation = await self._get_generation()
        result = await self.db.execute(select(User).where(User.id == generation.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        original_text = generation.resume.extracted_text if generation.resume else ""
        sections = extract_sections(original_text)
        repos = await self._get_repos(user)
        is_fallback = bool(sections.get("_fallback")) or (not sections.get("skills") and not sections.get("projects"))
        if is_fallback:
            yield {"event": "warning", "data": json.dumps({"message": "Could not detect Skills/Projects sections — using full resume text"})}
        generation.status = "running"
        max_iter = ats_max_iterations if ats_max_iterations is not None else settings.ats_max_iterations
        try:
            max_iter = max(5, min(7, int(max_iter)))
        except Exception:
            max_iter = settings.ats_max_iterations
        threshold = int(ats_threshold)
        generation.ats_threshold = threshold
        generation.ats_max_iterations = max_iter
        await self.db.commit()

        yield {"event": "step-start", "data": json.dumps({"step": "jd_parser", "message": "Analyzing job description requirements..."})}
        jd_parser = JDParserSkill()
        jd_requirements = await jd_parser.run(generation.job_description_text, self.llm, self.debug_dir)
        num_keywords = len(getattr(jd_requirements, "keywords", []) or [])
        yield {"event": "step-done", "data": json.dumps({"step": "jd_parser", "summary": f"Identified {num_keywords} key skills/requirements"})}

        yield {"event": "step-start", "data": json.dumps({"step": "project_matcher", "message": "Matching repositories against requirements..."})}
        matcher = ProjectMatcherSkill()
        repo_dicts = [{"name": r.name, "description": r.description, "stars": r.stars, "languages": r.languages, "topics": r.topics, "readme_text": r.readme_text} for r in repos]
        jd_req_dict = jd_requirements.model_dump() if hasattr(jd_requirements, "model_dump") else jd_requirements
        ranked_projects = await matcher.run(jd_req_dict, repo_dicts, self.llm, self.debug_dir)
        yield {"event": "step-done", "data": json.dumps({"step": "project_matcher", "summary": f"Ranked {len(ranked_projects)} matching projects"})}

        yield {"event": "step-start", "data": json.dumps({"step": "resume_writer", "message": "Rewriting Skills and Projects sections..."})}
        writer = ResumeWriterSkill()
        skills_raw = str(sections.get("skills") or "")
        projects_raw = str(sections.get("projects") or "")
        rewritten_sections = await writer.run(skills_section=skills_raw, projects_section=projects_raw, jd_requirements=jd_req_dict, ranked_projects=ranked_projects, llm=self.llm, debug_dir=self.debug_dir)
        new_skills = rewritten_sections.get("skills", "").strip()
        new_projects = rewritten_sections.get("projects", "").strip()
        full_rewritten_text = replace_sections_in_text(original_text, new_skills, new_projects)
        yield {"event": "step-done", "data": json.dumps({"step": "resume_writer", "summary": "Skills and Projects rewritten to match job profile"})}

        yield {"event": "step-start", "data": json.dumps({"step": "ats_checker", "message": "Running deterministic ATS compatibility audit..."})}
        original_pdf = None
        if generation.resume and generation.resume.pdf_content:
            original_pdf = generation.resume.pdf_content
        else:
            fallback_asset = Path(__file__).parent / "assets" / "resume.pdf"
            if fallback_asset.exists():
                original_pdf = fallback_asset.read_bytes()
                if generation.resume and not generation.resume.pdf_content:
                    generation.resume.pdf_content = original_pdf
        pdf_bytes: bytes | None = None
        if original_pdf:
            try:
                rewritten_md = f"## Skills\n{new_skills}\n\n## Projects\n{new_projects}"
                pdf_bytes = rewrite_pdf_layout(original_pdf, rewritten_md)
            except Exception as e:
                logger.warning("In-place PDF rewrite failed: %s", type(e).__name__)
                pdf_bytes = original_pdf
        else:
            try:
                from app.services.pdf_renderer import render_resume_to_pdf

                pdf_bytes = render_resume_to_pdf(full_rewritten_text)
            except Exception as e:
                logger.warning("PDF render failed: %s", type(e).__name__)
                pdf_bytes = None

        ats_result = await self._evaluate_ats(pdf_bytes, full_rewritten_text, generation.job_description_text)
        scores: list[int] = [ats_result.score]
        iterations_detail: list[dict] = [{"iteration": 1, "score": ats_result.score}]
        yield {"event": "step-done", "data": json.dumps({"step": "ats_checker", "summary": f"ATS Score: {ats_result.score}/100"})}
        will_retry = ats_result.score < threshold
        yield {"event": "ats_evaluation", "data": json.dumps({"score": ats_result.score, "threshold": threshold, "will_retry": will_retry, "iteration": 1})}

        if ats_result.score >= threshold:
            generation.ats_exit_reason = "threshold_met"
            generation.rewritten_resume_text = full_rewritten_text
            generation.pdf_content = pdf_bytes
            generation.ats_report = {"score": ats_result.score, "details": ats_result.details, "raw_report": ats_result.raw_report}
            generation.ats_scores = scores
            generation.iterations = iterations_detail
            generation.status = "completed"
            generation.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            yield {"event": "output", "data": full_rewritten_text}
            yield {"event": "done", "data": json.dumps({"generation_id": str(self.generation_id), "ats_score": ats_result.score, "ats_scores": scores, "exit_reason": "threshold_met", "iterations": iterations_detail, "rewritten_resume": full_rewritten_text, "pdf_url": f"/generate/{self.generation_id}/download"})}
            return

        for iteration in range(2, max_iter + 1):
            yield {"event": "ats_loop", "data": json.dumps({"iteration": iteration, "score": scores[-1], "threshold": threshold})}
            if should_early_break(scores, window=settings.ats_stagnation_window, min_relative_gain=settings.ats_min_gain):
                yield {"event": "ats_stagnation", "data": json.dumps({"window": settings.ats_stagnation_window, "min_gain": settings.ats_min_gain, "scores_slice": scores[-(settings.ats_stagnation_window + 1):]})}
                generation.ats_exit_reason = "stagnation"
                break
            missing = []
            warnings: list[str] = []
            if ats_result.details:
                missing = ats_result.details.get("missing_keywords") or ats_result.details.get("missing_required") or []
                warnings = ats_result.details.get("warnings") or ats_result.details.get("issues") or []
            feedback = f"ATS score {scores[-1]}/{threshold}; missing keywords: {', '.join(str(m) for m in missing[:10]) if missing else 'none'}; warnings: {'; '.join(str(w) for w in warnings[:5]) if warnings else 'none'}"
            yield {"event": "step-start", "data": json.dumps({"step": "resume_writer", "message": f"Refining resume (iteration {iteration}/{max_iter})..."})}
            rewritten_sections = await writer.run(skills_section=new_skills, projects_section=new_projects, jd_requirements=jd_req_dict, ranked_projects=ranked_projects, llm=self.llm, debug_dir=self.debug_dir, ats_feedback=feedback)
            new_skills = rewritten_sections.get("skills", "").strip() or new_skills
            new_projects = rewritten_sections.get("projects", "").strip() or new_projects
            full_rewritten_text = replace_sections_in_text(original_text, new_skills, new_projects)
            yield {"event": "step-done", "data": json.dumps({"step": "resume_writer", "summary": f"Refined Skills/Projects (iteration {iteration})"})}
            if original_pdf:
                try:
                    rewritten_md = f"## Skills\n{new_skills}\n\n## Projects\n{new_projects}"
                    pdf_bytes = rewrite_pdf_layout(original_pdf, rewritten_md)
                except Exception as e:
                    logger.warning("PDF rewrite failed iteration %s: %s", iteration, type(e).__name__)
                    pdf_bytes = original_pdf
            else:
                try:
                    from app.services.pdf_renderer import render_resume_to_pdf

                    pdf_bytes = render_resume_to_pdf(full_rewritten_text)
                except Exception as e:
                    logger.warning("PDF render failed iteration %s: %s", iteration, type(e).__name__)
                    pdf_bytes = None
            ats_result = await self._evaluate_ats(pdf_bytes, full_rewritten_text, generation.job_description_text)
            scores.append(ats_result.score)
            iterations_detail.append({"iteration": iteration, "score": ats_result.score})
            will_retry_inner = ats_result.score < threshold and iteration < max_iter
            yield {"event": "ats_evaluation", "data": json.dumps({"score": ats_result.score, "threshold": threshold, "will_retry": will_retry_inner, "iteration": iteration})}
            if ats_result.score >= threshold:
                generation.ats_exit_reason = "threshold_met"
                break
        else:
            if not generation.ats_exit_reason or generation.ats_exit_reason not in ("threshold_met", "stagnation"):
                generation.ats_exit_reason = "max_iterations"

        if not generation.ats_exit_reason:
            generation.ats_exit_reason = "max_iterations"
        final_score = scores[-1]
        generation.rewritten_resume_text = full_rewritten_text
        generation.pdf_content = pdf_bytes
        generation.ats_report = {"score": final_score, "details": ats_result.details if ats_result else {}, "raw_report": ats_result.raw_report if ats_result else None}
        generation.ats_scores = scores
        generation.iterations = iterations_detail
        generation.status = "completed"
        generation.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        yield {"event": "output", "data": full_rewritten_text}
        yield {"event": "done", "data": json.dumps({"generation_id": str(self.generation_id), "ats_score": final_score, "ats_scores": scores, "exit_reason": generation.ats_exit_reason, "iterations": iterations_detail, "rewritten_resume": full_rewritten_text, "pdf_url": f"/generate/{self.generation_id}/download"})}

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
