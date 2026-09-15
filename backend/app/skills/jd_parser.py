import asyncio
import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from app.schemas import JDRequirements
from app.utils.ats_normalize import ALIAS_MAP, normalize_list, resolve_alias
from app.utils.llm import LLMClient, extract_json

logger = logging.getLogger(__name__)

SKILL_FILE = Path(__file__).parent / "jd_parser.md"


@lru_cache(maxsize=4)
def _load_prompt_cached(path_str: str) -> str:
    return Path(path_str).read_text(encoding="utf-8")


try:
    _PROMPT_TEMPLATE = SKILL_FILE.read_text(encoding="utf-8")
except OSError:
    _PROMPT_TEMPLATE = ""


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
        template = _PROMPT_TEMPLATE or _load_prompt_cached(str(SKILL_FILE))
        prompt = template.replace("{{JD_TEXT}}", jd_text)
        result = await llm.complete(prompt, response_model=JDRequirements)
        normed = _coerce_result(result)
        if debug_dir:
            debug_path = Path(debug_dir) / "step1_jd_parser.json"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"prompt": prompt, "response": normed.model_dump()}
            await asyncio.to_thread(debug_path.write_text, json.dumps(payload, indent=2))
        return normed


def _coerce_result(result: object) -> JDRequirements:
    if isinstance(result, str):
        return _from_string(result)
    if isinstance(result, dict):
        return _from_dict(result)
    if isinstance(result, JDRequirements):
        return _normalize_requirements(result)
    return _normalize_requirements(JDRequirements(**result))  # type: ignore[arg-type]


def _from_string(text: str) -> JDRequirements:
    data = extract_json(text)
    if isinstance(data, dict):
        return _from_dict(data)
    return _fallback_from_text(text)


def _from_dict(data: dict) -> JDRequirements:
    data.setdefault("hard_requirements", [])
    data.setdefault("preferred_skills", [])
    data.setdefault("seniority_level", "mid")
    data.setdefault("red_flags", [])
    data.setdefault("keywords", [])
    data.setdefault("experience_requirements", [])
    data.setdefault("education_requirements", [])
    data.setdefault("aliases", {})
    try:
        fields = JDRequirements.model_fields
        candidate = JDRequirements(**{k: data[k] for k in fields if k in data})
    except Exception as ve:
        logger.warning("JD parser fallback validation failed: %s", ve)
        raise RuntimeError(f"JD parser could not extract structured requirements: {ve}") from ve
    return _normalize_requirements(candidate)


def _fallback_from_text(text: str) -> JDRequirements:
    parts = _split_fallback(text)
    return JDRequirements(
        hard_requirements=[],
        preferred_skills=[],
        seniority_level="mid",
        red_flags=[],
        keywords=normalize_list(parts),
        experience_requirements=[],
        education_requirements=[],
        aliases=_normalize_aliases(_collect_aliases(parts, {})),
    )


def _split_fallback(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"[,;\n|]+", text or "") if p.strip()]


def _normalize_aliases(aliases: dict | None) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, value in (aliases or {}).items():
        norm_key = str(key).strip().lower()
        norm_val = resolve_alias(str(value).strip().lower())
        if norm_key and norm_val:
            clean[norm_key] = norm_val
    return clean


def _collect_aliases(raw_items: list[str], existing: dict[str, str]) -> dict[str, str]:
    found = dict(existing or {})
    for raw in raw_items:
        low = str(raw).strip().lower()
        if not low:
            continue
        tokens = set(re.findall(r"[a-z0-9+#./-]+", low))
        for key, canon in ALIAS_MAP.items():
            if " " in key:
                if key in low and key not in found:
                    found[key] = canon
            elif key in tokens and key not in found and canon != key:
                found[key] = canon
    return found


def _normalize_requirements(req: JDRequirements) -> JDRequirements:
    raw = list(req.hard_requirements or [])
    raw += list(req.preferred_skills or [])
    raw += list(req.keywords or [])
    merged = _normalize_aliases(req.aliases)
    for key, val in _collect_aliases(raw, merged).items():
        merged.setdefault(key, val)
    seniority = (req.seniority_level or "mid").strip().lower() or "mid"
    return JDRequirements(
        hard_requirements=normalize_list(req.hard_requirements),
        preferred_skills=normalize_list(req.preferred_skills),
        seniority_level=seniority,
        red_flags=[r.strip() for r in (req.red_flags or []) if str(r).strip()],
        keywords=normalize_list(req.keywords),
        experience_requirements=[e.strip() for e in (req.experience_requirements or []) if str(e).strip()],
        education_requirements=[e.strip() for e in (req.education_requirements or []) if str(e).strip()],
        aliases=merged,
    )
