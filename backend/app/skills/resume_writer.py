import json
from pathlib import Path

from app.utils.llm import LLMClient


class ResumeWriterSkill:
    SKILL_FILE = Path(__file__).parent / "resume_writer.md"

    async def run(
        self,
        skills_text: str,
        projects_text: str,
        jd_requirements: dict,
        ranked_projects: list[dict],
        llm: LLMClient,
        debug_dir: Path | None = None,
    ) -> dict[str, str]:
        prompt = (
            self.SKILL_FILE.read_text()
            .replace("{{SKILLS_SECTION}}", skills_text)
            .replace("{{PROJECTS_SECTION}}", projects_text)
            .replace("{{JD_REQUIREMENTS}}", json.dumps(jd_requirements, indent=2))
            .replace("{{RANKED_PROJECTS}}", json.dumps(ranked_projects, indent=2))
        )

        result = await llm.complete(prompt)
        raw = str(result).strip()

        if debug_dir:
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / "step3_resume_writer.txt").write_text(raw)

        try:
            # Strip markdown code fences if present
            cleaned = raw
            if "```" in cleaned:
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            parsed = json.loads(cleaned.strip())
            return {"skills": parsed.get("skills", ""), "projects": parsed.get("projects", "")}
        except (json.JSONDecodeError, KeyError):
            return {"skills": raw, "projects": ""}
