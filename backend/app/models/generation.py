from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class Generation(TimestampMixin, Base):
    __tablename__ = "generations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resume_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    job_description_text: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ats_report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    skill_chain_debug_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="generations")
    resume: Mapped["Resume"] = relationship(back_populates="generations")