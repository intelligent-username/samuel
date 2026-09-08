"""PDF regeneration per iteration tests."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.ats import ATSResult
from app.services.ats_base import ATEvaluationError, ATSProvider


def _gen():
    gen = MagicMock()
    gen.user_id = uuid.uuid4()
    gen.resume_id = uuid.uuid4()
    resume = MagicMock()
    resume.extracted_text = "## Skills\nPython\n\n## Projects\nP"
    resume.pdf_content = b"%PDF orig"
    gen.resume = resume
    gen.job_description_text = "python docker job description long enough text"
    gen.ats_threshold = 80
    gen.ats_max_iterations = 3
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
async def test_pdf_regen_each_iteration(monkeypatch):
    from app.orchestrator import Orchestrator
    from app.skills.jd_parser import JDParserSkill
    from app.skills.project_matcher import ProjectMatcherSkill
    from app.skills.resume_writer import ResumeWriterSkill

    fake_gen = _gen()
    monkeypatch.setattr(Orchestrator, "_get_generation", AsyncMock(return_value=fake_gen))
    monkeypatch.setattr(Orchestrator, "_get_repos", AsyncMock(return_value=[]))

    mock_jd = MagicMock()
    mock_jd.keywords = ["python"]
    mock_jd.model_dump.return_value = {"keywords": ["python"]}
    monkeypatch.setattr(JDParserSkill, "run", AsyncMock(return_value=mock_jd))
    monkeypatch.setattr(ProjectMatcherSkill, "run", AsyncMock(return_value=[]))
    monkeypatch.setattr(ResumeWriterSkill, "run", AsyncMock(return_value={"skills": "s", "projects": "p"}))
    monkeypatch.setattr("app.orchestrator.extract_sections", lambda t: {"skills": "s", "projects": "p"})
    monkeypatch.setattr("app.orchestrator.replace_sections_in_text", lambda t, s, p: t)

    rendered = []

    def fake_rewrite(orig, md):
        rendered.append(md)
        return b"%PDF-" + str(len(rendered)).encode()

    monkeypatch.setattr("app.orchestrator.rewrite_pdf_layout", fake_rewrite)
    monkeypatch.setattr("app.orchestrator.should_early_break", lambda *a, **kw: False)

    scores = [60, 70, 85]
    seen_pdfs = []

    class Provider(ATSProvider):
        @property
        def provider_name(self) -> str:
            return "pdfcheck"

        async def evaluate(self, pdf_bytes, jd, resume_text=None):  # type: ignore[override]
            assert pdf_bytes.startswith(b"%PDF")
            seen_pdfs.append(pdf_bytes)
            return ATSResult(score=scores.pop(0), details={})

    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    orch = Orchestrator(uuid.uuid4(), MagicMock(), db, ats_provider=Provider())
    orch.db = db
    events = [e async for e in orch.run_with_ats_loop(ats_threshold=80, ats_max_iterations=3)]
    assert len(rendered) == 3  # initial + 2 retries => 3 renders
    assert len(seen_pdfs) == 3
    assert fake_gen.pdf_content == seen_pdfs[-1]
    assert fake_gen.pdf_content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_atevaluation_error_graceful(monkeypatch):
    from app.orchestrator import Orchestrator
    from app.skills.jd_parser import JDParserSkill
    from app.skills.project_matcher import ProjectMatcherSkill
    from app.skills.resume_writer import ResumeWriterSkill

    fake_gen = _gen()
    fake_gen.ats_max_iterations = 3
    monkeypatch.setattr(Orchestrator, "_get_generation", AsyncMock(return_value=fake_gen))
    monkeypatch.setattr(Orchestrator, "_get_repos", AsyncMock(return_value=[]))
    mock_jd = MagicMock()
    mock_jd.keywords = ["python"]
    mock_jd.model_dump.return_value = {"keywords": ["python"]}
    monkeypatch.setattr(JDParserSkill, "run", AsyncMock(return_value=mock_jd))
    monkeypatch.setattr(ProjectMatcherSkill, "run", AsyncMock(return_value=[]))
    monkeypatch.setattr(ResumeWriterSkill, "run", AsyncMock(return_value={"skills": "s", "projects": "p"}))
    monkeypatch.setattr("app.orchestrator.extract_sections", lambda t: {"skills": "s", "projects": "p"})
    monkeypatch.setattr("app.orchestrator.replace_sections_in_text", lambda t, s, p: t)
    monkeypatch.setattr("app.orchestrator.rewrite_pdf_layout", lambda o, m: b"%PDF")
    monkeypatch.setattr("app.orchestrator.should_early_break", lambda *a, **kw: False)

    call_count = 0

    class Flaky(ATSProvider):
        @property
        def provider_name(self) -> str:
            return "flaky"

        async def evaluate(self, pdf_bytes, jd, resume_text=None):  # type: ignore[override]
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ATEvaluationError("boom")
            return ATSResult(score=60 if call_count < 3 else 85, details={})

    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    orch = Orchestrator(uuid.uuid4(), MagicMock(), db, ats_provider=Flaky())
    orch.db = db
    events = [e async for e in orch.run_with_ats_loop(ats_threshold=80, ats_max_iterations=3)]
    # second evaluation should be score 0 due to ATEvaluationError handling
    evals = [e for e in events if e["event"] == "ats_evaluation"]
    assert len(evals) == 3
    second = json.loads(evals[1]["data"])
    assert second["score"] == 0
    # loop continued, final done still emitted
    done = [e for e in events if e["event"] == "done"][0]
    assert "exit_reason" in json.loads(done["data"])


@pytest.mark.asyncio
async def test_weasyprint_fallback(monkeypatch):
    from app.orchestrator import Orchestrator
    from app.skills.jd_parser import JDParserSkill
    from app.skills.project_matcher import ProjectMatcherSkill
    from app.skills.resume_writer import ResumeWriterSkill

    fake_gen = _gen()
    fake_gen.resume.pdf_content = None  # force weasy path
    # need fallback asset not to interfere: patch render to raise ImportError first then succeed via resume_text path
    monkeypatch.setattr(Orchestrator, "_get_generation", AsyncMock(return_value=fake_gen))
    monkeypatch.setattr(Orchestrator, "_get_repos", AsyncMock(return_value=[]))
    mock_jd = MagicMock()
    mock_jd.keywords = ["python"]
    mock_jd.model_dump.return_value = {"keywords": ["python"]}
    monkeypatch.setattr(JDParserSkill, "run", AsyncMock(return_value=mock_jd))
    monkeypatch.setattr(ProjectMatcherSkill, "run", AsyncMock(return_value=[]))
    monkeypatch.setattr(ResumeWriterSkill, "run", AsyncMock(return_value={"skills": "s", "projects": "p"}))
    monkeypatch.setattr("app.orchestrator.extract_sections", lambda t: {"skills": "s", "projects": "p"})
    monkeypatch.setattr("app.orchestrator.replace_sections_in_text", lambda t, s, p: t)
    # simulate missing weasyprint on first call then success via fallback orig pdf
    import app.services.pdf_renderer as pr

    original_render = pr.render_resume_to_pdf

    def fake_render(text):
        raise RuntimeError("weasyprint not installed")

    monkeypatch.setattr("app.services.pdf_renderer.render_resume_to_pdf", fake_render)
    monkeypatch.setattr("app.orchestrator.should_early_break", lambda *a, **kw: False)

    class Simple(ATSProvider):
        @property
        def provider_name(self) -> str:
            return "simple"

        async def evaluate(self, pdf_bytes, jd, resume_text=None):  # type: ignore[override]
            # when weasy fails, pdf_bytes may be None -> adapter should handle via resume_text
            # orchestrator passes b"" then evaluate returns score via fallback
            return ATSResult(score=90, details={})

    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    orch = Orchestrator(uuid.uuid4(), MagicMock(), db, ats_provider=Simple())
    orch.db = db
    events = [e async for e in orch.run_with_ats_loop(ats_threshold=80, ats_max_iterations=3)]
    done = [e for e in events if e["event"] == "done"][0]
    assert json.loads(done["data"])["exit_reason"] == "threshold_met"
