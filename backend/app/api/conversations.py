"""Conversaciones, entrada del canal simulado, cola de borradores y aprobación."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import Conversation, Draft, Message, Property, User
from app.schemas import (
    ApproveRequest,
    ConversationOut,
    DraftOut,
    InboundMessage,
    InboundResult,
    MessageOut,
)
from app.services.conversation import handle_inbound
from app.services.drafts import approve_draft

router = APIRouter(tags=["conversations"])


async def _owned_conversation(session: AsyncSession, conversation_id: int, user: User) -> Conversation:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    prop = await session.get(Property, conversation.property_id)
    if prop is None or prop.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return conversation


@router.post(
    "/channels/sim/inbound",
    response_model=InboundResult,
    status_code=status.HTTP_201_CREATED,
)
async def sim_inbound(
    data: InboundMessage,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InboundResult:
    prop = await session.get(Property, data.property_id)
    if prop is None or prop.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Piso no encontrado")
    outcome = await handle_inbound(session, prop, data.guest_ref, data.text)
    return InboundResult(
        conversation=ConversationOut.model_validate(outcome.conversation),
        inbound=MessageOut.model_validate(outcome.inbound),
        draft=DraftOut.model_validate(outcome.draft),
        auto_sent=outcome.auto_sent,
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Conversation]:
    result = await session.execute(
        select(Conversation)
        .join(Property, Conversation.property_id == Property.id)
        .where(Property.owner_id == user.id)
        .order_by(Conversation.id)
    )
    return list(result.scalars().all())


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def conversation_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Message]:
    await _owned_conversation(session, conversation_id, user)
    result = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
    )
    return list(result.scalars().all())


@router.get("/drafts", response_model=list[DraftOut])
async def list_drafts(
    status: str = "pending",
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Draft]:
    result = await session.execute(
        select(Draft)
        .join(Message, Draft.inbound_message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Property, Conversation.property_id == Property.id)
        .where(Property.owner_id == user.id, Draft.status == status)
        .order_by(Draft.id)
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
    return await approve_draft(session, draft, conversation, data.edited_text)
