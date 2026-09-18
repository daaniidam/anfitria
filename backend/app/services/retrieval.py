"""Recuperación de conocimiento por similitud (RAG).

Los embeddings están L2-normalizados, así que el producto escalar es el coseno.
El cálculo se hace en Python para funcionar igual en Postgres y SQLite; en
producción, con muchos fragmentos, se cambiaría por el operador indexado de
pgvector (`embedding <=> :query`) sin tocar el resto de la lógica.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeItem

RETRIEVAL_THRESHOLD = 0.25


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


async def retrieve(
    session: AsyncSession,
    property_id: int,
    query_embedding: list[float],
    k: int = 3,
    threshold: float = RETRIEVAL_THRESHOLD,
) -> list[tuple[str, float]]:
    rows = await session.execute(
        select(KnowledgeItem.content, KnowledgeItem.embedding).where(
            KnowledgeItem.property_id == property_id,
            KnowledgeItem.embedding.isnot(None),
        )
    )
    scored = [
        (content, _cosine(query_embedding, embedding))
        for content, embedding in rows.all()
        if embedding
    ]
    relevant = [item for item in scored if item[1] >= threshold]
    relevant.sort(key=lambda item: item[1], reverse=True)
    return relevant[:k]
