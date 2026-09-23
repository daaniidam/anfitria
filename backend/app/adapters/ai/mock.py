"""Proveedor de IA simulado (sin clave). Determinista, para la demo y los tests.

Recibe el conocimiento ya recuperado por el RAG (los fragmentos más relevantes
del piso) y compone la respuesta en el idioma del huésped. Si hay contexto de
reserva y no hay conocimiento que encaje, responde con los datos de la estancia.
La confianza sube con la similitud de la recuperación; si no hay nada, escala.
"""
from __future__ import annotations

import re

from app.adapters.ai.base import AIContext, AIProvider, GeneratedReply

# Marcadores por idioma (heurística ligera; Claude real detecta de verdad).
_MARKERS = {
    "en": {"the", "what", "when", "where", "how", "please", "hi", "hello", "time",
           "check", "checkin", "wifi", "password", "arrive", "address", "can", "is", "your"},
    "es": {"hola", "que", "qué", "como", "cómo", "donde", "dónde", "gracias", "hora",
           "cuando", "cuándo", "wifi", "puedo", "cual", "cuál"},
    "fr": {"bonjour", "merci", "quelle", "quel", "heure", "où", "comment", "arrivée",
           "clé", "je", "est", "puis", "s'il", "vous", "plaît"},
    "de": {"hallo", "danke", "wann", "wie", "wo", "uhr", "schlüssel", "ankunft",
           "ich", "ist", "kann", "bitte", "wlan", "passwort"},
    "it": {"ciao", "grazie", "quando", "come", "dove", "ora", "chiave", "arrivo",
           "posso", "è", "per", "favore", "qual"},
}
_ES_CHARS = re.compile(r"[¿¡ñ]", re.IGNORECASE)
_WORD = re.compile(r"[a-zàáâäçéèêëíìîïñóòôöúùûü']+", re.IGNORECASE)

# Frases de "aquí tienes la información" por idioma.
_LEAD = {
    "es": "¡Hola! Aquí tienes la información: ",
    "en": "Hi! Here's what you need: ",
    "fr": "Bonjour ! Voici l'information : ",
    "de": "Hallo! Hier die Info: ",
    "it": "Ciao! Ecco l'informazione: ",
}
_WAIT = {
    "es": "Gracias por escribir a {name}. Lo confirmo y te respondo enseguida.",
    "en": "Thanks for reaching out to {name}. I'll check this and get back to you shortly.",
    "fr": "Merci d'avoir contacté {name}. Je vérifie et je vous réponds très vite.",
    "de": "Danke für deine Nachricht an {name}. Ich prüfe das und melde mich gleich.",
    "it": "Grazie per aver scritto a {name}. Verifico e ti rispondo subito.",
}


def detect_language(text: str, default: str = "es") -> str:
    lower = text.lower()
    if _ES_CHARS.search(lower):
        return "es"
    words = set(_WORD.findall(lower))
    scores = {lang: len(words & markers) for lang, markers in _MARKERS.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else default


class MockAI(AIProvider):
    async def generate_reply(self, context: AIContext) -> GeneratedReply:
        language = detect_language(context.guest_text, context.default_language)
        lead = _LEAD.get(language, _LEAD["es"])

        if context.knowledge:
            best = context.knowledge[0]
            confidence = min(0.6 + 0.4 * context.retrieval_score, 0.97)
            text = f"{lead}{best}"
        elif context.stay_context:
            # Sin conocimiento que encaje, pero sabemos de su reserva: la usamos.
            confidence = 0.7
            text = f"{lead}{context.stay_context}"
        else:
            confidence = 0.3
            text = _WAIT.get(language, _WAIT["es"]).format(name=context.property_name)

        return GeneratedReply(text=text, language=language, confidence=confidence, model="mock")
