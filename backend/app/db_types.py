"""Tipo de columna de embedding, compatible con Postgres (pgvector) y SQLite (JSON).

En Postgres se materializa como `vector(N)` (búsqueda con pgvector); en SQLite
—que usan los tests— como JSON. Así el mismo modelo funciona en ambos.
"""
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator

from app.adapters.embeddings.base import EMBEDDING_DIM


class Embedding(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(EMBEDDING_DIM))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return [float(x) for x in value]
