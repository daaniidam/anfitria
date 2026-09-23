"""reservation source and conversation link

Revision ID: 25da2e3992e4
Revises: 2fe33f0dd073
Create Date: 2026-09-23 19:39:32.284174
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '25da2e3992e4'
down_revision: str | None = '2fe33f0dd073'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'reservations',
        sa.Column('source', sa.String(length=16), nullable=False, server_default='direct'),
    )
    op.add_column('conversations', sa.Column('reservation_id', sa.Integer(), nullable=True))
    op.create_index(
        op.f('ix_conversations_reservation_id'), 'conversations', ['reservation_id'], unique=False
    )
    op.create_foreign_key(None, 'conversations', 'reservations', ['reservation_id'], ['id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_conversations_reservation_id'), table_name='conversations')
    op.drop_column('conversations', 'reservation_id')
    op.drop_column('reservations', 'source')
