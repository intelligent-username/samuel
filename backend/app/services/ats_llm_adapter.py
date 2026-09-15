from __future__ import annotations

import asyncio
import json

from app.ats import ATS, ATSContext
from app.schemas.ats import ATSResult
from app.services.ats_base import ATEvaluationError, ATSProvider
from app.utils.ats_normalize import normalize_list


def _build_context(job_description: str | None) -> ATSContext:
    keywords = normalize_list([job_description] if job_description else [])
    return ATSContext(keywords=keywords, job_description_text=job_description or "")


async def _resolve_text(pdf_bytes: bytes, resume_text: str | None) -> str:
    if resume_text and resume_text.strip():
        return resume_text
    if not pdf_bytes:
        return resume_text or ""
    try:
        from app.services.pdf_extractor import extract_text_from_pdf

        extracted = await asyncio.to_thread(extract_text_from_pdf, pdf_bytes)
        if extracted and extracted.strip():
            return extracted
    except Exception:
        pass
    return resume_text or ""


class ATSLLMAdapter(ATSProvider):
    @property
    def provider_name(self) -> str:
        return "llm"

    async def evaluate(
        self,
        pdf_bytes: bytes,
        job_description: str,
        resume_text: str | None = None,
    ) -> ATSResult:
        try:
            text = await _resolve_text(pdf_bytes, resume_text)
            if not text or not text.strip():
                return ATSResult(score=0, details={"error": "empty input"}, raw_report=None)
            report = ATS().evaluate(text, _build_context(job_description))
            score = int(report.get("score", 0))
            score = max(0, min(100, score))
            details = {
                "issues": report.get("issues", []),
                "warnings": report.get("warnings", []),
                "missing_keywords": report.get("missing_keywords", []),
                "breakdown": report.get("breakdown", {}),
            }
            return ATSResult(score=score, details=details, raw_report=json.dumps(report))
        except ATEvaluationError:
            raise
        except Exception as e:
            raise ATEvaluationError("ATS evaluation failed") from e
