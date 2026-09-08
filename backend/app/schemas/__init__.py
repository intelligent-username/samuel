from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class UserResponse(BaseModel):
    """Public user profile returned to the frontend."""
    id: UUID
    github_id: int
    github_username: str
    created_at: datetime

    model_config = {"from_attributes": True, "extra": "forbid"}


class RepositoryResponse(BaseModel):
    """Cached GitHub repository data returned to the frontend."""
    id: UUID
    name: str
    description: str | None = None
    stars: int
    languages: dict[str, Any] | None = None
    topics: list[str] | None = None
    last_push: datetime | None = None
    last_fetched_at: datetime
    readme_text: str | None = None
    homepage_url: str | None = None
    forks: int
    is_archived: bool
    is_private: bool
    repo_created_at: datetime | None = None
    url: str | None = None

    model_config = {"from_attributes": True, "extra": "forbid"}


class ResumeResponse(BaseModel):
    """Uploaded resume metadata (extracted text is included in the response)."""
    id: UUID
    original_filename: str
    extracted_text: str
    created_at: datetime
    sections: dict[str, str] | None = None  # preview of skills/projects split, no DB column

    model_config = {"from_attributes": True, "extra": "forbid"}


class GenerateRequest(BaseModel):
    """Request body to start a new resume generation."""
    resume_id: UUID
    job_description: str = Field(..., min_length=10, max_length=24000, description="Job description 10-24000 chars")
    ats_threshold: int | None = Field(default=None, ge=0, le=100, description="ATS target 0-100, None/0=single-pass")
    ats_max_iterations: int | None = Field(default=None, ge=5, le=7, description="ATS max iterations 5-7")

    @field_validator("ats_max_iterations", mode="before")
    @classmethod
    def _clamp_max_iter(cls, v: int | str | None) -> int | None:
        if v is None:
            return None
        try:
            iv = int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise ValueError("ats_max_iterations must be integer 5-7")
        if iv < 5 or iv > 7:
            raise ValueError("ats_max_iterations must be between 5 and 7")
        return iv

    @field_validator("job_description")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Please paste a job description")
        if len(stripped) < 10:
            raise ValueError("Job description too short (min 10 characters)")
        if len(v) > 24000 or len(stripped) > 24000:
            raise ValueError("Job description too long (max 24000 characters)")
        return stripped


class UpdateGenerationRequest(BaseModel):
    """Request body to update generation metadata (e.g. custom title)."""
    title: str = Field(..., max_length=255, description="Custom title for generation")


class GenerationResponse(BaseModel):
    """Generation record returned to the frontend."""
    id: UUID
    status: str
    job_description_text: str
    title: str | None = None
    rewritten_resume_text: str | None = None
    ats_report: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None
    ats_threshold: int | None = None
    ats_max_iterations: int | None = None
    ats_exit_reason: str | None = None
    ats_scores: list[int] | None = None
    iterations: list[dict[str, Any]] | None = None

    model_config = {"from_attributes": True, "extra": "forbid"}

    @model_validator(mode="after")
    def populate_iteration_fallbacks(self) -> "GenerationResponse":
        if not self.iterations:
            if self.ats_scores:
                self.iterations = [{"iteration": idx + 1, "score": s} for idx, s in enumerate(self.ats_scores)]
            elif self.ats_report and isinstance(self.ats_report, dict) and "score" in self.ats_report:
                self.iterations = [{"iteration": 1, "score": self.ats_report["score"]}]
        if not self.ats_scores and self.iterations:
            self.ats_scores = [it["score"] for it in self.iterations if isinstance(it, dict) and "score" in it]
        if not self.ats_exit_reason and self.status == "completed":
            self.ats_exit_reason = "threshold_met" if (self.ats_threshold and self.ats_report and self.ats_report.get("score", 0) >= self.ats_threshold) else "single_pass"
        return self


class JDRequirements(BaseModel):
    """Structured requirements extracted from a job description by the JD Parser skill."""
    hard_requirements: list[str]
    preferred_skills: list[str]
    seniority_level: str
    red_flags: list[str]
    keywords: list[str]

    model_config = {"extra": "forbid"}


class RewrittenResumeSections(BaseModel):
    """Structured rewritten sections returned by ResumeWriterSkill."""
    skills: str = Field(default="", description="Rewritten skills section")
    projects: str = Field(default="", description="Rewritten projects section")

    model_config = {"extra": "ignore"}
