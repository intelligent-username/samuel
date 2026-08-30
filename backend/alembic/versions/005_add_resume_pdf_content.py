"""Add pdf_content column to resumes table

Revision ID: 005
Revises: 004
Create Date: 2026-08-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("pdf_content", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "pdf_content")
