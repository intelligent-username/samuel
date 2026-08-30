"""Add pdf_content column to generations table

Revision ID: 006
Revises: 005
Create Date: 2026-08-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generations", sa.Column("pdf_content", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("generations", "pdf_content")
