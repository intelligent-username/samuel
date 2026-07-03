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

        if debug_dir:
            debug_path = Path(debug_dir) / "step1_jd_parser.json"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(json.dumps({"prompt": prompt, "response": result.model_dump()}, indent=2))

        return result
