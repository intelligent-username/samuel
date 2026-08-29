import json
import logging
from pathlib import Path

from app.schemas import JDRequirements
from app.utils.llm import LLMClient

logger = logging.getLogger(__name__)

SKILL_FILE = Path(__file__).parent / "jd_parser.md"


class JDParserSkill:
    """Parse a job description into structured requirements using an LLM."""

    async def run(self, jd_text: str, llm: LLMClient, debug_dir: Path | None = None) -> JDRequirements:
        """Extract structured requirements from raw job description text.

        Args:
            jd_text: The raw job description text.
            llm: An initialized LLM client.
            debug_dir: Optional directory for debug output.

        Returns:
            A JDRequirements model with extracted skills, seniority, keywords, etc.
        """
        prompt = SKILL_FILE.read_text().replace("{{JD_TEXT}}", jd_text)
        result = await llm.complete(prompt, response_model=JDRequirements)

        if isinstance(result, str):
            # LLM returned raw text — try manual extraction as fallback before failing
            from app.utils.llm import extract_json

            data = extract_json(result)
            if isinstance(data, dict):
                try:
                    # Fill missing required fields with safe defaults
                    data.setdefault("hard_requirements", [])
                    data.setdefault("preferred_skills", [])
                    data.setdefault("seniority_level", "mid")
                    data.setdefault("red_flags", [])
                    data.setdefault("keywords", [])
                    result = JDRequirements(**{k: data[k] for k in JDRequirements.model_fields if k in data})
                except Exception as ve:
                    logger.warning("JD parser fallback validation failed: %s | raw: %s", ve, result[:800])
                    raise RuntimeError(f"JD parser could not extract structured requirements: {ve}") from ve
            else:
                logger.warning("JD parser got non-JSON string: %s", result[:800])
                raise RuntimeError("JD parser could not extract structured requirements from the job description")
        if not isinstance(result, JDRequirements):
            result = JDRequirements(**result)

        if debug_dir:
            debug_path = Path(debug_dir) / "step1_jd_parser.json"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(json.dumps({"prompt": prompt, "response": result.model_dump()}, indent=2))

        return result
