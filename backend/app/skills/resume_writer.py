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
        resume_text: str,
        jd_requirements: dict,
        ranked_projects: list[dict],
        llm: LLMClient,
        debug_dir: Path | None = None,
    ) -> str:
        """Generate a rewritten resume with optimized skills and projects sections.

        Args:
            resume_text: The original full resume text.
            jd_requirements: Structured requirements from JD Parser.
            ranked_projects: Ranked repositories from Project Matcher.
            llm: An initialized LLM client.
            debug_dir: Optional directory for debug output.

        Returns:
            The rewritten resume text (only skills and projects sections modified).
        """
        prompt = (
            SKILL_FILE.read_text()
            .replace("{{ORIGINAL_RESUME}}", resume_text)
            .replace("{{JD_REQUIREMENTS}}", json.dumps(jd_requirements, indent=2))
            .replace("{{RANKED_PROJECTS}}", json.dumps(ranked_projects, indent=2))
        )
        result = await llm.complete(prompt)

        # Strip everything before the output marker
        marker = "--- REWRITTEN RESUME ---"
        if marker in result:
            result = result.split(marker, 1)[1].strip()

        if debug_dir:
            debug_path = Path(debug_dir) / "step3_resume_writer.txt"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(f"PROMPT:\n{prompt}\n\nRESPONSE:\n{result}")

        return result
