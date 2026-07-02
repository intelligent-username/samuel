from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    github_id: int
    github_username: str
    github_access_token: str


class UserUpdate(BaseModel):
    openrouter_api_key: str | None = None


class UserResponse(BaseModel):
    id: UUID
    github_id: int
    github_username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RepositoryResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    stars: int
    languages: dict[str, Any] | None = None
    topics: list[str] | None = None
    last_push: datetime | None = None
    last_fetched_at: datetime

    model_config = {"from_attributes": True}


class ResumeUpload(BaseModel):
    original_filename: str
    extracted_text: str


class ResumeResponse(BaseModel):
    id: UUID
    original_filename: str
    extracted_text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    resume_id: UUID
    job_description: str = Field(..., min_length=10)


class GenerationResponse(BaseModel):
    id: UUID
    status: str
    rewritten_resume_text: str | None = None
    ats_report: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class JDRequirements(BaseModel):
    hard_requirements: list[str]
    preferred_skills: list[str]
    seniority_level: str
    red_flags: list[str]
    keywords: list[str]


class RankedProject(BaseModel):
    repo_id: UUID
    name: str
    relevance_score: float
    match_reasons: list[str]


class ATSReport(BaseModel):
    score: int = Field(..., ge=0, le=100)
    issues: list[str]
    warnings: list[str]