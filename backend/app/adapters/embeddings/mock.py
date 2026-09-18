"""Embeddings simulados (sin clave): bolsa de palabras con hashing, normalizada.

Deterministas y sin dependencias externas. El coseno entre textos que comparten
vocabulario es alto, lo que basta para demostrar el RAG. Se sustituyen por un
proveedor real (OpenAI/Voyage…) cambiando `settings` sin tocar la lógica.
"""
import hashlib
import math
import re

from app.adapters.embeddings.base import EMBEDDING_DIM, EmbeddingProvider

_WORD = re.compile(r"[a-z0-9áéíóúüñ]+", re.IGNORECASE)
_STOP = {
    "los", "las", "una", "uno", "del", "que", "por", "para", "con",
    "las", "sus", "mis", "tus", "está", "esta", "este", "como", "cerca",
    "the", "and", "for", "with", "you", "your",
}


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if len(w) > 2 and w not in _STOP]


class MockEmbeddings(EmbeddingProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIM
        for token in _tokens(text):
            bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % EMBEDDING_DIM
            vector[bucket] += 1.0
        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            return vector
        return [x / norm for x in vector]
