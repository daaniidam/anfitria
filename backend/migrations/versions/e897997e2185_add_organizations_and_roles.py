"""add organizations and roles

Revision ID: e897997e2185
Revises: 96f1fcb55cc4
Create Date: 2026-09-23 19:18:52.563886
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e897997e2185'
down_revision: str | None = '96f1fcb55cc4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('users', sa.Column('org_id', sa.Integer(), nullable=True))
    op.add_column(
        'users', sa.Column('role', sa.String(length=16), nullable=False, server_default='owner')
    )
    op.create_index(op.f('ix_users_org_id'), 'users', ['org_id'], unique=False)
    op.create_foreign_key(None, 'users', 'organizations', ['org_id'], ['id'])

    for table in ('properties', 'buildings', 'notifications'):
        op.add_column(table, sa.Column('org_id', sa.Integer(), nullable=True))
        op.create_index(op.f(f'ix_{table}_org_id'), table, ['org_id'], unique=False)
        op.create_foreign_key(None, table, 'organizations', ['org_id'], ['id'])

    # Backfill: una organización por usuario existente (queda como propietario), y
    # los pisos/edificios/avisos heredan la org de su dueño. (Postgres.)
    op.execute(
        """
        DO $$
        DECLARE r RECORD; new_org_id INT;
        BEGIN
          FOR r IN SELECT id, name FROM users WHERE org_id IS NULL LOOP
            INSERT INTO organizations (name, created_at) VALUES (r.name, now())
              RETURNING id INTO new_org_id;
            UPDATE users SET org_id = new_org_id, role = 'owner' WHERE id = r.id;
          END LOOP;
        END $$;
        """
    )
    op.execute(
        "UPDATE properties p SET org_id = u.org_id FROM users u "
        "WHERE p.owner_id = u.id AND p.org_id IS NULL"
    )
    op.execute(
        "UPDATE buildings b SET org_id = u.org_id FROM users u "
        "WHERE b.owner_id = u.id AND b.org_id IS NULL"
    )
    op.execute(
        "UPDATE notifications n SET org_id = u.org_id FROM users u "
        "WHERE n.owner_id = u.id AND n.org_id IS NULL"
    )


def downgrade() -> None:
    for table in ('notifications', 'buildings', 'properties'):
        op.drop_index(op.f(f'ix_{table}_org_id'), table_name=table)
        op.drop_column(table, 'org_id')
    op.drop_index(op.f('ix_users_org_id'), table_name='users')
    op.drop_column('users', 'role')
    op.drop_column('users', 'org_id')
    op.drop_table('organizations')
