import json
from pathlib import Path

from app.schemas import JDRequirements
from app.utils.llm import LLMClient


class JDParserSkill:
    SKILL_FILE = Path(__file__).parent / "jd_parser.md"

    async def run(self, jd_text: str, llm: LLMClient, debug_dir: Path | None = None) -> JDRequirements:
        prompt = self.SKILL_FILE.read_text().replace("{{JD_TEXT}}", jd_text)
        result = await llm.complete(prompt, response_model=JDRequirements)

        if debug_dir:
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / "step1_jd_parser.json").write_text(
                json.dumps(result if isinstance(result, dict) else result.model_dump(), indent=2)
            )

        return result if isinstance(result, JDRequirements) else JDRequirements(**result)
