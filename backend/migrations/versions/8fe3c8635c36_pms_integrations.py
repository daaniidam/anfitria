"""pms integrations

Revision ID: 8fe3c8635c36
Revises: 0f4026521d17
Create Date: 2026-09-24 14:28:16.495743
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '8fe3c8635c36'
down_revision: str | None = '0f4026521d17'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('account', sa.String(length=120), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_integrations_org_id'), 'integrations', ['org_id'], unique=False)
    op.add_column('properties', sa.Column('external_ref', sa.String(length=64), nullable=True))
    op.create_index(
        op.f('ix_properties_external_ref'), 'properties', ['external_ref'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_properties_external_ref'), table_name='properties')
    op.drop_column('properties', 'external_ref')
    op.drop_index(op.f('ix_integrations_org_id'), table_name='integrations')
    op.drop_table('integrations')
