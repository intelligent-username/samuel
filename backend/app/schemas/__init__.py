from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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

    model_config = {"from_attributes": True, "extra": "forbid"}


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
