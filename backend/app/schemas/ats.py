from typing import Literal

from pydantic import BaseModel, Field

from app.services.ats_base import ATSResult

__all__ = ["ATSResult", "ExitReason", "IterationRecord", "LoopResult"]

ExitReason = Literal["threshold_met", "stagnation", "max_iterations"]


class IterationRecord(BaseModel):
    iteration: int = Field(ge=1)
    score: int = Field(ge=0, le=100)
    details: dict | None = None

    model_config = {"extra": "forbid"}


class LoopResult(BaseModel):
    final_resume_text: str
    final_pdf_bytes: bytes | None = Field(default=None, exclude=True)
    final_score: int = Field(ge=0, le=100)
    iterations: list[IterationRecord]
    exit_reason: ExitReason

    model_config = {"extra": "forbid"}
