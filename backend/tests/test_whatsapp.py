"""Tests del canal y webhook de WhatsApp (sin llamadas reales a Meta)."""
import hashlib
import hmac
import json

import app.api.whatsapp as wa
from app.config import Settings
from tests.conftest import register_and_login


def _patch_settings(monkeypatch, **kwargs):
    settings = Settings(**kwargs)
    monkeypatch.setattr(wa, "get_settings", lambda: settings)
    return settings


def test_valid_signature():
    body = b'{"a":1}'
    good = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    assert wa.valid_signature("secret", body, good) is True
    assert wa.valid_signature("secret", body, "sha256=deadbeef") is False
    assert wa.valid_signature(None, body, good) is False
    assert wa.valid_signature("secret", body, None) is False


async def test_webhook_verification(client, monkeypatch):
    _patch_settings(monkeypatch, whatsapp_verify_token="verifyme")
    ok = await client.get(
        "/channels/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "verifyme", "hub.challenge": "42"},
    )
    assert ok.status_code == 200
    assert ok.text == "42"

    bad = await client.get(
        "/channels/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "42"},
    )
    assert bad.status_code == 403


async def test_webhook_receives_and_routes_to_property(client, monkeypatch):
    _patch_settings(monkeypatch, whatsapp_app_secret="topsecret")
    headers = await register_and_login(client, email="wa@test.com")
    resp = await client.post(
        "/properties",
        json={"name": "Piso WA", "default_language": "es", "whatsapp_phone_number_id": "PN123"},
        headers=headers,
    )
    assert resp.json()["whatsapp_phone_number_id"] == "PN123"
    prop_id = resp.json()["id"]
    await client.post(
        f"/properties/{prop_id}/knowledge",
        json={"category": "wifi", "content": "La contraseña del wifi es WA-777."},
        headers=headers,
    )

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "PN123"},
                            "messages": [
                                {"type": "text", "from": "34600111", "text": {"body": "contraseña wifi?"}}
                            ],
                        }
                    }
                ]
            }
        ]
    }
    raw = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(b"topsecret", raw, hashlib.sha256).hexdigest()

    ok = await client.post(
        "/channels/whatsapp/webhook",
        content=raw,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert ok.status_code == 200

    bad = await client.post(
        "/channels/whatsapp/webhook",
        content=raw,
        headers={"X-Hub-Signature-256": "sha256=bad", "Content-Type": "application/json"},
    )
    assert bad.status_code == 403

    convs = await client.get("/conversations", headers=headers)
    assert any(c["guest_ref"] == "34600111" for c in convs.json())


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"messages": [{"id": "wamid.1"}]}


class _FakeHttp:
    def __init__(self):
        self.calls = []

    async def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _FakeResponse()


async def test_whatsapp_channel_send():
    from app.adapters.channel.whatsapp import WhatsAppCloudChannel

    fake = _FakeHttp()
    channel = WhatsAppCloudChannel(client=fake)
    result = await channel.send("34600", "hola mundo")
    assert result["status"] == "sent"
    body = fake.calls[0]["json"]
    assert body["to"] == "34600"
    assert body["text"]["body"] == "hola mundo"
    assert body["messaging_product"] == "whatsapp"
