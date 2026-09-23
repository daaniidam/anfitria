"""Servicio de aprobación de borradores (respuesta a escaladas)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.channel.factory import get_channel
from app.adapters.embeddings.factory import get_embedding_provider
from app.models import AuditLog, Conversation, Draft, KnowledgeItem, Message
from app.services.retrieval import _cosine

# Si lo aprendido se parece mucho a algo ya guardado, se actualiza en vez de duplicar.
LEARN_DEDUP_THRESHOLD = 0.9


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

    # Aprender: guardar la respuesta como conocimiento del piso para futuras dudas idénticas.
    if save_to_knowledge and question:
        embedder = get_embedding_provider()
        # Se indexa con pregunta + respuesta para que la próxima duda similar la encuentre.
        embedding = embedder.embed([f"{question}\n{text}"])[0]
        existing = await _dedup_learned(session, conversation.property_id, embedding)
        if existing is not None:
            # Ya había algo casi idéntico: se actualiza en vez de acumular duplicados.
            existing.content = text
            existing.embedding = embedding
        else:
            session.add(
                KnowledgeItem(
                    property_id=conversation.property_id,
                    category="aprendido",
                    content=text,
                    embedding=embedding,
                )
            )
        session.add(
            AuditLog(actor="host", action="learned", conversation_id=conversation.id)
        )

    await session.commit()
    return outbound
