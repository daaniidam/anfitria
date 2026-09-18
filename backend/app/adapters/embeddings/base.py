"""Interfaz del proveedor de embeddings."""
from abc import ABC, abstractmethod

EMBEDDING_DIM = 256


class EmbeddingProvider(ABC):
    """Convierte textos en vectores para el RAG."""

    dim: int = EMBEDDING_DIM

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...
