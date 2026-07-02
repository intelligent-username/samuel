import json
from pathlib import Path

from app.utils.llm import LLMClient


class ATSCheckerSkill:
    SKILL_FILE = Path(__file__).parent / "ats_checker.md"

    async def run(
        self,
        rewritten_resume: str,
        jd_keywords: list[str],
        llm: LLMClient,
        debug_dir: Path | None = None,
    ) -> dict:
        prompt = (
            self.SKILL_FILE.read_text()
            .replace("{{REWRITTEN_RESUME}}", rewritten_resume)
            .replace("{{JD_KEYWORDS}}", json.dumps(jd_keywords, indent=2))
        )

        result = await llm.complete(prompt)
        report = json.loads(result) if isinstance(result, str) else result

        if debug_dir:
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / "step4_ats_checker.json").write_text(json.dumps(report, indent=2))

        return report
