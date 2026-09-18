"""Proveedor de IA simulado (sin clave). Determinista, para la demo y los tests.

Detecta idioma (ES/EN) de forma sencilla, busca el fragmento de conocimiento
más relevante por solapamiento de palabras y compone una respuesta. La confianza
sube cuando encuentra conocimiento que encaja.
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


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if len(w) > 2}


def _best_knowledge(text: str, knowledge: list[str]) -> tuple[str | None, float]:
    q = _tokens(text)
    best, best_score = None, 0.0
    for item in knowledge:
        overlap = len(q & _tokens(item))
        if overlap > best_score:
            best, best_score = item, float(overlap)
    return best, best_score


class MockAI(AIProvider):
    async def generate_reply(self, context: AIContext) -> GeneratedReply:
        language = detect_language(context.guest_text, context.default_language)
        best, score = _best_knowledge(context.guest_text, context.knowledge)

        if best:
            confidence = min(0.6 + 0.1 * score, 0.95)
            if language == "en":
                text = f"Hi! Here's what you need: {best}"
            else:
                text = f"¡Hola! Aquí tienes la información: {best}"
        else:
            confidence = 0.35
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
