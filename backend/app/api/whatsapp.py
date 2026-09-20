"""Webhook de WhatsApp (Meta Cloud API): verificación + recepción de mensajes.

GET  /channels/whatsapp/webhook  -> verificación del webhook (hub.challenge).
POST /channels/whatsapp/webhook  -> mensajes entrantes; valida la firma HMAC,
     enruta al piso por su phone_number_id y lanza el flujo de conserje.

En producción, el procesamiento pesado (IA) se movería al worker (ARQ) para
responder al webhook al instante; aquí se hace en línea por simplicidad.
"""
from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Property
from app.services.conversation import handle_inbound

router = APIRouter(prefix="/channels/whatsapp", tags=["whatsapp"])


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    settings = get_settings()
    if (
        hub_mode == "subscribe"
        and settings.whatsapp_verify_token
        and hub_verify_token == settings.whatsapp_verify_token
    ):
        return Response(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verificación fallida")


def valid_signature(app_secret: str | None, raw_body: bytes, signature_header: str | None) -> bool:
    if not app_secret or not signature_header:
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    settings = get_settings()
    raw = await request.body()
    if not valid_signature(
        settings.whatsapp_app_secret, raw, request.headers.get("X-Hub-Signature-256")
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Firma inválida")

    data = json.loads(raw or b"{}")
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            if not phone_number_id:
                continue
            result = await session.execute(
                select(Property).where(Property.whatsapp_phone_number_id == phone_number_id)
            )
            property = result.scalar_one_or_none()
            if property is None:
                continue  # número no asignado a ningún piso
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                sender = message.get("from")
                text = (message.get("text") or {}).get("body")
                if sender and text:
                    await handle_inbound(session, property, sender, text)

    return {"status": "ok"}
