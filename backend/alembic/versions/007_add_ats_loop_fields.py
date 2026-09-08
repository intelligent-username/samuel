"""Add ATS loop fields to generations

Revision ID: 007
Revises: 006
Create Date: 2026-09-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generations", sa.Column("ats_threshold", sa.Integer(), nullable=True, server_default="80"))
    op.add_column("generations", sa.Column("ats_max_iterations", sa.Integer(), nullable=True, server_default="6"))
    op.add_column("generations", sa.Column("ats_exit_reason", sa.Text(), nullable=True))
    op.add_column("generations", sa.Column("ats_scores", sa.JSON(), nullable=True))
    op.add_column("generations", sa.Column("iterations", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("generations", "iterations")
    op.drop_column("generations", "ats_scores")
    op.drop_column("generations", "ats_exit_reason")
    op.drop_column("generations", "ats_max_iterations")
    op.drop_column("generations", "ats_threshold")
