"""Webhook de WhatsApp (Meta Cloud API): verificación + recepción de mensajes.

GET  /channels/whatsapp/webhook  -> verificación del webhook (hub.challenge).
POST /channels/whatsapp/webhook  -> mensajes entrantes; valida la firma HMAC,
     enruta al piso por su phone_number_id y lanza el flujo de conserje.

Con `PROCESS_ASYNC=true` el trabajo pesado (IA) se encola en el worker (ARQ) y se
responde a Meta al instante; con `false` se procesa en línea (demo/tests).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.channel.factory import get_channel
from app.config import get_settings
from app.db import get_session
from app.models import Message, Property
from app.services.conversation import handle_inbound

logger = logging.getLogger("anfitria.whatsapp")

# Respuesta cuando el huésped manda algo que aún no sabemos leer (imagen, audio…).
_NON_TEXT_REPLY = {
    "es": "¡Gracias por escribir! De momento solo puedo leer mensajes de texto. "
    "¿Puedes contarme tu duda por escrito?",
    "en": "Thanks for reaching out! For now I can only read text messages. "
    "Could you type your question?",
    "fr": "Merci de votre message ! Pour l'instant je ne peux lire que du texte. "
    "Pouvez-vous écrire votre question ?",
    "de": "Danke für deine Nachricht! Momentan kann ich nur Text lesen. "
    "Kannst du deine Frage schreiben?",
    "it": "Grazie per il messaggio! Per ora posso leggere solo testo. "
    "Puoi scrivere la tua domanda?",
}

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
                    # Aún solo entendemos texto; avisamos al huésped en vez de ignorarlo.
                    sender = message.get("from")
                    if sender:
                        note = _NON_TEXT_REPLY.get(
                            property.default_language, _NON_TEXT_REPLY["es"]
                        )
                        try:
                            await get_channel().send(sender, note)
                        except Exception:  # pragma: no cover - no romper por el canal
                            logger.warning("No se pudo avisar de mensaje no-texto", exc_info=True)
                    continue
                sender = message.get("from")
                text = (message.get("text") or {}).get("body")
                external_id = message.get("id")
                if not (sender and text):
                    continue

                # Dedup temprano: si ya procesamos este message id, descartar el reintento.
                if external_id is not None:
                    seen = await session.execute(
                        select(Message.id).where(Message.external_id == external_id)
                    )
                    if seen.scalar_one_or_none() is not None:
                        continue

                if settings.process_async:
                    # Encolar y responder al instante; si Redis no está, procesar en línea.
                    try:
                        from app.queue import enqueue_inbound

                        await enqueue_inbound(property.id, sender, text, external_id)
                        continue
                    except Exception:  # pragma: no cover - fallback si la cola no está
                        logger.warning("No se pudo encolar; se procesa en línea", exc_info=True)
                await handle_inbound(session, property, sender, text, external_id=external_id)

    return {"status": "ok"}
