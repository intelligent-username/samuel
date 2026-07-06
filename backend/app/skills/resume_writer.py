import json
import logging
from pathlib import Path

from app.utils.llm import LLMClient

logger = logging.getLogger(__name__)

SKILL_FILE = Path(__file__).parent / "resume_writer.md"


class ResumeWriterSkill:
    """Rewrite the skills and projects sections of a resume to align with a job description."""

    async def run(
        self,
        skills_section: str,
        projects_section: str,
        jd_requirements: dict,
        ranked_projects: list[dict],
        llm: LLMClient,
        debug_dir: Path | None = None,
    ) -> dict:
        """Generate rewritten skills and projects sections optimized for the job.

        Args:
            skills_section: The original skills section text from the resume.
            projects_section: The original projects section text from the resume.
            jd_requirements: Structured requirements from JD Parser.
            ranked_projects: Ranked repositories from Project Matcher.
            llm: An initialized LLM client.
            debug_dir: Optional directory for debug output.

        Returns:
            A dict with 'skills' and 'projects' rewritten strings.
        """
        prompt = (
            SKILL_FILE.read_text()
            .replace("{{SKILLS_SECTION}}", skills_section)
            .replace("{{PROJECTS_SECTION}}", projects_section)
            .replace("{{JD_REQUIREMENTS}}", json.dumps(jd_requirements, indent=2))
            .replace("{{RANKED_PROJECTS}}", json.dumps(ranked_projects, indent=2))
        )
        result = await llm.complete(prompt)

        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                result = {"skills": result, "projects": ""}
        elif isinstance(result, dict):
            result = {"skills": result.get("skills", ""), "projects": result.get("projects", "")}
        else:
            result = {"skills": str(result), "projects": ""}

        if debug_dir:
            debug_path = Path(debug_dir) / "step3_resume_writer.txt"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(f"PROMPT:\n{prompt}\n\nRESPONSE:\n{result}")

        return result
