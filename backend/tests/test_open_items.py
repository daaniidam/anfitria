"""Tests de los puntos que quedaban abiertos: CSRF, rotación de refresh, dedup
del conocimiento aprendido y aviso ante mensajes no-texto de WhatsApp."""
import hashlib
import hmac
import json

import pytest

from tests.conftest import register_and_login


async def _register_login_cookies(client, email="cookie@test.com"):
    await client.post(
        "/auth/register", json={"email": email, "name": "Host", "password": "secret123"}
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    assert resp.status_code == 200
    return resp


@pytest.mark.asyncio
async def test_csrf_required_for_cookie_mutations(client):
    await _register_login_cookies(client)
    # Autenticado por cookie y sin cabecera CSRF -> rechazado.
    resp = await client.post("/properties", json={"name": "Piso", "default_language": "es"})
    assert resp.status_code == 403

    # Con la cabecera X-CSRF-Token (double-submit) -> aceptado.
    csrf = client.cookies.get("csrf_token")
    resp = await client.post(
        "/properties",
        json={"name": "Piso", "default_language": "es"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_refresh_token_rotation(client):
    await _register_login_cookies(client, email="rotate@test.com")
    old_refresh = client.cookies.get("refresh_token")

    # Primer refresh: rota el token (nuevo jti).
    resp = await client.post("/auth/refresh")
    assert resp.status_code == 200

    # Reusar el refresh viejo (ya rotado) queda invalidado.
    client.cookies.set("refresh_token", old_refresh)
    resp = await client.post("/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_learned_knowledge_is_deduplicated(client):
    headers = await register_and_login(client, email="dedup@test.com")  # Bearer -> sin CSRF
    pid = (
        await client.post(
            "/properties", json={"name": "Piso", "auto_answer": True}, headers=headers
        )
    ).json()["id"]

    q = "¿se admiten mascotas?"
    for guest in ("+34600", "+34601"):
        await client.post(
            "/channels/sim/inbound",
            json={"property_id": pid, "guest_ref": guest, "text": q},
            headers=headers,
        )
    inbox = (await client.get("/inbox", headers=headers)).json()
    assert len(inbox) == 2

    for item in inbox:
        await client.post(
            f"/drafts/{item['draft']['id']}/approve",
            json={"edited_text": "Sí, mascotas pequeñas.", "save_to_knowledge": True},
            headers=headers,
        )

    knowledge = (await client.get(f"/properties/{pid}/knowledge", headers=headers)).json()
    learned = [k for k in knowledge if k["category"] == "aprendido"]
    assert len(learned) == 1  # el segundo actualizó al primero, no duplicó


@pytest.mark.asyncio
async def test_webhook_non_text_does_not_create_conversation(client, monkeypatch):
    import app.config as config_module

    monkeypatch.setenv("WHATSAPP_APP_SECRET", "test-secret")
    config_module.get_settings.cache_clear()

    headers = await register_and_login(client, email="nontext@test.com")
    await client.post(
        "/properties",
        json={"name": "Piso", "whatsapp_phone_number_id": "PN9"},
        headers=headers,
    )

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "PN9"},
                            "messages": [{"id": "wamid.IMG", "from": "+34600", "type": "image"}],
                        }
                    }
                ]
            }
        ]
    }
    raw = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()
    resp = await client.post(
        "/channels/whatsapp/webhook",
        content=raw,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    # No se procesa como conversación (solo se avisa por el canal).
    assert (await client.get("/conversations", headers=headers)).json() == []
    config_module.get_settings.cache_clear()
