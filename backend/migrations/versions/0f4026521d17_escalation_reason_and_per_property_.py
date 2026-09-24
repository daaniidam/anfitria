"""escalation reason and per-property threshold

Revision ID: 0f4026521d17
Revises: 25da2e3992e4
Create Date: 2026-09-24 11:09:38.558555
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0f4026521d17'
down_revision: str | None = '25da2e3992e4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('drafts', sa.Column('reason', sa.String(length=24), nullable=True))
    op.add_column('properties', sa.Column('auto_answer_threshold', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('properties', 'auto_answer_threshold')
    op.drop_column('drafts', 'reason')
