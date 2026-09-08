from __future__ import annotations

import json

from app.schemas.ats import ATSResult
from app.services.ats_base import ATEvaluationError, ATSProvider


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
            text = resume_text
            if (not text or not str(text).strip()) and pdf_bytes:
                try:
                    from app.services.pdf_extractor import extract_text_from_pdf

                    extracted = extract_text_from_pdf(pdf_bytes)
                    if extracted and extracted.strip():
                        text = extracted
                    else:
                        text = text or ""
                except Exception:
                    text = text or ""
            if not text or not str(text).strip():
                if not pdf_bytes and (not resume_text or not str(resume_text).strip()):
                    return ATSResult(score=0, details={"error": "empty input"}, raw_report=None)
                text = str(text or "")

            keywords = [w.strip() for w in (job_description or "").split() if len(w.strip()) > 2][:20]

            from app.services.ats import ATS

            engine = ATS()
            report = engine.evaluate(text, {"keywords": keywords, "job_description_text": job_description or ""})
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
