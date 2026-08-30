from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    user: Mapped["User"] = relationship(back_populates="resumes")
    generations: Mapped[list["Generation"]] = relationship(back_populates="resume", cascade="all, delete-orphan")