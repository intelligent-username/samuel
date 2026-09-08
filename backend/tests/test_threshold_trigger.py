"""Threshold trigger tests for orchestrator ATS loop."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.ats import ATSResult
from app.services.ats_base import ATSProvider


def _make_fake_generation():
    gen = MagicMock()
    gen.user_id = uuid.uuid4()
    gen.resume_id = uuid.uuid4()
    resume = MagicMock()
    resume.extracted_text = "## Skills\nPython\n\n## Projects\nP"
    resume.pdf_content = b"%PDF original"
    gen.resume = resume
    gen.job_description_text = "python docker job description with enough length"
    gen.ats_threshold = 80
    gen.ats_max_iterations = 6
    gen.ats_exit_reason = None
    gen.ats_scores = None
    gen.iterations = None
    gen.status = "pending"
    gen.ats_report = None
    gen.rewritten_resume_text = None
    gen.pdf_content = None
    gen.completed_at = None
    return gen


@pytest.mark.asyncio
async def test_threshold_trigger_retry_then_met(monkeypatch):
    from app.orchestrator import Orchestrator

    fake_gen = _make_fake_generation()
    fake_gen.ats_threshold = 80
    fake_gen.ats_max_iterations = 6

    monkeypatch.setattr(Orchestrator, "_get_generation", AsyncMock(return_value=fake_gen))
    monkeypatch.setattr(Orchestrator, "_get_repos", AsyncMock(return_value=[]))

    # mock skills
    from app.skills.jd_parser import JDParserSkill
    from app.skills.project_matcher import ProjectMatcherSkill
    from app.skills.resume_writer import ResumeWriterSkill

    mock_jd = MagicMock()
    mock_jd.keywords = ["python"]
    mock_jd.model_dump.return_value = {"keywords": ["python"], "hard_requirements": [], "preferred_skills": []}
    monkeypatch.setattr(JDParserSkill, "run", AsyncMock(return_value=mock_jd))
    monkeypatch.setattr(ProjectMatcherSkill, "run", AsyncMock(return_value=[]))
    monkeypatch.setattr(ResumeWriterSkill, "run", AsyncMock(return_value={"skills": "Python, Docker", "projects": "Proj A"}))

    monkeypatch.setattr("app.orchestrator.extract_sections", lambda t: {"skills": "Python", "projects": "P"})
    monkeypatch.setattr("app.orchestrator.replace_sections_in_text", lambda t, s, p: t + s + p)
    monkeypatch.setattr("app.orchestrator.rewrite_pdf_layout", lambda orig, md: b"%PDF-rendered-" + md.encode()[:10])

    # provider returns 62 then 85
    scores = [62, 85]

    class SeqProvider(ATSProvider):
        @property
        def provider_name(self) -> str:
            return "seq"

        async def evaluate(self, pdf_bytes, jd, resume_text=None):  # type: ignore[override]
            return ATSResult(score=scores.pop(0), details={"missing_keywords": ["k8s"], "warnings": []})

    provider = SeqProvider()
    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()

    orch = Orchestrator(uuid.uuid4(), MagicMock(), db, ats_provider=provider)
    orch.db = db
    events = []
    async for ev in orch.run_with_ats_loop(ats_threshold=80, ats_max_iterations=6):
        events.append(ev)

    eval_events = [e for e in events if e["event"] == "ats_evaluation"]
    assert len(eval_events) == 2
    first = json.loads(eval_events[0]["data"])
    assert first["score"] == 62
    assert first["will_retry"] is True
    second = json.loads(eval_events[1]["data"])
    assert second["score"] == 85
    assert second["will_retry"] is False
    done = [e for e in events if e["event"] == "done"][0]
    data = json.loads(done["data"])
    assert data["exit_reason"] == "threshold_met"


@pytest.mark.asyncio
async def test_threshold_exact_match_no_extra_iteration(monkeypatch):
    from app.orchestrator import Orchestrator

    fake_gen = _make_fake_generation()
    monkeypatch.setattr(Orchestrator, "_get_generation", AsyncMock(return_value=fake_gen))
    monkeypatch.setattr(Orchestrator, "_get_repos", AsyncMock(return_value=[]))
    from app.skills.jd_parser import JDParserSkill
    from app.skills.project_matcher import ProjectMatcherSkill
    from app.skills.resume_writer import ResumeWriterSkill

    mock_jd = MagicMock()
    mock_jd.keywords = ["python"]
    mock_jd.model_dump.return_value = {"keywords": ["python"]}
    monkeypatch.setattr(JDParserSkill, "run", AsyncMock(return_value=mock_jd))
    monkeypatch.setattr(ProjectMatcherSkill, "run", AsyncMock(return_value=[]))
    monkeypatch.setattr(ResumeWriterSkill, "run", AsyncMock(return_value={"skills": "s", "projects": "p"}))
    monkeypatch.setattr("app.orchestrator.extract_sections", lambda t: {"skills": "s", "projects": "p"})
    monkeypatch.setattr("app.orchestrator.replace_sections_in_text", lambda t, s, p: t)
    monkeypatch.setattr("app.orchestrator.rewrite_pdf_layout", lambda o, m: b"%PDF")

    class ExactProvider(ATSProvider):
        @property
        def provider_name(self) -> str:
            return "exact"

        async def evaluate(self, pdf_bytes, jd, resume_text=None):  # type: ignore[override]
            return ATSResult(score=80, details={})

    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    orch = Orchestrator(uuid.uuid4(), MagicMock(), db, ats_provider=ExactProvider())
    orch.db = db
    events = [e async for e in orch.run_with_ats_loop(ats_threshold=80, ats_max_iterations=6)]
    done = [e for e in events if e["event"] == "done"][0]
    assert json.loads(done["data"])["exit_reason"] == "threshold_met"
    # only one evaluation
    assert len([e for e in events if e["event"] == "ats_evaluation"]) == 1


@pytest.mark.asyncio
async def test_single_pass_when_threshold_zero(monkeypatch):
    from app.orchestrator import Orchestrator

    fake_gen = _make_fake_generation()
    monkeypatch.setattr(Orchestrator, "_get_generation", AsyncMock(return_value=fake_gen))
    monkeypatch.setattr(Orchestrator, "_get_repos", AsyncMock(return_value=[]))
    from app.skills.jd_parser import JDParserSkill
    from app.skills.project_matcher import ProjectMatcherSkill
    from app.skills.resume_writer import ResumeWriterSkill

    mock_jd = MagicMock()
    mock_jd.keywords = ["python"]
    mock_jd.model_dump.return_value = {"keywords": ["python"]}
    monkeypatch.setattr(JDParserSkill, "run", AsyncMock(return_value=mock_jd))
    monkeypatch.setattr(ProjectMatcherSkill, "run", AsyncMock(return_value=[]))
    monkeypatch.setattr(ResumeWriterSkill, "run", AsyncMock(return_value={"skills": "s", "projects": "p"}))
    monkeypatch.setattr("app.orchestrator.extract_sections", lambda t: {"skills": "s", "projects": "p"})
    monkeypatch.setattr("app.orchestrator.replace_sections_in_text", lambda t, s, p: t)
    monkeypatch.setattr("app.orchestrator.rewrite_pdf_layout", lambda o, m: b"%PDF")

    provider = MagicMock(spec=ATSProvider)
    provider.evaluate = AsyncMock(return_value=ATSResult(score=10, details={}))
    provider.provider_name = "mock"
    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    orch = Orchestrator(uuid.uuid4(), MagicMock(), db, ats_provider=provider)  # type: ignore[arg-type]
    orch.db = db
    events = [e async for e in orch.run_with_ats_loop(ats_threshold=0, ats_max_iterations=6)]
    # single evaluation
    evals = [e for e in events if e["event"] == "ats_evaluation"]
    assert len(evals) == 1
    assert provider.evaluate.call_count == 1
    done = [e for e in events if e["event"] == "done"][0]
    assert json.loads(done["data"])["exit_reason"] == "single_pass"
