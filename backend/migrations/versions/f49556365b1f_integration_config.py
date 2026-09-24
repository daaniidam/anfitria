"""integration config

Revision ID: f49556365b1f
Revises: 8fe3c8635c36
Create Date: 2026-09-24 14:34:26.241784
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f49556365b1f'
down_revision: str | None = '8fe3c8635c36'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('integrations', sa.Column('config', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('integrations', 'config')
