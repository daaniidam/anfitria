"""Recuperación de conocimiento por similitud (RAG).

Los embeddings están L2-normalizados, así que el producto escalar es el coseno.
El cálculo se hace en Python para funcionar igual en Postgres y SQLite; en
producción, con muchos fragmentos, se cambiaría por el operador indexado de
pgvector (`embedding <=> :query`) sin tocar el resto de la lógica.
"""
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeItem

# Umbral de similitud para considerar un fragmento "relevante". Por debajo de ~0.4,
# compartir una sola palabra común (p. ej. "piso") colaría conocimiento irrelevante
# y la IA respondería con seguridad algo equivocado en vez de escalar.
RETRIEVAL_THRESHOLD = 0.40


@dataclass
class Hit:
    """Un fragmento recuperado por el RAG, con su origen y similitud (para las citas)."""

    knowledge_item_id: int
    content: str
    category: str
    score: float


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def scope_clause(property_id: int, building_id: int | None):
    """Conocimiento del piso + el compartido de su edificio (si tiene)."""
    clauses = [KnowledgeItem.property_id == property_id]
    if building_id is not None:
        clauses.append(KnowledgeItem.building_id == building_id)
    return or_(*clauses)


async def retrieve(
    session: AsyncSession,
    property_id: int,
    query_embedding: list[float],
    building_id: int | None = None,
    k: int = 3,
    threshold: float = RETRIEVAL_THRESHOLD,
) -> list[Hit]:
    rows = await session.execute(
        select(
            KnowledgeItem.id,
            KnowledgeItem.content,
            KnowledgeItem.category,
            KnowledgeItem.embedding,
        ).where(
            scope_clause(property_id, building_id),
            KnowledgeItem.embedding.isnot(None),
        )
    )
    scored = [
        Hit(item_id, content, category, _cosine(query_embedding, embedding))
        for item_id, content, category, embedding in rows.all()
        if embedding
    ]
    relevant = [hit for hit in scored if hit.score >= threshold]
    relevant.sort(key=lambda hit: hit.score, reverse=True)
    return relevant[:k]
