"""Proveedor de IA simulado (sin clave). Determinista, para la demo y los tests.

Recibe el conocimiento ya recuperado por el RAG (los fragmentos más relevantes
del piso) y compone la respuesta en el idioma del huésped. La confianza sube con
la similitud de la recuperación; si no hubo nada relevante, responde con una
frase de espera y baja confianza (nunca inventa datos del piso).
"""
from __future__ import annotations

import re

from app.adapters.ai.base import AIContext, AIProvider, GeneratedReply

_EN_MARKERS = {
    "the", "what", "when", "where", "how", "please", "hi", "hello", "time",
    "check", "checkin", "wifi", "password", "arrive", "address", "can", "is",
}
_ES_CHARS = re.compile(r"[¿¡ñáéíóúü]", re.IGNORECASE)
_WORD = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)


def detect_language(text: str, default: str = "es") -> str:
    lower = text.lower()
    if _ES_CHARS.search(lower):
        return "es"
    words = set(_WORD.findall(lower))
    en_hits = len(words & _EN_MARKERS)
    es_hits = len(words & {"hola", "que", "como", "donde", "gracias", "hora", "cuando", "wifi"})
    if en_hits > es_hits:
        return "en"
    if es_hits > en_hits:
        return "es"
    return default


class MockAI(AIProvider):
    async def generate_reply(self, context: AIContext) -> GeneratedReply:
        language = detect_language(context.guest_text, context.default_language)

        if context.knowledge:
            best = context.knowledge[0]
            confidence = min(0.6 + 0.4 * context.retrieval_score, 0.97)
            if language == "en":
                text = f"Hi! Here's what you need: {best}"
            else:
                text = f"¡Hola! Aquí tienes la información: {best}"
        else:
            confidence = 0.3
            if language == "en":
                text = (
                    f"Thanks for reaching out to {context.property_name}. "
                    "I'll check this and get back to you shortly."
                )
            else:
                text = (
                    f"Gracias por escribir a {context.property_name}. "
                    "Lo confirmo y te respondo enseguida."
                )

        return GeneratedReply(text=text, language=language, confidence=confidence, model="mock")
