"""Max iterations hard cap and exit_reason tests."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.ats import ATSResult
from app.services.ats_base import ATSProvider


def _fake_gen():
    gen = MagicMock()
    gen.user_id = uuid.uuid4()
    gen.resume_id = uuid.uuid4()
    resume = MagicMock()
    resume.extracted_text = "## Skills\nPython\n\n## Projects\nP"
    resume.pdf_content = b"%PDF orig"
    gen.resume = resume
    gen.job_description_text = "python docker job description long enough text"
    gen.ats_threshold = 80
    gen.ats_max_iterations = 5
    gen.ats_exit_reason = None
    gen.ats_scores = None
    gen.iterations = None
    gen.status = "pending"
    gen.ats_report = None
    gen.rewritten_resume_text = None
    gen.pdf_content = None
    gen.completed_at = None
    return gen


def _patch_common(monkeypatch):
    from app.orchestrator import Orchestrator
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
    return Orchestrator


@pytest.mark.asyncio
async def test_hard_cap_never_exceeds(monkeypatch):
    Orchestrator = _patch_common(monkeypatch)
    fake_gen = _fake_gen()
    fake_gen.ats_max_iterations = 5
    monkeypatch.setattr(Orchestrator, "_get_generation", AsyncMock(return_value=fake_gen))
    monkeypatch.setattr(Orchestrator, "_get_repos", AsyncMock(return_value=[]))
    # disable stagnation
    monkeypatch.setattr("app.orchestrator.should_early_break", lambda scores, window=None, min_relative_gain=None: False)

    class Always60(ATSProvider):
        @property
        def provider_name(self) -> str:
            return "always60"

        async def evaluate(self, pdf_bytes, jd, resume_text=None):  # type: ignore[override]
            return ATSResult(score=60, details={})

    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    orch = Orchestrator(uuid.uuid4(), MagicMock(), db, ats_provider=Always60())
    orch.db = db
    events = [e async for e in orch.run_with_ats_loop(ats_threshold=80, ats_max_iterations=5)]
    evals = [e for e in events if e["event"] == "ats_evaluation"]
    assert len(evals) == 5
    done = [e for e in events if e["event"] == "done"][0]
    assert json.loads(done["data"])["exit_reason"] == "max_iterations"
    # verify persistence
    assert fake_gen.ats_exit_reason == "max_iterations"
    assert fake_gen.ats_scores == [60, 60, 60, 60, 60]
    assert len(fake_gen.iterations) == 5
    # no extra call beyond max
    assert len(evals) <= 5


@pytest.mark.asyncio
async def test_threshold_met_stops_early(monkeypatch):
    Orchestrator = _patch_common(monkeypatch)
    fake_gen = _fake_gen()
    fake_gen.ats_max_iterations = 6
    monkeypatch.setattr(Orchestrator, "_get_generation", AsyncMock(return_value=fake_gen))
    monkeypatch.setattr(Orchestrator, "_get_repos", AsyncMock(return_value=[]))
    monkeypatch.setattr("app.orchestrator.should_early_break", lambda *a, **kw: False)

    scores = [60, 70, 85, 90]

    class Seq(ATSProvider):
        @property
        def provider_name(self) -> str:
            return "seq"

        async def evaluate(self, pdf_bytes, jd, resume_text=None):  # type: ignore[override]
            return ATSResult(score=scores.pop(0), details={})

    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    orch = Orchestrator(uuid.uuid4(), MagicMock(), db, ats_provider=Seq())
    orch.db = db
    events = [e async for e in orch.run_with_ats_loop(ats_threshold=80, ats_max_iterations=6)]
    done = [e for e in events if e["event"] == "done"][0]
    assert json.loads(done["data"])["exit_reason"] == "threshold_met"
    evals = [e for e in events if e["event"] == "ats_evaluation"]
    assert len(evals) == 3  # 60,70,85 -> stop at 85


@pytest.mark.asyncio
async def test_stagnation_exit(monkeypatch):
    Orchestrator = _patch_common(monkeypatch)
    fake_gen = _fake_gen()
    fake_gen.ats_max_iterations = 6
    monkeypatch.setattr(Orchestrator, "_get_generation", AsyncMock(return_value=fake_gen))
    monkeypatch.setattr(Orchestrator, "_get_repos", AsyncMock(return_value=[]))

    # stagnation true after 4 scores with window 3
    def fake_break(scores, window=None, min_relative_gain=None):
        return len(scores) >= 4

    monkeypatch.setattr("app.orchestrator.should_early_break", fake_break)

    class Slow(ATSProvider):
        @property
        def provider_name(self) -> str:
            return "slow"

        async def evaluate(self, pdf_bytes, jd, resume_text=None):  # type: ignore[override]
            return ATSResult(score=71, details={})

    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    orch = Orchestrator(uuid.uuid4(), MagicMock(), db, ats_provider=Slow())
    orch.db = db
    events = [e async for e in orch.run_with_ats_loop(ats_threshold=80, ats_max_iterations=6)]
    done = [e for e in events if e["event"] == "done"][0]
    assert json.loads(done["data"])["exit_reason"] == "stagnation"
    assert any(e["event"] == "ats_stagnation" for e in events)
