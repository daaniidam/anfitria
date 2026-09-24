"""Asistente de conexión de WhatsApp Business (guiado): conectar número →
plantillas → asignar a pisos → probar. La verificación con Meta se simula aquí;
en real, se enchufa la Cloud API sin tocar el resto de la lógica."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.properties import get_owned_property
from app.db import get_session
from app.deps import get_current_user, require_owner
from app.models import Integration, Property, User
from app.schemas import WhatsAppAssign, WhatsAppConnect, WhatsAppStatus

router = APIRouter(prefix="/integrations/whatsapp", tags=["whatsapp-setup"])
PROVIDER = "whatsapp"


async def _get(session: AsyncSession, org_id: int | None) -> Integration | None:
    result = await session.execute(
        select(Integration).where(
            Integration.org_id == org_id, Integration.provider == PROVIDER
        )
    )
    return result.scalar_one_or_none()


async def _status(session: AsyncSession, user: User) -> WhatsAppStatus:
    integ = await _get(session, user.org_id)
    connected = integ is not None and integ.status == "connected"
    total = await session.execute(
        select(func.count()).select_from(Property).where(Property.org_id == user.org_id)
    )
    assigned = await session.execute(
        select(func.count())
        .select_from(Property)
        .where(Property.org_id == user.org_id, Property.whatsapp_phone_number_id.isnot(None))
    )
    return WhatsAppStatus(
        connected=connected,
        phone=integ.account if connected else None,
        templates_approved=bool((integ.config or {}).get("templates_approved")) if integ else False,
        pisos_assigned=int(assigned.scalar_one() or 0),
        total_pisos=int(total.scalar_one() or 0),
    )


@router.get("", response_model=WhatsAppStatus)
async def status_(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WhatsAppStatus:
    return await _status(session, user)


@router.post("/connect", response_model=WhatsAppStatus)
async def connect(
    data: WhatsAppConnect,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> WhatsAppStatus:
    # Verificación de Meta simulada: se da por buena y se conecta el número.
    integ = await _get(session, user.org_id)
    if integ is None:
        integ = Integration(org_id=user.org_id, provider=PROVIDER)
        session.add(integ)
    integ.status = "connected"
    integ.account = data.phone
    integ.config = {"business_name": data.business_name, "templates_approved": False}
    await session.commit()
    return await _status(session, user)


@router.post("/templates", response_model=WhatsAppStatus)
async def approve_templates(
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> WhatsAppStatus:
    integ = await _get(session, user.org_id)
    if integ is None or integ.status != "connected":
        raise HTTPException(status_code=400, detail="Conecta el número primero")
    integ.config = {**(integ.config or {}), "templates_approved": True}
    await session.commit()
    return await _status(session, user)


@router.post("/assign", response_model=WhatsAppStatus)
async def assign(
    data: WhatsAppAssign,
    user: User = Depends(require_owner),
    session: AsyncSession = Depends(get_session),
) -> WhatsAppStatus:
    integ = await _get(session, user.org_id)
    if integ is None or integ.status != "connected":
        raise HTTPException(status_code=400, detail="Conecta el número primero")
    if not (integ.config or {}).get("templates_approved"):
        raise HTTPException(status_code=400, detail="Aprueba las plantillas primero")
    prop = await get_owned_property(session, data.property_id, user)
    # Cada piso recibe su propio phone_number_id (numeración por anuncio, lo habitual).
    prop.whatsapp_phone_number_id = f"wa-{prop.id}"
    await session.commit()
    return await _status(session, user)
