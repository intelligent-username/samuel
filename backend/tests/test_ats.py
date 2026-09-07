import pytest
from app.ats import ATS, ATSCriterion, ATSContext, CriterionResult, KeywordMatchCriterion, SectionHeaderCriterion


def test_keyword_match_criterion_full():
    criterion = KeywordMatchCriterion()
    ctx = ATSContext(
        keywords=["Python", "FastAPI", "Docker", "PostgreSQL"],
        hard_requirements=["Python"],
    )
    resume = "Built production backend services with Python, FastAPI, Docker, and PostgreSQL."
    result = criterion.evaluate(resume, ctx)
    assert result.score == 100.0
    assert result.passed is True
    assert len(result.details["matched"]) == 4
    assert len(result.details["missing"]) == 0
    assert len(result.issues) == 0


def test_keyword_match_criterion_partial():
    criterion = KeywordMatchCriterion()
    ctx = ATSContext(
        keywords=["Python", "Kubernetes", "AWS"],
        hard_requirements=["Kubernetes"],
        preferred_skills=["AWS"],
    )
    resume = "Experienced with Python development."
    result = criterion.evaluate(resume, ctx)
    assert result.score == 33.3
    assert result.passed is False
    assert "Kubernetes" in result.details["missing"]
    assert any("Kubernetes" in iss for iss in result.issues)
    assert any("AWS" in w for w in result.warnings)


def test_ats_class_evaluation():
    engine = ATS()
    res = engine.evaluate(
        resume_text="Experienced in Python and C++.",
        context={
            "keywords": ["Python", "C++", "Docker"],
            "hard_requirements": ["Python"],
        },
    )
    assert "score" in res
    assert res["score"] == 67
    assert "Docker" in res["missing_keywords"]
    assert "keyword_coverage" in res["breakdown"]


def test_ats_custom_criterion_registration():
    class CustomLengthCriterion(ATSCriterion):
        name = "length_check"
        weight = 2.0

        def evaluate(self, resume_text: str, context: ATSContext) -> CriterionResult:
            passed = len(resume_text) > 10
            return CriterionResult(
                criterion_name=self.name,
                score=100.0 if passed else 0.0,
                passed=passed,
            )

    engine = ATS([KeywordMatchCriterion()])
    engine.add_criterion(CustomLengthCriterion())
    assert len(engine.criteria) == 2

    res = engine.evaluate("Short text", {"keywords": []})
    assert "length_check" in res["breakdown"]
