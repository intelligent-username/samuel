from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """Public user profile returned to the frontend."""
    id: UUID
    github_id: int
    github_username: str
    created_at: datetime

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}


class ResumeResponse(BaseModel):
    """Uploaded resume metadata (extracted text is included in the response)."""
    id: UUID
    original_filename: str
    extracted_text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    """Request body to start a new resume generation."""
    resume_id: UUID
    job_description: str = Field(..., min_length=10)


class GenerationResponse(BaseModel):
    """Generation record returned to the frontend."""
    id: UUID
    status: str
    rewritten_resume_text: str | None = None
    ats_report: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class JDRequirements(BaseModel):
    """Structured requirements extracted from a job description by the JD Parser skill."""
    hard_requirements: list[str]
    preferred_skills: list[str]
    seniority_level: str
    red_flags: list[str]
    keywords: list[str]
