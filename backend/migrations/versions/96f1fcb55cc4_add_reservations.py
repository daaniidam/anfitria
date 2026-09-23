"""add reservations

Revision ID: 96f1fcb55cc4
Revises: 3c8c68b3410f
Create Date: 2026-09-23 14:49:39.582834
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '96f1fcb55cc4'
down_revision: str | None = '3c8c68b3410f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('guest_name', sa.String(length=160), nullable=False),
        sa.Column('guest_ref', sa.String(length=64), nullable=False),
        sa.Column('check_in', sa.Date(), nullable=False),
        sa.Column('check_out', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_reservations_property_id'), 'reservations', ['property_id'], unique=False
    )
    op.create_index(
        op.f('ix_reservations_guest_ref'), 'reservations', ['guest_ref'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_reservations_guest_ref'), table_name='reservations')
    op.drop_index(op.f('ix_reservations_property_id'), table_name='reservations')
    op.drop_table('reservations')
