import json
from pathlib import Path

from app.utils.llm import LLMClient


class ResumeWriterSkill:
    SKILL_FILE = Path(__file__).parent / "resume_writer.md"

    async def run(
        self,
        original_resume: str,
        jd_requirements: dict,
        ranked_projects: list[dict],
        llm: LLMClient,
        debug_dir: Path | None = None,
    ) -> str:
        prompt = (
            self.SKILL_FILE.read_text()
            .replace("{{ORIGINAL_RESUME}}", original_resume)
            .replace("{{JD_REQUIREMENTS}}", json.dumps(jd_requirements, indent=2))
            .replace("{{RANKED_PROJECTS}}", json.dumps(ranked_projects, indent=2))
        )

        result = await llm.complete(prompt)

        if debug_dir:
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / "step3_resume_writer.txt").write_text(str(result))

        text = str(result)
        if "--- REWRITTEN RESUME ---" in text:
            text = text.split("--- REWRITTEN RESUME ---")[1].strip()
        return text
