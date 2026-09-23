"""Avisos al anfitrión (escaladas), para no depender de estar mirando el panel."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import Notification, User
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    only_unread: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Notification]:
    stmt = select(Notification).where(Notification.org_id == user.org_id)
    if only_unread:
        stmt = stmt.where(Notification.read.is_(False))
    stmt = stmt.order_by(Notification.id.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    count = await session.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.org_id == user.org_id, Notification.read.is_(False))
    )
    return {"count": int(count.scalar_one() or 0)}


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    notification.read = True
    await session.commit()


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await session.execute(
        update(Notification)
        .where(Notification.org_id == user.org_id, Notification.read.is_(False))
        .values(read=True)
    )
    await session.commit()
