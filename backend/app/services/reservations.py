"""Contexto de reserva para la IA: en qué fase de la estancia está el huésped.

Con esto la IA responde con datos concretos ("tu check-in es mañana a las 15:00")
en vez de en genérico. La fase se calcula de las fechas (fuente de verdad), no del
estado guardado.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Reservation


def stay_phase(check_in: date, check_out: date, today: date | None = None) -> str:
    today = today or date.today()
    if today < check_in:
        return "pre_llegada"
    if today <= check_out:
        return "durante"
    return "pasada"


async def find_reservation(
    session: AsyncSession, property_id: int, guest_ref: str, today: date | None = None
) -> Reservation | None:
    """Reserva relevante del huésped: la actual o la próxima; si no, la última pasada."""
    today = today or date.today()
    rows = await session.execute(
        select(Reservation)
        .where(
            Reservation.property_id == property_id,
            Reservation.guest_ref == guest_ref,
            Reservation.status != "cancelled",
        )
        .order_by(Reservation.check_in)
    )
    reservations = list(rows.scalars().all())
    if not reservations:
        return None
    # Preferir la que cubre hoy o la próxima (check_out >= hoy).
    upcoming = [r for r in reservations if r.check_out >= today]
    if upcoming:
        return upcoming[0]
    return reservations[-1]  # la última pasada


def build_stay_context(reservation: Reservation, today: date | None = None) -> str:
    """Frase de hechos (en español) que la IA usa y traduce al idioma del huésped."""
    today = today or date.today()
    phase = stay_phase(reservation.check_in, reservation.check_out, today)
    ci = reservation.check_in.isoformat()
    co = reservation.check_out.isoformat()
    fase = {
        "pre_llegada": "aún no ha llegado (pre-llegada)",
        "durante": "está alojado ahora mismo",
        "pasada": "la estancia ya terminó",
    }[phase]
    code = f" Código de reserva: {reservation.code}." if reservation.code else ""
    return (
        f"Reserva de {reservation.guest_name}. Entrada (check-in): {ci}. "
        f"Salida (check-out): {co}. Estado hoy: {fase}.{code}"
    )
