"""Reservas de los pisos del anfitrión."""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.properties import MAX_IMPORT_BYTES, get_owned_property
from app.db import get_session
from app.deps import get_current_user
from app.models import Property, Reservation, User
from app.schemas import (
    ReservationCreate,
    ReservationImportOut,
    ReservationListItem,
    ReservationOut,
    ReservationUpdate,
)
from app.services.ical import parse_ics

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
        source=data.source,
        code=data.code,
    )
    session.add(reservation)
    await session.commit()
    await session.refresh(reservation)
    return reservation


@router.post(
    "/properties/{property_id}/reservations/import-ics",
    response_model=ReservationImportOut,
    status_code=status.HTTP_201_CREATED,
)
async def import_reservations_ics(
    property_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReservationImportOut:
    """Importa reservas del calendario iCal (.ics) de Booking/Airbnb del anuncio."""
    await get_owned_property(session, property_id, user)
    data = await file.read()
    if len(data) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="El fichero es demasiado grande (máx. 5 MB)")
    source, events = parse_ics(data)
    if not events:
        raise HTTPException(status_code=400, detail="No se encontraron reservas en el calendario")
    for ev in events:
        session.add(
            Reservation(
                property_id=property_id,
                guest_name=ev["guest_name"],
                guest_ref="",  # el iCal no trae teléfono; se añade cuando el huésped escribe
                check_in=ev["check_in"],
                check_out=ev["check_out"],
                source=source,
                code=ev.get("code"),
            )
        )
    await session.commit()
    return ReservationImportOut(imported=len(events), source=source)


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


@router.get("/reservations", response_model=list[ReservationListItem])
async def list_reservations(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ReservationListItem]:
    """Todas las reservas del propietario (de todos sus pisos), con el nombre del piso."""
    result = await session.execute(
        select(Reservation, Property.name)
        .join(Property, Reservation.property_id == Property.id)
        .where(Property.org_id == user.org_id)
        .order_by(Reservation.check_in.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        ReservationListItem(
            **ReservationOut.model_validate(reservation).model_dump(),
            property_name=property_name,
        )
        for reservation, property_name in result.all()
    ]


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
