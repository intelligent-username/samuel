from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ATSResult(BaseModel):
    score: int = Field(ge=0, le=100)
    details: dict | None = None
    raw_report: str | None = None

    model_config = {"extra": "forbid"}


class ATEvaluationError(Exception):
    def __init__(self, message: str = "ATS evaluation failed") -> None:
        super().__init__(message)

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else "ATS evaluation failed"


class ATSProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def evaluate(
        self,
        pdf_bytes: bytes,
        job_description: str,
        resume_text: str | None = None,
    ) -> ATSResult: ...
