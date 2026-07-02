import json
from pathlib import Path

from app.utils.llm import LLMClient


class ProjectMatcherSkill:
    SKILL_FILE = Path(__file__).parent / "project_matcher.md"

    async def run(
        self,
        jd_requirements: dict,
        repos: list[dict],
        llm: LLMClient,
        debug_dir: Path | None = None,
    ) -> list[dict]:
        repo_summaries = []
        for r in repos:
            langs = ", ".join(r.get("languages", {}).keys())
            topics = ", ".join(r.get("topics", []) or [])
            readme = (r.get("readme_text") or "")[:500]
            repo_summaries.append(
                f"- {r['name']} ({r['stars']} stars) [{langs}] topics: {topics}\n"
                f"  desc: {r.get('description', '')}\n"
                f"  readme: {readme}"
            )

        prompt = (
            self.SKILL_FILE.read_text()
            .replace("{{JD_REQUIREMENTS}}", json.dumps(jd_requirements, indent=2))
            .replace("{{REPOSITORIES}}", "\n".join(repo_summaries))
        )

        result = await llm.complete(prompt)
        ranked = json.loads(result) if isinstance(result, str) else result

        if debug_dir:
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / "step2_project_matcher.json").write_text(json.dumps(ranked, indent=2))

        return ranked
