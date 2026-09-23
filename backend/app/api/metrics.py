"""Métricas agregadas del anfitrión."""
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import AuditLog, Conversation, Draft, Message, Property, User
from app.schemas import MetricsOut, MetricsPoint

router = APIRouter(tags=["metrics"])

MINUTES_SAVED_PER_ANSWER = 3
TREND_DAYS = 14


async def _daily_series(session: AsyncSession, prop_ids: Select) -> list[MetricsPoint]:
    """Auto-resueltas vs escaladas por día (últimos TREND_DAYS), agregado en Python."""
    since = datetime.now(UTC) - timedelta(days=TREND_DAYS - 1)
    rows = await session.execute(
        select(AuditLog.action, AuditLog.created_at)
        .join(Conversation, AuditLog.conversation_id == Conversation.id)
        .where(
            Conversation.property_id.in_(prop_ids),
            AuditLog.action.in_(["auto_answered", "escalated"]),
            AuditLog.created_at >= since,
        )
    )
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"auto": 0, "esc": 0})
    for action, created_at in rows.all():
        day = created_at.date().isoformat()
        buckets[day]["auto" if action == "auto_answered" else "esc"] += 1

    series: list[MetricsPoint] = []
    start = since.date()
    for i in range(TREND_DAYS):
        day = (start + timedelta(days=i)).isoformat()
        b = buckets.get(day, {"auto": 0, "esc": 0})
        series.append(MetricsPoint(date=day, auto_answered=b["auto"], escalated=b["esc"]))
    return series


async def _count(session: AsyncSession, stmt: Select) -> int:
    return int((await session.execute(stmt)).scalar_one() or 0)


@router.get("/metrics", response_model=MetricsOut)
async def metrics(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MetricsOut:
    prop_ids = select(Property.id).where(Property.owner_id == user.id)

    def _messages(direction: str) -> Select:
        return (
            select(func.count())
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.property_id.in_(prop_ids), Message.direction == direction)
        )

    def _audits(action: str) -> Select:
        return (
            select(func.count())
            .select_from(AuditLog)
            .join(Conversation, AuditLog.conversation_id == Conversation.id)
            .where(Conversation.property_id.in_(prop_ids), AuditLog.action == action)
        )

    properties = await _count(
        session, select(func.count()).select_from(Property).where(Property.owner_id == user.id)
    )
    conversations = await _count(
        session,
        select(func.count()).select_from(Conversation).where(Conversation.property_id.in_(prop_ids)),
    )
    messages_in = await _count(session, _messages("in"))
    messages_out = await _count(session, _messages("out"))
    auto_answered = await _count(session, _audits("auto_answered"))
    escalated = await _count(session, _audits("escalated"))
    pending = await _count(
        session,
        select(func.count())
        .select_from(Draft)
        .join(Message, Draft.inbound_message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.property_id.in_(prop_ids), Draft.status == "pending"),
    )

    handled = auto_answered + escalated
    auto_rate = round(auto_answered / handled, 3) if handled else 0.0
    daily = await _daily_series(session, prop_ids)
    return MetricsOut(
        properties=properties,
        conversations=conversations,
        messages_in=messages_in,
        messages_out=messages_out,
        auto_answered=auto_answered,
        escalated=escalated,
        pending=pending,
        auto_rate=auto_rate,
        minutes_saved=auto_answered * MINUTES_SAVED_PER_ANSWER,
        daily=daily,
    )
