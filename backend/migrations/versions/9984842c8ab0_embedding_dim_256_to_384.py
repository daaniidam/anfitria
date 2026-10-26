"""embedding dim 256 to 384

Revision ID: 9984842c8ab0
Revises: 7b7c7ca0b348
Create Date: 2026-10-22 10:36:32.473898
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '9984842c8ab0'
down_revision: str | None = '7b7c7ca0b348'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Cambio de modelo de embeddings (256 -> 384, MiniLM multilingüe). Los vectores
    # viejos no son compatibles con el nuevo espacio: se vacían y se re-embeben
    # (scripts/reembed.py). La columna solo existe como vector(N) en Postgres.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("UPDATE knowledge_items SET embedding = NULL")
        op.execute("ALTER TABLE knowledge_items ALTER COLUMN embedding TYPE vector(384)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("UPDATE knowledge_items SET embedding = NULL")
        op.execute("ALTER TABLE knowledge_items ALTER COLUMN embedding TYPE vector(256)")
