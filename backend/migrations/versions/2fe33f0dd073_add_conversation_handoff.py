"""add conversation handoff

Revision ID: 2fe33f0dd073
Revises: e897997e2185
Create Date: 2026-09-23 19:27:07.789795
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '2fe33f0dd073'
down_revision: str | None = 'e897997e2185'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'conversations',
        sa.Column('handoff', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('conversations', sa.Column('assigned_to', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'conversations', 'users', ['assigned_to'], ['id'])


def downgrade() -> None:
    op.drop_column('conversations', 'assigned_to')
    op.drop_column('conversations', 'handoff')
