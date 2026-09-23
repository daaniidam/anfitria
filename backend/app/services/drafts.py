"""Servicio de aprobación de borradores (respuesta a escaladas)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.channel.factory import get_channel
from app.adapters.embeddings.factory import get_embedding_provider
from app.models import AuditLog, Conversation, Draft, KnowledgeItem, Message


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
        # Se indexa con la pregunta + la respuesta para que la próxima pregunta similar la encuentre.
        embedding = embedder.embed([f"{question}\n{text}"])[0]
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
