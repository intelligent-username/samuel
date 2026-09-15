import pytest

from app.ats import ATS, ATSContext, KeywordMatchCriterion
from app.schemas import JDRequirements
from app.skills.jd_parser import JDParserSkill
from app.utils.ats_normalize import normalize_list, normalize_skill


def _resume_text() -> str:
    return (
        "Skills\nPython, Docker\n\nProjects\nBuilt API service\n\n"
        "Experience\nBackend Engineer\n\nEducation\nBS Computer Science\n\n"
        "Contact me@example.com +1 555 123 4567\n- Did work\n" + "x " * 200
    )


def _context() -> dict:
    return {
        "keywords": ["python", "docker", "kubernetes"],
        "hard_requirements": ["python"],
        "preferred_skills": ["docker"],
    }


def test_scorer_determinism():
    engine = ATS()
    resume = _resume_text()
    first = engine.evaluate(resume, _context())
    second = engine.evaluate(resume, _context())
    assert first["score"] == second["score"]
    assert first["issues"] == second["issues"]
    assert first["warnings"] == second["warnings"]
    assert first["missing_keywords"] == second["missing_keywords"]
    assert first["breakdown"] == second["breakdown"]


def test_alias_postgres_credit():
    criterion = KeywordMatchCriterion()
    ctx = ATSContext(keywords=["postgresql"], hard_requirements=["postgresql"])
    result = criterion.evaluate("Built pipelines with postgres and SQL.", ctx)
    assert result.details["credits"]["postgresql"] >= 0.9
    assert "postgresql" in result.details["matched"]


def test_stem_microservice_credit():
    criterion = KeywordMatchCriterion()
    ctx = ATSContext(keywords=["microservices"], hard_requirements=["microservices"])
    result = criterion.evaluate("Maintained a microservice for billing.", ctx)
    assert result.details["credits"]["microservices"] >= 0.9
    assert "microservices" in result.details["matched"]


def test_fuzzy_tier_below_exact_above_miss():
    criterion = KeywordMatchCriterion()
    ctx = ATSContext(keywords=["python"], hard_requirements=["python"])
    exact = criterion.evaluate("Built tools with python for automation.", ctx)
    fuzzy = criterion.evaluate("Built tools with pythom for automation.", ctx)
    miss = criterion.evaluate("Built bridges with concrete and steel.", ctx)
    assert exact.details["credits"]["python"] == 1.0
    assert 0.0 < fuzzy.details["credits"]["python"] < 1.0
    assert miss.details["credits"]["python"] == 0.0
    assert fuzzy.score < exact.score
    assert fuzzy.score > miss.score


def test_normalize_skill_aliases():
    assert normalize_skill("  K8s ") == "kubernetes"
    assert normalize_skill("Postgres") == "postgresql"
    assert normalize_skill("JS") == "javascript"


def test_normalize_list_atomic():
    result = normalize_list(["5+ years Python", "familiarity with Kubernetes", "looking", "our"])
    assert result == ["python", "kubernetes"]


class _StringLLM:
    async def complete(self, prompt, response_model=None):
        return "5+ years Python, familiarity with Kubernetes, k8s"


class _ObjectLLM:
    async def complete(self, prompt, response_model=None):
        return JDRequirements(
            hard_requirements=["5+ years Python"],
            preferred_skills=["familiarity with Kubernetes"],
            seniority_level="mid",
            red_flags=[],
            keywords=["k8s"],
            experience_requirements=[],
            education_requirements=[],
            aliases={},
        )


@pytest.mark.asyncio
async def test_jd_atomicity_string_fallback():
    req = await JDParserSkill().run("dummy jd", _StringLLM())  # type: ignore[arg-type]
    targets = req.hard_requirements + req.preferred_skills + req.keywords
    assert "python" in targets
    assert "kubernetes" in targets
    assert req.aliases.get("k8s") == "kubernetes"
    assert "5+ years Python" not in targets
    assert not any("familiarity" in t or "years" in t for t in targets)


@pytest.mark.asyncio
async def test_jd_atomicity_object_path():
    req = await JDParserSkill().run("dummy jd", _ObjectLLM())  # type: ignore[arg-type]
    targets = req.hard_requirements + req.preferred_skills + req.keywords
    assert "python" in req.hard_requirements
    assert "kubernetes" in req.preferred_skills + req.keywords
    assert req.aliases.get("k8s") == "kubernetes"
    assert "5+ years Python" not in targets
    assert "familiarity with Kubernetes" not in targets
