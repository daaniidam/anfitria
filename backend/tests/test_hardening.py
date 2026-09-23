"""Tests de la auditoría: idempotencia, notificaciones, edición/borrado,
auditoría visible, revocación de sesión, límites de entrada y anti-inyección."""
import hashlib
import hmac
import json

import pytest

from tests.conftest import register_and_login


async def _create_property(client, headers, **extra) -> int:
    body = {"name": "Ático Malasaña", "auto_answer": True, **extra}
    resp = await client.post("/properties", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_edit_and_delete_knowledge(client):
    headers = await register_and_login(client)
    pid = await _create_property(client, headers)
    resp = await client.post(
        f"/properties/{pid}/knowledge",
        json={"category": "wifi", "content": "La clave del wifi es CASA-1234."},
        headers=headers,
    )
    item_id = resp.json()["id"]

    # Editar (re-embebe el contenido).
    resp = await client.patch(
        f"/properties/{pid}/knowledge/{item_id}",
        json={"content": "La clave del wifi es SOL-9999."},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "SOL-9999" in resp.json()["content"]

    # Borrar.
    resp = await client.delete(f"/properties/{pid}/knowledge/{item_id}", headers=headers)
    assert resp.status_code == 204
    resp = await client.get(f"/properties/{pid}/knowledge", headers=headers)
    assert resp.json() == []


@pytest.mark.asyncio
async def test_delete_property(client):
    headers = await register_and_login(client)
    pid = await _create_property(client, headers)
    resp = await client.delete(f"/properties/{pid}", headers=headers)
    assert resp.status_code == 204
    resp = await client.get("/properties", headers=headers)
    assert resp.json() == []


@pytest.mark.asyncio
async def test_escalation_creates_notification(client):
    headers = await register_and_login(client)
    pid = await _create_property(client, headers)  # sin conocimiento → la IA escala
    resp = await client.post(
        "/channels/sim/inbound",
        json={"property_id": pid, "guest_ref": "+34600", "text": "¿tenéis cuna?"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["answered"] is False

    resp = await client.get("/notifications", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    resp = await client.get("/notifications/unread-count", headers=headers)
    assert resp.json()["count"] == 1

    nid = (await client.get("/notifications", headers=headers)).json()[0]["id"]
    await client.post(f"/notifications/{nid}/read", headers=headers)
    resp = await client.get("/notifications/unread-count", headers=headers)
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_audit_log_visible(client):
    headers = await register_and_login(client)
    pid = await _create_property(client, headers)
    await client.post(
        "/channels/sim/inbound",
        json={"property_id": pid, "guest_ref": "+34600", "text": "hola"},
        headers=headers,
    )
    resp = await client.get("/audit", headers=headers)
    assert resp.status_code == 200
    actions = {row["action"] for row in resp.json()}
    assert "draft_generated" in actions


@pytest.mark.asyncio
async def test_metrics_has_daily_series(client):
    headers = await register_and_login(client)
    resp = await client.get("/metrics", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["daily"]) == 14


@pytest.mark.asyncio
async def test_logout_revokes_token(client):
    headers = await register_and_login(client)
    resp = await client.post("/auth/logout", headers=headers)
    assert resp.status_code == 204
    # El token anterior (Bearer) queda revocado: token_version incrementado.
    resp = await client.get("/auth/me", headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_input_length_limits(client):
    headers = await register_and_login(client)
    pid = await _create_property(client, headers)
    resp = await client.post(
        f"/properties/{pid}/knowledge",
        json={"category": "wifi", "content": "x" * 5000},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_prompt_injection_guardrail_present():
    from app.adapters.ai.anthropic_ai import _SYSTEM

    assert "NUNCA una" in _SYSTEM or "nunca" in _SYSTEM.lower()
    assert "instrucci" in _SYSTEM.lower()


@pytest.mark.asyncio
async def test_webhook_idempotent(client, monkeypatch):
    """El mismo message id de WhatsApp no se procesa dos veces (reintento de Meta)."""
    import app.config as config_module

    monkeypatch.setenv("WHATSAPP_APP_SECRET", "test-secret")
    monkeypatch.setenv("CHANNEL_PROVIDER", "sim")
    config_module.get_settings.cache_clear()

    headers = await register_and_login(client)
    await _create_property(client, headers, whatsapp_phone_number_id="PN123")

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "PN123"},
                            "messages": [
                                {
                                    "id": "wamid.ABC",
                                    "from": "+34600",
                                    "type": "text",
                                    "text": {"body": "¿a qué hora es el check-in?"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }
    raw = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()
    hdrs = {"X-Hub-Signature-256": sig, "Content-Type": "application/json"}

    r1 = await client.post("/channels/whatsapp/webhook", content=raw, headers=hdrs)
    r2 = await client.post("/channels/whatsapp/webhook", content=raw, headers=hdrs)
    assert r1.status_code == 200 and r2.status_code == 200

    # Solo debe existir UN mensaje entrante pese a los dos webhooks.
    convs = (await client.get("/conversations", headers=headers)).json()
    assert len(convs) == 1
    msgs = (await client.get(f"/conversations/{convs[0]['id']}/messages", headers=headers)).json()
    inbound = [m for m in msgs if m["direction"] == "in"]
    assert len(inbound) == 1

    config_module.get_settings.cache_clear()
