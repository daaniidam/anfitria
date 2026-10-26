"""Re-embebe todo el conocimiento con el proveedor de embeddings actual.

Necesario al cambiar de proveedor/modelo (los vectores viejos no son compatibles
con el nuevo espacio). Uso:

    EMBED_PROVIDER=local uv run python -m scripts.reembed
"""
import asyncio

from sqlalchemy import select

from app.adapters.embeddings.factory import get_embedding_provider
from app.db import SessionLocal
from app.models import KnowledgeItem


async def main() -> None:
    provider = get_embedding_provider()
    async with SessionLocal() as session:
        items = list((await session.execute(select(KnowledgeItem))).scalars().all())
        if not items:
            print("No hay conocimiento que re-embeber.")
            return
        vectors = provider.embed([item.content for item in items])
        for item, vector in zip(items, vectors, strict=True):
            item.embedding = vector
        await session.commit()
        print(f"Re-embebidos {len(items)} fragmentos con {type(provider).__name__}.")


if __name__ == "__main__":
    asyncio.run(main())
