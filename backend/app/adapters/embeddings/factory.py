"""Selección del proveedor de embeddings según la configuración.

- `mock`  -> bolsa de palabras, sin dependencias ni descargas (tests y arranque).
- `local` -> transformer multilingüe local (fastembed/ONNX), semántica real.
"""
from functools import lru_cache

from app.adapters.embeddings.base import EmbeddingProvider
from app.adapters.embeddings.mock import MockEmbeddings
from app.config import get_settings


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    # El modelo local se carga una vez (lru_cache): evita recargarlo en cada mensaje.
    if get_settings().embed_provider == "local":
        from app.adapters.embeddings.local import LocalEmbeddings

        return LocalEmbeddings()
    return MockEmbeddings()
