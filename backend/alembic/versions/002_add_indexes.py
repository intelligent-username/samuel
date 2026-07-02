"""Add performance indexes

Revision ID: 002
Revises: 001
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # repositories: most queries filter by user_id; ordering by last_push
    op.create_index("ix_repositories_user_id", "repositories", ["user_id"])
    op.create_index("ix_repositories_user_id_last_push", "repositories", ["user_id", "last_push"])
    # resumes: filter by user_id
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])
    # generations: filter by user_id, order by created_at
    op.create_index("ix_generations_user_id", "generations", ["user_id"])
    op.create_index("ix_generations_user_id_created_at", "generations", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_generations_user_id_created_at", table_name="generations")
    op.drop_index("ix_generations_user_id", table_name="generations")
    op.drop_index("ix_resumes_user_id", table_name="resumes")
    op.drop_index("ix_repositories_user_id_last_push", table_name="repositories")
    op.drop_index("ix_repositories_user_id", table_name="repositories")
