from abc import ABC, abstractmethod

from app.schemas.ats import ATSResult


class ATEvaluationError(Exception):
    def __str__(self) -> str:
        return "ATS evaluation failed"


class ATSProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def evaluate(
        self,
        pdf_bytes: bytes,
        job_description: str,
        resume_text: str | None = None,
    ) -> ATSResult:
        ...
