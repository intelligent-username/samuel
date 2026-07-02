"""Add repository extra columns and sort indexes

Revision ID: 003
Revises: 002
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column("homepage_url", sa.String(511), nullable=True))
    op.add_column("repositories", sa.Column("forks", sa.Integer(), server_default="0", nullable=False))
    op.add_column("repositories", sa.Column("is_archived", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("repositories", sa.Column("is_private", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("repositories", sa.Column("repo_created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("repositories", sa.Column("url", sa.String(511), nullable=True))

    # index on repo_created_at for sorting
    op.create_index("ix_repositories_user_id_repo_created_at", "repositories", ["user_id", "repo_created_at"])


def downgrade() -> None:
    op.drop_index("ix_repositories_user_id_repo_created_at", table_name="repositories")
    op.drop_column("repositories", "url")
    op.drop_column("repositories", "repo_created_at")
    op.drop_column("repositories", "is_private")
    op.drop_column("repositories", "is_archived")
    op.drop_column("repositories", "forks")
    op.drop_column("repositories", "homepage_url")
