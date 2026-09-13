import asyncio
import json
import logging
from functools import lru_cache
from pathlib import Path

from app.utils.llm import LLMClient, extract_json

logger = logging.getLogger(__name__)

SKILL_FILE = Path(__file__).parent / "project_matcher.md"


@lru_cache(maxsize=4)
def _load_prompt_cached(path_str: str) -> str:
    return Path(path_str).read_text(encoding="utf-8")


try:
    _PROMPT_TEMPLATE = SKILL_FILE.read_text(encoding="utf-8")
except OSError:
    _PROMPT_TEMPLATE = ""


class ProjectMatcherSkill:
    """Match GitHub repositories against job requirements and rank by relevance."""

    async def run(
        self,
        jd_requirements: dict,
        repos: list[dict],
        llm: LLMClient,
        debug_dir: Path | None = None,
    ) -> list[dict]:
        """Rank GitHub repositories by their relevance to the job requirements.

        Args:
            jd_requirements: Structured requirements from JD Parser.
            repos: List of repository dicts with name, description, README, etc.
            llm: An initialized LLM client.
            debug_dir: Optional directory for debug output.

        Returns:
            A list of ranked repositories with relevance scores and match reasons.
        """
        repo_summaries = []
        for r in repos:
            summary = (
                f"Repo: {r.get('name', 'unknown')}\n"
                f"Stars: {r.get('stars', 0)}\n"
                f"Languages: {list((r.get('languages') or {}).keys())}\n"
                f"Topics: {r.get('topics', [])}\n"
                f"Description: {r.get('description', 'N/A')}\n"
                f"README: {(r.get('readme_text') or '')[:500]}\n"
            )
            repo_summaries.append(summary)

        prompt = (
            (_PROMPT_TEMPLATE or _load_prompt_cached(str(SKILL_FILE)))
            .replace("{{JD_REQUIREMENTS}}", json.dumps(jd_requirements, indent=2))
            .replace("{{REPOSITORIES}}", "\n---\n".join(repo_summaries))
        )
        result = await llm.complete(prompt)

        try:
            ranked = extract_json(result) if isinstance(result, str) else result
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse project matcher response: %s", e)
            ranked = []
        if not isinstance(ranked, list):
            logger.warning("Project matcher response was not a list; discarding")
            ranked = []

        if debug_dir:
            debug_path = Path(debug_dir) / "step2_project_matcher.json"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(debug_path.write_text, json.dumps({"prompt": prompt, "response": result}, indent=2))

        return ranked
