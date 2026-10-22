"""Interfaz del proveedor de embeddings."""
from abc import ABC, abstractmethod

# Dimensión de los vectores (y de la columna pgvector). 384 = MiniLM multilingüe;
# el mock hashea en este mismo número de cubos, así que ambos conviven en la columna.
EMBEDDING_DIM = 384

# Umbral de similitud por defecto (el del mock). Cada proveedor puede ajustarlo:
# la escala de coseno depende del modelo de embeddings.
DEFAULT_RETRIEVAL_THRESHOLD = 0.40


class EmbeddingProvider(ABC):
    """Convierte textos en vectores para el RAG."""

    dim: int = EMBEDDING_DIM
    # Por debajo de este coseno, un fragmento no se considera relevante.
    retrieval_threshold: float = DEFAULT_RETRIEVAL_THRESHOLD

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...
