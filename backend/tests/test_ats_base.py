"""Tests for ATSProvider ABC and ATSResult validation."""

import pytest
from pydantic import ValidationError

from app.schemas.ats import ATSResult
from app.services.ats_base import ATEvaluationError, ATSProvider


def test_ats_result_valid_bounds():
    for score in (0, 50, 100):
        r = ATSResult(score=score)
        assert r.score == score
    r = ATSResult(score=42, details={"k": 1}, raw_report="raw")
    assert r.details == {"k": 1}
    assert r.raw_report == "raw"


def test_ats_result_invalid_scores():
    for bad in (150, -1, 101):
        with pytest.raises(ValidationError):
            ATSResult(score=bad)
    with pytest.raises(ValidationError):
        ATSResult(score="not-int")  # type: ignore[arg-type]


def test_ats_result_extra_forbidden():
    with pytest.raises(ValidationError):
        ATSResult(score=10, unknown="x")  # type: ignore[call-arg]


def test_ats_provider_is_abstract():
    with pytest.raises(TypeError):
        ATSProvider()  # type: ignore[abstract]
    assert hasattr(ATSProvider, "provider_name")
    assert hasattr(ATSProvider, "evaluate")


@pytest.mark.asyncio
async def test_dummy_provider():
    class Dummy(ATSProvider):
        @property
        def provider_name(self) -> str:
            return "dummy"

        async def evaluate(self, pdf_bytes, job_description, resume_text=None):  # type: ignore[override]
            return ATSResult(score=42, details={"ok": True})

    p = Dummy()
    assert p.provider_name == "dummy"
    assert isinstance(p, ATSProvider)
    r = await p.evaluate(b"%PDF", "jd", "resume")
    assert r.score == 42

    # also without resume_text
    r2 = await p.evaluate(b"%PDF", "jd")
    assert r2.score == 42


def test_atevaluation_error_sanitized():
    secret_jd = "SECRET_JD_CONTENT_123"
    try:
        raise ATEvaluationError(secret_jd)
    except ATEvaluationError as exc:
        msg = str(exc)
        assert secret_jd not in msg
        assert "ATS evaluation failed" in msg
    except Exception:
        pytest.fail("should be catchable as Exception")
    # catchable as Exception
    assert issubclass(ATEvaluationError, Exception)
