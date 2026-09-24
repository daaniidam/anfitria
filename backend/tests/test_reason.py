"""Tests del '¿por qué escaló?' (motivo) y del umbral de sensibilidad por piso."""
import pytest

from tests.conftest import register_and_login


async def _prop(client, headers, **extra):
    body = {"name": "Piso", "auto_answer": True, **extra}
    return (await client.post("/properties", json=body, headers=headers)).json()["id"]


async def _inbound(client, headers, pid, text, guest="+34600"):
    return await client.post(
        "/channels/sim/inbound",
        json={"property_id": pid, "guest_ref": guest, "text": text},
        headers=headers,
    )


async def _last_reason(client, headers):
    inbox = (await client.get("/inbox", headers=headers)).json()
    return inbox[0]["draft"]["reason"]


@pytest.mark.asyncio
async def test_reason_sin_info(client):
    headers = await register_and_login(client, email="r1@test.com")
    pid = await _prop(client, headers)  # sin conocimiento
    r = await _inbound(client, headers, pid, "¿hay piscina?")
    assert r.json()["answered"] is False
    assert await _last_reason(client, headers) == "sin_info"


@pytest.mark.asyncio
async def test_reason_poca_confianza(client):
    headers = await register_and_login(client, email="r2@test.com")
    pid = await _prop(client, headers)
    await client.post(
        f"/properties/{pid}/knowledge",
        json={"category": "check-in", "content": "El check-in es a las 15:00"},
        headers=headers,
    )
    # Hay ficha, pero la pregunta no encaja → escala por poca confianza.
    await _inbound(client, headers, pid, "¿hay piscina climatizada?")
    assert await _last_reason(client, headers) == "poca_confianza"


@pytest.mark.asyncio
async def test_reason_manual(client):
    headers = await register_and_login(client, email="r3@test.com")
    pid = await _prop(client, headers, auto_answer=False)
    await _inbound(client, headers, pid, "hola")
    assert await _last_reason(client, headers) == "manual"


@pytest.mark.asyncio
async def test_per_property_threshold(client):
    headers = await register_and_login(client, email="r4@test.com")
    pid = await _prop(client, headers, auto_answer_threshold=0.99)
    await client.post(
        f"/properties/{pid}/knowledge",
        json={"category": "wifi", "content": "La contraseña del wifi es CASA-1234"},
        headers=headers,
    )
    # Umbral altísimo: aunque encuentre el wifi, no llega → escala.
    r = await _inbound(client, headers, pid, "¿cuál es la contraseña del wifi?", guest="+34601")
    assert r.json()["answered"] is False

    # Bajamos el umbral (PATCH) → ahora responde sola.
    patch = await client.patch(
        f"/properties/{pid}", json={"auto_answer_threshold": 0.1}, headers=headers
    )
    assert patch.status_code == 200
    assert patch.json()["auto_answer_threshold"] == 0.1
    r = await _inbound(client, headers, pid, "¿cuál es la contraseña del wifi?", guest="+34602")
    assert r.json()["answered"] is True
