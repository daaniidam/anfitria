"""Reservas de los pisos del anfitrión."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.properties import get_owned_property
from app.db import get_session
from app.deps import get_current_user
from app.models import Property, Reservation, User
from app.schemas import ReservationCreate, ReservationOut, ReservationUpdate

router = APIRouter(tags=["reservations"])


async def _owned_reservation(session: AsyncSession, reservation_id: int, user: User) -> Reservation:
    reservation = await session.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    await get_owned_property(session, reservation.property_id, user)
    return reservation


@router.post(
    "/properties/{property_id}/reservations",
    response_model=ReservationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation(
    property_id: int,
    data: ReservationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Reservation:
    await get_owned_property(session, property_id, user)
    if data.check_out < data.check_in:
        raise HTTPException(status_code=400, detail="La salida no puede ser antes de la entrada")
    reservation = Reservation(
        property_id=property_id,
        guest_name=data.guest_name,
        guest_ref=data.guest_ref,
        check_in=data.check_in,
        check_out=data.check_out,
        code=data.code,
    )
    session.add(reservation)
    await session.commit()
    await session.refresh(reservation)
    return reservation


@router.get("/properties/{property_id}/reservations", response_model=list[ReservationOut])
async def list_property_reservations(
    property_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Reservation]:
    await get_owned_property(session, property_id, user)
    result = await session.execute(
        select(Reservation)
        .where(Reservation.property_id == property_id)
        .order_by(Reservation.check_in.desc())
    )
    return list(result.scalars().all())


@router.get("/reservations", response_model=list[ReservationOut])
async def list_reservations(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Reservation]:
    prop_ids = select(Property.id).where(Property.owner_id == user.id)
    result = await session.execute(
        select(Reservation)
        .where(Reservation.property_id.in_(prop_ids))
        .order_by(Reservation.check_in.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.patch("/reservations/{reservation_id}", response_model=ReservationOut)
async def update_reservation(
    reservation_id: int,
    data: ReservationUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Reservation:
    reservation = await _owned_reservation(session, reservation_id, user)
    for field_name, value in data.model_dump(exclude_unset=True).items():
        setattr(reservation, field_name, value)
    if reservation.check_out < reservation.check_in:
        raise HTTPException(status_code=400, detail="La salida no puede ser antes de la entrada")
    await session.commit()
    await session.refresh(reservation)
    return reservation


@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reservation(
    reservation_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    reservation = await _owned_reservation(session, reservation_id, user)
    await session.delete(reservation)
    await session.commit()
