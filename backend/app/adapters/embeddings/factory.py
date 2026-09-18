"""Selección del proveedor de embeddings según la configuración."""
from app.adapters.embeddings.base import EmbeddingProvider
from app.adapters.embeddings.mock import MockEmbeddings


def get_embedding_provider() -> EmbeddingProvider:
    # En una fase futura: proveedor real (OpenAI/Voyage) según settings.
    return MockEmbeddings()
