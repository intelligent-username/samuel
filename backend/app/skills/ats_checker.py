"""Deprecated: LLM-based ATS checker skill replaced by deterministic ATS module."""
from pathlib import Path
from typing import Any

from app.ats import ATS


class ATSCheckerSkill:
    """Compatibility wrapper redirecting to the deterministic ATS module."""

    async def run(
        self,
        rewritten_resume: str,
        jd_keywords: list[str],
        llm: Any = None,
        debug_dir: Path | None = None,
    ) -> dict[str, Any]:
        ats = ATS()
        return ats.evaluate(rewritten_resume, {"keywords": jd_keywords})
