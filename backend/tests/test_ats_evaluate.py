"""Tests for ATSLLMAdapter evaluate with pdf_bytes and resume_text paths."""

import json
from unittest.mock import patch

import pytest

from app.schemas.ats import ATSResult
from app.services.ats_base import ATEvaluationError
from app.services.ats_llm_adapter import ATSLLMAdapter


@pytest.mark.asyncio
async def test_adapter_resume_text_path():
    adapter = ATSLLMAdapter()
    assert adapter.provider_name == "llm"
    result = await adapter.evaluate(b"%PDF fake", "python developer", "python docker resume text")
    assert isinstance(result, ATSResult)
    assert 0 <= result.score <= 100
    assert result.details is not None
    assert "missing_keywords" in result.details
    assert "breakdown" in result.details
    assert result.raw_report is not None
    json.loads(result.raw_report)


@pytest.mark.asyncio
async def test_adapter_pdf_fallback(monkeypatch):
    def fake_extract(pdf_bytes):
        assert pdf_bytes == b"%PDF fake bytes"
        return "python docker text from pdf"

    monkeypatch.setattr("app.services.pdf_extractor.extract_text_from_pdf", fake_extract)
    adapter = ATSLLMAdapter()
    result = await adapter.evaluate(b"%PDF fake bytes", "python docker", None)
    assert 0 <= result.score <= 100
    assert result.details is not None


@pytest.mark.asyncio
async def test_adapter_empty_both():
    adapter = ATSLLMAdapter()
    result = await adapter.evaluate(b"", "jd", None)
    assert isinstance(result, ATSResult)
    assert result.score == 0
    assert result.details is not None

    result2 = await adapter.evaluate(b"", "", "")
    assert result2.score == 0


@pytest.mark.asyncio
async def test_adapter_error_sanitized():
    adapter = ATSLLMAdapter()
    secret = "SECRET_JD_CONTENT_12345"
    with patch("app.services.ats.ATS.evaluate", side_effect=RuntimeError("boom " + secret)):
        with pytest.raises(ATEvaluationError) as exc:
            await adapter.evaluate(b"", secret, "some text")
        msg = str(exc.value)
        assert secret not in msg
        assert "ATS evaluation failed" in msg


@pytest.mark.asyncio
async def test_adapter_extract_exception_falls_back(monkeypatch):
    def bad_extract(_b):
        raise RuntimeError("fitz missing")

    monkeypatch.setattr("app.services.pdf_extractor.extract_text_from_pdf", bad_extract)
    adapter = ATSLLMAdapter()
    # should not raise, fallback to empty resume_text handling
    result = await adapter.evaluate(b"%PDF", "python docker jd", None)
    assert isinstance(result, ATSResult)
    assert 0 <= result.score <= 100
