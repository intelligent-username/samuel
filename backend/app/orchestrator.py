import asyncio
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
from app.constants import ATS_MAX_ITERATIONS_CAP, ATS_MIN_ITERATIONS
from app.models.generation import Generation
from app.models.repository import Repository
from app.models.user import User
from app.ats import ATS, ATSContext
from app.schemas.ats import ATSResult
from app.services.ats_base import ATEvaluationError, ATSProvider
from app.services.ats_stagnation import should_early_break
from app.skills.jd_parser import JDParserSkill
from app.skills.project_matcher import ProjectMatcherSkill
from app.skills.resume_writer import ResumeWriterSkill
from app.utils.ats_normalize import normalize_list
from app.utils.llm import LLMClient
from app.services.pdf_extractor import extract_sections, replace_sections_in_text, rewrite_pdf_layout

logger = logging.getLogger(__name__)


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def build_ats_context(jd_requirements: object, jd_text: str = "") -> ATSContext:
    if jd_requirements is None:
        return ATSContext(job_description_text=str(jd_text or ""))
    if isinstance(jd_requirements, dict):
        keywords = normalize_list(_as_str_list(jd_requirements.get("keywords")))
        hard = normalize_list(_as_str_list(jd_requirements.get("hard_requirements")))
        preferred = normalize_list(_as_str_list(jd_requirements.get("preferred_skills")))
        text = str(jd_requirements.get("job_description_text") or jd_text or "")
    else:
        keywords = normalize_list(_as_str_list(getattr(jd_requirements, "keywords", [])))
        hard = normalize_list(_as_str_list(getattr(jd_requirements, "hard_requirements", [])))
        preferred = normalize_list(_as_str_list(getattr(jd_requirements, "preferred_skills", [])))
        text = str(getattr(jd_requirements, "job_description_text", "") or jd_text or "")
    return ATSContext(keywords=keywords, hard_requirements=hard, preferred_skills=preferred, job_description_text=text)


def _report_to_result(report: dict) -> ATSResult:
    score = max(0, min(100, int(report.get("score", 0))))
    details = {
        "issues": report.get("issues", []),
        "warnings": report.get("warnings", []),
        "missing_keywords": report.get("missing_keywords", []),
        "breakdown": report.get("breakdown", {}),
    }
    return ATSResult(score=score, details=details, raw_report=json.dumps(report))


def _loop_feedback(details: dict | None) -> tuple[list, list[str]]:
    if not details:
        return [], []
    missing = details.get("missing_keywords") or []
    if not missing:
        breakdown = details.get("breakdown") or {}
        kw = breakdown.get("keyword_coverage") or {}
        missing = (kw.get("details") or {}).get("missing") or []
    warnings = details.get("warnings") or []
    issues = details.get("issues") or []
    merged = list(warnings) + [w for w in issues if w not in warnings]
    return list(missing), merged


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

    async def _evaluate_ats(self, resume_text: str, jd_requirements: object, jd_text: str = "") -> ATSResult:
        try:
            ctx = build_ats_context(jd_requirements, jd_text)
            if not resume_text or not resume_text.strip():
                return ATSResult(score=0, details={"error": "empty input"}, raw_report=None)
            return _report_to_result(ATS().evaluate(resume_text, ctx))
        except ATEvaluationError:
            logger.warning("ATS eval failed: %s", "ATEvaluationError")
            return ATSResult(score=0, details={"error": "evaluation failed"}, raw_report=None)
        except Exception as e:
            logger.warning("ATS eval unexpected: %s", type(e).__name__)
            return ATSResult(score=0, details={"error": "evaluation failed"}, raw_report=None)

    async def _load_context(self) -> tuple:
        """Load generation, user, resume sections, repos, original PDF."""
        generation = await self._get_generation()
        result = await self.db.execute(select(User).where(User.id == generation.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        original_text = generation.resume.extracted_text if generation.resume else ""
        sections = extract_sections(original_text)
        repos, original_pdf = await asyncio.gather(
            self._get_repos(user),
            self._load_original_pdf(generation),
        )
        return generation, user, original_text, sections, repos, original_pdf

    async def _load_original_pdf(self, generation: Generation) -> bytes | None:
        if generation.resume and generation.resume.pdf_content:
            return generation.resume.pdf_content
        fallback_asset = Path(__file__).parent / "assets" / "resume.pdf"
        if fallback_asset.exists():
            original_pdf = await asyncio.to_thread(fallback_asset.read_bytes)
            if generation.resume and not generation.resume.pdf_content:
                generation.resume.pdf_content = original_pdf
            return original_pdf
        return None

    async def _run_steps_1_3(self, generation: Generation, repos: list, sections: dict, out: dict) -> AsyncGenerator[dict, None]:
        """Yield jd_parser, project_matcher, resume_writer events. Store results in out."""
        yield {"event": "step-start", "data": json.dumps({"step": "jd_parser", "message": "Analyzing job description requirements..."})}
        jd_requirements = await JDParserSkill().run(generation.job_description_text, self.llm, self.debug_dir)
        num_keywords = len(getattr(jd_requirements, "keywords", []) or [])
        yield {"event": "step-done", "data": json.dumps({"step": "jd_parser", "summary": f"Identified {num_keywords} key skills/requirements"})}
        yield {"event": "step-start", "data": json.dumps({"step": "project_matcher", "message": "Matching repositories against requirements..."})}
        repo_dicts = [{"name": r.name, "description": r.description, "stars": r.stars, "languages": r.languages, "topics": r.topics, "readme_text": r.readme_text} for r in repos[:30]]
        jd_req_dict = jd_requirements.model_dump() if hasattr(jd_requirements, "model_dump") else jd_requirements
        ranked_projects = await ProjectMatcherSkill().run(jd_req_dict, repo_dicts, self.llm, self.debug_dir)
        yield {"event": "step-done", "data": json.dumps({"step": "project_matcher", "summary": f"Ranked {len(ranked_projects)} matching projects"})}
        yield {"event": "step-start", "data": json.dumps({"step": "resume_writer", "message": "Rewriting Skills and Projects sections..."})}
        writer = ResumeWriterSkill()
        skills_raw = str(sections.get("skills") or "")
        projects_raw = str(sections.get("projects") or "")
        rewritten = await writer.run(skills_section=skills_raw, projects_section=projects_raw, jd_requirements=jd_req_dict, ranked_projects=ranked_projects, llm=self.llm, debug_dir=self.debug_dir)
        new_skills = rewritten.get("skills", "").strip()
        new_projects = rewritten.get("projects", "").strip()
        original_text = generation.resume.extracted_text if generation.resume else ""
        full_text = replace_sections_in_text(original_text, new_skills, new_projects)
        yield {"event": "step-done", "data": json.dumps({"step": "resume_writer", "summary": "Skills and Projects rewritten to match job profile"})}
        out.update({"jd_requirements": jd_requirements, "jd_req_dict": jd_req_dict, "ranked_projects": ranked_projects, "writer": writer, "new_skills": new_skills, "new_projects": new_projects, "full_rewritten_text": full_text})

    async def _render_pdf_bytes(self, original_pdf: bytes | None, new_skills: str, new_projects: str, full_text: str) -> bytes | None:
        """Rewrite original PDF in place, else render from text."""
        if original_pdf:
            try:
                rewritten_md = f"## Skills\n{new_skills}\n\n## Projects\n{new_projects}"
                return await asyncio.to_thread(rewrite_pdf_layout, original_pdf, rewritten_md)
            except Exception as e:
                logger.warning("In-place PDF rewrite failed, keeping original: %s", type(e).__name__)
                return original_pdf
        try:
            from app.services.pdf_renderer import render_resume_to_pdf

            return await asyncio.to_thread(render_resume_to_pdf, full_text)
        except Exception as e:
            logger.warning("PDF render failed: %s", type(e).__name__)
            return None

    async def run(self) -> AsyncGenerator[dict, None]:
        """Yield SSE events for the 4-skill chain.

        Note: Idempotency is enforced by the router's cached-replay guard.
        This method assumes status is pending/running; calling it for a
        completed generation would re-run LLM calls and overwrite DB.
        """
        generation, user, original_text, sections, repos, original_pdf = await self._load_context()
        is_fallback = bool(sections.get("_fallback")) or (not sections.get("skills") and not sections.get("projects"))
        if is_fallback:
            yield {"event": "warning", "data": json.dumps({"message": "Could not detect Skills/Projects sections — using full resume text"})}
        generation.status = "running"
        await self.db.commit()
        out: dict = {}
        async for event in self._run_steps_1_3(generation, repos, sections, out):
            yield event
        jd_requirements = out["jd_requirements"]
        new_skills = out["new_skills"]
        new_projects = out["new_projects"]
        full_rewritten_text = out["full_rewritten_text"]
        yield {"event": "step-start", "data": json.dumps({"step": "ats_checker", "message": "Running deterministic ATS compatibility audit..."})}
        ats_result = await self._evaluate_ats(full_rewritten_text, jd_requirements, generation.job_description_text)
        ats_score = ats_result.score
        ats_report = {"score": ats_score, "details": ats_result.details, "raw_report": ats_result.raw_report}
        yield {"event": "step-done", "data": json.dumps({"step": "ats_checker", "summary": f"ATS Score: {ats_score}/100"})}
        pdf_bytes = await self._render_pdf_bytes(original_pdf, new_skills, new_projects, full_rewritten_text)
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
            generation, user, original_text, sections, repos, original_pdf = await self._load_context()
            is_fallback = bool(sections.get("_fallback")) or (not sections.get("skills") and not sections.get("projects"))
            if is_fallback:
                yield {"event": "warning", "data": json.dumps({"message": "Could not detect Skills/Projects sections — using full resume text"})}
            generation.status = "running"
            generation.ats_threshold = ats_threshold
            generation.ats_max_iterations = ats_max_iterations or settings.ats_max_iterations
            generation.ats_exit_reason = "single_pass"
            await self.db.commit()
            out: dict = {}
            async for event in self._run_steps_1_3(generation, repos, sections, out):
                yield event
            jd_requirements = out["jd_requirements"]
            new_skills = out["new_skills"]
            new_projects = out["new_projects"]
            full_rewritten_text = out["full_rewritten_text"]
            yield {"event": "step-start", "data": json.dumps({"step": "ats_checker", "message": "Running deterministic ATS compatibility audit..."})}
            pdf_bytes = await self._render_pdf_bytes(original_pdf, new_skills, new_projects, full_rewritten_text)
            ats_result = await self._evaluate_ats(full_rewritten_text, jd_requirements, generation.job_description_text)
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

        generation, user, original_text, sections, repos, original_pdf = await self._load_context()
        is_fallback = bool(sections.get("_fallback")) or (not sections.get("skills") and not sections.get("projects"))
        if is_fallback:
            yield {"event": "warning", "data": json.dumps({"message": "Could not detect Skills/Projects sections — using full resume text"})}
        generation.status = "running"
        max_iter = ats_max_iterations if ats_max_iterations is not None else settings.ats_max_iterations
        try:
            max_iter = max(ATS_MIN_ITERATIONS, min(ATS_MAX_ITERATIONS_CAP, int(max_iter)))
        except Exception:
            max_iter = settings.ats_max_iterations
        threshold = int(ats_threshold)
        generation.ats_threshold = threshold
        generation.ats_max_iterations = max_iter
        await self.db.commit()
        out: dict = {}
        async for event in self._run_steps_1_3(generation, repos, sections, out):
            yield event
        jd_requirements = out["jd_requirements"]
        jd_req_dict = out["jd_req_dict"]
        ranked_projects = out["ranked_projects"]
        writer = out["writer"]
        new_skills = out["new_skills"]
        new_projects = out["new_projects"]
        full_rewritten_text = out["full_rewritten_text"]
        yield {"event": "step-start", "data": json.dumps({"step": "ats_checker", "message": "Running deterministic ATS compatibility audit..."})}
        pdf_bytes = await self._render_pdf_bytes(original_pdf, new_skills, new_projects, full_rewritten_text)
        ats_result = await self._evaluate_ats(full_rewritten_text, jd_requirements, generation.job_description_text)
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
            missing, warnings = _loop_feedback(ats_result.details)
            feedback = f"ATS score {scores[-1]}/{threshold}; missing keywords: {', '.join(str(m) for m in missing[:10]) if missing else 'none'}; warnings: {'; '.join(str(w) for w in warnings[:5]) if warnings else 'none'}"
            yield {"event": "step-start", "data": json.dumps({"step": "resume_writer", "message": f"Refining resume (iteration {iteration}/{max_iter})..."})}
            rewritten_sections = await writer.run(skills_section=new_skills, projects_section=new_projects, jd_requirements=jd_req_dict, ranked_projects=ranked_projects, llm=self.llm, debug_dir=self.debug_dir, ats_feedback=feedback)
            new_skills = rewritten_sections.get("skills", "").strip() or new_skills
            new_projects = rewritten_sections.get("projects", "").strip() or new_projects
            full_rewritten_text = replace_sections_in_text(original_text, new_skills, new_projects)
            yield {"event": "step-done", "data": json.dumps({"step": "resume_writer", "summary": f"Refined Skills/Projects (iteration {iteration})"})}
            pdf_bytes = await self._render_pdf_bytes(original_pdf, new_skills, new_projects, full_rewritten_text)
            ats_result = await self._evaluate_ats(full_rewritten_text, jd_requirements, generation.job_description_text)
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
