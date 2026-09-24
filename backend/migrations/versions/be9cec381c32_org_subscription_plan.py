"""org subscription plan

Revision ID: be9cec381c32
Revises: f49556365b1f
Create Date: 2026-09-24 19:27:26.053251
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'be9cec381c32'
down_revision: str | None = 'f49556365b1f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'organizations',
        sa.Column('plan', sa.String(length=16), nullable=False, server_default='free'),
    )


def downgrade() -> None:
    op.drop_column('organizations', 'plan')
