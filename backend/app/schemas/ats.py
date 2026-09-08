from pydantic import BaseModel, Field


class ATSResult(BaseModel):
    score: int = Field(ge=0, le=100)
    details: dict | None = None
    raw_report: str | None = None

    model_config = {"extra": "forbid"}
