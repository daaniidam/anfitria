"""Servicio de aprobación de borradores (respuesta a escaladas)."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.channel.factory import get_channel
from app.adapters.embeddings.factory import get_embedding_provider
from app.models import AuditLog, Conversation, Draft, KnowledgeItem, Message
from app.services.retrieval import _cosine

# Si lo aprendido se parece mucho a algo ya guardado, se actualiza en vez de duplicar.
LEARN_DEDUP_THRESHOLD = 0.9


def _normalize(text: str) -> str:
    """Minúsculas y sin signos, para comparar contra las plantillas de espera."""
    return re.sub(r"[^a-z0-9áéíóúüñ ]", "", text.lower()).strip()


def _holding_signatures() -> set[str]:
    """Fragmentos distintivos de los mensajes de espera (en todos los idiomas).

    Se derivan de las propias plantillas, así que si cambian no hay que tocar esto.
    De cada plantilla con `{name}` se toma el segmento estático más largo (el tramo
    distintivo, no el saludo genérico).
    """
    from app.adapters.ai.mock import _WAIT
    from app.services.conversation import HOLDING

    sigs = {_normalize(t) for t in HOLDING.values()}
    for template in _WAIT.values():
        sigs.add(max((_normalize(p) for p in template.split("{name}")), key=len))
    return {s for s in sigs if s}


def _is_learnable(text: str) -> bool:
    """Los mensajes de espera son relleno de la IA, no respuestas: no se aprenden."""
    norm = _normalize(text)
    if not norm:
        return False
    return not any(sig in norm for sig in _holding_signatures())


async def _dedup_learned(
    session: AsyncSession, property_id: int, embedding: list[float]
) -> KnowledgeItem | None:
    """Devuelve el conocimiento del piso casi idéntico (para actualizar en vez de duplicar)."""
    rows = await session.execute(
        select(KnowledgeItem).where(
            KnowledgeItem.property_id == property_id,
            KnowledgeItem.embedding.isnot(None),
        )
    )
    best: KnowledgeItem | None = None
    best_score = 0.0
    for item in rows.scalars().all():
        score = _cosine(embedding, item.embedding)
        if score > best_score:
            best, best_score = item, score
    return best if best_score >= LEARN_DEDUP_THRESHOLD else None


async def approve_draft(
    session: AsyncSession,
    draft: Draft,
    conversation: Conversation,
    edited_text: str | None = None,
    question: str | None = None,
    save_to_knowledge: bool = False,
) -> Message:
    text = (edited_text if edited_text is not None else draft.text).strip()
    edited = edited_text is not None and text != draft.text.strip()

    channel = get_channel()
    await channel.send(conversation.guest_ref, text)

    outbound = Message(
        conversation_id=conversation.id,
        direction="out",
        text=text,
        language=draft.language,
    )
    session.add(outbound)
    draft.status = "sent"
    session.add(
        AuditLog(
            actor="host",
            action="edited_and_sent" if edited else "approved_and_sent",
            conversation_id=conversation.id,
        )
    )

    # Aprender: guardar pregunta + respuesta como conocimiento del piso para futuras
    # dudas similares. Se guardan JUNTAS para que una respuesta corta ("el 26") siga
    # teniendo sentido al leerla y al recuperarla. Los mensajes de espera no se aprenden.
    if save_to_knowledge and question and _is_learnable(text):
        embedder = get_embedding_provider()
        content = f"{question.strip()} → {text}"
        embedding = embedder.embed([content])[0]
        existing = await _dedup_learned(session, conversation.property_id, embedding)
        if existing is not None:
            # Ya había algo casi idéntico: se actualiza en vez de acumular duplicados.
            existing.content = content
            existing.embedding = embedding
        else:
            session.add(
                KnowledgeItem(
                    property_id=conversation.property_id,
                    category="aprendido",
                    content=content,
                    embedding=embedding,
                )
            )
        session.add(
            AuditLog(actor="host", action="learned", conversation_id=conversation.id)
        )
    elif save_to_knowledge and question:
        # Se pidió guardar pero no es aprendible (p. ej. un mensaje de espera): se omite.
        session.add(
            AuditLog(actor="host", action="learn_skipped", conversation_id=conversation.id)
        )

    await session.commit()
    return outbound
