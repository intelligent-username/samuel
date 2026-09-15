"""Unification tests: adapter and orchestrator share one ATS engine."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ats import ATS, ATSContext
from app.orchestrator import build_ats_context
from app.schemas import JDRequirements
from app.services.ats_llm_adapter import ATSLLMAdapter
from app.utils.ats_normalize import normalize_list

STOPWORDS = ["looking", "join", "our", "team"]
ATOMIC_JD = {"keywords": ["python", "kubernetes"], "hard_requirements": ["python"]}


def _atomic_reqs() -> JDRequirements:
    return JDRequirements(
        hard_requirements=["python"],
        preferred_skills=["kubernetes"],
        seniority_level="mid",
        red_flags=[],
        keywords=["python", "kubernetes"],
        experience_requirements=[],
        education_requirements=[],
        aliases={},
    )


def _resume() -> str:
    return (
        "John Doe\njohn@example.com\n+1 555-0100\n"
        "## Skills\nPython, Kubernetes, Docker\n"
        "## Projects\n- Deployed Python service on Kubernetes\n"
        "## Experience\nSoftware Engineer\n"
        "## Education\nBS Computer Science\n"
    )


def _missing_all(details: dict) -> list[str]:
    missing = list(details.get("missing_keywords") or [])
    breakdown = (details.get("breakdown") or {}).get("keyword_coverage") or {}
    missing += list((breakdown.get("details") or {}).get("missing") or [])
    return [str(m).lower() for m in missing]


@pytest.mark.asyncio
async def test_adapter_excludes_stopwords():
    adapter = ATSLLMAdapter()
    resume = "Python developer with Docker experience. " + _resume()
    result = await adapter.evaluate(b"", "looking join our team python", resume)
    missing = _missing_all(result.details or {})
    for stop in STOPWORDS:
        assert stop not in missing
    ctx_keywords = normalize_list(["looking join our team python"])
    assert ctx_keywords == ["python"]


@pytest.mark.asyncio
async def test_adapter_matches_direct_ats_score():
    jd = "Senior Python developer with Kubernetes experience"
    resume = _resume()
    adapter = ATSLLMAdapter()
    adapted = await adapter.evaluate(b"", jd, resume)
    ctx = ATSContext(keywords=normalize_list([jd]), job_description_text=jd)
    direct = ATS().evaluate(resume, ctx)
    assert adapted.score == direct["score"]
    assert (adapted.details or {})["missing_keywords"] == direct["missing_keywords"]


@pytest.mark.asyncio
async def test_orchestrator_evaluate_matches_adapter():
    from app.orchestrator import Orchestrator

    req = _atomic_reqs()
    resume = _resume()
    db = MagicMock()
    db.commit = AsyncMock()
    orch = Orchestrator(uuid.uuid4(), MagicMock(), db, ats_provider=MagicMock())
    first = await orch._evaluate_ats(resume, req, "python kubernetes")
    second = await orch._evaluate_ats(resume, req, "python kubernetes")
    assert first.score == second.score
    adapter = ATSLLMAdapter()
    adapted = await adapter.evaluate(b"", "python kubernetes", resume)
    assert first.score == adapted.score


def test_build_ats_context_atomic_no_stopwords():
    req = _atomic_reqs()
    ctx = build_ats_context(req, "looking join our team python kubernetes")
    assert ctx.keywords == ["python", "kubernetes"]
    for stop in STOPWORDS:
        assert stop not in [k.lower() for k in ctx.keywords]
    assert ATOMIC_JD["keywords"] == ctx.keywords[:2]
