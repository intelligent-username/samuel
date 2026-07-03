import json
import logging
from pathlib import Path

from app.utils.llm import LLMClient

logger = logging.getLogger(__name__)

SKILL_FILE = Path(__file__).parent / "ats_checker.md"


class ATSCheckerSkill:
    """Evaluate a rewritten resume for ATS compatibility and generate an improvement report."""

    async def run(
        self,
        rewritten_resume: str,
        jd_keywords: list[str],
        llm: LLMClient,
        debug_dir: Path | None = None,
    ) -> dict:
        """Check ATS compatibility of the rewritten resume against JD keywords.

        Args:
            rewritten_resume: The rewritten resume text.
            jd_keywords: List of keywords extracted from the job description.
            llm: An initialized LLM client.
            debug_dir: Optional directory for debug output.

        Returns:
            ATS report dict with score, issues, warnings, and missing keywords.
        """
        prompt = (
            SKILL_FILE.read_text()
            .replace("{{REWRITTEN_RESUME}}", rewritten_resume)
            .replace("{{JD_KEYWORDS}}", json.dumps(jd_keywords))
        )
        result = await llm.complete(prompt)

        try:
            report = json.loads(result) if isinstance(result, str) else result
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse ATS checker response: %s", e)
            report = {"score": 0, "issues": ["Failed to parse ATS report"], "warnings": [], "missing_keywords": jd_keywords}

        if debug_dir:
            debug_path = Path(debug_dir) / "step4_ats_checker.json"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(json.dumps({"prompt": prompt, "response": result}, indent=2))

        return report
