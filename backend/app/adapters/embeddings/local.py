"""Embeddings locales con fastembed (sin clave, sin torch).

Modelo transformer multilingüe (ES/EN/FR/DE/IT) ejecutado con ONNX Runtime:
semántica real —entiende sinónimos y paráfrasis— sin API ni coste. El modelo se
descarga una vez y se cachea. La escala de coseno es más baja que la léxica, por
eso su umbral de recuperación propio es menor que el del mock.
"""
from __future__ import annotations

import numpy as np

from app.adapters.embeddings.base import EmbeddingProvider

_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class LocalEmbeddings(EmbeddingProvider):
    retrieval_threshold = 0.25

    def __init__(self) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(_MODEL_NAME)

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for vec in self._model.embed(list(texts)):
            arr = np.asarray(vec, dtype=float)
            norm = float(np.linalg.norm(arr))
            out.append((arr / norm).tolist() if norm else arr.tolist())
        return out
