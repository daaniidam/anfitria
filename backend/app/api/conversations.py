"""Conversaciones, entrada del canal simulado, cola de borradores y aprobación."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.channel.factory import get_channel
from app.db import get_session
from app.deps import get_current_user
from app.models import AuditLog, Conversation, Draft, Message, Property, User
from app.ratelimit import limiter
from app.schemas import (
    ApproveRequest,
    ConversationOut,
    DraftOut,
    InboundMessage,
    InboundResult,
    InboxItem,
    LiveReplyRequest,
    MessageOut,
)
from app.services.conversation import handle_inbound
from app.services.drafts import approve_draft

router = APIRouter(tags=["conversations"])


async def _owned_conversation(
    session: AsyncSession, conversation_id: int, user: User
) -> Conversation:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    prop = await session.get(Property, conversation.property_id)
    if prop is None or prop.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return conversation


@router.post(
    "/channels/sim/inbound",
    response_model=InboundResult,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def sim_inbound(
    request: Request,
    data: InboundMessage,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InboundResult:
    prop = await session.get(Property, data.property_id)
    if prop is None or prop.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Piso no encontrado")
    outcome = await handle_inbound(session, prop, data.guest_ref, data.text)
    return InboundResult(
        conversation=ConversationOut.model_validate(outcome.conversation),
        inbound=MessageOut.model_validate(outcome.inbound),
        draft=DraftOut.model_validate(outcome.draft) if outcome.draft else None,
        answered=outcome.answered,
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Conversation]:
    result = await session.execute(
        select(Conversation)
        .join(Property, Conversation.property_id == Property.id)
        .where(Property.org_id == user.org_id)
        .order_by(Conversation.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def conversation_messages(
    conversation_id: int,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Message]:
    await _owned_conversation(session, conversation_id, user)
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.get("/inbox", response_model=list[InboxItem])
async def inbox(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[InboxItem]:
    result = await session.execute(
        select(
            Draft,
            Message.text,
            Conversation.id,
            Conversation.guest_ref,
            Property.id,
            Property.name,
        )
        .join(Message, Draft.inbound_message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Property, Conversation.property_id == Property.id)
        .where(Property.org_id == user.org_id, Draft.status == "pending")
        .order_by(Draft.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        InboxItem(
            draft=DraftOut.model_validate(draft),
            inbound_text=inbound_text,
            conversation_id=conversation_id,
            guest_ref=guest_ref,
            property_id=property_id,
            property_name=property_name,
        )
        for draft, inbound_text, conversation_id, guest_ref, property_id, property_name in (
            result.all()
        )
    ]


@router.get("/drafts", response_model=list[DraftOut])
async def list_drafts(
    status: str = "pending",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Draft]:
    result = await session.execute(
        select(Draft)
        .join(Message, Draft.inbound_message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Property, Conversation.property_id == Property.id)
        .where(Property.org_id == user.org_id, Draft.status == status)
        .order_by(Draft.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.post(
    "/drafts/{draft_id}/approve",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def approve(
    draft_id: int,
    data: ApproveRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Message:
    draft = await session.get(Draft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")
    inbound = await session.get(Message, draft.inbound_message_id)
    conversation = await _owned_conversation(session, inbound.conversation_id, user)
    if draft.status == "sent":
        raise HTTPException(status_code=400, detail="El borrador ya fue enviado")
    return await approve_draft(
        session,
        draft,
        conversation,
        edited_text=data.edited_text,
        question=inbound.text,
        save_to_knowledge=data.save_to_knowledge,
    )


@router.post("/conversations/{conversation_id}/takeover", response_model=ConversationOut)
async def takeover(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Conversation:
    """El anfitrión toma el control: la IA se aparta y responde una persona en vivo."""
    conversation = await _owned_conversation(session, conversation_id, user)
    conversation.handoff = True
    conversation.assigned_to = user.id
    session.add(
        AuditLog(actor="host", action="handoff_started", conversation_id=conversation.id)
    )
    await session.commit()
    await session.refresh(conversation)
    return conversation


@router.post("/conversations/{conversation_id}/release", response_model=ConversationOut)
async def release(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Conversation:
    """Devuelve la conversación a la IA."""
    conversation = await _owned_conversation(session, conversation_id, user)
    conversation.handoff = False
    conversation.assigned_to = None
    session.add(
        AuditLog(actor="host", action="handoff_ended", conversation_id=conversation.id)
    )
    await session.commit()
    await session.refresh(conversation)
    return conversation


@router.post(
    "/conversations/{conversation_id}/reply",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def live_reply(
    conversation_id: int,
    data: LiveReplyRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Message:
    """El anfitrión escribe directamente al huésped (atención en vivo)."""
    conversation = await _owned_conversation(session, conversation_id, user)
    await get_channel().send(conversation.guest_ref, data.text)
    outbound = Message(
        conversation_id=conversation.id,
        direction="out",
        text=data.text,
        language="es",
    )
    session.add(outbound)
    session.add(
        AuditLog(actor="host", action="host_replied_live", conversation_id=conversation.id)
    )
    await session.commit()
    await session.refresh(outbound)
    return outbound
