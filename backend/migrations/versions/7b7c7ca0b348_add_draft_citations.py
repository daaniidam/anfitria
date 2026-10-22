"""add draft_citations

Revision ID: 7b7c7ca0b348
Revises: be9cec381c32
Create Date: 2026-10-22 10:12:09.241980
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '7b7c7ca0b348'
down_revision: str | None = 'be9cec381c32'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # RAG visible: fragmentos de conocimiento que anclaron cada borrador.
    op.create_table(
        "draft_citations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_item_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["drafts.id"]),
        sa.ForeignKeyConstraint(["knowledge_item_id"], ["knowledge_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_draft_citations_draft_id", "draft_citations", ["draft_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_draft_citations_draft_id", table_name="draft_citations")
    op.drop_table("draft_citations")
